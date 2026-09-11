# AGENTS.md — Memória Operacional do Projeto GymFlow (ex-GMS)

> Este arquivo é a fonte de verdade para qualquer agente/LLM que retomar o projeto.
> Leia-o **inteiro** no início de cada sessão. Atualize-o ao final de cada marco.

## 1. O que é o GymFlow

**GymFlow** (ex-GMS) — nome escolhido em 2026-09-11 (evita marca Henry, ver `docs/DECISIONS.md` ADR-007). Sugestões descartadas: `IronGate`, `FitCatraca`, `TitanGym`, `HenryFlow` (risco marca Henry).
Substituto open-source para controle de catracas **Henry 7x** em academias Windows.

- **Objetivo final:** executável/instalador Windows (.exe/.msi via Inno Setup) que roda em recepção, gerencia alunos, planos, pagamentos e libera/bloqueia catraca por biometria/cartão/teclado.
- **Inspiração SCA:** apenas domínio, não copiar código. Código 100% próprio, licença a definir Apache-2.0 vs GPL (ver `LICENSE` + ADR-004).
- **Restrição crítica:** `kernel7x.dll` é **COM 32-bit** (`DllRegisterServer`, não exports planos). Build produção **deve** ser Python 32-bit + `pywin32` COM (`win32com.client.Dispatch("Henry.Kernel7x")`) em Windows 10/11 64-bit (WOW64). Dev Linux = mockado.
- **Conexão:** Serial (COMx via `SComConfig` + `AdicionaCard`/`ListaPortasSeriais`), não TCP.

## 2. Ambiente e Convenções Atuais

| Item | Valor |
|------|-------|
| Linguagem | Python 3.11 (pinado em `.python-version`, `requires-python >=3.11,<3.13`) |
| Gerenciador | `uv` (NUNCA pip/poetry/conda) |
| Estrutura | `src/gms_app` (src-layout), `uv_build` |
| SO dev | Linux x86_64 (você está aqui) |
| SO prod | Windows 10/11 64-bit rodando app 32-bit |
| DB local | SQLite + SQLAlchemy 2.0 + Alembic (Postgres futuro opcional) |
| UI planejada | PySide6 (Qt6, LGPL) — Fase 1: CLI/Service, Fase 2: Desktop |
| Empacotamento | PyInstaller (32-bit Windows) + Inno Setup |
| Lint/Teste | ruff, mypy, pytest, loguru |

### Comandos canônicos

```bash
uv sync --group dev          # instala deps
uv run pytest                # testes
uv run ruff check src tests
uv run ruff format src tests
uv run mypy src
uv run gms --help            # entry point
# Inspeção DLL (quando tiver kernel7x.dll):
uv run python scripts/inspect_dll.py vendor/kernel7x.dll
uv run python scripts/inspect_dll.py --dump vendor/kernel7x.dll --output dumps/kernel7x.txt
```

## 3. Arquitetura (resumo, detalhes em `docs/ARCHITECTURE.md`)

```
src/gms_app/
├── config/        # pydantic-settings (.env)
├── core/          # domínio puro: aluno, plano, pagamento, acesso, regras de catraca
├── hardware/
│   ├── henry7x/   # -> interface.py (ABC) + mock.py + real.py (ctypes Win32)
│   └── biometric/ # abstração biometria
├── infra/         # db (sqlalchemy models, repositories), migrations
├── services/      # casos de uso (ex: LiberarAcessoService)
└── ui/            # PySide6 futuro (isolado, não importa hardware direto)
```

**Regra de ouro:** `core` e `services` NUNCA importam `ctypes`/`pywin32`/`PySide6`. Todo I/O de hardware passa por `hardware/henry7x/interface.py`.

## 4. Estado Atual (atualizar a cada sessão)

- **2026-09-11 — Sessão 0 (bootstrap):**
  - Projeto `uv init` criado, `pyproject.toml` com deps base.
  - Docs iniciais: `README.md`, `docs/ARCHITECTURE.md`, `docs/REQUIREMENTS.md`, `docs/DLL_CONTRACT.md`, `docs/DECISIONS.md`, `docs/ROADMAP.md`.
  - Estrutura `src/gms_app` + `hardware/henry7x` com `interface.py` + `mock.py` + `factory.py`.
  - `scripts/inspect_dll.py` para extrair exports da DLL via `pefile` + fallback `strings`.
  - Git repo iniciado, commit inicial feito.
  - Próximo passo: usuário deve enviar dump do `kernel7x.dll` (texto do PowerShell) para preencher `docs/DLL_CONTRACT.md` e gerar `real.py` esqueleto.

