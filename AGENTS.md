# AGENTS.md — Memória Operacional do Projeto GymFlux

> Este arquivo é a fonte de verdade para qualquer agente/LLM que retomar o projeto.
> Leia-o **inteiro** no início de cada sessão. Atualize-o ao final de cada marco.

## 1. O que é o GymFlux

**GymFlux** — substituto open-source para controle de catracas **Henry 7x** em academias Windows. v1 sem legado GMS (ver `docs/DECISIONS.md` ADR-007/ADR-009).

- **Objetivo final:** executável/instalador Windows (.exe/.msi via Inno Setup) que roda em recepção, gerencia alunos, planos, pagamentos e libera/bloqueia catraca por biometria/cartão/teclado.
- **Inspiração SCA:** apenas domínio, não copiar código. Código 100% próprio, licença **Apache-2.0** (ver `LICENSE` + ADR-004).
- **Restrição crítica:** `kernel7x.dll` é **COM 32-bit** (`DllRegisterServer`, não exports planos). Build produção **deve** ser Python 32-bit + `pywin32` COM (`win32com.client.Dispatch("Henry.Kernel7x")`) em Windows 10/11 64-bit (WOW64). Dev Linux = mockado.
- **Conexão:** Serial (COMx via `SComConfig` + `AdicionaCard`/`ListaPortasSeriais`), não TCP.

## 2. Ambiente e Convenções Atuais

| Item | Valor |
|------|-------|
| Linguagem | Python 3.11 (pinado em `.python-version`, `requires-python >=3.11,<3.13`) |
| Gerenciador | `uv` (NUNCA pip/poetry/conda) |
| Estrutura | `src/gymflux` (único, sem shim), `uv_build` |
| SO dev | Linux x86_64 (você está aqui) |
| SO prod | Windows 10/11 64-bit rodando app 32-bit |
| DB local | SQLite + SQLAlchemy 2.0 + Alembic (Postgres futuro opcional) |
| UI planejada | PySide6 (Qt6, LGPL) — Fase 1-2: CLI, Fase 4: Desktop |
| Empacotamento | PyInstaller (32-bit Windows) + Inno Setup |
| Lint/Teste | ruff, mypy, pytest, loguru |

### Comandos canônicos

```bash
uv sync --group dev          # instala deps
uv run pytest                # testes (153 passed + 1 skipped HW em 2026-09-12)
uv run ruff check src tests
uv run ruff format src tests
uv run mypy src
uv run gymflux --help        # entry point único
uv run gymflux db upgrade && uv run gymflux db seed
# Inspeção DLL (quando tiver kernel7x.dll):
uv run python scripts/inspect_dll.py vendor/kernel7x.dll
```

## 3. Arquitetura (resumo, detalhes em `docs/ARCHITECTURE.md`)

