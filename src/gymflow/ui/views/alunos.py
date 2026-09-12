"""Tela de alunos — tabela + busca, cadastro, perfil editável e matrícula."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol

from loguru import logger
from PySide6.QtCore import QDate, QPoint, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gymflow.core.aluno import Aluno, StatusAluno
from gymflow.core.pagamento import FormaPagamento, Pagamento
from gymflow.ui.viewmodels.alunos import AlunosViewModel
from gymflow.ui.views.pagamentos import NovoPagamentoDialog


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
    """Campos do aluno reutilizados no cadastro e no perfil (inclui status)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        self.edt_nome = QLineEdit()
        self.edt_cpf = QLineEdit()
        self.edt_cpf.setPlaceholderText("somente números (opcional)")
        self.edt_nasc = QLineEdit()
        self.edt_nasc.setPlaceholderText("AAAA-MM-DD (opcional)")
        self.edt_tel = QLineEdit()
        self.edt_email = QLineEdit()
        self.edt_obs = QLineEdit()
        self.edt_senha = QLineEdit()
        self.edt_senha.setEchoMode(QLineEdit.EchoMode.Password)
        self.edt_senha.setPlaceholderText("4 a 8 dígitos (opcional)")
        self.edt_cartao = QLineEdit()
        self.edt_cartao.setPlaceholderText("ID do cartão (opcional)")
        self.cmb_status = QComboBox()
        for st in StatusAluno:
            self.cmb_status.addItem(st.value, st)
        form.addRow("Nome*:", self.edt_nome)
        form.addRow("CPF:", self.edt_cpf)
        form.addRow("Nascimento:", self.edt_nasc)
        form.addRow("Telefone:", self.edt_tel)
        form.addRow("E-mail:", self.edt_email)
        form.addRow("Observações:", self.edt_obs)
        form.addRow("Senha numérica:", self.edt_senha)
        form.addRow("Cartão:", self.edt_cartao)
        form.addRow("Status:", self.cmb_status)

    def preencher(self, aluno: Aluno) -> None:
        self.edt_nome.setText(aluno.nome)
        self.edt_cpf.setText(aluno.cpf or "")
        self.edt_nasc.setText(aluno.data_nasc.isoformat() if aluno.data_nasc else "")
        self.edt_tel.setText(aluno.telefone or "")
        self.edt_email.setText(aluno.email or "")
        self.edt_obs.setText(aluno.observacoes or "")
        self.edt_senha.clear()  # em branco = mantém o hash atual
        self.edt_senha.setPlaceholderText("em branco = manter atual")
        self.edt_cartao.setText(aluno.cartao_id or "")
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
            "observacoes": self.edt_obs.text(),
            "senha": self.edt_senha.text(),
            "cartao_id": self.edt_cartao.text().strip(),
            "status": str(status) if status is not None else StatusAluno.ATIVO.value,
        }


class NovoAlunoDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Novo aluno")
        layout = QVBoxLayout(self)
        self.form = _AlunoForm(self)
        # atalhos compat (testes legados acessam edt_* direto no dialog)
        self.edt_nome = self.form.edt_nome
        self.edt_cpf = self.form.edt_cpf
        self.edt_nasc = self.form.edt_nasc
        self.edt_tel = self.form.edt_tel
        self.edt_email = self.form.edt_email
        self.edt_obs = self.form.edt_obs
        self.edt_senha = self.form.edt_senha
        self.edt_cartao = self.form.edt_cartao
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
    """Modal de perfil: todos os campos editáveis + pagamentos do aluno."""

    COLUNAS_PAG = ("Vencimento", "Valor (R$)", "Pagamento", "Forma")

    def __init__(
        self,
        alunos_vm: AlunosViewModel,
        pagamentos_vm: PagamentosProto,
        aluno_id: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        aluno = alunos_vm.alunos.buscar(aluno_id)
        if aluno is None:
            raise ValueError(f"Aluno id={aluno_id} não encontrado")
        self._vm = alunos_vm
        self._pagamentos = pagamentos_vm
        self._aluno_id = aluno_id
        self.setWindowTitle(f"Perfil — {aluno.nome}")
        self.resize(560, 520)
        layout = QVBoxLayout(self)

        self.form = _AlunoForm(self)
        self.form.preencher(aluno)
        layout.addWidget(self.form)

        layout.addWidget(QLabel("Pagamentos do aluno:"))
        self.tbl_pag = QTableWidget(0, len(self.COLUNAS_PAG))
        self.tbl_pag.setHorizontalHeaderLabels(list(self.COLUNAS_PAG))
        self.tbl_pag.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_pag.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tbl_pag, 1)

        hb = QHBoxLayout()
        self.btn_novo_pag = QPushButton("Novo pagamento")
        hb.addWidget(self.btn_novo_pag)
        hb.addStretch(1)
        layout.addLayout(hb)

        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        botoes.accepted.connect(self._salvar)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

        self.btn_novo_pag.clicked.connect(self._novo_pagamento)
        self._recarregar_pagamentos()

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
            self._pagamentos.registrar(
                aluno_id=self._aluno_id,
                valor=Decimal(str(dlg.spn_valor.value())),
                data_vencimento=dlg.vencimento(),
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
                senha=d["senha"],
                cartao_id=d["cartao_id"],
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
    ) -> None:
        super().__init__(parent)
        self.vm = vm
        self.pagamentos_vm = pagamentos_vm
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
        layout.addWidget(self.tbl, 1)

        hbtn = QHBoxLayout()
        self.btn_novo = QPushButton("Novo aluno")
        self.btn_matricular = QPushButton("Matricular...")
        self.btn_bloquear = QPushButton("Bloquear")
        self.btn_desbloquear = QPushButton("Desbloquear")
        self.btn_inativar = QPushButton("Inativar/Reativar")
        for b in (
            self.btn_novo,
            self.btn_matricular,
            self.btn_bloquear,
            self.btn_desbloquear,
            self.btn_inativar,
        ):
            hbtn.addWidget(b)
        layout.addLayout(hbtn)

        self.edt_busca.textChanged.connect(lambda _t: self.recarregar())
        self.cmb_status.currentIndexChanged.connect(lambda _i: self.recarregar())
        self.tbl.cellDoubleClicked.connect(lambda _r, _c: self._abrir_perfil())
        self.tbl.customContextMenuRequested.connect(self._menu_contexto)
        self.btn_novo.clicked.connect(self._novo)
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
                self.tbl.setItem(row, col, QTableWidgetItem(v))

    # -- ações -------------------------------------------------------------------
    def _menu_contexto(self, pos: QPoint) -> None:
        item = self.tbl.itemAt(pos)
        if item is None:
            return
        self.tbl.selectRow(item.row())
        menu = QMenu(self)
        acao = menu.addAction("Abrir perfil...")
        if menu.exec(self.tbl.viewport().mapToGlobal(pos)) == acao:
            self._abrir_perfil()

    def _abrir_perfil(self) -> None:
        sel = self._selecionado()
        if sel is None:
            return
        if self.pagamentos_vm is None:
            QMessageBox.warning(self, "Alunos", "Módulo de pagamentos indisponível.")
            return
        aluno_id, _nome = sel
        try:
            dlg = PerfilAlunoDialog(self.vm, self.pagamentos_vm, aluno_id, self)
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
                senha=d["senha"],
                cartao_id=d["cartao_id"],
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
