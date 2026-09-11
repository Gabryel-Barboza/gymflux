# Decisões de Arquitetura (ADRs) — GMS

Formato leve de ADR: Contexto → Decisão → Consequências. Revisar a cada marco.

---

## ADR-001 — Python como linguagem base

**Data:** 2026-09-11 · **Status:** Aceito · **Autor:** Gabryel + bootstrap agent

**Contexto:** Autor é especialista Python. Alternativas nativas Windows: C# (.NET 8/WPF), Delphi (legado Henry), Java. `kernel7x.dll` é 32-bit Windows, sugere .NET por interop P/Invoke mais maduro. Produto final deve ser .exe/.msi para recepção de academia (usuário não-técnico).

**Opções avaliadas:**

| Opção | Prós | Contras |
|-------|------|---------|
| **Python (PySide6 + PyInstaller)** | Expertise existente, prototipagem rápida, ecossistema dados, SQLite/SQLAlchemy maduros, mock fácil Linux | Requer Python 32-bit no build, bundle maior (~80-150MB), interop via ctypes menos ergonômico que P/Invoke |
| C# WPF/WinForms + .NET 8 | Interop nativo com DLL, instalador trivial, performance, suporte Henry (exemplos em C#) | Curva aprendizado, sem expertise autor, overkill para CRUD |
| Electron/Node | UI web rica, cross-platform | Pesado, interop DLL via ffi-napi frágil, consumo RAM alto |
| Java Swing/JavaFX | Cross-platform, JNA para DLL | Verboso, UX datada, bundle grande |

**Decisão:** Usar **Python 3.11, src-layout, uv**, com PyInstaller 32-bit + Inno Setup. Mitigar risco DLL com camada `hardware/henry7x/interface.py` + `mock.py` + testes Windows CI.

**Consequências:**
- Build de release **obrigatoriamente** em Windows com Python 3.11 32-bit (`architecture: x86` no Actions ou VM).
- `ctypes.WinDLL` (stdcall) em `real.py`, não `CDLL`. Falha graciosa em Linux.
- Tamanho do .exe maior; aceitável para academia (instalação única).

---

## ADR-002 — SQLite como DB inicial (SQLAlchemy 2.0 + Alembic)

**Data:** 2026-09-11 · **Status:** Aceito

**Contexto:** Academia típica = 1 PC recepção, sem servidor, sem TI. Precisa funcionar offline. Futuro: rede multi-catraca ou nuvem.

**Decisão:** **SQLite** arquivo local `data/gms.db`, via SQLAlchemy 2.0 Typed + Alembic. URL configurável (`GMS_DB_URL`) para migrar a Postgres/MySQL sem reescrever repos.

**Consequências:**
- Zero infra, backup = copiar arquivo.
- Limite de concorrência OK (1 escrita por vez). Se escalar, migra para Postgres.
- Alembic desde o dia 0 evita dor de migração.

---

## ADR-003 — PySide6 para UI desktop (faseada)

**Data:** 2026-09-11 · **Status:** Proposto (confirmar na Fase 4)

**Contexto:** Precisa de tabelas de alunos, formulários, dashboard catraca tempo real, captura biometria. Opções: Tkinter (nativo, feio/limitado), CustomTkinter (melhor, mas Tkinter base), PyQt6 (GPL/comercial), PySide6 (LGPL), Kivy (mobile-first).

**Decisão:** **PySide6 (Qt6)** adiado para Fase 4. Fase 1-2 usa CLI (`argparse` + `rich`) e `services` testáveis sem UI. UI depende apenas de `services`, nunca de `hardware` direto.

**Consequências:**
- LGPL permite distribuição comercial sem abrir código (dinâmico).
- Qt maduro para tabelas/forms, signals/slots casam com eventos da catraca.
- CLI permite dev Linux sem Qt.

**Alternativa se bundle ficar pesado:** `CustomTkinter` ou `Dear PyGui`.

---

## ADR-004 — Licença MIT

**Data:** 2026-09-11 · **Status:** Proposto (aguardando confirmação do dono)

**Contexto:** Quer open-source. Opções: MIT (permissiva), Apache-2.0 (permissiva + patente), GPLv3 (copyleft forte), AGPLv3 (copyleft rede).

**Decisão:** **MIT** como padrão (arquivo `LICENSE` já criado). Mais permissiva, maximiza adoção por academias/fornecedores. Se houver medo de fork fechado concorrente, migrar para **AGPLv3** antes do v1.0 — AGPL força liberar código mesmo como serviço.

**Consequências:**
- MIT: qualquer um pode forkar fechado. Bom para adoção, ruim para proteção.
- Apache-2.0 seria ligeiramente melhor proteção patentes, sem copyleft. Troca trivial se preferir.
- Escolha deve ser selada antes de aceitar contribuições externas.

---

## ADR-005 — Mock-first e estratégia cross-platform

**Data:** 2026-09-11 · **Status:** Aceito

**Contexto:** Dev em Linux x86_64, prod em Windows 32-bit DLL. Não dá para testar hardware real no dia-a-dia.

**Decisão:** 
- `hardware/henry7x/interface.py` define contrato (`Henry7xDriver` ABC).
- `mock.py` implementa simulação (libera/bloqueia, timeout, evento giro via `threading.Timer`).
- `real.py` só carrega em `sys.platform=="win32"` e Python 32-bit; caso contrário `RuntimeError`.
- `factory.py:get_henry_driver()` decide por `GMS_HENRY_MOCK` env + plataforma.
- `scripts/inspect_dll.py` usa `pefile` + `strings` para extrair exports sem precisar Windows.

**Consequências:**
- Dev Linux 100% funcional.
- Testes unitários sempre contra mock; integração real só em Windows CI/VM.
- `core/services` nunca sabem se é mock ou real.

---

## ADR-006 — uv e Python pinado

**Data:** 2026-09-11 · **Status:** Aceito

**Contexto:** pip/poetry/conda fragmentados. Projeto precisa de ambientes reprodutíveis e dev rápido.

**Decisão:** `uv` como único gerenciador, `3.11` pinado em `.python-version` e `requires-python >=3.11,<3.13`. `uv_build` + `src-layout`. Nunca usar pip/poetry direto.

**Consequências:**
- `uv sync --group dev` canônico. `uv run` para tudo.
- Python 3.11 escolhido por ser LTS com wheels estáveis para PySide6/SQLAlchemy e suporte PyInstaller 32-bit. 3.12 funciona, 3.14 ainda sem 32-bit estável Windows.

---

## Template para novas ADRs

```markdown
## ADR-0XX — Título
**Data:** AAAA-MM-DD · **Status:** Proposto/Aceito/Rejeitado/Supercedido
**Contexto:** ...
**Decisão:** ...
**Consequências:** ...
```