```
src/gymflux/       # único
├── config/        # pydantic-settings (.env GYMFLUX_*)
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
  - Renomeado `src/gms_app` → `src/gymflux`, `name: gymflux`, `GYMFLUX_*` puro, licença **Apache-2.0**.
- **2026-09-11 — Fase 1 (domínio + mock) ✅:**
  - `core/` puro e tipado (RB01-RB05) + `services/` com repos memória + `LiberarAcessoService`.
  - Testes `tests/core`, `tests/services`, `tests/hardware` — base dos 45 verdes.
- **2026-09-11 — Fase 2 (persistência SQLite + Alembic) ✅:**
  - `infra/db.py` (WAL, FK ON), 5 models Typed, migração inicial `f2d9f6545bb8`, 5 repos Protocol+SQLAlchemy, `services` com injeção opcional + `tentar_acesso_por_id`, CLI `gymflux db upgrade|downgrade|seed` (seed idempotente 3 alunos + 2 planos).
  - Verificação: 47 passed, ruff/mypy limpos, `gymflux info`/`db seed` ok.
- **2026-09-11 — Fase 2.1 (correções auditoria) ✅:**
  - `pyproject.toml`: removido override `gymflux.infra.*` + removido `types-sqlalchemy` 1.4 obsoleto (conflitava com SQLAlchemy 2.0 tipado); corrigido erro real `migrations/env.py:41` (`str|None`).
  - Deletado `tests/test_mock_henry.py` duplicado (mantido `tests/hardware/test_mock_henry.py`).
  - `infra/db.py:86` `session_scope` com `@contextmanager` (`Iterator[Session]`).
  - `AlunoModel` +`data_nasc Date nullable` +`observacoes Text`; `AcessoLogModel` +`detalhes Text`; migração `8c81436e0086` (autogenerate limpo); repos mapeiam novos campos.
  - `RegistrarPagamentoService.registrar` simplificado p/ `buscar_por_id` direto; `liberar_acesso` removido `TYPE_CHECKING` vazio; `AcessoLogRepository` + `Memoria` com `buscar_ultimo_por_aluno`; `_AcessoRepoProto` idem (sem `hasattr`).
  - `__main__.py:135` `suppress` trocado por `try/log` explícito (loguru + print).
  - Verificação: 45 passed (47−2 duplicados), ruff/mypy limpos, `alembic upgrade head` em `8c81436e0086`, `gymflux db seed` idempotente.
- **2026-09-11 — Fase 3 (driver real Henry 7x, commissioning pendente VM) ⏳:**
  - `hardware/henry7x/real.py` implementado (COM via `EnsureDispatch`+fallback `Dispatch`): `conectar` (`AdicionaCard(SComConfig)` + fallbacks `AdicionaCardSerial/485/TcpIp` + best-effort comtypes), `desconectar` (`PararColetaEventos`+`RemoveCard`), `liberar` (`EnviaTipoCatraca`+pulso `EnviaAcionaCtrl` relé 1/2), `bloquear` (`csgBloqueada`), `on_giro` (polling `ColetaEventos`+`QuantRegsColetados` em thread daemon), `status` (`Versao`/`ListaPortasSeriais`/`ThreadLastError`). Falha graciosa fora de Windows 32-bit; factory **inalterada**.
  - `docs/DLL_CONTRACT.md` §3/§4 (contrato local, gitignored) + `scripts/dump_henry_typelib.py` (4 ProgIDs, roda em 64-bit com aviso); CLI `gymflux catraca status|liberar|bloquear`; `tests/hardware/test_real_henry.py` (4 testes Linux + 1 integração `GYMFLOW_HENRY_HW=1` skipada).
  - **Validado em Windows 2026-09-14 (DLL 7.2.0.52, catraca desligada):** ProgID real `Kernel7x.Kernel` (`Henry.Kernel7x` NÃO existe; CLSID `{6649E95F-...}`, TypeLib `{25DC738C-...}`); `status()` retorna `Versao 7.2.0.52`; enums numéricos (`ctcSerial=0`, `cv9600=0`, `cmcOnOff=2`, `csgLibEntrada=1`...); `SComConfig` 48 bytes + `SAcionaCtrl` só `TempoRele` (sem bool); `comtypes` no extra `windows`; dual-env (`.venv` x64 UI + `.venv32` minimal HW). **Pendente catraca ligada:** `AdicionaCard` ainda falha sem hardware (`-2147352568`/access violation); tentar `DPInst.exe`+COMx real ou pré-config via `Henry7x.exe`. Detalhes em `vendor/RELATORIO_HENRY7X.md` (local).
- **2026-09-11 — Fase 4 (UI desktop PySide6) ✅:**
  - `ui/` Qt6 PT-BR: `catraca_bridge.py` (QObject giro→Signal, único ponto que importa `hardware`), `viewmodels/` (dashboard/alunos/planos/pagamentos, Qt-free, só `services`+`core` + Protocols locais + callback commit), `views/` (4 telas + dialogs), `app.py` (composition root: SQLite via alembic c/ fallback memória + QMainWindow 4 abas). CLI `gymflux ui` (erro amigável sem PySide6). `tests/ui/` (8 VMs + 6 pytest-qt offscreen).
  - Verificação Linux: 62 passed + 1 skipped, ruff/mypy limpos, `gymflux ui` abre com mock+SQLite. **core/services/infra/hardware e testes Fases 1-3 intocados.**
- **2026-09-11 — Fase 4.1 (fix dashboard) ✅:**
  - `DashboardViewModel` recebe `commit` e persiste após `liberar_entrada/saida`; log exibe `nome_aluno()` com fallback p/ ID.
- **2026-09-11 — Fase 4.2 (tema academia) ✅:**
  - `ui/theme.py` (paleta aprovada `#5AC8FA`/`#0F1113`/`#A3D65C`/`#E57373`/`#F2F5F7` + QSS dark nas 4 abas, LIBERADO verde/NEGADO vermelho); `tests/ui/test_theme.py` + `conftest.py`.
  - Verificação Linux: 69 passed + 1 skipped, ruff/mypy limpos. **core/services/infra/hardware intocados.**
- **2026-09-12 — Fase 4.3 (senha numérica estilo SCA, sem driver) ✅:**
  - `Aluno` +`senha_hash` (PBKDF2+salt, validação 4-8 dígitos) +`cartao_id`; migração `3f9a2c1bd4e5`; repos com `buscar_por_cartao`; `IdentificarAcessoService` (TECLADO|CARTAO → `LiberarAcessoService`, sem commit próprio); mock `simular_teclado`/fila; dashboard painel `NOME — LIBERADO/NEGADO` + dialog com senha/cartão.
  - Verificação Linux: 96 passed + 1 skipped, ruff/mypy limpos, downgrade/upgrade `3f9a2c1bd4e5` reversível. **RB01-RB05, real.py, factory e migrations aplicadas intocados.**
