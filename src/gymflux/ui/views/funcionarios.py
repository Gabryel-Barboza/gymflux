"""Tela de funcionários — tabela + duplo-clique + edição completa (replica alunos)."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gymflux.ui.viewmodels.funcionarios import FuncionariosViewModel


class NovoFuncionarioDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, titulo: str = "Novo funcionário") -> None:
        super().__init__(parent)
        self.setWindowTitle(titulo)
        form = QFormLayout(self)
        self.edt_nome = QLineEdit()
        self.edt_senha = QLineEdit()
        # senha visível (texto claro) como no perfil aluno — estilo catraca
        self.edt_senha.setEchoMode(QLineEdit.EchoMode.Normal)
        self.edt_senha.setPlaceholderText("4 a 8 dígitos")
        self.edt_horarios = QLineEdit()
        self.edt_horarios.setPlaceholderText("Ex.: 08:00-18:00 (opcional)")
        self.edt_dias = QLineEdit()
        self.edt_dias.setPlaceholderText("Ex.: Seg-Sex (opcional)")
        form.addRow("Nome*:", self.edt_nome)
        form.addRow("Senha numérica*:", self.edt_senha)
        form.addRow("Horários:", self.edt_horarios)
        form.addRow("Dias:", self.edt_dias)
        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        form.addRow(botoes)

    def preencher(
        self, nome: str, horarios: str | None = None, dias: str | None = None
    ) -> None:
        self.edt_nome.setText(nome)
        self.edt_senha.clear()
        self.edt_senha.setPlaceholderText("em branco = manter atual")
        self.edt_horarios.setText(horarios or "")
        self.edt_dias.setText(dias or "")


class PerfilFuncionarioDialog(QDialog):
    """Perfil simples (replica alunos): dados + senha visível + horarios/dias."""

    def __init__(
        self,
        vm: FuncionariosViewModel,
        funcionario_id: str,
        parent: QWidget | None = None,
        read_only: bool = False,
    ) -> None:
        super().__init__(parent)
        func = vm.buscar(funcionario_id)
        if func is None:
            raise ValueError(f"Funcionário id={funcionario_id} não encontrado")
        self._vm = vm
        self._func_id = funcionario_id
        self._read_only = read_only
        self.setWindowTitle(f"Perfil — {func.nome}" + (" (visualização)" if read_only else ""))
        self.resize(420, 260)
        form = QFormLayout(self)
        self.edt_nome = QLineEdit()
        self.edt_nome.setText(func.nome)
        self.edt_nome.setReadOnly(read_only)
        self.edt_senha = QLineEdit()
        self.edt_senha.setEchoMode(QLineEdit.EchoMode.Normal)
        self.edt_senha.setPlaceholderText("em branco = manter atual (4-8 dígitos)")
        self.edt_senha.setText("")
        self.edt_senha.setReadOnly(read_only)
        if read_only:
            self.edt_senha.setPlaceholderText("••••")
        self.edt_horarios = QLineEdit()
        self.edt_horarios.setText(func.horarios or "")
        self.edt_horarios.setPlaceholderText("Ex.: 08:00-18:00 (opcional)")
        self.edt_horarios.setReadOnly(read_only)
        self.edt_dias = QLineEdit()
        self.edt_dias.setText(func.dias or "")
        self.edt_dias.setPlaceholderText("Ex.: Seg-Sex (opcional)")
        self.edt_dias.setReadOnly(read_only)
        form.addRow("Nome*:", self.edt_nome)
        form.addRow("Senha numérica:", self.edt_senha)
        form.addRow("Horários:", self.edt_horarios)
        form.addRow("Dias:", self.edt_dias)
        if read_only:
            botoes = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            botoes.rejected.connect(self.reject)
            # desabilita edição visualmente
            self.edt_nome.setStyleSheet("QLineEdit { background: transparent; border: none; }")
        else:
            botoes = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
            )
            btn_save = botoes.button(QDialogButtonBox.StandardButton.Save)
            if btn_save is not None:
                btn_save.setText("Salvar")
            botoes.accepted.connect(self._salvar)
            botoes.rejected.connect(self.reject)
        form.addRow(botoes)

    def _salvar(self) -> None:
        if self._read_only:
            self.reject()
            return
        if not self.edt_nome.text().strip():
            QMessageBox.warning(self, "Funcionário", "Nome é obrigatório.")
            return
        try:
            self._vm.atualizar(
                self._func_id,
                nome=self.edt_nome.text(),
                senha=self.edt_senha.text(),
                horarios=self.edt_horarios.text(),
                dias=self.edt_dias.text(),
            )
        except ValueError as e:
            QMessageBox.warning(self, "Funcionário", str(e))
            return
        self.accept()


class FuncionariosView(QWidget):
    COLUNAS = ("ID", "Nome", "Ativo", "Horários", "Dias")

    def __init__(self, vm: FuncionariosViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.vm = vm
        layout = QVBoxLayout(self)

        self.tbl = QTableWidget(0, len(self.COLUNAS))
        self.tbl.setHorizontalHeaderLabels(list(self.COLUNAS))
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setColumnHidden(0, True)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        layout.addWidget(self.tbl, 1)
        # empurra botões para baixo
        layout.addStretch(1)
        hbtn = QHBoxLayout()
        self.btn_novo = QPushButton("Novo funcionário")
        self.btn_editar = QPushButton("Editar")
        self.btn_ativar = QPushButton("Ativar/Inativar")
        hbtn.addWidget(self.btn_novo)
        hbtn.addWidget(self.btn_editar)
        hbtn.addWidget(self.btn_ativar)
        hbtn.addStretch(1)
        layout.addLayout(hbtn)

        self.btn_novo.clicked.connect(self._novo)
        self.btn_editar.clicked.connect(self._editar)
        self.btn_ativar.clicked.connect(self._alternar_ativo)
        self.tbl.cellDoubleClicked.connect(lambda _r, _c: self._abrir_perfil())
        self.tbl.customContextMenuRequested.connect(self._menu_contexto)
        self.recarregar()

    def recarregar(self) -> None:
        funcs = self.vm.listar()
        self.tbl.setRowCount(len(funcs))
        for row, f in enumerate(funcs):
            vals = (
                f.id,
                f.nome,
                "SIM" if f.ativo else "não",
                f.horarios or "—",
                f.dias or "—",
            )
            for col, v in enumerate(vals):
                self.tbl.setItem(row, col, QTableWidgetItem(v))

    def _selecionado(self) -> str | None:
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.information(self, "Funcionários", "Selecione um funcionário.")
            return None
        item = self.tbl.item(row, 0)
        return item.text() if item is not None else None

    def _novo(self) -> None:
        dlg = NovoFuncionarioDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if not dlg.edt_nome.text().strip():
            QMessageBox.warning(self, "Funcionários", "Nome é obrigatório.")
            return
        try:
            self.vm.cadastrar(
                nome=dlg.edt_nome.text(),
                senha=dlg.edt_senha.text(),
                horarios=dlg.edt_horarios.text(),
                dias=dlg.edt_dias.text(),
            )
        except ValueError as e:
            QMessageBox.warning(self, "Funcionários", str(e))
            return
        self.recarregar()

    def _editar(self) -> None:
        func_id = self._selecionado()
        if func_id is None:
            return
        func = self.vm.buscar(func_id)
        if func is None:
            QMessageBox.warning(self, "Funcionários", "Funcionário não encontrado.")
            return
        dlg = NovoFuncionarioDialog(self, titulo=f"Editar funcionário — {func.nome}")
        dlg.preencher(func.nome, func.horarios, func.dias)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.vm.atualizar(
                func_id,
                nome=dlg.edt_nome.text(),
                senha=dlg.edt_senha.text(),
                horarios=dlg.edt_horarios.text(),
                dias=dlg.edt_dias.text(),
            )
        except ValueError as e:
            QMessageBox.warning(self, "Funcionários", str(e))
            return
        self.recarregar()

    def _alternar_ativo(self) -> None:
        func_id = self._selecionado()
        if func_id is None:
            return
        func = self.vm.buscar(func_id)
        if func is None:
            QMessageBox.warning(self, "Funcionários", "Funcionário não encontrado.")
            return
        self.vm.definir_ativo(func_id, not func.ativo)
        self.recarregar()

    def _abrir_perfil(self) -> None:
        func_id = self._selecionado()
        if func_id is None:
            return
        self.abrir_perfil_por_id(func_id, read_only=True)

    def abrir_perfil_por_id(self, funcionario_id: str, read_only: bool = True) -> None:
        try:
            dlg = PerfilFuncionarioDialog(self.vm, funcionario_id, self, read_only=read_only)
        except ValueError as e:
            QMessageBox.warning(self, "Funcionários", str(e))
            return
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        # só recarrega se houve edição
        if not read_only:
            self.recarregar()

    def _editar_via_perfil(self) -> None:
        func_id = self._selecionado()
        if func_id is None:
            return
        try:
            dlg = PerfilFuncionarioDialog(self.vm, func_id, self, read_only=False)
        except ValueError as e:
            QMessageBox.warning(self, "Funcionários", str(e))
            return
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self.recarregar()

    def _menu_contexto(self, pos: QPoint) -> None:
        item = self.tbl.itemAt(pos)
        if item is None:
            return
        self.tbl.selectRow(item.row())
        menu = QMenu(self)
        a_perfil = menu.addAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView),
            "Abrir perfil",
        )
        a_editar = menu.addAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView),
            "Editar",
        )
        a_ativar = menu.addAction("Ativar/Inativar")
        acao = menu.exec(self.tbl.viewport().mapToGlobal(pos))
        if acao == a_perfil:
            self._abrir_perfil()
        elif acao == a_editar:
            self._editar()
        elif acao == a_ativar:
            self._alternar_ativo()
