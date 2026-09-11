# Arquitetura — GMS

## 1. Princípios

1. **Domínio isolado:** `core` e `services` não importam `ctypes`, `PySide6`, `sqlalchemy` diretamente (via protocolos/repos).
2. **Hardware como detalhe:** toda catraca/biometria atrás de `hardware/*/interface.py` (ABC). Mock e Real implementam o mesmo contrato.
3. **Mock-first:** Linux dev nunca precisa de Windows/DLL. CI Windows valida o real.
4. **Src-layout + uv:** `src/gms_app`, build `uv_build`, Python 3.11 pinado.
5. **SOLID + Clean-ish:** camadas concêntricas leves, sem over-engineering para academia de bairro.

## 2. Diagrama de Camadas

```
┌─────────────────────────────────────────────┐
│  ui/  (PySide6 - Fase 4)                    │  ← depende de services, nunca de hardware/infra direto
├─────────────────────────────────────────────┤
│  services/  (casos de uso)                  │  ← orquestra core + ports
│   LiberarAcessoService, CadastrarAluno...   │
├─────────────────────────────────────────────┤
│  core/  (domínio puro, sem I/O)             │  ← entidades, value objects, regras
│   Aluno, Plano, Pagamento, RegraAcesso      │
├─────────────────────────────────────────────┤
│  ports (interfaces)                         │  ← hardware/henry7x/interface.py
│   Henry7xDriver (ABC)                       │
├───────────┬──────────────┬──────────────────┤
│ hardware/ │    infra/    │     config/      │  ← adapters / detalhes
│ mock/real │ sqlalchemy   │  pydantic-settings
└───────────┴──────────────┴──────────────────┘
```

Fluxo de acesso:

```
[Catraca] --evento--> Hardware.Henry7xDriver --callback--> Services.LiberarAcessoService --consulta--> Core.RegraAcesso --decide--> Hardware.liberar() + infra.log
                                      ^                           |
                                      | mock em Linux             v
                                      └─────────── SQLite (infra)
```

## 3. Estrutura de Pastas (alvo)

```
src/gms_app/
├── __init__.py
├── __main__.py          # entry point `gms`
├── config/
│   ├── settings.py      # pydantic_settings.BaseSettings + .env
│   └── constants.py
├── core/
│   ├── aluno.py         # Aluno, StatusAluno
│   ├── plano.py         # Plano, Vigencia
│   ├── pagamento.py     # Pagamento, StatusPagamento
│   ├── acesso.py        # TentativaAcesso, ResultadoAcesso
│   └── regras.py        # RegraAcesso. pode_acessar(aluno) -> bool + motivo
├── hardware/
│   ├── henry7x/
│   │   ├── interface.py # Henry7xDriver ABC
│   │   ├── mock.py      # MockHenry7x (simula giro, timeout, biometria)
│   │   ├── real.py      # RealHenry7x (ctypes.WinDLL, 32-bit, Windows-only)
│   │   └── factory.py   # get_henry_driver() -> decide mock/real por env + platform
│   └── biometric/
│       ├── interface.py
│       └── mock.py
├── infra/
│   ├── db.py            # engine, sessionmaker, Base
│   ├── models/          # sqlalchemy ORM (AlunoModel etc)
│   ├── repositories/    # AlunoRepo, AcessoRepo
│   └── migrations/      # alembic (gerado via `alembic init`)
├── services/
│   ├── cadastrar_aluno.py
│   ├── liberar_acesso.py
│   └── registrar_pagamento.py
└── ui/
    ├── app.py           # QApplication
    ├── views/
    └── viewmodels/
tests/
├── core/
├── hardware/
├── services/
└── infra/
scripts/
├── inspect_dll.py
vendor/                 # NÃO versionado — colocar kernel7x.dll aqui localmente
dumps/                  # saída de inspect_dll.py
```

## 4. Contratos Críticos

### 4.1 Henry7xDriver (interface.py)

```python
from abc import ABC, abstractmethod
from enum import Enum

class Direcao(Enum): ENTRADA = 1; SAIDA = 2
class ResultadoCatraca(Enum): LIBERADO = 1; BLOQUEADO = 2; TIMEOUT = 3

class Henry7xDriver(ABC):
    @abstractmethod
    def conectar(self, porta: str | int, timeout_ms: int = 5000) -> bool: ...
    @abstractmethod
    def desconectar(self) -> None: ...
    @abstractmethod
    def liberar(self, direcao: Direcao) -> ResultadoCatraca: ...
    @abstractmethod
    def bloquear(self) -> None: ...
    @abstractmethod
    def on_giro(self, callback): ...  # evento de giro da catraca
    @abstractmethod
    def status(self) -> dict: ...  # saúde, firmware, etc
```

