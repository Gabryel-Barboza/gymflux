# AGENTS.md — Memória Operacional do Projeto GymFlow

> Este arquivo é a fonte de verdade para qualquer agente/LLM que retomar o projeto.
> Leia-o **inteiro** no início de cada sessão. Atualize-o ao final de cada marco.

## 1. O que é o GymFlow

**GymFlow** — substituto open-source para controle de catracas **Henry 7x** em academias Windows. v1 sem legado GMS (renomeação final 2026-09-11, ver `docs/DECISIONS.md` ADR-007/ADR-009).

- **Objetivo final:** executável/instalador Windows (.exe/.msi via Inno Setup) que roda em recepção, gerencia alunos, planos, pagamentos e libera/bloqueia catraca por biometria/cartão/teclado.
- **Inspiração SCA:** apenas domínio, não copiar código. Código 100% próprio, licença **Apache-2.0** (ver `LICENSE` + ADR-004).
- **Restrição crítica:** `kernel7x.dll` é **COM 32-bit** (`DllRegisterServer`, não exports planos). Build produção **deve** ser Python 32-bit + `pywin32` COM (`win32com.client.Dispatch("Henry.Kernel7x")`) em Windows 10/11 64-bit (WOW64). Dev Linux = mockado.
- **Conexão:** Serial (COMx via `SComConfig` + `AdicionaCard`/`ListaPortasSeriais`), não TCP.

## 2. Ambiente e Convenções Atuais

| Item | Valor |
|------|-------|
| Linguagem | Python 3.11 (pinado em `.python-version`, `requires-python >=3.11,<3.13`) |
| Gerenciador | `uv` (NUNCA pip/poetry/conda) |
| Estrutura | `src/gymflow` (único, sem shim), `uv_build` |
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
uv run gymflow --help        # entry point único
# Inspeção DLL (quando tiver kernel7x.dll):
uv run python scripts/inspect_dll.py vendor/kernel7x.dll
uv run python scripts/inspect_dll.py --dump vendor/kernel7x.dll --output dumps/kernel7x.txt
```

## 3. Arquitetura (resumo, detalhes em `docs/ARCHITECTURE.md`)

```
src/gymflow/       # único
├── config/        # pydantic-settings (.env GYMFLOW_*)
├── core/          # domínio puro: aluno, plano, pagamento, acesso, regras de catraca
├── hardware/
│   ├── henry7x/   # -> interface.py (ABC) + mock.py + real.py (COM pywin32 32-bit)
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
  - Estrutura `src/gymflow` + `hardware/henry7x` com `interface.py` + `mock.py` + `factory.py`.
  - `scripts/inspect_dll.py` para extrair exports da DLL via `pefile` + fallback `strings`.
  - Git repo iniciado, commit inicial feito.
- **2026-09-11 — Sessão 1 (renomeação GymFlow):**
  - Renomeado pacote `src/gms_app` → `src/gymflow` (`pyproject.toml` `name: gymflow`).
  - Licença confirmada **Apache-2.0** (ADR-004 aceito).
- **2026-09-11 — Sessão 2 (limpeza v1):**
  - Removido shim `src/gms_app` e todos fallbacks `GMS_*` — projeto agora é **apenas `gymflow`** (v1 puro).
  - `pyproject.toml` scripts: apenas `gymflow` (sem aliases `gms`/`gms-app`).
  - `gymflow/config/settings.py` e `factory.py` simplificados para `GYMFLOW_*` puro.
  - Docs limpos de menções legado; `AGENTS.md`/`DECISIONS.md` ADR-009 atualizado para v1 sem compat.
  - `uv sync --group dev && uv run pytest` verde (2 testes), ruff/mypy limpos.