- **2026-09-12 — Fase 4.4 (dashboard enxuto + configurações) ✅:**
  - `ui/config_store.py` (`UiConfig` + JSON `data/gymflux_config.json`, Qt-free) + `viewmodels/config.py`; aba Configurações (bloqueios, senha mín 4-8, tolerância, timeout, anti-passback, porta; salva+aplica sem restart); `DashboardViewModel.ui_config` (direção bloqueada e senha curta → NEGADO direto); regra do domínio montada da config; dashboard em 2 linhas compactas + status tabela Campo|Valor + log/giros ~5 linhas + ícones QStyle; screenshots `/tmp/shots44`.
  - Verificação Linux: 111 passed + 1 skipped, ruff/mypy limpos. **core/regras, services, infra/models, migrations e hardware intocados.**
- **2026-09-12 — Fase 4.5 (evolução das telas) ✅:**
  - Alunos editável: `AlunosViewModel.atualizar` + `PerfilAlunoDialog` (form reutilizável + status + pagamentos do aluno + novo pagamento); duplo-clique/botão-direito abrem o perfil.
  - Caixa (substitui aba Pagamentos): `FechamentoCaixa` (model `fechamentos_caixa` + migração `9a0cf12f3688` + repo SQL/memória) + `CaixaViewModel` (filtro por mês, totais recebido/pendente/total, `fechar_mes`, bloqueio de registro em mês fechado) + selo FECHADO.
  - Planos em cards (`QFrame#PlanoCard` no tema) + dialog com `preencher()` p/ edição; `vm.salvar(plano_id=...)` já cobria update.
  - Funcionários: `Funcionario` (core novo, hash PBKDF2) + model `funcionarios` + migração `f7e9182ac1bb` + repo; `IdentificarAcessoService` checa funcionário antes (ativo → pulso direto + LIBERADO "Funcionário", inativo → BLOQUEIO_MANUAL, sem persistir tentativa por FK); tela + aba.
  - Verificação Linux: 128 passed + 1 skipped, ruff/mypy limpos, `alembic upgrade head` ok. **RB01-RB05, hardware, migrations aplicadas e dashboard 4.4 intocados.**
- **2026-09-12 — Fase 4.6 (frequência + antifraude) ✅:**
  - `acesso_logs` +`funcionario_id` nullable (migração `a41f0c9d2e7b`, `aluno_id` passa a nullable) + repo; bypass de funcionário agora persiste tentativa (memória + SQL).
  - Log do dashboard filtra só hoje (coluna só hora + nomes de funcionários); click no registro → troca p/ aba Alunos e abre o perfil (signal, funcionário sem perfil é ignorado).
  - `FrequenciaViewModel` (Qt-free: filtros dia/mês/aluno, meses, resumo por dia LIBERADO) + aba Frequência + seção "Frequência (outros dias)" no perfil.
  - Removidos `views/pagamentos.py` + `PagamentosViewModel` (`CaixaViewModel` absorve services; `NovoPagamentoDialog` mora em `views/caixa.py`; testes atualizados, RB01 segue coberta em `tests/core`).
  - Verificação Linux: 138 passed + 1 skipped, ruff/mypy limpos, upgrade/downgrade `a41f0c9d2e7b` reversível. **Regras, hardware e dashboard 4.4 (só click-through) intocados.**
- **2026-09-12 — Fase 4.7 (modo claro) ✅:**
  - `theme.py`: `ModoTema` + `stylesheet(modo)` (claro troca só a base: `#F2F5F7`/`#FFFFFF`/`#1A1E22`/`#5A6B78`/`#D5DCE2`; acentos intactos; títulos com tinta escura e texto-sobre-acento sempre escuro p/ contraste) + `contraste()` WCAG + `estilo_resultado(_, modo)` (selo no claro) + `cores_indicador`/`estilo_selo`; `UiConfig.tema` persistido; aba Configurações alterna sem restart (`app.setStyleSheet`); selo FECHADO revisado; screenshots `/tmp/shots47`.
  - Verificação Linux: 145 passed + 1 skipped, ruff/mypy limpos. **Regras, services, infra e hardware intocados; telas só com estilos inline por modo.**
