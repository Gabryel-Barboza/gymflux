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
uv run pytest                # testes (128 passed + 1 skipped HW em 2026-09-12)
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
  - Testes `tests/core`, `tests/services`, `tests/hardware` — base dos 45 verdes.
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
- **2026-09-11 — Fase 3 (driver real Henry 7x, commissioning pendente VM) ⏳:**
  - `hardware/henry7x/real.py` implementado (COM `Henry.Kernel7x` via `EnsureDispatch`+fallback `Dispatch`): `conectar` (`AdicionaCard(SComConfig)` + fallback `AdicionaCardSerial`), `desconectar` (`PararColetaEventos`+`RemoveCard`), `liberar` (`EnviaTipoCatraca`+pulso `EnviaAcionaCtrl` relé 1/2), `bloquear` (`csgBloqueada`), `on_giro` (polling `ColetaEventos`+`QuantRegsColetados` em thread daemon), `status` (`Versao`/`ListaPortasSeriais`/`ThreadLastError`). Falha graciosa fora de Windows 32-bit; factory **inalterada**.
  - `docs/DLL_CONTRACT.md` §3/§4 (contrato local, gitignored) + `scripts/dump_henry_typelib.py` (commissioning Windows); CLI `gymflow catraca status|liberar|bloquear`; `tests/hardware/test_real_henry.py` (3 testes Linux + 1 integração `GYMFLOW_HENRY_HW=1` skipada).
  - Verificação Linux: 48 passed + 1 skipped, ruff/mypy limpos, CLI mock ok. **Pendente VM Windows 32-bit:** `dump_henry_typelib` + checklist §4.1.
- **2026-09-11 — Fase 4 (UI desktop PySide6) ✅:**
  - `ui/` Qt6 PT-BR: `catraca_bridge.py` (QObject giro→Signal, único ponto que importa `hardware`), `viewmodels/` (dashboard/alunos/planos/pagamentos, Qt-free, só `services`+`core` + Protocols locais + callback commit), `views/` (4 telas + dialogs), `app.py` (composition root: SQLite via alembic c/ fallback memória + QMainWindow 4 abas). CLI `gymflow ui` (erro amigável sem PySide6). `tests/ui/` (8 VMs + 6 pytest-qt offscreen).
  - Verificação Linux: 62 passed + 1 skipped, ruff/mypy limpos, `gymflow ui` abre com mock+SQLite. **core/services/infra/hardware e testes Fases 1-3 intocados.**
- **2026-09-11 — Fase 4.1 (fix dashboard) ✅:**
  - `DashboardViewModel` recebe `commit` e persiste após `liberar_entrada/saida`; log exibe `nome_aluno()` com fallback p/ ID.
- **2026-09-11 — Fase 4.2 (tema academia) ✅:**
  - `ui/theme.py` (paleta aprovada `#5AC8FA`/`#0F1113`/`#A3D65C`/`#E57373`/`#F2F5F7` + QSS dark nas 4 abas, LIBERADO verde/NEGADO vermelho); `tests/ui/test_theme.py` + `conftest.py`.
  - Verificação Linux: 69 passed + 1 skipped, ruff/mypy limpos. **core/services/infra/hardware intocados.**
- **2026-09-12 — Fase 4.3 (senha numérica estilo SCA, sem driver) ✅:**
  - `Aluno` +`senha_hash` (PBKDF2+salt, validação 4-8 dígitos) +`cartao_id`; migração `3f9a2c1bd4e5`; repos com `buscar_por_cartao`; `IdentificarAcessoService` (TECLADO|CARTAO → `LiberarAcessoService`, sem commit próprio); mock `simular_teclado`/fila; dashboard painel `NOME — LIBERADO/NEGADO` + dialog com senha/cartão.
  - Verificação Linux: 96 passed + 1 skipped, ruff/mypy limpos, downgrade/upgrade `3f9a2c1bd4e5` reversível. **RB01-RB05, real.py, factory e migrations aplicadas intocados.**
- **2026-09-12 — Fase 4.4 (dashboard enxuto + configurações) ✅:**
  - `ui/config_store.py` (`UiConfig` + JSON `data/gymflow_config.json`, Qt-free) + `viewmodels/config.py`; aba Configurações (bloqueios, senha mín 4-8, tolerância, timeout, anti-passback, porta; salva+aplica sem restart); `DashboardViewModel.ui_config` (direção bloqueada e senha curta → NEGADO direto); regra do domínio montada da config; dashboard em 2 linhas compactas + status tabela Campo|Valor + log/giros ~5 linhas + ícones QStyle; screenshots `/tmp/shots44`.
  - Verificação Linux: 111 passed + 1 skipped, ruff/mypy limpos. **core/regras, services, infra/models, migrations e hardware intocados.**
