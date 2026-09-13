"""Tela de funcionários — tabela + duplo-clique + edição completa (replica alunos)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
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
        root = QHBoxLayout(self)
        form = QFormLayout()
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
        root.addLayout(form, 1)
        # foto quadrada à direita
        foto_wrap = QVBoxLayout()
        foto_wrap.setContentsMargins(0, 0, 0, 0)
        self.lbl_foto = QLabel()
        self.lbl_foto.setFixedSize(110, 110)
        self.lbl_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_foto.setStyleSheet(
            "QLabel { border: 2px dashed #5AC8FA; border-radius: 8px; background-color: #1A1E22; color: #9AA7B2; }"  # noqa: E501
        )
        self.lbl_foto.setText("Foto\n(clique)")
        self.lbl_foto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_foto.mousePressEvent = lambda e: self._escolher_foto()  # type: ignore[method-assign]
        self._foto_path: str | None = None
        foto_wrap.addWidget(self.lbl_foto, 0, Qt.AlignmentFlag.AlignTop)
        self.btn_remover_foto = QPushButton("Remover foto")
        self.btn_remover_foto.setMaximumWidth(110)
        self.btn_remover_foto.clicked.connect(self._remover_foto)
        foto_wrap.addWidget(self.btn_remover_foto)
        foto_wrap.addStretch(1)
        root.addLayout(foto_wrap)

    def _escolher_foto(self) -> None:
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Escolher foto", "", "Imagens (*.png *.jpg *.jpeg *.bmp);;Todos (*)"
        )
        if caminho:
            self._foto_path = caminho
            self._atualizar_foto()

    def _remover_foto(self) -> None:
        self._foto_path = None
        self.lbl_foto.clear()
        self.lbl_foto.setText("Foto\n(clique)")
        self.lbl_foto.setStyleSheet(
            "QLabel { border: 2px dashed #5AC8FA; border-radius: 8px; background-color: #1A1E22; color: #9AA7B2; }"  # noqa: E501
        )

    def _atualizar_foto(self) -> None:
        if not self._foto_path or not Path(self._foto_path).exists():
            self.lbl_foto.clear()
            self.lbl_foto.setText("Foto\n(clique)")
            return
        pix = QPixmap(self._foto_path)
        if pix.isNull():
            self.lbl_foto.setText("Inválida")
            return
        scaled = pix.scaled(
            QSize(110, 110),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = max(0, (scaled.width() - 110) // 2)
        y = max(0, (scaled.height() - 110) // 2)
        cropped = scaled.copy(x, y, 110, 110)
        self.lbl_foto.setPixmap(cropped)
        self.lbl_foto.setStyleSheet(
            "QLabel { border: 2px solid #5AC8FA; border-radius: 8px; background-color: #0F1113; }"
        )

    def preencher(
        self, nome: str, horarios: str | None = None, dias: str | None = None
    ) -> None:
        self.edt_nome.setText(nome)
        self.edt_senha.clear()
        self.edt_senha.setPlaceholderText("em branco = manter atual")
        self.edt_horarios.setText(horarios or "")
        self.edt_dias.setText(dias or "")


class PerfilFuncionarioDialog(QDialog):
    """Perfil simples (replica alunos): dados + senha visível + horarios/dias + foto."""

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
        self.resize(540, 300)
        root = QHBoxLayout(self)
        form = QFormLayout()
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
        root.addLayout(form, 1)
        # foto quadrada à direita
        foto_wrap = QVBoxLayout()
        foto_wrap.setContentsMargins(0, 0, 0, 0)
        self.lbl_foto = QLabel()
        self.lbl_foto.setFixedSize(120, 120)
        self.lbl_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_foto.setStyleSheet(
            "QLabel { border: 2px solid #5AC8FA; border-radius: 8px; background-color: #0F1113; color: #9AA7B2; }"  # noqa: E501
        )
        self.lbl_foto.setText("Sem foto")
        if not read_only:
            self.lbl_foto.setCursor(Qt.CursorShape.PointingHandCursor)
            self.lbl_foto.mousePressEvent = lambda e: self._escolher_foto()  # type: ignore[method-assign]
        self._foto_path: str | None = getattr(func, "foto", None)
        if self._foto_path and Path(self._foto_path).exists():
            pix = QPixmap(self._foto_path)
            if not pix.isNull():
                scaled = pix.scaled(
                    QSize(120, 120),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                x = max(0, (scaled.width() - 120) // 2)
                y = max(0, (scaled.height() - 120) // 2)
                cropped = scaled.copy(x, y, 120, 120)
                self.lbl_foto.setPixmap(cropped)
                self.lbl_foto.setStyleSheet(
                    "QLabel { border: 2px solid #5AC8FA; border-radius: 8px; background-color: #0F1113; }"  # noqa: E501
                )
            else:
                self.lbl_foto.setText("Sem foto")
        foto_wrap.addWidget(self.lbl_foto, 0, Qt.AlignmentFlag.AlignTop)
        if not read_only:
            self.btn_remover_foto = QPushButton("Remover foto")
            self.btn_remover_foto.setMaximumWidth(120)
            self.btn_remover_foto.clicked.connect(self._remover_foto)
            foto_wrap.addWidget(self.btn_remover_foto)
        foto_wrap.addStretch(1)
        root.addLayout(foto_wrap)

    def _escolher_foto(self) -> None:
        if getattr(self, "_read_only", False):
            return
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Escolher foto", "", "Imagens (*.png *.jpg *.jpeg *.bmp);;Todos (*)"
        )
        if caminho:
            self._foto_path = caminho
            pix = QPixmap(caminho)
            if not pix.isNull():
                scaled = pix.scaled(
                    QSize(120, 120),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                x = max(0, (scaled.width() - 120) // 2)
                y = max(0, (scaled.height() - 120) // 2)
                cropped = scaled.copy(x, y, 120, 120)
                self.lbl_foto.setPixmap(cropped)
                self.lbl_foto.setStyleSheet(
                    "QLabel { border: 2px solid #5AC8FA; border-radius: 8px; background-color: #0F1113; }"  # noqa: E501
                )

    def _remover_foto(self) -> None:
        self._foto_path = None
        self.lbl_foto.clear()
        self.lbl_foto.setText("Sem foto")
        self.lbl_foto.setStyleSheet(
            "QLabel { border: 2px dashed #5AC8FA; border-radius: 8px; background-color: #1A1E22; color: #9AA7B2; }"  # noqa: E501
        )

    def _salvar(self) -> None:
        if self._read_only:
            self.reject()
            return
        if not self.edt_nome.text().strip():
            QMessageBox.warning(self, "Funcionário", "Nome é obrigatório.")
            return
        foto_src = getattr(self, "_foto_path", None)
        foto_final = None
        func_atual = self._vm.buscar(self._func_id)
        foto_atual = getattr(func_atual, "foto", None) if func_atual else None
        if foto_src and Path(foto_src).exists():  # type: ignore[arg-type]
            if foto_atual and Path(foto_src).resolve() == Path(foto_atual).resolve() if Path(foto_atual).exists() else False:  # type: ignore[arg-type]  # noqa: E501
                foto_final = foto_atual
            else:
                try:
                    dst_dir = Path("data/fotos/funcionarios")
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    ext = Path(foto_src).suffix or ".jpg"  # type: ignore[arg-type]
                    dst = dst_dir / f"{self._func_id}{ext}"
                    import shutil

                    shutil.copy2(foto_src, dst)
                    foto_final = str(dst)
                except Exception:
                    foto_final = foto_src
        elif foto_src is None and foto_atual:
            # remover foto
            foto_final = None
        else:
            foto_final = foto_atual
        try:
            self._vm.atualizar(
                self._func_id,
                nome=self.edt_nome.text(),
                senha=self.edt_senha.text(),
                horarios=self.edt_horarios.text(),
                dias=self.edt_dias.text(),
                foto=foto_final,
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
        foto_src = getattr(dlg, "_foto_path", None)
        foto_dst = foto_src if foto_src and Path(foto_src).exists() else None  # type: ignore[arg-type]
        try:
            func = self.vm.cadastrar(
                nome=dlg.edt_nome.text(),
                senha=dlg.edt_senha.text(),
                horarios=dlg.edt_horarios.text(),
                dias=dlg.edt_dias.text(),
                foto=foto_dst,
            )
            if foto_src and Path(foto_src).exists():  # type: ignore[arg-type]
                try:
                    dst_dir = Path("data/fotos/funcionarios")
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    ext = Path(foto_src).suffix or ".jpg"  # type: ignore[arg-type]
                    dst = dst_dir / f"{func.id}{ext}"
                    import shutil

                    shutil.copy2(foto_src, dst)
                    self.vm.atualizar(func.id, nome=func.nome, senha="", horarios=func.horarios, dias=func.dias, foto=str(dst))  # noqa: E501
                except Exception:
                    pass
        except ValueError as e:
            QMessageBox.warning(self, "Funcionários", str(e))
            return
        self.recarregar()

    def _editar(self) -> None:
        # Editar via perfil editável (distinto de Abrir perfil que é só visualização)
        self._editar_via_perfil()

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