- **2026-09-12 — Fase 4.8 (credencial simplificada) ✅:**
  - `Aluno.senha` em TEXTO (4-8 dígitos, PIN visível no perfil; docstring registra decisão do dono + risco aceito) — `senha_hash`/`cartao_id`/`definir_cartao` removidos; helpers PBKDF2 mantidos só p/ `Funcionario` (hash inalterado); migração `b2c4d6e8f0a1` (add `senha`, drop `cartao_id`+índice+`senha_hash`; hashes irrecuperáveis → campo nasce NULL + aviso logado; reversível).
  - `buscar_por_senha` (Protocol + SQL + memórias) substitui `buscar_por_cartao`; `IdentificarAcessoService` só TECLADO (origem CARTAO + `por_cartao` removidos; lookup direto, sem varredura); dashboard sem combo de origem; mock `simular_teclado` intocado.
  - `services/inatividade.py`: `aplicar_inatividade(dias=90, ref)` — ATIVO não-bloqueado sem LIBERADO há 90d (nunca entrou conta; só NEGADO não segura) → INATIVO + `senha=None`; chamada no `_wire` (startup UI, nunca aborta, committa se inativou); `tests/unit/services/test_inatividade.py` (7 testes).
  - Verificação Linux: 153 passed + 1 skipped, ruff/mypy limpos, upgrade/downgrade `b2c4d6e8f0a1` reversível (dados preservados), `gymflux db seed` idempotente, smoke `create_context` offscreen ok. **RB01-RB05, hardware, factory e mock intocados.**
- **2026-09-13 — Fase 4.9 (refino das telas) ✅:**
  - Catraca: status compacto (`lbl_compacto` + `DetalhesDialog` Versao/portas/último erro) + toast QTimer 4s sem ocupar layout + log NEGADO em vermelho (`#3a1a1a`/`#ffe0e0`) + campo único CPF/senha + botão único "Liberar catraca" (`liberar_catraca_unico` resolve direção via config; sem Bloquear; compat mantém widgets legados ocultos).
  - `UiConfig` +`ModoAcesso` LIVRE/SENHA por direção (default entrada=SENHA/saída=LIVRE; legado `bloquear_*` mantido p/ compat JSON) + `DashboardViewModel` (`_livre_liberar_direto`, `_modo`, `liberar_catraca_unico`; LIVRE pula RB e pulsa hardware; SENHA exige identificação; LEGADO ainda NEGADO); LIVRE vs SENHA respeitados em `liberar_entrada/saida` e `identificar_acesso`.
  - Alunos: `AlunosView` só 2 botões visíveis (Novo + `btn_bloq_toggle` toggle) + resto em `QMenu` contexto + header `sectionClicked` filtra por valor (Nome/CPF/Status) + bloqueados em vermelho; `_AlunoForm` em `QGridLayout` grade (largura 560) + `PerfilAlunoDialog` em 4 abas (`QTabWidget` Pessoais/Plano/Matrícula/Frequência/Pagamentos) + botão Liberar (via `dashboard_vm` injetado em `app.py`).
  - Planos: `NovoPlanoDialog` em `QGridLayout` 2x2 largura 520 + `PlanosView` em grade 2 colunas (cards 320px).
  - Caixa: `CaixaView` sidebar esquerda (Fechar + 3 stats coloridas sem data `Recebido`/`Pendente`/`Total` + `lbl_totais` oculto p/ compat) + `cmb_aluno` editável com `QCompleter` `MatchContains` e scroll (500+); `NovoPagamentoDialog` sem vencimento (usa hoje/competência; vencimento edita-se no perfil `tbl_pag`).
  - Config: categorias `QGroupBox` Catraca (porta + entrada/saída ModoAcesso) / Personalização (tema) / Regras; mantém `chk_bloq_*` ocultos p/ compat testes.
  - Verificação Linux: 153 passed + 1 skipped, ruff/mypy limpos, screenshots claro/escuro em `/tmp/shots49` (7 abas × 2 modos). **core/services/infra/hardware intocados (só `config_store` + `dashboard_vm` + `ui/`).**
- **2026-09-13 — Fase 4.10-A (tema claro + catraca) ✅:**
  - `theme.py`: claro `FUNDO_CLARO`/`PAINEL_CLARO` `#E8EDF1` (era `#F2F5F7`/`#FFFFFF`) + `BORDA_CLARA` `#C8D0D8` (era `#D5DCE2`) + sombra leve + `QTabBar::tab:selected` texto+ícone `#5AC8FA` (tint via `_tint_icon` em `app.py`; `stylesheet` usa `color: AZUL` + `border-bottom: 2px solid AZUL` no claro); `app.py` `GymFluxMainWindow` guarda `_base_icons` + `_aplicar_tema_icones`/`_on_tab_changed` e `_wire._aplicar` atualiza ícones sem restart.
  - `dashboard.py`: header `QFrame#CatracaHeader` (borda `#C8D0D8`, radius 8) com `lbl_compacto` + `btn_detalhes` à direita, centro `QFrame#CatracaCentro` com `edt_unico` 40px + `btn_liberar` 40px/160px moderno, abaixo `QGroupBox` "Acessos de hoje"/"Giros" lado a lado com headers fixos; toast overlay centralizado `QTimer` 4s + `resizeEvent` centraliza; `config.py` intocado (categorias já em 4.9).
  - Verificação Linux: 153 passed + 1 skipped, ruff/mypy limpos, screenshots claro/escuro em `/tmp/shots410A` (7 abas × 2 modos). **core/services/infra/hardware intocados (só `theme.py` + `dashboard.py` + `app.py`).**
