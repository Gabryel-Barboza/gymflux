"""Tela de alunos — tabela + busca, cadastro, bloqueio e matrícula."""

from __future__ import annotations

from datetime import date

from loguru import logger
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gymflow.core.aluno import StatusAluno
from gymflow.ui.viewmodels.alunos import AlunosViewModel


class NovoAlunoDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Novo aluno")
        form = QFormLayout(self)
        self.edt_nome = QLineEdit()
        self.edt_cpf = QLineEdit()
        self.edt_cpf.setPlaceholderText("somente números (opcional)")
        self.edt_nasc = QLineEdit()
        self.edt_nasc.setPlaceholderText("AAAA-MM-DD (opcional)")
        self.edt_tel = QLineEdit()
        self.edt_email = QLineEdit()
        self.edt_obs = QLineEdit()
        form.addRow("Nome*:", self.edt_nome)
        form.addRow("CPF:", self.edt_cpf)
        form.addRow("Nascimento:", self.edt_nasc)
        form.addRow("Telefone:", self.edt_tel)
        form.addRow("E-mail:", self.edt_email)
        form.addRow("Observações:", self.edt_obs)
        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        form.addRow(botoes)

    def dados(self) -> dict[str, str]:
        return {
            "nome": self.edt_nome.text(),
            "cpf": self.edt_cpf.text(),
            "data_nasc": self.edt_nasc.text().strip(),
            "telefone": self.edt_tel.text(),
            "email": self.edt_email.text(),
            "observacoes": self.edt_obs.text(),
        }


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

    def __init__(self, vm: AlunosViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.vm = vm
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