- `mock.py`: simula sem DLL, gera eventos fake via `threading.Timer`.
- `real.py`: carrega `kernel7x.dll` via `ctypes.WinDLL` (stdcall). Deve falhar com `RuntimeError` em Linux/Mac ou Python 64-bit se a DLL for 32-bit.

### 4.2 Factory

```python
def get_henry_driver() -> Henry7xDriver:
    if os.getenv("GMS_HENRY_MOCK") == "1" or sys.platform != "win32":
        return MockHenry7x()
    # opcional: checar 32-bit
    if struct.calcsize("P")*8 != 32:
        raise RuntimeError("kernel7x.dll requer Python 32-bit")
    return RealHenry7x("kernel7x.dll")
```

## 5. Banco de Dados

- **Motor:** SQLite arquivo `data/gms.db` (configurável via `GMS_DB_URL`).
- **ORM:** SQLAlchemy 2.0 (Typed, `Mapped[]`), Alembic para migrações.
- **Modelos iniciais:** `aluno`, `plano`, `matricula`, `pagamento`, `acesso_log`.
- **Migrações:** `uv run alembic upgrade head` (a criar na Fase 2).

Alternativa futura: Postgres via `GMS_DB_URL=postgresql+psycopg://...` sem mudar repos.

## 6. Configuração

`pydantic-settings`:

```python
class Settings(BaseSettings):
    henry_mock: bool = True
    henry_dll_path: str = "vendor/kernel7x.dll"
    db_url: str = "sqlite:///data/gms.db"
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_prefix="GMS_", env_file=".env")
```

## 7. UI (Fase 4)

- **Framework:** PySide6 (Qt6, LGPL) — QMainWindow, QTableView, QDialog para CRUD aluno, dashboard catraca com status em tempo real via signals.
- **Isolamento:** UI chama `services/*`, nunca `hardware` direto. Sinais da catraca chegam via `QObject` wrapper que adapta `Henry7xDriver.on_giro`.
- **Alternativa provisória (Fase 1-2):** CLI `gms` com `argparse` + `rich` para tabelas, útil para testes em Linux.

## 8. Empacotamento

- **PyInstaller:** `pyinstaller --onefile --windowed --name GMS --icon assets/icon.ico src/gms_app/__main__.py` — **deve ser executado em Windows com Python 32-bit**.
- **Inno Setup:** script `installer/gms.iss` gera `GMS-Setup-0.1.0.exe` que instala em `C:\Program Files\GMS\` + coloca `kernel7x.dll` + `VC++ redist` se necessário.
- **Assinatura:** signtool com certificado A1/A3 (Fase 5).

## 9. Cross-Platform e 32-bit

| Cenário | Comportamento |
|---------|---------------|
| Linux + Python 64-bit (dev) | `factory` retorna `MockHenry7x` sempre. `RealHenry7x` levanta `RuntimeError` se importado. |
| Windows + Python 64-bit | Alerta + força mock ou falha explícita (DLL 32-bit não carrega em processo 64-bit). |
| Windows + Python 32-bit | `RealHenry7x` carrega `kernel7x.dll` via `WinDLL`. |

Detecção:

```python
import struct, sys
is_32 = struct.calcsize("P")*8 == 32
is_win = sys.platform == "win32"
```

CI sugerido: GitHub Actions matrix com `windows-latest` + `architecture: x86` (Python 3.11 32-bit).

## 10. Observabilidade

- `loguru` para logs (arquivo rotativo `logs/gms.log` + console).
- `acesso_log` tabela audita toda tentativa (aluno_id, timestamp, resultado, motivo, direcao).

## 11. Segurança

- Biometria: templates nunca em claro; hash/armazenamento via abstração `biometric` (Henry SDK ou hash local).
- Senhas (operador recepção): `bcrypt`/`argon2` futuro.
- `kernel7x.dll` não versionada; cada academia usa sua licença Henry.

---
Próximo passo: preencher `hardware/henry7x/interface.py` e `mock.py` na Fase 1, e `real.py` após receber `DLL_CONTRACT.md` completo.