- **2026-09-13 — Fase 4.10-B (telas alunos/planos/frequência/caixa) ✅:**
  - `core/aluno.py` +`endereco` + `infra/models/aluno.py` + migração `d3e8f1a2c4b9` + repos/viewmodels (`alunos.py` `endereco`, `caixa.py` `reabrir_mes`); `views/alunos.py`: `_AlunoForm` `QTextEdit` 80px separado + `edt_endereco` + grade, `PerfilAlunoDialog` botão `Salvar` + `_header_clicado` menu Excel (valores únicos + busca `QLineEdit` + `QListWidget`), `views/planos.py`: `QVBoxLayout` 1 coluna compacta + `NovoPlanoDialog` `PERSONALIZADO` mostra `spn_dur` (senão esconde, usa `DURACAO_POR_TIPO`), `views/frequencia.py`: `QCompleter` + `QListView` + paginação 50 + fix `chk_dia` (desmarcado lista mês inteiro), `views/caixa.py`: `CaixaViewModel.reabrir_mes` + `btn_reabrir` quando FECHADO.
  - Verificação Linux: 153 passed + 1 skipped, ruff/mypy limpos, `alembic upgrade` `d3e8f1a2c4b9` head + `downgrade` ok, `QT_QPA_PLATFORM=offscreen pytest tests/ui` 69 passed. **RB01-RB05 e hardware intocados.**
- **2026-09-15 — Fase 4.16 perf Caixa + turnos ✅:**
  - **Perf Caixa:** `pagamento` repo `listar_por_mes(mes,limit,offset)` WHERE `competencia==mes OR (IS NULL AND strftime==mes)` + `contar_por_mes` + `totais_por_mes` SUM(CASE) + `meses_distintos` DISTINCT coalesce; `aluno` repo `mapa_nomes(ids)` IN + `listar_ordenado`; `pagamento.competencia` índice `ix_pagamentos_competencia` migração `1a2b3c4d5e6f`; `CaixaViewModel` pushdown (meses DISTINCT, paginado+mapa só página, SUM, COUNT) + `views/caixa.py` UM refresh por mês (só meses DISTINCT + combo alunos cacheado), paginação 500 via COUNT, scroll busca próxima página offset, marcar/desmarcar via `buscar_por_id` direto; `tests/unit/ui/test_caixa_perf.py` 2k <1s slow; medido 7,6k/10k: 136ms cold /21ms warm (era 2s) `recarregar` 93-179ms.
  - **Turnos:** `core/funcionario.py` `Turno(dias,inicio,fim)` + `parse_turnos()`/`format_turnos()`/`parse_turnos_tolerante()`/`format_turnos_compacto()` valida HH:MM e dias `Seg Ter Qua Qui Sex Sáb Dom` com `-` e `;`; `viewmodels/funcionarios.py` normaliza via parse/format (ValueError amigável); `views/funcionarios.py` editor de turnos no `Novo/Perfil` (linhas: combo preset `Seg-Sex Sáb Dom Seg-Sáb Todos Personalizado` + `edt_custom` + 2 `QTimeEdit` + +/-) substitui `QLineEdit` livre e migra legado; tabela coluna Horários compacto multilinha `Seg–Sex\n08h–12h · 14h–18h` com tooltip full, wordWrap + largura 200; `FuncionariosView` detalhes `Nome:` capitalizado (fix); `tests/unit/core/test_turnos.py` 6 testes roundtrip.
  - Verificação Linux: 196 passed +1 skipped, ruff ok (RUF001-003 ignorado p/ en-dash), mypy 87 files ok, `data/gymflux.db` 7,6k/10k medido; commits `3917be5 perf(caixa)` + `643bf7b feat(funcionarios)`.
  - Auditoria gerente 2026-09-15: refresh medido 53ms (meses 10 + totais 9 + pág500 30 + count 4; era ~2s, 38×); totais idênticos pré/pós (`399.70/1004987.90`); downgrade/upgrade `1a2b3c4d5e6f` reversível em cópia; head único; ressalvas: `pyproject` ignora RUF001-003 global (preferir noqa local), docstring migração cita `Revises: f4a1b2c3d9e0` mas `down_revision` correto `a15f4e2d9c31`, busca-ativa do caixa ainda full-load (~0,4s/keystroke em 7,6k).
