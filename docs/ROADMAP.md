# Roadmap — GMS

> Fases sequenciais; cada fase tem entregáveis testáveis. Marque `[x]` ao concluir.

## Fase 0 — Bootstrap (atual) ✅ 2026-09-11

- [x] `uv init` + `pyproject.toml` (Python 3.11, src-layout)
- [x] Docs: `README`, `ARCHITECTURE`, `REQUIREMENTS`, `DLL_CONTRACT`, `DECISIONS`, `ROADMAP`, `AGENTS.md`
- [x] Estrutura `src/gms_app` + `scripts/inspect_dll.py`
- [x] `.gitignore`, `LICENSE` (MIT)
- [ ] Git init + commit inicial

**Próxima entrada:** dump PowerShell da `kernel7x.dll` para preencher `DLL_CONTRACT`.

## Fase 1 — Domínio + Hardware Mockado + Testes (2-3 semanas)

**Objetivo:** regras de negócio puras, sem DB nem UI nem DLL real.

- [ ] `core/aluno.py`, `plano.py`, `pagamento.py`, `acesso.py`, `regras.py`
- [ ] `hardware/henry7x/interface.py` (ABC) + `mock.py` + `factory.py` + `hardware/biometric/interface.py`
- [ ] `services/liberar_acesso.py` (orquestra regra + hardware mock + log em memória)
- [ ] `config/settings.py` (pydantic-settings)
- [ ] Testes: `tests/core/test_regras.py`, `tests/services/test_liberar_acesso.py` (mock), `tests/hardware/test_mock.py`
- [ ] `scripts/inspect_dll.py` funcional (pefile + strings)
- [ ] CLI `gms mock-demo` demonstrando fluxo

Critério de aceite: `uv run pytest` verde em Linux, `RegraAcesso` cobre inadimplente/vigência/bloqueio.

## Fase 2 — Persistência SQLite (1-2 semanas)

- [ ] `infra/db.py` (engine, Base, sessionmaker)
- [ ] `infra/models/*` (AlunoModel, PlanoModel, Matricula, Pagamento, AcessoLog) — SQLAlchemy 2.0
- [ ] `infra/repositories/*`
- [ ] Alembic `alembic init` + primeira migração
- [ ] `services` passam a usar repos reais (injeção de dependência)
- [ ] Seed de demo + `gms db upgrade`

Critério: CRUD aluno/plano/pagamento persistido, teste `infra/test_repositories.py` com SQLite `:memory:`.

## Fase 3 — Integração Real kernel7x.dll (2-4 semanas, depende de VM Windows)

- [ ] Preencher `docs/DLL_CONTRACT.md` com dump real
- [ ] `hardware/henry7x/real.py` (ctypes.WinDLL, stdcall, argtypes/restype, tratamento de erro 32-bit)
- [ ] `hardware/henry7x/__init__.py` exporta factory
- [ ] Teste manual em VM Windows 10/11 32-bit com catraca (checklist `docs/DLL_CONTRACT.md` §4)
- [ ] CI opcional: GitHub Actions `windows-latest` + Python 3.11 x86 + mock tests

Critério: em Windows 32-bit, `gms catraca liberar --direcao entrada` gira a catraca de verdade.

## Fase 4 — UI PySide6 (3-4 semanas)

- [ ] `ui/app.py` (QApplication, navegação)
- [ ] Telas: Login operador, Dashboard catraca (status tempo real), Cadastro aluno, Planos, Pagamentos, Relatórios
- [ ] ViewModels que chamam `services` (sem importar hardware direto)
- [ ] `QThread`/`Signal` para eventos da catraca (giro, timeout)
- [ ] Testes UI headless (pytest-qt) + screenshots

Critério: recepcionista cadastra aluno e libera catraca pela UI.

## Fase 5 — Biometria + Instalador + Hardening (2-3 semanas)

- [ ] `hardware/biometric/real.py` (templates, enrol/verify via Henry)
- [ ] `LibBiometria` abstraída (mock vs real)
- [ ] PyInstaller spec (`gms.spec`) + Inno Setup (`installer/gms.iss`)
- [ ] Assinatura de executável (signtool)
- [ ] Logs rotativos, backup 1-click, tratamento offline catraca
- [ ] Manual de instalação + vídeo demo

Critério: `GMS-Setup-0.1.0.exe` instala e roda em PC limpo de academia sem Python pré-instalado.

## Fase 6 — Futuro (pós-MVP)

- Multi-catraca / multi-unidade, Postgres opcional, API REST para app aluno, QR code, gateway pagamento (Pix), relatórios avançados, nuvem opcional.

## Marcos e Tags Git

- `v0.1.0-bootstrap` — Fase 0
- `v0.2.0-domain-mock` — Fase 1
- `v0.3.0-sqlite` — Fase 2
- `v0.4.0-henry-real` — Fase 3
- `v0.5.0-ui` — Fase 4
- `v1.0.0-mvp` — Fase 5

Gere releases com `git tag -a vX.Y.Z -m "..." && git push --tags`.