- **2026-09-11 — Sessão 3 (Fase 1 — domínio + mock):**
  - `core/aluno.py` (StatusAluno, Aluno), `plano.py` (Plano, Vigencia, Matricula), `pagamento.py` (Pagamento, esta_adimplente), `acesso.py` (DecisaoAcesso, TentativaAcesso, DirecaoAcesso/ResultadoAcesso), `regras.py` (RegraAcesso RB01-RB05, timeout_giro, anti-passback) — puros, tipados, sem sqlalchemy/pywin32.
  - `services/liberar_acesso.py` (LiberarAcessoService + RegistroMemoria, orquestra RegraAcesso + Henry7xDriver + log memória, RB04 timeout), `cadastrar_aluno.py` e `registrar_pagamento.py` (repos memória mínimos).
  - `hardware/henry7x/interface.py` (Direcao, ResultadoCatraca) + `mock.py` + `factory.py` verificados; `real.py` mantém falha graciosa Linux 32-bit.
  - Testes: `tests/core/test_regras.py` (24 testes RB01 tolerância, RB02 vigência, RB03 bloqueio manual, RB04 timeout, RB05 anti-passback), `tests/services/test_liberar_acesso.py` (11 testes mock), `tests/hardware/test_mock_henry.py` (2 testes, mantidos; também `tests/test_mock_henry.py` legado) — total 39 verdes.
  - Verificação: `uv sync --group dev && uv run pytest -v` 39 passed, `uv run ruff check src tests` All checks passed, `uv run ruff format --check` ok, `uv run python -m mypy src` Success 25 files, `uv run gymflow mock-demo` ok (MockHenry7x liberação + giro).
- **2026-09-11 — Sessão 4 (Fase 2 — persistência SQLite + Alembic) ✅:**
  - `infra/db.py` (Engine SQLAlchemy 2.0 `sqlite:///data/gymflow.db`, WAL `journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON`, `Base` DeclarativeBase Typed, `get_engine()/get_session()/init_db()`, `reset_engine()` p/ testes).
  - `infra/models/` 5 models Typed `Mapped[]`: `AlunoModel` (id PK str, nome, cpf unique indexed, telefone, email, status, bloqueado_manual, created_at), `PlanoModel` (id, nome, duracao_dias, valor Numeric(10,2), tolerancia_dias, tipo), `MatriculaModel` (id, aluno_id FK, plano_id FK, inicio, fim, ativa, índice aluno_id+ativa), `PagamentoModel` (id, aluno_id FK, valor Numeric(10,2), vencimento indexed, pagamento nullable, forma, competencia), `AcessoLogModel` (id, aluno_id FK, timestamp indexed, direcao, resultado, motivo, catraca_id, timeout) — sem importar hardware, Decimal/Numeric.
  - Alembic `src/gymflow/infra/migrations` com `env.py` (`Base.metadata` + `GYMFLOW_DB_URL` via `settings.get_settings().db_url`, compare_type/server_default, prepend_sys_path=src) e revisão `f2d9f6545bb8_initial_gymflow_v1` (5 tabelas + índices, FKs CASCADE); `alembic.ini` `sqlalchemy.url=sqlite:///data/gymflow.db`.
  - `infra/repositories/` 5 repos Protocol+SQLAlchemy (`AlunoRepositorySQLAlchemy`, `PlanoRepositorySQLAlchemy`, `MatriculaRepositorySQLAlchemy`, `PagamentoRepositorySQLAlchemy`, `AcessoLogRepositorySQLAlchemy`) com injeção `Session`, métodos CRUD, busca cpf normalizada, matricula vigente por data, acesso log por aluno; mantém `*Memoria` fallback Fase 1.
  - `services` refatorados p/ injeção: `CadastrarAlunoService(repo)`, `RegistrarPagamentoService(repo)`, `LiberarAcessoService` com repos opcionais (`aluno_repo`, `matricula_repo`, `pagamento_repo`, `acesso_repo`) + `tentar_acesso_por_id()` + `_persistir_tentativa()` dual memória/DB, compatível se repo None.
  - CLI `gymflow` estendido: `gymflow db upgrade|downgrade [rev]`, `gymflow db seed`/`gymflow seed` (idempotente 3 alunos Ana/Bruno/Carla + planos Mensal 99.90/Trimestral 259.90, matrículas vigentes, pagamentos adimplentes).
  - Testes `tests/infra/test_repositories.py` (6 testes :memory: CRUD cpf, plano, matrícula vigente, pagamento, acesso log, cpf único) + `tests/infra/test_migrations.py` (2 testes create_all + alembic upgrade head) — total 47 verdes.
  - Verificação: `uv sync --group dev && uv run python -m alembic upgrade head && uv run pytest -v` 47 passed, `uv run ruff check src tests` All checks passed, `uv run python -m mypy src` Success 40 files, `uv run gymflow info` ok (3 alunos, 2 planos), `uv run gymflow db seed` idempotente, `data/gymflow.db` 76KB (WAL).