- **2026-09-15 — Fase 4.17 (ficha scroll + turnos botões + frequência 100) ✅:**
  - `views/alunos.py`: aba Ficha vira `QScrollArea` direto (widgetResizable, NoFrame, sem scroll horizontal) + `addStretch`; `views/funcionarios.py`: editor turnos sem +/- por linha (linhas fixas alinhadas cmb 120/custom 120/time 80 + seleção por clique borda `#5AC8FA`) + 2 botões abaixo c/ ícones (Adicionar / Remover selecionado-ou-último); `views/frequencia.py`: combo/completer 50→100 (cache 7,6k, evita segfault de 7k no completer).
  - Verificação Linux: 198 passed +1 skipped, ruff/mypy limpos, smoke offscreen (5 abas, ficha `QScrollArea`, turnos add+remove) ok; commit `6630791`.
  - Auditoria gerente 2026-09-15: APROVADO c/ ressalva — `pyproject` passou a ignorar `E501` global (19 linhas >100 ocultas em `caixa/dashboard/frequencia/funcionarios`; mesmo anti-padrão do RUF já corrigido) + `# noqa: E501` removidos em `caixa.py`/`dashboard.py` (ainda NÃO commitados). Prompt de correção entregue p/ outro agente (reverter p/ noqa local).
- **2026-09-14 — Fase 4.15 (vencimento ancorado + ficha) ✅:**
  - `core/plano.py` `vencimento_no_mes(ano, mes, dia_base)` com `calendar.monthrange` clamp (31→28/29/30); testes clamp fev/bissexto/30d; `services/cobranca.py` por matrícula vigente com `dia_base = mat.vigencia.inicio.day`, `venc_mes = vencimento_no_mes(...)`, pula se `venc_mes > hoje`, `competencia = venc_mes YYYY-MM`, trava `(venc_mes - ultimo).days >= duracao`; `viewmodels/alunos.py` matricular primeiro débito `venc = inicio` (não 10); `views/caixa.py` `NovoPagamentoDialog(dia_base)` default `vencimento_no_mes` do mês atual ancorado na matrícula ativa (sem matrícula → hoje).
  - `core/ficha.py` `AvaliacaoFisica` (peso/altura/gordura/medidas 6 campos + saúde 4 Text + contato, validações >0, medidas normalizadas, texto legível `Braço 30cm · Peito...`); `infra/models/avaliacao_fisica.py` + migração `a15f4e2d9c31` + repos SQL/memória + `viewmodels/ficha.py` Qt-free (salvar/listar desc); `views/alunos.py` aba "Ficha" em `PerfilAlunoDialog` (grade medidas + QTextEdit saúde + histórico lista clicável + Nova/Salvar/Excluir), integrada via `AppContext.ficha_vm` e `AlunosView(ficha_vm)`, fotos já ignoradas.
  - Verificação: 187 passed +1 skipped, ruff/mypy limpos, `alembic upgrade` `a15f4e2d9c31` + downgrade ok, smoke offscreen perfil Ficha (5 abas) ok. **RB01-RB05, hardware intocados.**
- **2026-09-14 — Fase 4.14 (campos obrigatórios configuráveis) ✅:**
  - `ui/config_store.py` `UiConfig.cadastro_obrigatorios: dict[str,bool]` (cpf, telefone, email, data_nasc, endereco; default tudo False; normaliza desconhecidas fora; persiste em `data/gymflux_config.json`); `ui/views/config.py` categoria Cadastro com 5 checks + salva+aplica sem restart; `ui/views/alunos.py` `_AlunoForm.aplicar_obrigatorios(config)` com "*" dinâmico nos labels + `_obrigatorios_atual()` lendo `ConfigStore` na abertura; `ui/viewmodels/alunos.py` `cadastrar/atualizar(obrigatorios: dict|None)` validam e levantam `ValueError "X é obrigatório"`; `tests/ui` cobre 5 campos + Nome + persistência + form.
  - Verificação Linux: 175 passed + 1 skipped, ruff/mypy limpos, smoke offscreen Alunos + Configurações + `gymflux db upgrade` ok. **core/aluno.py (Nome obrigatório) e infra/hardware intocados.**
