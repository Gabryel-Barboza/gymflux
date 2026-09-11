# Decisões de Arquitetura (ADRs) — GMS

Formato leve de ADR: Contexto → Decisão → Consequências. Revisar a cada marco.

---

## ADR-001 — Python como linguagem base (atualizada 2026-09-11)

**Data:** 2026-09-11 · **Status:** Aceito · **Autor:** Gabryel

**Contexto:** Autor especialista Python. `Kernel7x.dll` é **COM 32-bit** (`DllRegisterServer`/`DllGetClassObject`, não exports planos — `scripts/inspect_dll.py` confirma `Machine 0x14c` + só 4 exports COM). Henry expõe `Henry.Kernel7x` via `New-Object -ComObject` com 100+ métodos (`docs/DLL_CONTRACT.md:30` `AdicionaCard(SComConfig,int)`, `ListaPortasSeriais`, `Bio_*`, `ColetaEventos`). Alternativas: C# COM interop nativo vs Python `pywin32`.

**Opções avaliadas:**

| Opção | Prós | Contras |
|-------|------|---------|
| **Python + pywin32 COM + PyInstaller 32-bit** | Expertise existente, `win32com.client.Dispatch("Henry.Kernel7x")` maduro, mock fácil Linux, SQLAlchemy, PySide6 | Requer Python 32-bit no build, bundle 80-150MB, COM só Windows |
| C# WPF/.NET 8 | COM interop nativo, exemplos Henry em C# | Curva aprendizado, overkill CRUD |
| ctypes.WinDLL puro | Funcionaria se fosse DLL plana | **Não funciona** aqui — Kernel7x é COM, não tem `Conecta@8` exportado |

**Decisão:** Python 3.11 src-layout uv, COM via `pywin32` em `real.py` (não `ctypes.WinDLL`). Mitigar com `interface.py` + `mock.py` + CI Windows 32-bit.

**Consequências:**
- Build release **obrigatoriamente** Windows 10/11 64-bit (WOW64) com **Python 3.11 32-bit** (`py -0p` lista, `python -c "import struct;print(struct.calcsize('P')*8)"` deve dar 32).
- `real.py` usa `win32com.client.Dispatch`, não `ctypes`. Em Linux levanta `RuntimeError`.
- Conexão **Serial** via `SComConfig` (baud, paridade, porta COMx) — `ListaPortasSeriais` enumera portas.

---

## ADR-002 — SQLite como DB inicial (SQLAlchemy 2.0 + Alembic) — confirmado para 2000+ registros

**Data:** 2026-09-11 · **Status:** Aceito — bench 2026-09-11 valida

**Contexto:** Academia típica = 1 PC recepção, sem servidor, 2000 alunos hoje, pode ir a 10k. Precisa offline + backup simples.

**Bench real (Linux, SQLite WAL, 5000 alunos):**
- INSERT 5000 alunos: 28ms (0.005ms/aluno)
- 1000 buscas `cpf=?` + `nome LIKE 'Aluno 1%'`: 2.55s total → **2.5ms/busca** (índice em `cpf`)
- JOIN aluno+pagamentos + GROUP BY 100 linhas: 6ms
- Tamanho DB 5000 alunos + pagamentos: **448KB**

**Decisão:** **SQLite** `data/gms.db` + `SQLAlchemy 2.0 Typed` + `Alembic` + índice em `cpf`/`matricula`. URL `GMS_DB_URL` migrável a Postgres sem reescrever repos. Modo WAL + `PRAGMA journal_mode=WAL` + `synchronous=NORMAL` já cobre performance.

**Consequências:**
- 2000 registros é trivial (SQLite aguenta **milhões**, limite arquivo 281TB). Academia de 2000 cabe em <1MB.
- Zero infra, backup = copiar arquivo. Concorrência 1 escritor só, mas recepção só tem 1 thread escrevendo acesso.
- Se escalar para multi-catraca rede, migra para Postgres só mudando URL.

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

## ADR-004 — Licença Apache-2.0 vs GPLv3 (atualizada 2026-09-11)

**Data:** 2026-09-11 · **Status:** Proposto — decidir entre Apache-2.0 (recomendada) e GPLv3 · **Autor:** Gabryel

