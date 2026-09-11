# AGENTS.md — Memória Operacional do Projeto GymFlow

> Este arquivo é a fonte de verdade para qualquer agente/LLM que retomar o projeto.
> Leia-o **inteiro** no início de cada sessão. Atualize-o ao final de cada marco.

## 1. O que é o GymFlow

**GymFlow** — substituto open-source para controle de catracas **Henry 7x** em academias Windows. v1 sem legado GMS (ver `docs/DECISIONS.md` ADR-007/ADR-009).

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
| UI planejada | PySide6 (Qt6, LGPL) — Fase 1-2: CLI, Fase 4: Desktop |
| Empacotamento | PyInstaller (32-bit Windows) + Inno Setup |
| Lint/Teste | ruff, mypy, pytest, loguru |

### Comandos canônicos

```bash
uv sync --group dev          # instala deps
uv run pytest                # testes (47 verdes em 2026-09-11)
uv run ruff check src tests
uv run ruff format src tests
uv run mypy src
uv run gymflow --help        # entry point único
uv run gymflow db upgrade && uv run gymflow db seed
# Inspeção DLL (quando tiver kernel7x.dll):
uv run python scripts/inspect_dll.py vendor/kernel7x.dll
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

**Regra de ouro:** `core` e `services` NUNCA importam `ctypes`/`pywin32`/`PySide6`. Todo I/O de hardware passa por `hardware/henry7x/interface.py`. `infra` nunca é importado por `core`.

## 4. Estado Atual (atualizar a cada sessão)

- **2026-09-11 — Bootstrap + renomeação:**
  - `uv init`, docs base, `hardware/henry7x` (interface + mock + factory), `scripts/inspect_dll.py`.
  - Renomeado `src/gms_app` → `src/gymflow`, `name: gymflow`, `GYMFLOW_*` puro, licença **Apache-2.0**.
- **2026-09-11 — Fase 1 (domínio + mock) ✅:**
  - `core/` puro e tipado (RB01-RB05) + `services/` com repos memória + `LiberarAcessoService`.
  - Testes `tests/core`, `tests/services`, `tests/hardware` — base dos 47 verdes.
- **2026-09-11 — Fase 2 (persistência SQLite + Alembic) ✅:**
  - `infra/db.py` (WAL, FK ON), 5 models Typed, migração inicial `f2d9f6545bb8`, 5 repos Protocol+SQLAlchemy, `services` com injeção opcional + `tentar_acesso_por_id`, CLI `gymflow db upgrade|downgrade|seed` (seed idempotente 3 alunos + 2 planos).
  - Verificação: 47 passed, ruff/mypy limpos, `gymflow info`/`db seed` ok.
- **2026-09-11 — Fase 2.1 (correções auditoria) ✅:**
  - `pyproject.toml`: removido override `gymflow.infra.*` + removido `types-sqlalchemy` 1.4 obsoleto (conflitava com SQLAlchemy 2.0 tipado); corrigido erro real `migrations/env.py:41` (`str|None`).
  - Deletado `tests/test_mock_henry.py` duplicado (mantido `tests/hardware/test_mock_henry.py`).
  - `infra/db.py:86` `session_scope` com `@contextmanager` (`Iterator[Session]`).
  - `AlunoModel` +`data_nasc Date nullable` +`observacoes Text`; `AcessoLogModel` +`detalhes Text`; migração `8c81436e0086` (autogenerate limpo); repos mapeiam novos campos.
  - `RegistrarPagamentoService.registrar` simplificado p/ `buscar_por_id` direto; `liberar_acesso` removido `TYPE_CHECKING` vazio; `AcessoLogRepository` + `Memoria` com `buscar_ultimo_por_aluno`; `_AcessoRepoProto` idem (sem `hasattr`).
  - `__main__.py:135` `suppress` trocado por `try/log` explícito (loguru + print).
  - Verificação: 45 passed (47−2 duplicados), ruff/mypy limpos, `alembic upgrade head` em `8c81436e0086`, `gymflow db seed` idempotente.

## 5. Contrato Henry 7x — O que sabemos (2026-09-11)

- DLL: `kernel7x.dll` (32-bit, COM/OLE) — **não** é DLL plana, é `Henry.Kernel7x` COM — ver `docs/DLL_CONTRACT.md:30` dump PowerShell com 100+ métodos (`AdicionaCard`, `Bio_*`, `Envia*`, `Recebe*`, `ColetaEventos` etc).
- Acesso real em Windows: `win32com.client.Dispatch("Henry.Kernel7x")` (pywin32 32-bit).
- Conexão: **Serial** (`SComConfig` + `AdicionaCard`/`RemoveCard`), `ListaPortasSeriais` lista COMs.

## 6. Decisões Chave (ADRs resumidas, ver `docs/DECISIONS.md`)

1. **Python sim** — expertise > C#; mas COM exige `pywin32` (ADR-001).
2. **SQLite local** — 2000+ registros é trivial (ADR-002).
3. **PySide6** — Qt LGPL, faseado (ADR-003).
4. **Mock-first** — Linux mock, COM real só Windows 32-bit (ADR-005).
5. **Licença Apache-2.0** — aceito (ADR-004).
6. **GymFlow** — nome sem marca Henry (ADR-007/ADR-009).
7. **vendor/docs gitignore** — `vendor/` 100% ignorado, `docs/` opcional (ADR-008).

## 7. Roadmap (ver `docs/ROADMAP.md`)

- Fase 0: Bootstrap ✅
- Fase 1: Domínio + Hardware mockado + Testes ✅
- Fase 2: Persistência SQLite + Alembic ✅
- Fase 3: Integração real kernel7x.dll + testes em VM Windows 32-bit
- Fase 4: UI PySide6 (cadastro, dashboard catraca)
- Fase 5: Biometria + instalador + assinatura

## 8. Pendências / Perguntas para o Dono

- [x] Dump PowerShell colado em `docs/DLL_CONTRACT.md:30` (100+ métodos COM).
- [x] Licença: **Apache-2.0** aceito.
- [x] Nome: **GymFlow** v1 puro (sem GMS).
- [ ] Modelo catraca exato? (7x / 7x Plus / Biométrica — confirmar p/ Fase 3).
- [x] Correções Fase 2.1 aplicadas (2026-09-11: mypy override, teste duplicado, session_scope, campos não persistidos).

## 9. Checklist para Próxima Sessão

1. Ler este arquivo + `docs/ARCHITECTURE.md` + `docs/DLL_CONTRACT.md`.
2. `uv sync --group dev && uv run pytest` deve passar (47 verdes).
3. Se houver `vendor/kernel7x.dll`, rodar `scripts/inspect_dll.py`.
4. Não quebrar regra 32-bit: `real.py` só Windows 32-bit via COM, nunca `ctypes.CDLL`.

## 10. Notas de Cross-Platform

- Em Linux, `hardware/henry7x/real.py` deve falhar graciosamente com `RuntimeError("Disponível apenas em Windows 32-bit")`.
- Factory `get_henry_driver()` decide por `sys.platform` + env var `GYMFLOW_HENRY_MOCK=1`. Em prod usa `win32com.client.Dispatch("Henry.Kernel7x")`, não `ctypes`.
- Build Windows: usar GitHub Actions `windows-latest` com Python 3.11 32-bit (`architecture: x86`) ou VM local. Windows 64-bit roda app 32-bit via WOW64 sem problema.
- `vendor/` e `docs/` em `.gitignore:74` — ambos ignorados p/ GitHub (interno).
- Serial: `ListaPortasSeriais` → escolher `COM3` etc, `SComConfig` define baud/paridade; `AdicionaCard(SComConfig, int)` abre porta.

---
*Última atualização: 2026-09-11 por agente Fase 2.1 GymFlow (auditoria aplicada). Mantenha este arquivo enxuto e factual.*