- **2026-09-12 — chore(tests): suite rápida ✅ (commit `618a071`):**
  - PBKDF2 configurável: `core/aluno.py` +`_iteracoes_pbkdf2()` lendo `GYMFLUX_PBKDF2_ITERATIONS` (default prod 100_000 INALTERADO; `conferir_senha` já lia a contagem do hash, hashes antigos seguem válidos); `tests/conftest.py` fixa 1000 via fixture autouse + offscreen centralizado. 2 testes-guarda do default em `unit/core/test_senha_hash.py`.
  - Qt: `integration/ui/conftest.py` (`ctx` função-escopo + `dash` view direta sem montar 7 abas); `waitExposed` removido (processEvents); teardown destrói top-levels via `shiboken6.delete` (views vazavam 1000+ widgets/run por lambdas `self` em signals — governança impediu fix em prod, mitigado só nos testes). Nenhum sleep fixo existia (`waitSignal` do bridge já era o padrão certo).
  - Coverage fora do default (`addopts=-v`; CI: `uv run pytest --cov=gymflux --cov-report=term-missing`); xdist avaliado e REJEITADO (7,5s vs 2,5s serial — spawn domina); markers `unit|integration|ui|slow` (`-m "not slow"`, `-m ui` ok).
  - Migrations isolado: upgrade roda em `tmp_path` via `GYMFLUX_DB_URL` + `cache_clear` (+`slow`); `data/gymflux.db` intocado; `test_migrations_criam_tabelas` ganhou `import gymflux.infra.models` (antes só passava por ordem de imports). Infra com engine `:memory:` por sessão + limpeza por teste.
  - Reorg `tests/unit|integration`: splits por domínio (regras RB01-RB05, senha valid/hash/aluno, identificar teclado-cartão/funcionário, liberar fluxo/regras, VMs por tela, views por tela, theme puro/render, repos por entidade). Nenhum teste perdido.
  - Verificação Linux: **146 passed + 1 skipped** (145 +2 guardas −1 fusão theme), `uv run pytest -q` 3,4–5,2s (3 rodadas; 18,1s→~4s com cov fora), ruff/mypy limpos. **Lógica prod, segurança (100k), regras e UI intocados.**
  - Nota env: `uv sync --group dev` REMOVE o extra `ui` (PySide6 some) — usar `uv sync --group dev --extra ui`.

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
6. **GymFlux** — nome sem marca Henry (ADR-007/ADR-009).
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
- [x] Nome: **GymFlux** v1 puro (sem GMS).
- [x] Modelo catraca: **Henry 7x padrão** (dono 2026-09-15, serial sem biométrica acoplada) — commissioning Fase 3 usa valores `csg*`/relé do 7x padrão.
- [x] Fase 4.1 aplicada (commit no dashboard + nome no log).
- [x] Fase 4.4 (feedback dono 2026-09-12) ✅: aba Configurações + dashboard enxuto (ver §4).
- [x] Fase 4.5 (feedback dono 2026-09-12) ✅: perfil editável + Caixa + Planos cards + Funcionários (ver §4).
- [x] Follow-up Fase 4.5 resolvido na 4.6 (`funcionario_id` em `acesso_logs`).
- [x] Fase 4.6 (feedback dono 2026-09-12) ✅: click-perfil, log do dia, Frequência global/do aluno, legados de pagamentos removidos (ver §4).
- [x] Fase 4.6 original (feedback dono) ✅ concluída — ver linha acima; `test_pagamentos_situacao_rb01` saiu com o `PagamentosViewModel` (RB01 segue em `tests/core`).
- [x] Bandeja ao fechar ✅ (gerente 2026-09-15): `closeEvent` minimiza p/ tray (ícone+menu Abrir/Sair, balão "catraca ativa", `desconectar` só no Sair real); `tests/integration/ui/test_tray.py` verde. Resta (pós-MVP): gateway pagamento (Pix recorrente — falta escolher provedor).
- [ ] Biometria (dono 2026-09-15): sensor USB direto no PC → caminho B (SDK Suprema `NBioBSP`/`UFScanner`, match no PC, templates no SQLite). Adiado p/ commissioning Fase 3 (dono sem acesso à VM no momento).
- [ ] Futuro: app multi-catracas Henry7x (TCP/IP, USB, multi-unidades) — arquitetura `Henry7xDriver` por equipamento já prevê.
- [x] Fase 4.14 (feedback dono 2026-09-15) ✅: campos obrigatórios do cadastro configuráveis na tela Configurações (só essenciais; asterisco dinâmico + validação).
- [x] Fase 4.7 (feedback dono 2026-09-12) ✅: modo claro + alternância de tema sem restart (ver §4).
- [x] Renomeação GymFlux (dono 2026-09-12, após 4.6/4.7) ✅: `src/gymflow`→`src/gymflux` (git mv), imports, `GYMFLUX_*`, `data/gymflux.db`, marca UI/docs, alembic (revisions intactas), `uv lock` + `requirements*.txt` p/ sem-uv. Verificação 2026-09-12: 146 passed + 1 skipped, ruff/mypy limpos, `gymflux --help`/`db upgrade`/smoke UI offscreen ok. Nota histórica em `docs/DECISIONS.md` (único residual `gymflow` permitido).
- [x] Fluxo senha-na-catraca (estilo SCA) — Fase 4.3 parcial (2026-09-12, sem driver): credencial no `Aluno` (`senha_hash` PBKDF2+salt + `cartao_id`, migração `3f9a2c1bd4e5`), `IdentificarAcessoService` (TECLADO|CARTAO → `LiberarAcessoService`), mock `simular_teclado`/fila, painel verificação `NOME — LIBERADO/NEGADO` + campos senha/cartão no dialog. Falta (commissioning VM): loop de identificação via `ColetaEventos` + parse real do `SRegistro`/`RespostaOn` (TODO em `identificar_acesso.py`, DLL_CONTRACT §3.4).
- [x] `cartao_id` duplicado: moot — cartão removido na Fase 4.8 (decisão dono 2026-09-12).
- [x] Fase 4.8 (feedback dono 2026-09-12) ✅: senha visível no perfil, sem cartão, inatividade 90d (ver §4).
- [x] Fase 4.9 (feedback dono 2026-09-12) ✅: catraca (status+modal detalhes, toast 4s, log vermelho, CPF/senha + Liberar único, sem Bloquear), alunos (2 botões + contexto, header filtra, perfil em abas + Liberar), modais/planos em grade, caixa (sidebar + stats + combo pesquisável + vencimento só no perfil), config em categorias (LIVRE vs SENHA por direção, default entrada SENHA/saída LIVRE).
- [ ] Importação SCA: **adiada pelo dono** (2026-09-15: sem dump; só há `henry.fdb` demo Henry 2011 no repo).
- [x] Identidade visual aprovada: azul `#5AC8FA` + preto `#0F1113` + lima suave `#A3D65C` — aplicar como tema QSS na Fase 4.2.
- [ ] VM Windows 32-bit: `dump_henry_typelib` + checklist `docs/DLL_CONTRACT.md` §4.1 (layout exato `SComConfig`/`SAcionaCtrl`, valores `csg*` do 7x padrão, convenção relé 1=entrada/2=saída). Dono sem acesso no momento (2026-09-15) — Fase 3/biometria seguem no mock.
- [x] Fase 4.16 (dono 2026-09-15) ✅: caixa fluido em 7k+ (medido ~2s→53ms/refresh, auditoria gerente) → pushdown SQL + refresh único; horários de funcionário em turnos (manhã/tarde) com boa legibilidade (ver §4).
- [ ] Nota: `docs/` e `vendor/` são 100% gitignored — atualizações do contrato (§3/§4) e `dumps/` vivem só localmente, não sobem no commit.
- [x] Correções Fase 2.1 aplicadas (2026-09-11: mypy override, teste duplicado, session_scope, campos não persistidos).
- [x] Fase 4.10-A (feedback dono 2026-09-12) ✅: tema claro (containers `#E8EDF1` + borda `#C8D0D8` + sombra leve + `QTabBar::tab:selected` `#5AC8FA`) + catraca moderno (header compacto+Detalhes, centro CPF/senha+Liberar, logs/giros lado a lado, toast) — ver §4.
- [x] Fase 4.10-B (telas alunos/planos/frequência/caixa) ✅: alunos (observações QTextEdit 80px + endereço + Salvar + filtro Excel), planos (cards verticais compactos + PERSONALIZADO dias), frequência (chk Dia + combos 500+ com paginação), caixa `reabrir_mes` + btn Reabrir — ver §4.