- **2026-09-12 — Fase 4.5 (evolução das telas) ✅:**
  - Alunos editável: `AlunosViewModel.atualizar` + `PerfilAlunoDialog` (form reutilizável + status + pagamentos do aluno + novo pagamento); duplo-clique/botão-direito abrem o perfil.
  - Caixa (substitui aba Pagamentos): `FechamentoCaixa` (model `fechamentos_caixa` + migração `9a0cf12f3688` + repo SQL/memória) + `CaixaViewModel` (filtro por mês, totais recebido/pendente/total, `fechar_mes`, bloqueio de registro em mês fechado) + selo FECHADO.
  - Planos em cards (`QFrame#PlanoCard` no tema) + dialog com `preencher()` p/ edição; `vm.salvar(plano_id=...)` já cobria update.
  - Funcionários: `Funcionario` (core novo, hash PBKDF2) + model `funcionarios` + migração `f7e9182ac1bb` + repo; `IdentificarAcessoService` checa funcionário antes (ativo → pulso direto + LIBERADO "Funcionário", inativo → BLOQUEIO_MANUAL, sem persistir tentativa por FK); tela + aba.
  - Verificação Linux: 128 passed + 1 skipped, ruff/mypy limpos, `alembic upgrade head` ok. **RB01-RB05, hardware, migrations aplicadas e dashboard 4.4 intocados.**

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
- Fase 4: UI PySide6 (cadastro, dashboard catraca) ✅
- Fase 5: Biometria + instalador + assinatura

## 8. Pendências / Perguntas para o Dono

- [x] Dump PowerShell colado em `docs/DLL_CONTRACT.md:30` (100+ métodos COM).
- [x] Licença: **Apache-2.0** aceito.
- [x] Nome: **GymFlow** v1 puro (sem GMS).
- [ ] Modelo catraca exato? (7x / 7x Plus / Biométrica — confirmar p/ Fase 3).
- [x] Fase 4.1 aplicada (commit no dashboard + nome no log).
- [x] Fase 4.4 (feedback dono 2026-09-12) ✅: aba Configurações + dashboard enxuto (ver §4).
- [x] Fase 4.5 (feedback dono 2026-09-12) ✅: perfil editável + Caixa + Planos cards + Funcionários (ver §4).
- [ ] Follow-up Fase 4.5: passes de funcionário NÃO aparecem no log persistido (`acesso_logs.aluno_id` tem FK p/ alunos; bypass não persiste tentativa) e o painel mostra "NÃO IDENTIFICADO — LIBERADO" (dashboard.py intocado por governança) — futuro: coluna `funcionario_id` ou exibir nome via detalhes.
- [ ] Follow-up Fase 4.5: `views/pagamentos.py` (`PagamentosView`) e `pagamentos_vm` mantidos mas sem aba (compat testes); remover quando o gerente aprovar.
- [x] Fluxo senha-na-catraca (estilo SCA) — Fase 4.3 parcial (2026-09-12, sem driver): credencial no `Aluno` (`senha_hash` PBKDF2+salt + `cartao_id`, migração `3f9a2c1bd4e5`), `IdentificarAcessoService` (TECLADO|CARTAO → `LiberarAcessoService`), mock `simular_teclado`/fila, painel verificação `NOME — LIBERADO/NEGADO` + campos senha/cartão no dialog. Falta (commissioning VM): loop de identificação via `ColetaEventos` + parse real do `SRegistro`/`RespostaOn` (TODO em `identificar_acesso.py`, DLL_CONTRACT §3.4).
- [ ] `CadastrarAlunoService` não verifica `cartao_id` duplicado (só CPF) — decidir se cartão deve ser único no cadastro (DB já tem índice único).
- [ ] Importação SCA: **adiada pelo dono** (retomar quando enviar `.bak`/dump; só há `henry.fdb` demo Henry 2011 no repo).
- [x] Identidade visual aprovada: azul `#5AC8FA` + preto `#0F1113` + lima suave `#A3D65C` — aplicar como tema QSS na Fase 4.2.
- [ ] VM Windows 32-bit: `dump_henry_typelib` + checklist `docs/DLL_CONTRACT.md` §4.1 (layout exato `SComConfig`/`SAcionaCtrl`, valores `csg*`, convenção relé 1=entrada/2=saída).
- [ ] Nota: `docs/` e `vendor/` são 100% gitignored — atualizações do contrato (§3/§4) e `dumps/` vivem só localmente, não sobem no commit.
- [x] Correções Fase 2.1 aplicadas (2026-09-11: mypy override, teste duplicado, session_scope, campos não persistidos).

## 9. Checklist para Próxima Sessão

1. Ler este arquivo + `docs/ARCHITECTURE.md` + `docs/DLL_CONTRACT.md`.
2. `uv sync --group dev && uv run pytest` deve passar (128 passed + 1 skipped HW em 2026-09-12).
3. Se houver `vendor/Henry/Henry7x/Kernel7x.dll`, rodar `scripts/inspect_dll.py`.
4. Não quebrar regra 32-bit: `real.py` só Windows 32-bit via COM, nunca `ctypes.CDLL`.

## 10. Notas de Cross-Platform

- Em Linux, `hardware/henry7x/real.py` deve falhar graciosamente com `RuntimeError("Disponível apenas em Windows 32-bit")`.
- Factory `get_henry_driver()` decide por `sys.platform` + env var `GYMFLOW_HENRY_MOCK=1`. Em prod usa `win32com.client.Dispatch("Henry.Kernel7x")`, não `ctypes`.
- Build Windows: usar GitHub Actions `windows-latest` com Python 3.11 32-bit (`architecture: x86`) ou VM local. Windows 64-bit roda app 32-bit via WOW64 sem problema.
- `vendor/` e `docs/` em `.gitignore:74` — ambos ignorados p/ GitHub (interno).
- Serial: `ListaPortasSeriais` → escolher `COM3` etc, `SComConfig` define baud/paridade; `AdicionaCard(SComConfig, int)` abre porta.

---
*Última atualização: 2026-09-11 por gerente GymFlow (auditoria Fase 3 + limpeza). Mantenha este arquivo enxuto e factual.*