## 5. Contrato Henry 7x — O que sabemos (2026-09-11 atualizado)

- DLL: `kernel7x.dll` (32-bit, COM/OLE) — **não** é DLL plana, é `Henry.Kernel7x` COM — ver `docs/DLL_CONTRACT.md:30` dump PowerShell com 100+ métodos (`AdicionaCard`, `Bio_*`, `Envia*`, `Recebe*`, `ColetaEventos` etc).
- Acesso real em Windows: `win32com.client.Dispatch("Henry.Kernel7x")` (pywin32 32-bit). `factory.py` detectará `ListaPortasSeriais` + `SComConfig`.
- Conexão: **Serial** (`SComConfig` + `AdicionaCard`/`RemoveCard`), `ListaPortasSeriais` lista COMs.
- Ver `docs/DLL_CONTRACT.md` completo e `scripts/inspect_dll.py` para automatizar.

## 6. Decisões Chave (ADRs resumidas, ver `docs/DECISIONS.md`)

1. **Python sim** — expertise > C#; mas COM exige `pywin32` (ADR-001 atualizada).
2. **SQLite local** — 2000+ registros é trivial (ver ADR-002, bench <3ms/busca).
3. **PySide6** — Qt LGPL, faseado (ADR-003).
4. **Mock-first** — Linux mock, COM real só Windows 32-bit (ADR-005).
5. **Licença Apache-2.0 vs GPL** — decidir (ADR-004, MIT descartado).
6. **GymFlow** — nome sem marca Henry (ADR-007).
7. **vendor/docs gitignore** — `vendor/` 100% ignorado (Henry proprietário), `docs/` opcional (ADR-008).

## 7. Roadmap (ver `docs/ROADMAP.md`)

- Fase 0: Bootstrap (esta) ✅
- Fase 1: Domínio + Hardware mockado + Testes (aluno, plano, acesso liberado/negado)
- Fase 2: Persistência SQLite + Alembic
- Fase 3: Integração real kernel7x.dll + testes em VM Windows 32-bit
- Fase 4: UI PySide6 (cadastro, dashboard catraca)
- Fase 5: Biometria + instalador + assinatura

## 8. Pendências / Perguntas para o Dono

- [x] Dump PowerShell colado em `docs/DLL_CONTRACT.md:30` (100+ métodos COM).
- [x] Vendor `vendor/` extraído localmente p/ inspeção do contrato.
- [x] Modelo catraca? Ainda pendente.
- [ ] Confirmar licença: **Apache-2.0** (recomendada) vs **GPLv3** — ver `docs/DECISIONS.md:63` ADR-004.
- [x] Nome: **GymFlow** aprovado (HenryFlow descartado por marca).

## 9. Checklist para Próxima Sessão

1. Ler este arquivo + `docs/ARCHITECTURE.md` + `docs/DLL_CONTRACT.md`.
2. `uv sync --group dev && uv run pytest` deve passar (mesmo que 0 testes).
3. Se houver `vendor/kernel7x.dll`, rodar `scripts/inspect_dll.py`.
4. Não quebrar regra 32-bit: avisar se alguém sugerir `ctypes.CDLL` sem checar `stdcall`.

## 10. Notas de Cross-Platform

- Em Linux, `hardware/henry7x/real.py` deve falhar graciosamente com `RuntimeError("Disponível apenas em Windows 32-bit")`.
- Factory `get_henry_driver()` decide por `sys.platform` + env var `GMS_HENRY_MOCK=1`. Em prod usa `win32com.client.Dispatch("Henry.Kernel7x")`, não `ctypes`.
- Build Windows: usar GitHub Actions `windows-latest` com Python 3.11 32-bit (`architecture: x86`) ou VM local. Windows 64-bit roda app 32-bit via WOW64 sem problema.
- `vendor/` e `docs/` agora em `.gitignore:74` — ambos ignorados p/ GitHub (interno).
- Serial: `ListaPortasSeriais` → escolher `COM3` etc, `SComConfig` define baud/paridade; `AdicionaCard(SComConfig, int)` abre porta.

---
*Última atualização: 2026-09-11 por bootstrap agent. Mantenha este arquivo enxuto e factual.*
