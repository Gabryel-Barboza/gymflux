# GymFlow — Sistema de Gestão para Academias (Henry 7x)

> Substituto open-source moderno para controle de acesso, cadastro de alunos, planos, pagamentos e biometria com **catracas Henry 7x**.

![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20(dev)-lightgrey)
![License](https://img.shields.io/badge/license-Apache--2.0-green)
![Status](https://img.shields.io/badge/status-bootstrap-yellow)

## Por que Python?

O autor é especialista em Python. C#/.NET teria integração nativa ligeiramente melhor com `kernel7x.dll` 32-bit, mas Python resolve o problema com `ctypes.WinDLL` + build 32-bit via PyInstaller, mantendo velocidade de desenvolvimento, ecossistema de dados e portabilidade Linux para dev.

**Veredicto:** Sim, Python é a melhor escolha **para este contexto**. Restrição crítica: o executável final **deve** ser compilado com **Python 32-bit em Windows** para carregar `kernel7x.dll`. Em Linux usamos mocks (ver `docs/ARCHITECTURE.md`).

Ver `docs/DECISIONS.md` ADR-001 para análise completa.

## Quickstart (Linux dev)

```bash
# 1. Pré-requisitos
# uv instalado: https://docs.astral.sh/uv/getting-started/installation/
# python 3.11 gerenciado pelo uv (pinado em .python-version)

# 2. Instalar deps
uv sync --group dev

# 3. Testes / lint
uv run pytest
uv run ruff check src tests
uv run ruff format src tests
uv run mypy src

# 4. Rodar CLI
uv run gymflow --help
uv run gymflow mock-demo  # demonstra hardware mockado

# 5. Inspecionar DLL (quando disponível)
uv run python scripts/inspect_dll.py --help
uv run python scripts/inspect_dll.py vendor/kernel7x.dll
```

## Quickstart (Windows prod / teste real)

```powershell
# PowerShell — DEVE ser Python 32-bit!
python -c "import struct; print(struct.calcsize('P')*8)"  # deve imprimir 32
uv sync --group dev --python 3.11
$env:GYMFLOW_HENRY_MOCK="0"
uv run gymflow catraca status
.\vendor\kernel7x.dll  # colocar ao lado do .exe após build
```

## Estrutura

```
src/gymflow/       # pacote único (v1 sem legado)
├── config/        # pydantic-settings, .env (GYMFLOW_*)
├── core/          # domínio puro (aluno, plano, pagamento, acesso)
├── hardware/
│   ├── henry7x/   # interface.py (ABC) + mock.py + real.py (COM pywin32 32-bit)
│   └── biometric/ # abstração biometria
├── infra/         # sqlalchemy models, repositories, alembic
├── services/      # casos de uso (LiberarAcessoService etc)
└── ui/            # PySide6 (Fase 4)
docs/              # documentações (ignorado no git, ver .gitignore)
scripts/           # inspect_dll.py
tests/             # pytest
```

Ver `docs/ARCHITECTURE.md` para diagrama completo.

## Funcionalidades (roadmap)

- [x] Fase 0: Bootstrap + docs + mock hardware
- [ ] Fase 1: Domínio (aluno, plano, pagamento) + regras de acesso
- [ ] Fase 2: Persistência SQLite + Alembic
- [ ] Fase 3: Integração real `kernel7x.dll` + testes em VM Windows 32-bit
- [ ] Fase 4: UI PySide6 (cadastro, dashboard catraca, relatórios)
- [ ] Fase 5: Biometria, QR, instalador Inno Setup

Ver `docs/ROADMAP.md` detalhado.

## Contrato Henry 7x

A catraca Henry 7x expõe `kernel7x.dll` (32-bit, **COM** `Henry.Kernel7x`, não stdcall plana). Toda comunicação passa por `src/gymflow/hardware/henry7x/interface.py`.

- **Dev Linux:** `MockHenry7x` simula liberação/bloqueio, timeout, eventos.
- **Prod Windows (32-bit):** `RealHenry7x` via `win32com.client.Dispatch("Henry.Kernel7x")` (pywin32, serial `SComConfig` + `AdicionaCard`).

Para mapear a DLL, cole o dump PowerShell em `docs/DLL_CONTRACT.md` ou rode:

```bash
# Linux (pefile + strings)
uv run python scripts/inspect_dll.py vendor/kernel7x.dll --dump --output dumps/kernel7x.txt

# Windows (PowerShell)
[Reflection.Assembly]::LoadFile(".\kernel7x.dll") # ou use dumpbin
dumpbin /exports kernel7x.dll
```

Ver `docs/DLL_CONTRACT.md` para template e extração avançada.

## Licença

Apache-2.0 — ver `LICENSE`. Permissiva com grant de patentes, permite uso comercial por academias/fornecedores, sem obrigar liberação de forks fechados (ver `docs/DECISIONS.md` ADR-004 — MIT descartado, GPLv3 avaliado).

## Documentação

- [Arquitetura](docs/ARCHITECTURE.md)
- [Requisitos](docs/REQUIREMENTS.md)
- [Contrato DLL Henry 7x](docs/DLL_CONTRACT.md)
- [Decisões (ADRs)](docs/DECISIONS.md)
- [Roadmap](docs/ROADMAP.md)
- [Memória do agente](AGENTS.md)

## Contribuindo

```bash
uv sync --group dev
uv run ruff check src tests
uv run mypy src
uv run pytest
```

Commits em português ou inglês, conventional commits preferido (`feat:`, `fix:`, `docs:`).

## Aviso Legal

Este projeto **não** contém código do SCA e não é afiliado à Henry. `kernel7x.dll` é propriedade da Henry Equipamentos Eletrônicos Ltda. e não é distribuída neste repositório. O usuário deve possuir licença válida do hardware.
