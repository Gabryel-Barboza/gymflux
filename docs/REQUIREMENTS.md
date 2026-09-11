# Requisitos — GMS

> MVP inspirado no domínio SCA, sem copiar código. Fases em `docs/ROADMAP.md`.

## 1. Atores

- **Recepcionista** — cadastra alunos, planos, registra pagamentos, libera manualmente.
- **Aluno** — passa cartão/biometria/teclado na catraca; consulta status.
- **Administrador** — relatórios, backup, configuração catraca/biometria.
- **Catraca Henry 7x** — hardware que consome decisões do software.

## 2. Requisitos Funcionais

### RF01 — Gestão de Alunos (CRUD)
- Cadastro: nome, CPF (opcional), data nasc., foto, contato (tel/email), status (ativo/inativo/bloqueado), observações.
- Matrícula com plano e vencimento.
- Busca/filtro por nome/CPF/status.
- Histórico de acessos por aluno.

### RF02 — Planos e Vigência
- Plano: nome, duração (mensal/trimestral/anual/diária), valor, tolerância de atraso.
- Matrícula vincula aluno ↔ plano com data início/fim, status.
- Renovação / upgrade / congelamento.

### RF03 — Pagamentos
- Registro de pagamento (data, valor, forma, competência).
- Cálculo de pendência/atraso; aluno inadimplente = acesso negado (parametrizável).
- Relatório financeiro simples (por período, por plano).

### RF04 — Controle de Acesso (core)
- Ao tentar acesso (cartão/biometria/teclado), sistema avalia:
  - Aluno existe e está ativo?
  - Matrícula vigente?
  - Pagamento em dia (ou dentro da tolerância)?
  - Horário permitido (se houver `grade_horaria`)?
  - Bloqueio manual?
- Decisão: **LIBERADO** (gira catraca) ou **NEGADO + motivo** (exibe no display/buzzer).
- Toda tentativa é logada: timestamp, aluno_id, método, direção (entrada/saída), resultado, motivo, catraca_id.

### RF05 — Integração Henry 7x
- Conectar/desconectar catraca (serial/TCP, configurável).
- Liberar catraca em direção entrada/saída; bloquear.
- Receber evento de giro (confirma passagem) e timeout.
- Status da catraca (online/offline, firmware, contador).
- Suporte a múltiplas catracas (futuro, mas arquitetura preparada).

### RF06 — Biometria (Fase 5)
- Cadastro de digital via leitor Henry (template).
- Associação template ↔ aluno.
- Verificação 1:N ou 1:1 (quando cartão + digital).
- Tratamento de falha de leitura.

### RF07 — Métodos de Identificação
- Cartão/RFID (código), teclado (matrícula/senha), biometria, QR (futuro).
- Todos mapeados para `aluno_id`.

### RF08 — Relatórios e Dashboard
- Acessos do dia, taxa ocupação, inadimplentes, aniversariantes.
- Export CSV/PDF (futuro).

### RF09 — Backup e Admin
- Backup/restore do SQLite (copiar arquivo + dump).
- Configuração via `.env` / tela admin (caminho DLL, porta catraca, tolerância).

## 3. Requisitos Não-Funcionais

| ID | Requisito | Critério |
|----|-----------|----------|
| RNF01 | Plataforma | Windows 10/11 64-bit, app 32-bit (DLL). Dev Linux suportado via mock. |
| RNF02 | Instalação | Instalador .exe/.msi (Inno Setup), double-click, sem dependência manual. |
| RNF03 | Offline-first | Funciona sem internet; SQLite local. |
| RNF04 | Performance | Decisão de acesso < 500ms após identificação (sem contar biometria). |
| RNF05 | Confiabilidade | Log de acesso nunca perdido; transação atômica. |
| RNF06 | Usabilidade | Recepcionista treina em <30min; UI em PT-BR. |
| RNF07 | Segurança | Templates biométricos não em claro; logs auditáveis; sem senhas em texto. |
| RNF08 | Testabilidade | `core/services` 100% testáveis sem hardware; mocks para catraca. |
| RNF09 | Manutenibilidade | Código 100% próprio, tipado (mypy), lint (ruff), testes (pytest). |
| RNF10 | Licensing | MIT, sem distribuir `kernel7x.dll` (usuário provê sua DLL licenciada Henry). |

## 4. Regras de Negócio (exemplos)

- RB01: Aluno com pagamento atrasado > `tolerancia_dias` (default 3) tem acesso negado.
- RB02: Matrícula expirada = negado, mesmo que pagamento recente (precisa renovar).
- RB03: Bloqueio manual do admin sobrepõe qualquer liberação.
- RB04: Acesso liberado expira em `timeout_giro` (default 7s) se não houver giro; catraca bloqueia e loga `TIMEOUT`.
- RB05: Entrada e saída são direções distintas; anti-passback opcional (não deixar entrar duas vezes sem sair).

## 5. Fora de Escopo (MVP)

- App mobile do aluno, integração gateway pagamento online, multi-unidade nuvem, controle de treino/ficha, financeiro completo (NF-e). Podem virar Fase 6+.

## 6. Requisitos de Integração DLL

- Ver `docs/DLL_CONTRACT.md`. Métodos mínimos esperados: `Conectar`, `Desconectar`, `LiberarCatraca`, `Bloquear`, `Status`, callbacks de giro/teclado/biometria.
- Assinaturas exatas a confirmar após dump PowerShell / `inspect_dll.py`.

## 7. Critérios de Aceite (MVP)

- [ ] Cadastrar aluno + plano + pagamento e ter acesso liberado em mock.
- [ ] Aluno inadimplente tem acesso negado com motivo claro.
- [ ] `uv run pytest` verde em Linux (mocks).
- [ ] Em Windows 32-bit com DLL real, catraca libera/bloqueia de verdade.
- [ ] Instalador gera .exe que roda sem instalar Python manualmente.