## 5. Contrato Henry 7x — O que sabemos (2026-09-11 atualizado)

- DLL: `kernel7x.dll` (32-bit, COM/OLE) — **não** é DLL plana, é `Henry.Kernel7x` COM — ver `docs/DLL_CONTRACT.md:30` dump PowerShell com 100+ métodos (`AdicionaCard`, `Bio_*`, `Envia*`, `Recebe*`, `ColetaEventos` etc).
- Acesso real em Windows: `win32com.client.Dispatch("Henry.Kernel7x")` (pywin32 32-bit). `factory.py` detectará `ListaPortasSeriais` + `SComConfig`.
- Conexão: **Serial** (`SComConfig` + `AdicionaCard`/`RemoveCard`), `ListaPortasSeriais` lista COMs.
- Ver `docs/DLL_CONTRACT.md` completo e `scripts/inspect_dll.py` para automatizar.

## 6. Decisões Chave (ADRs resumidas, ver `docs/DECISIONS.md`)

1. **Python sim** — expertise > C#; mas COM exige `pywin32` (ADR-001).
2. **SQLite local** — 2000+ registros é trivial (ver ADR-002, bench <3ms/busca).
3. **PySide6** — Qt LGPL, faseado (ADR-003).
4. **Mock-first** — Linux mock, COM real só Windows 32-bit (ADR-005).
5. **Licença Apache-2.0** — aceito (ADR-004).
6. **GymFlow** — nome sem marca Henry (ADR-007) + renomeação total v1 (ADR-009).
7. **vendor/docs gitignore** — `vendor/` 100% ignorado (Henry proprietário), `docs/` opcional (ADR-008).

## 7. Roadmap (ver `docs/ROADMAP.md`)

- Fase 0: Bootstrap ✅
- Fase 1: Domínio + Hardware mockado + Testes (aluno, plano, acesso liberado/negado) ✅
- Fase 2: Persistência SQLite + Alembic ✅ (2026-09-11 concluída)
- Fase 3: Integração real kernel7x.dll + testes em VM Windows 32-bit
- Fase 4: UI PySide6 (cadastro, dashboard catraca)
- Fase 5: Biometria + instalador + assinatura

## 8. Pendências / Perguntas para o Dono

- [x] Dump PowerShell colado em `docs/DLL_CONTRACT.md:30` (100+ métodos COM).
- [x] Vendor `vendor/` extraído localmente p/ inspeção do contrato.
- [x] Modelo catraca? Pendente.
- [x] Licença: **Apache-2.0** aceito.
- [x] Nome: **GymFlow** v1 puro (sem GMS).

## 9. Checklist para Próxima Sessão

1. Ler este arquivo + `docs/ARCHITECTURE.md` + `docs/DLL_CONTRACT.md`.
2. `uv sync --group dev && uv run pytest` deve passar (2 testes v1).
3. Se houver `vendor/kernel7x.dll`, rodar `scripts/inspect_dll.py`.
4. Não quebrar regra 32-bit: avisar se alguém sugerir `ctypes.CDLL` sem checar `stdcall`.

## 10. Notas de Cross-Platform

- Em Linux, `hardware/henry7x/real.py` deve falhar graciosamente com `RuntimeError("Disponível apenas em Windows 32-bit")`.
- Factory `get_henry_driver()` decide por `sys.platform` + env var `GYMFLOW_HENRY_MOCK=1`. Em prod usa `win32com.client.Dispatch("Henry.Kernel7x")`, não `ctypes`.
- Build Windows: usar GitHub Actions `windows-latest` com Python 3.11 32-bit (`architecture: x86`) ou VM local. Windows 64-bit roda app 32-bit via WOW64 sem problema.
- `vendor/` e `docs/` agora em `.gitignore:74` — ambos ignorados p/ GitHub (interno).
- Serial: `ListaPortasSeriais` → escolher `COM3` etc, `SComConfig` define baud/paridade; `AdicionaCard(SComConfig, int)` abre porta.

---
*Última atualização: 2026-09-11 por agente Fase 1 GymFlow. Mantenha este arquivo enxuto e factual.*
