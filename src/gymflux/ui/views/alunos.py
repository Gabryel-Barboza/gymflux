"""Tela de alunos — tabela + busca, cadastro, perfil editável e matrícula."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol

from loguru import logger
from PySide6.QtCore import QDate, QPoint, Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gymflux.core.aluno import Aluno, StatusAluno
from gymflux.core.pagamento import FormaPagamento, Pagamento
from gymflux.ui.viewmodels.alunos import AlunosViewModel
from gymflux.ui.viewmodels.frequencia import FrequenciaViewModel
from gymflux.ui.views.caixa import NovoPagamentoDialog


class PagamentosProto(Protocol):
    """Subconjunto usado pelo perfil: lista + registra (Pagamentos ou Caixa VM)."""

    def do_aluno(self, aluno_id: str) -> list[Pagamento]: ...
    def registrar(
        self,
        *,
        aluno_id: str,
        valor: Decimal | float | str,
        data_vencimento: date,
        forma: FormaPagamento | str | None = None,
        pago: bool = False,
        data_pagamento: date | None = None,
        competencia: str | None = None,
    ) -> Pagamento: ...


class _AlunoForm(QWidget):
    """Campos do aluno em grade: fileiras horizontais por domínio, largura contida."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMaximumWidth(560)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        self.edt_nome = QLineEdit()
        self.edt_cpf = QLineEdit()
        self.edt_cpf.setPlaceholderText("somente números (opcional)")
        self.edt_nasc = QLineEdit()
        self.edt_nasc.setPlaceholderText("AAAA-MM-DD (opcional)")
        self.edt_tel = QLineEdit()
        self.edt_email = QLineEdit()
        self.edt_endereco = QLineEdit()
        self.edt_endereco.setPlaceholderText("Rua, número, bairro (opcional)")
        self.edt_obs = QTextEdit()
        self.edt_obs.setPlaceholderText("Observações (opcional)")
        self.edt_obs.setMinimumHeight(80)
        self.edt_senha = QLineEdit()
        self.edt_senha.setPlaceholderText("4 a 8 dígitos (opcional)")
        self.cmb_status = QComboBox()
        for st in StatusAluno:
            self.cmb_status.addItem(st.value, st)
        # linha 0: Nome* | CPF
        grid.addWidget(QLabel("Nome*:"), 0, 0)
        grid.addWidget(self.edt_nome, 0, 1)
        grid.addWidget(QLabel("CPF:"), 0, 2)
        grid.addWidget(self.edt_cpf, 0, 3)
        # linha 1: Nascimento | Telefone
        grid.addWidget(QLabel("Nascimento:"), 1, 0)
        grid.addWidget(self.edt_nasc, 1, 1)
        grid.addWidget(QLabel("Telefone:"), 1, 2)
        grid.addWidget(self.edt_tel, 1, 3)
        # linha 2: E-mail | Endereço
        grid.addWidget(QLabel("E-mail:"), 2, 0)
        grid.addWidget(self.edt_email, 2, 1)
        grid.addWidget(QLabel("Endereço:"), 2, 2)
        grid.addWidget(self.edt_endereco, 2, 3)
        # linha 3: Senha | Status
        grid.addWidget(QLabel("Senha numérica:"), 3, 0)
        grid.addWidget(self.edt_senha, 3, 1)
        grid.addWidget(QLabel("Status:"), 3, 2)
        grid.addWidget(self.cmb_status, 3, 3)
        # linha 4: Observações (separado, span)
        grid.addWidget(QLabel("Observações:"), 4, 0)
        grid.addWidget(self.edt_obs, 4, 1, 1, 3)

    def preencher(self, aluno: Aluno) -> None:
        self.edt_nome.setText(aluno.nome)
        self.edt_cpf.setText(aluno.cpf or "")
        self.edt_nasc.setText(aluno.data_nasc.isoformat() if aluno.data_nasc else "")
        self.edt_tel.setText(aluno.telefone or "")
        self.edt_email.setText(aluno.email or "")
        self.edt_endereco.setText(aluno.endereco or "")
        self.edt_obs.setPlainText(aluno.observacoes or "")
        self.edt_senha.setText(aluno.senha or "")
        self.edt_senha.setPlaceholderText("em branco = manter atual")
        idx = self.cmb_status.findData(aluno.status)
        if idx >= 0:
            self.cmb_status.setCurrentIndex(idx)

    def dados(self) -> dict[str, str]:
        status = self.cmb_status.currentData()
        return {
            "nome": self.edt_nome.text(),
            "cpf": self.edt_cpf.text(),
            "data_nasc": self.edt_nasc.text().strip(),
            "telefone": self.edt_tel.text(),
            "email": self.edt_email.text(),
            "observacoes": self.edt_obs.toPlainText(),
            "endereco": self.edt_endereco.text(),
            "senha": self.edt_senha.text(),
            "status": str(status) if status is not None else StatusAluno.ATIVO.value,
        }


class NovoAlunoDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Novo aluno")
        self.setMaximumWidth(620)
        layout = QVBoxLayout(self)
        self.form = _AlunoForm(self)
        self.edt_nome = self.form.edt_nome
        self.edt_cpf = self.form.edt_cpf
        self.edt_nasc = self.form.edt_nasc
        self.edt_tel = self.form.edt_tel
        self.edt_email = self.form.edt_email
        self.edt_obs = self.form.edt_obs
        self.edt_endereco = self.form.edt_endereco
        self.edt_senha = self.form.edt_senha
        layout.addWidget(self.form)
        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

    def dados(self) -> dict[str, str]:
        return self.form.dados()


class PerfilAlunoDialog(QDialog):
    """Modal de perfil em abas (Pessoais | Plano/Matrícula | Frequência | Pagamentos) + Liberar."""

    COLUNAS_PAG = ("Vencimento", "Valor (R$)", "Pagamento", "Forma")
    COLUNAS_FREQ = ("Data", "Entradas", "Saídas")

    def __init__(
        self,
        alunos_vm: AlunosViewModel,
        pagamentos_vm: PagamentosProto,
        aluno_id: str,
        parent: QWidget | None = None,
        frequencia_vm: FrequenciaViewModel | None = None,
        dashboard_vm: object | None = None,
    ) -> None:
        super().__init__(parent)
        aluno = alunos_vm.alunos.buscar(aluno_id)
        if aluno is None:
            raise ValueError(f"Aluno id={aluno_id} não encontrado")
        self._vm = alunos_vm
        self._pagamentos = pagamentos_vm
        self._aluno_id = aluno_id
        self._frequencia = frequencia_vm
        self._dashboard_vm = dashboard_vm
        self.setWindowTitle(f"Perfil — {aluno.nome}")
        self.resize(640, 520)
        self.setMaximumWidth(700)
        layout = QVBoxLayout(self)

        tabs = QTabWidget(self)
        # aba 1: Pessoais
        tab_pessoais = QWidget()
        lay_p = QVBoxLayout(tab_pessoais)
        self.form = _AlunoForm(tab_pessoais)
        self.form.preencher(aluno)
        lay_p.addWidget(self.form)
        lay_p.addStretch(1)
        tabs.addTab(tab_pessoais, "Pessoais")

        # aba 2: Plano/Matrícula
        tab_plano = QWidget()
        lay_plano = QVBoxLayout(tab_plano)
        lay_plano.addWidget(QLabel("Matrículas do aluno:"))
        self.tbl_mat = QTableWidget(0, 2)
        self.tbl_mat.setHorizontalHeaderLabels(["Plano", "Vigência"])
        self.tbl_mat.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_mat.horizontalHeader().setStretchLastSection(True)
        lay_plano.addWidget(self.tbl_mat, 1)
        self.btn_matricular = QPushButton("Matricular...")
        lay_plano.addWidget(self.btn_matricular)
        tabs.addTab(tab_plano, "Plano/Matrícula")

        # aba 3: Frequência
        tab_freq = QWidget()
        lay_f = QVBoxLayout(tab_freq)
        self.tbl_freq = QTableWidget(0, len(self.COLUNAS_FREQ))
        self.tbl_freq.setHorizontalHeaderLabels(list(self.COLUNAS_FREQ))
        self.tbl_freq.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_freq.horizontalHeader().setStretchLastSection(True)
        lay_f.addWidget(self.tbl_freq, 1)
        tabs.addTab(tab_freq, "Frequência")

        # aba 4: Pagamentos
        tab_pag = QWidget()
        lay_pag = QVBoxLayout(tab_pag)
        self.tbl_pag = QTableWidget(0, len(self.COLUNAS_PAG))
        self.tbl_pag.setHorizontalHeaderLabels(list(self.COLUNAS_PAG))
        self.tbl_pag.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_pag.horizontalHeader().setStretchLastSection(True)
        lay_pag.addWidget(self.tbl_pag, 1)
        hb = QHBoxLayout()
        self.btn_novo_pag = QPushButton("Novo pagamento")
        hb.addWidget(self.btn_novo_pag)
        hb.addStretch(1)
        lay_pag.addLayout(hb)
        tabs.addTab(tab_pag, "Pagamentos")

        layout.addWidget(tabs, 1)

        # botão Liberar (extra, fora das abas)
        hlib = QHBoxLayout()
        self.btn_liberar = QPushButton("Liberar")
        self.btn_liberar.setToolTip("Liberar catraca para este aluno")
        hlib.addWidget(self.btn_liberar)
        hlib.addStretch(1)
        layout.addLayout(hlib)

        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        # traduz Save -> Salvar
        btn_save = botoes.button(QDialogButtonBox.StandardButton.Save)
        if btn_save is not None:
            btn_save.setText("Salvar")
        botoes.accepted.connect(self._salvar)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

        self.btn_novo_pag.clicked.connect(self._novo_pagamento)
        self.btn_matricular.clicked.connect(self._matricular)
        self.btn_liberar.clicked.connect(self._liberar)
        self._recarregar_pagamentos()
        self._recarregar_frequencia()
        self._recarregar_matriculas()

    def _recarregar_matriculas(self) -> None:
        mats = self._vm.matriculas_do_aluno(self._aluno_id)
        self.tbl_mat.setRowCount(len(mats))
        for row, m in enumerate(mats):
            vig = f"{m.vigencia.inicio.isoformat()} → {m.vigencia.fim.isoformat()}"
            self.tbl_mat.setItem(row, 0, QTableWidgetItem(m.plano.nome))
            self.tbl_mat.setItem(row, 1, QTableWidgetItem(vig))

    def _matricular(self) -> None:
        planos = [(p.id, f"{p.nome} ({p.duracao_dias}d)") for p in self._vm.planos_disponiveis()]
        if not planos:
            QMessageBox.information(self, "Perfil", "Cadastre um plano primeiro (aba Planos).")
            return
        aluno = self._vm.alunos.buscar(self._aluno_id)
        if aluno is None:
            return
        dlg = MatricularDialog(aluno.nome, planos, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self._vm.matricular(self._aluno_id, dlg.plano_id(), dlg.inicio())
        except (ValueError, RuntimeError) as e:
            QMessageBox.warning(self, "Perfil", str(e))
            return
        self._recarregar_matriculas()

    def _liberar(self) -> None:
        # tenta via dashboard_vm se disponível, senão via alunos_vm + mensagem
        if self._dashboard_vm is not None:
            try:
                decisao = self._dashboard_vm.liberar_entrada(self._aluno_id)  # type: ignore[attr-defined]
                QMessageBox.information(
                    self,
                    "Liberar",
                    self._dashboard_vm.resume_decisao(decisao),  # type: ignore[attr-defined]
                )
                return
            except Exception as e:
                QMessageBox.warning(self, "Liberar", str(e))
                return
        # fallback: informa que catraca liberada depende do dashboard
        QMessageBox.information(self, "Liberar", "Use a aba Catraca para liberar com CPF/senha.")

    def _recarregar_frequencia(self) -> None:
        if self._frequencia is None:
            return
        linhas = self._frequencia.resumo_por_dia(self._aluno_id)
        self.tbl_freq.setRowCount(len(linhas))
        for row, (dia, entradas, saidas) in enumerate(linhas):
            for col, v in enumerate((dia.isoformat(), str(entradas), str(saidas))):
                self.tbl_freq.setItem(row, col, QTableWidgetItem(v))

    def _recarregar_pagamentos(self) -> None:
        pags = sorted(
            self._pagamentos.do_aluno(self._aluno_id),
            key=lambda p: p.data_vencimento,
            reverse=True,
        )
        self.tbl_pag.setRowCount(len(pags))
        for row, p in enumerate(pags):
            vals = (
                p.data_vencimento.isoformat(),
                f"{Decimal(str(p.valor)):.2f}",
                p.data_pagamento.isoformat() if p.data_pagamento else "—",
                str(p.forma) if p.forma else "—",
            )
            for col, v in enumerate(vals):
                self.tbl_pag.setItem(row, col, QTableWidgetItem(v))

    def _novo_pagamento(self) -> None:
        aluno = self._vm.alunos.buscar(self._aluno_id)
        if aluno is None:
            return
        dlg = NovoPagamentoDialog(aluno.nome, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            # vencimento editável só no perfil; aqui usa hoje/competência
            venc = dlg.vencimento() if hasattr(dlg, "vencimento") else date.today()
            self._pagamentos.registrar(
                aluno_id=self._aluno_id,
                valor=Decimal(str(dlg.spn_valor.value())),
                data_vencimento=venc,
                forma=dlg.forma(),
                pago=dlg.chk_pago.isChecked(),
                competencia=dlg.edt_comp.text(),
            )
        except ValueError as e:
            QMessageBox.warning(self, "Perfil", str(e))
            return
        self._recarregar_pagamentos()

    def _salvar(self) -> None:
        d = self.form.dados()
        if not d["nome"].strip():
            QMessageBox.warning(self, "Perfil", "Nome é obrigatório.")
            return
        nasc: date | None = None
        if d["data_nasc"]:
            try:
                nasc = date.fromisoformat(d["data_nasc"])
            except ValueError:
                QMessageBox.warning(self, "Perfil", "Nascimento inválido (use AAAA-MM-DD).")
                return
        try:
            status = StatusAluno(d["status"])
        except ValueError:
            QMessageBox.warning(self, "Perfil", "Status inválido.")
            return
        try:
            self._vm.atualizar(
                self._aluno_id,
                nome=d["nome"],
                cpf=d["cpf"],
                data_nasc=nasc,
                telefone=d["telefone"],
                email=d["email"],
                observacoes=d["observacoes"],
                endereco=d["endereco"],
                senha=d["senha"],
                status=status,
            )
        except ValueError as e:
            QMessageBox.warning(self, "Perfil", str(e))
            return
        logger.info(f"[UI] perfil atualizado id={self._aluno_id}")
        self.accept()


class MatricularDialog(QDialog):
    def __init__(
        self, aluno_nome: str, planos: list[tuple[str, str]], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Matricular — {aluno_nome}")
        self.setMaximumWidth(420)
        form = QFormLayout(self)
        self.cmb_plano = QComboBox()
        for plano_id, plano_nome in planos:
            self.cmb_plano.addItem(plano_nome, plano_id)
        self.dat_inicio = QDateEdit(QDate.currentDate())
        self.dat_inicio.setCalendarPopup(True)
        form.addRow("Plano:", self.cmb_plano)
        form.addRow("Início:", self.dat_inicio)
        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        form.addRow(botoes)

    def plano_id(self) -> str:
        return str(self.cmb_plano.currentData())

    def inicio(self) -> date:
        qd = self.dat_inicio.date()
        return date(qd.year(), qd.month(), qd.day())


class AlunosView(QWidget):
    COLUNAS = ("ID", "Nome", "CPF", "Telefone", "Status", "Bloqueio")

    def __init__(
        self,
        vm: AlunosViewModel,
        pagamentos_vm: PagamentosProto | None = None,
        parent: QWidget | None = None,
        frequencia_vm: FrequenciaViewModel | None = None,
        dashboard_vm: object | None = None,
    ) -> None:
        super().__init__(parent)
        self.vm = vm
        self.pagamentos_vm = pagamentos_vm
        self.frequencia_vm = frequencia_vm
        self.dashboard_vm = dashboard_vm
        layout = QVBoxLayout(self)

        hbusca = QHBoxLayout()
        self.edt_busca = QLineEdit()
        self.edt_busca.setPlaceholderText("Buscar por nome ou CPF...")
        self.cmb_status = QComboBox()
        self.cmb_status.addItem("Todos", None)
        for st in StatusAluno:
            self.cmb_status.addItem(st.value, st)
        hbusca.addWidget(self.edt_busca, 3)
        hbusca.addWidget(QLabel("Status:"))
        hbusca.addWidget(self.cmb_status, 1)
        layout.addLayout(hbusca)

        self.tbl = QTableWidget(0, len(self.COLUNAS))
        self.tbl.setHorizontalHeaderLabels(list(self.COLUNAS))
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setColumnHidden(0, True)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tbl.horizontalHeader().setSectionsClickable(True)
        layout.addWidget(self.tbl, 1)

        hbtn = QHBoxLayout()
        self.btn_novo = QPushButton("Novo aluno")
        # toggle Bloquear/Desbloquear (único visível)
        self.btn_bloq_toggle = QPushButton("Bloquear/Desbloquear")
        # legados ocultos mas mantidos p/ compat testes antigos
        self.btn_matricular = QPushButton("Matricular...")
        self.btn_bloquear = QPushButton("Bloquear")
        self.btn_desbloquear = QPushButton("Desbloquear")
        self.btn_inativar = QPushButton("Inativar/Reativar")
        self.btn_matricular.setVisible(False)
        self.btn_bloquear.setVisible(False)
        self.btn_desbloquear.setVisible(False)
        self.btn_inativar.setVisible(False)
        for b in (
            self.btn_novo,
            self.btn_bloq_toggle,
            self.btn_matricular,
            self.btn_bloquear,
            self.btn_desbloquear,
            self.btn_inativar,
        ):
            hbtn.addWidget(b)
        hbtn.addStretch(1)
        layout.addLayout(hbtn)

        self.edt_busca.textChanged.connect(lambda _t: self.recarregar())
        self.cmb_status.currentIndexChanged.connect(lambda _i: self.recarregar())
        self.tbl.cellDoubleClicked.connect(lambda _r, _c: self._abrir_perfil())
        self.tbl.horizontalHeader().sectionClicked.connect(self._header_clicado)
        self.tbl.customContextMenuRequested.connect(self._menu_contexto)
        self.btn_novo.clicked.connect(self._novo)
        self.btn_bloq_toggle.clicked.connect(self._toggle_bloqueio)
        # legados
        self.btn_matricular.clicked.connect(self._matricular)
        self.btn_bloquear.clicked.connect(lambda: self._acao("bloquear"))
        self.btn_desbloquear.clicked.connect(lambda: self._acao("desbloquear"))
        self.btn_inativar.clicked.connect(lambda: self._acao("inativar"))

        self.recarregar()

    # -- helpers ---------------------------------------------------------------
    def _selecionado(self) -> tuple[str, str] | None:
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.information(self, "Alunos", "Selecione um aluno na tabela.")
            return None
        item_id = self.tbl.item(row, 0)
        item_nome = self.tbl.item(row, 1)
        if item_id is None:
            return None
        return (item_id.text(), item_nome.text() if item_nome else "")

    def recarregar(self) -> None:
        status = self.cmb_status.currentData()
        alunos = self.vm.listar(busca=self.edt_busca.text(), status=status)
        self.tbl.setRowCount(len(alunos))
        for row, a in enumerate(alunos):
            vals = (
                a.id,
                a.nome,
                a.cpf or "—",
                a.telefone or "—",
                str(a.status),
                "SIM" if a.esta_bloqueado else "não",
            )
            for col, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if a.esta_bloqueado:
                    item.setForeground(QBrush(QColor("#E57373")))
                self.tbl.setItem(row, col, item)

    def _header_clicado(self, col: int) -> None:
        """Menu tipo Excel: lista valores únicos da coluna + busca, aplica filtro."""
        header = self.tbl.horizontalHeader()
        # coleta valores únicos da coluna
        valores: set[str] = set()
        for aluno in self.vm.alunos.listar():
            if col == 1:
                valores.add(aluno.nome)
            elif col == 2:
                valores.add(aluno.cpf or "—")
            elif col == 3:
                valores.add(aluno.telefone or "—")
            elif col == 4:
                valores.add(str(aluno.status))
            elif col == 5:
                valores.add("SIM" if aluno.esta_bloqueado else "não")
            elif col == 0:
                valores.add(aluno.id)
        if not valores:
            return
        menu = QMenu(self)
        # busca
        edt = QLineEdit(menu)
        edt.setPlaceholderText("Buscar...")
        # placeholder
        container = QWidget(menu)
        lay = QHBoxLayout(container)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.addWidget(edt)
        # cria QListWidget para valores filtráveis
        lst = QListWidget(menu)
        lst.setMaximumHeight(180)
        for v in sorted(valores):
            it = QListWidgetItem(v)
            lst.addItem(it)
        # layout menu custom: adiciona widgets via layout do menu é tricky; usa QWidgetAction
        from PySide6.QtWidgets import QWidgetAction

        wa_search = QWidgetAction(menu)
        wa_search.setDefaultWidget(container)
        menu.addAction(wa_search)
        wa_list = QWidgetAction(menu)
        wa_list.setDefaultWidget(lst)
        menu.addAction(wa_list)
        menu.addSeparator()
        act_limpar = menu.addAction("Limpar filtro")
        act_todos = menu.addAction("Todos")

        def _filtrar_lista(txt: str) -> None:
            txt_l = txt.lower()
            for i in range(lst.count()):
                it = lst.item(i)
                assert it is not None
                it.setHidden(txt_l not in it.text().lower())

        edt.textChanged.connect(_filtrar_lista)
        lst.itemClicked.connect(
            lambda it: self._aplicar_filtro_coluna(col, it.text())  # type: ignore[arg-type]
        )
        act_limpar.triggered.connect(lambda: self._aplicar_filtro_coluna(col, ""))
        act_todos.triggered.connect(lambda: self._aplicar_filtro_coluna(col, ""))

        # posiciona abaixo do header
        x = header.sectionViewportPosition(col)
        y = header.height()
        global_pos = header.mapToGlobal(QPoint(x, y))
        menu.exec(global_pos)

    def _aplicar_filtro_coluna(self, col: int, texto: str) -> None:
        if not texto or texto == "—":
            self.edt_busca.clear()
            self.cmb_status.setCurrentIndex(0)
            self.recarregar()
            return
        if col == 4:
            try:
                st = StatusAluno(texto)
                idx = self.cmb_status.findData(st)
                if idx >= 0:
                    self.cmb_status.setCurrentIndex(idx)
                    return
            except ValueError:
                pass
        self.edt_busca.setText(texto)

    def _toggle_bloqueio(self) -> None:
        sel = self._selecionado()
        if sel is None:
            return
        aluno_id, _nome = sel
        aluno = self.vm.alunos.buscar(aluno_id)
        if aluno is None:
            return
        try:
            if aluno.esta_bloqueado:
                self.vm.desbloquear(aluno_id)
            else:
                self.vm.bloquear(aluno_id)
        except ValueError as e:
            QMessageBox.warning(self, "Alunos", str(e))
            return
        self.recarregar()

    # -- ações -------------------------------------------------------------------
    def _menu_contexto(self, pos: QPoint) -> None:
        item = self.tbl.itemAt(pos)
        if item is None:
            return
        self.tbl.selectRow(item.row())
        menu = QMenu(self)
        a_perfil = menu.addAction("Abrir perfil...")
        a_mat = menu.addAction("Matricular...")
        a_bloq = menu.addAction("Bloquear/Desbloquear")
        a_inat = menu.addAction("Inativar/Reativar")
        acao = menu.exec(self.tbl.viewport().mapToGlobal(pos))
        if acao == a_perfil:
            self._abrir_perfil()
        elif acao == a_mat:
            self._matricular()
        elif acao == a_bloq:
            self._toggle_bloqueio()
        elif acao == a_inat:
            self._acao("inativar")

    def _abrir_perfil(self) -> None:
        sel = self._selecionado()
        if sel is None:
            return
        aluno_id, _nome = sel
        self.abrir_perfil_por_id(aluno_id)

    def abrir_perfil_por_id(self, aluno_id: str) -> None:
        """Abre o perfil direto pelo id (uso do click-through do dashboard)."""
        if self.pagamentos_vm is None:
            QMessageBox.warning(self, "Alunos", "Módulo de pagamentos indisponível.")
            return
        try:
            dlg = PerfilAlunoDialog(
                self.vm,
                self.pagamentos_vm,
                aluno_id,
                self,
                frequencia_vm=self.frequencia_vm,
                dashboard_vm=self.dashboard_vm,
            )
        except ValueError as e:
            QMessageBox.warning(self, "Alunos", str(e))
            return
        dlg.exec()
        self.recarregar()

    def _novo(self) -> None:
        dlg = NovoAlunoDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        d = dlg.dados()
        if not d["nome"].strip():
            QMessageBox.warning(self, "Alunos", "Nome é obrigatório.")
            return
        nasc: date | None = None
        if d["data_nasc"]:
            try:
                nasc = date.fromisoformat(d["data_nasc"])
            except ValueError:
                QMessageBox.warning(self, "Alunos", "Nascimento inválido (use AAAA-MM-DD).")
                return
        try:
            aluno = self.vm.cadastrar(
                nome=d["nome"],
                cpf=d["cpf"],
                data_nasc=nasc,
                telefone=d["telefone"],
                email=d["email"],
                observacoes=d["observacoes"],
                endereco=d["endereco"],
                senha=d["senha"],
            )
        except ValueError as e:
            QMessageBox.warning(self, "Alunos", str(e))
            return
        logger.info(f"[UI] aluno cadastrado id={aluno.id}")
        self.recarregar()

    def _acao(self, qual: str) -> None:
        sel = self._selecionado()
        if sel is None:
            return
        aluno_id, _nome = sel
        try:
            if qual == "bloquear":
                self.vm.bloquear(aluno_id)
            elif qual == "desbloquear":
                self.vm.desbloquear(aluno_id)
            else:
                atual = self.vm.alunos.buscar(aluno_id)
                if atual is not None and atual.status == StatusAluno.INATIVO:
                    self.vm.reativar(aluno_id)
                else:
                    self.vm.inativar(aluno_id)
        except ValueError as e:
            QMessageBox.warning(self, "Alunos", str(e))
            return
        self.recarregar()

    def _matricular(self) -> None:
        sel = self._selecionado()
        if sel is None:
            return
        aluno_id, aluno_nome = sel
        planos = [(p.id, f"{p.nome} ({p.duracao_dias}d)") for p in self.vm.planos_disponiveis()]
        if not planos:
            QMessageBox.information(self, "Alunos", "Cadastre um plano primeiro (aba Planos).")
            return
        dlg = MatricularDialog(aluno_nome, planos, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.vm.matricular(aluno_id, dlg.plano_id(), dlg.inicio())
        except (ValueError, RuntimeError) as e:
            QMessageBox.warning(self, "Alunos", str(e))
            return
        QMessageBox.information(self, "Alunos", f"{aluno_nome} matriculado com sucesso.")