## 9. Checklist para Próxima Sessão

1. Ler este arquivo + `docs/ARCHITECTURE.md` + `docs/DLL_CONTRACT.md`.
2. `uv sync --group dev --extra ui && uv run pytest` deve passar (153 passed + 1 skipped HW em 2026-09-12).
3. Se houver `vendor/Henry/Henry7x/Kernel7x.dll`, rodar `scripts/inspect_dll.py`.
4. Não quebrar regra 32-bit: `real.py` só Windows 32-bit via COM, nunca `ctypes.CDLL`.

## 10. Notas de Cross-Platform

- Em Linux, `hardware/henry7x/real.py` deve falhar graciosamente com `RuntimeError("Disponível apenas em Windows 32-bit")`.
- Factory `get_henry_driver()` decide por `sys.platform` + env var `GYMFLUX_HENRY_MOCK=1`. Em prod usa `win32com.client.Dispatch("Henry.Kernel7x")`, não `ctypes`.
- Build Windows: usar GitHub Actions `windows-latest` com Python 3.11 32-bit (`architecture: x86`) ou VM local. Windows 64-bit roda app 32-bit via WOW64 sem problema.
- `vendor/` e `docs/` em `.gitignore:74` — ambos ignorados p/ GitHub (interno).
- Serial: `ListaPortasSeriais` → escolher `COM3` etc, `SComConfig` define baud/paridade; `AdicionaCard(SComConfig, int)` abre porta.

---
*Última atualização: 2026-09-15 por gerente (auditoria Fase 4.16, 196 passed). Mantenha este arquivo enxuto e factual.*