**Contexto:** Projeto open-source que será instalado em academias (uso comercial permitido). `kernel7x.dll` é proprietário Henry e não entra na licença. Precisa decidir copyleft vs permissiva + proteção patentária.

| Critério | MIT (antiga) | **Apache-2.0** | **GPLv3** | AGPLv3 |
|----------|--------------|----------------|-----------|--------|
| Uso comercial | ✅ | ✅ | ✅ (mas derivados devem ser GPL) | ✅ (rede também) |
| Fork fechado permitido | ✅ sem liberar código | ✅ sem liberar, mas exige aviso + licença | ❌ derivados devem ser GPLv3 | ❌ + rede deve liberar |
| Proteção patentes | ❌ nada | ✅ grant expresso + retaliação se processar | ✅ grant implícito, sem retaliação clara | ✅ |
| Obriga liberar código fonte | ❌ | ❌ só NOTICES | ✅ se distribuir binário | ✅ mesmo como SaaS |
| Compatível com `kernel7x.dll` proprietário? | ✅ | ✅ | ⚠️ zona cinzenta (link com DLL fechada pode violar GPL se distribuir junto) | ⚠️ |
| Adoção por fornecedores | ★★★ | ★★★ (preferida por empresas) | ★☆☆ (empresas evitam) | ★☆☆ |

**Decisão proposta:** **Apache-2.0**.
- Motivo: você quer que academias/fornecedores adotem sem medo jurídico, mas com proteção contra alguém patentear e processar o projeto. Permite vender instalação/suporte fechado sem obrigar a liberar customizações internas da academia.
- **GPLv3** só faria sentido se o objetivo for **forçar** que todo fork/melhoramento volte para a comunidade (copyleft forte). Desvantagem: quem instalar `GymFlow + kernel7x.dll` e distribuir o bundle pode ter que lidar com compatibilidade GPL+proprietário (Henry não é GPL). Mitigável separando `vendor/` 100% ignorado, mas ainda gera atrito jurídico e afasta empresas.

**Consequências Apache-2.0:**
- Arquivo `LICENSE` será substituído por Apache-2.0 (troca 1 comando).
- Mantém atribuição obrigatória + aviso de mudanças, sem copyleft.
- Se depois quiser copyleft, pode dual-licenciar ou migrar antes do v1.0 com consentimento de contribuidores.

**Se escolher GPLv3:** avisar — precisaremos adicionar `COPYING`, header GPL em cada arquivo, e NUNCA distribuir `Kernel7x.dll` no mesmo artefato sem exceção de linking.

---

## ADR-005 — Mock-first e estratégia cross-platform (Serial COM)

**Data:** 2026-09-11 · **Status:** Aceito

**Contexto:** Dev em Linux x86_64, prod em Windows 32-bit COM Serial. Não dá para testar hardware real no dia-a-dia. Conexão é **Serial** (`SComConfig`), não TCP. `ListaPortasSeriais` lista `COM1`..`COMn`. `AdicionaCard(SComConfig, int)` abre porta, `RemoveCard`, `ColetaEventos(int, string)` faz polling. Baud/paridade em `SVelocidade`/`SComConfig`.

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

## ADR-007 — Nome GymFlow (vs HenryFlow)

**Data:** 2026-09-11 · **Status:** Aceito
**Contexto:** `HenryFlow` contém marca registrada "Henry" (Henry Equipamentos). Uso pode gerar oposição marcária, mesmo open-source.
**Decisão:** **GymFlow**. Curto, sem marca de terceiro, domínio `.com` genérico mas livre para app desktop. Descartados: IronGate/FitCatraca/TitanGym (muito nicho). `Henry` só aparece como `Henry 7x` descritivo em docs.
**Consequências:** Renomear `pyproject.toml` `name: gymflow` + binário `gymflow.exe` + `GymFlow-Setup.exe`. Manter `GMS` como sigla interna até v0.2.

## ADR-008 — Gitignore vendor + docs

**Data:** 2026-09-11 · **Status:** Aceito
**Contexto:** `vendor/` contém artefatos proprietários para inspeção local do contrato. `docs/` contém decisões internas.
**Decisão:** `vendor/` e `docs/` 100% ignorados (`.gitignore:74`) — não sobem ao GitHub. `data/*.db` + `dumps/*.txt` já ignorados.
**Consequências:** `git status` não mostra `vendor/` nem `docs/`.

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
