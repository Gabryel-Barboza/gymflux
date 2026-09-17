"""Tela de funcionários — tabela + duplo-clique + edição completa (turnos)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QSize, Qt, QTime
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
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
    QTimeEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gymflux.core.funcionario import format_turnos_compacto, parse_turnos_tolerante
from gymflux.ui.theme import icone_preto
from gymflux.ui.viewmodels.funcionarios import FuncionariosViewModel

_DIAS_PRESETS = ["Seg-Sex", "Sáb", "Dom", "Seg-Sáb", "Todos", "Personalizado"]
_PRESET_MAP = {
    "Seg-Sex": "Seg-Sex",
    "Sáb": "Sáb",
    "Dom": "Dom",
    "Seg-Sáb": "Seg-Sáb",
    "Todos": "Seg-Dom",
}


def _horarios_text_from_rows(rows: list[dict]) -> str | None:
    if not rows:
        return None
    turnos = []
    for r in rows:
        cmb: QComboBox = r["cmb"]
        edt_custom: QLineEdit = r["edt_custom"]
        t_ini: QTimeEdit = r["t_ini"]
        t_fim: QTimeEdit = r["t_fim"]
        dias_raw = cmb.currentText().strip()
        if dias_raw == "Personalizado":
            dias_raw = edt_custom.text().strip()
            if not dias_raw:
                continue
        else:
            dias_raw = _PRESET_MAP.get(dias_raw, dias_raw)
        ini = t_ini.time().toString("HH:mm")
        fim = t_fim.time().toString("HH:mm")
        # skip empty?
        if not dias_raw:
            continue
        turnos.append(f"{dias_raw} {ini}-{fim}")
    if not turnos:
        return None
    txt = "; ".join(turnos)
    # valida/normaliza via VM helpers (will raise if inválido)
    from gymflux.core.funcionario import format_turnos, parse_turnos

    try:
        parsed = parse_turnos(txt)
        return format_turnos(parsed)
    except ValueError:
        # deixa VM levantar mensagem amigável depois
        return txt


def _create_turno_row(
    parent: QWidget,
    dias: str = "Seg-Sex",
    inicio: str = "08:00",
    fim: str = "18:00",
) -> dict:
    row_widget = QWidget(parent)
    # borda leve para seleção visual
    row_widget.setObjectName("TurnoRow")
    row_widget.setStyleSheet(
        "QWidget#TurnoRow { border: 1px solid transparent; border-radius: 6px; }"
    )
    lay = QHBoxLayout(row_widget)
    lay.setContentsMargins(4, 2, 4, 2)
    lay.setSpacing(8)
    cmb = QComboBox(row_widget)
    cmb.addItems(_DIAS_PRESETS)
    cmb.setMinimumWidth(120)
    cmb.setMaximumWidth(130)
    edt_custom = QLineEdit(row_widget)
    edt_custom.setPlaceholderText("Seg, Qua ...")
    edt_custom.setVisible(False)
    edt_custom.setMaximumWidth(120)
    # seleciona preset ou personalizado
    if dias in _PRESET_MAP.values() or dias in _PRESET_MAP:
        inv = {v: k for k, v in _PRESET_MAP.items()}
        preset = inv.get(dias, dias)
        if preset in _DIAS_PRESETS:
            cmb.setCurrentText(preset)
        else:
            cmb.setCurrentText(dias if dias in _DIAS_PRESETS else "Seg-Sex")
    else:
        if dias in _DIAS_PRESETS:
            cmb.setCurrentText(dias)
        else:
            cmb.setCurrentText("Personalizado")
            edt_custom.setText(dias)
            edt_custom.setVisible(True)
    if dias == "Seg-Dom":
        cmb.setCurrentText("Todos")

    def _on_preset_changed(txt: str) -> None:
        edt_custom.setVisible(txt == "Personalizado")

    cmb.currentTextChanged.connect(_on_preset_changed)

    t_ini = QTimeEdit(row_widget)
    t_ini.setDisplayFormat("HH:mm")
    t_ini.setMinimumWidth(80)
    t_ini.setMaximumWidth(90)
    t_ini.setAlignment(Qt.AlignmentFlag.AlignCenter)
    try:
        h, m = inicio.split(":")
        t_ini.setTime(QTime(int(h), int(m)))
    except Exception:
        t_ini.setTime(QTime(8, 0))
    t_fim = QTimeEdit(row_widget)
    t_fim.setDisplayFormat("HH:mm")
    t_fim.setMinimumWidth(80)
    t_fim.setMaximumWidth(90)
    t_fim.setAlignment(Qt.AlignmentFlag.AlignCenter)
    try:
        h, m = fim.split(":")
        t_fim.setTime(QTime(int(h), int(m)))
    except Exception:
        t_fim.setTime(QTime(18, 0))

    lay.addWidget(cmb)
    lay.addWidget(edt_custom)
    lay.addWidget(t_ini)
    lay.addWidget(QLabel("—", row_widget))
    lay.addWidget(t_fim)
    lay.addStretch(1)

    return {
        "widget": row_widget,
        "cmb": cmb,
        "edt_custom": edt_custom,
        "t_ini": t_ini,
        "t_fim": t_fim,
        "layout": lay,
    }


class NovoFuncionarioDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, titulo: str = "Novo funcionário") -> None:
        super().__init__(parent)
        self.setWindowTitle(titulo)
        root = QHBoxLayout(self)
        form = QFormLayout()
        self.edt_nome = QLineEdit()
        self.edt_senha = QLineEdit()
        self.edt_senha.setEchoMode(QLineEdit.EchoMode.Normal)
        self.edt_senha.setPlaceholderText("4 a 8 dígitos")
        # senha com botão ver
        h_senha = QHBoxLayout()
        h_senha.addWidget(self.edt_senha, 1)
        self.btn_ver_senha = QToolButton()
        self.btn_ver_senha.setText("👁")
        self.btn_ver_senha.setToolTip("Mostrar/ocultar senha")
        self.btn_ver_senha.setCheckable(True)
        self.btn_ver_senha.toggled.connect(  # type: ignore[no-untyped-call]
            lambda c: self.edt_senha.setEchoMode(  # type: ignore[union-attr]
                QLineEdit.EchoMode.Normal if c else QLineEdit.EchoMode.Password
            )
        )
        self.edt_senha.setEchoMode(QLineEdit.EchoMode.Normal)
        self.btn_ver_senha.setChecked(True)
        h_senha.addWidget(self.btn_ver_senha)
        form.addRow("Nome*:", self.edt_nome)
        form.addRow("Senha numérica*:", h_senha)

        # editor de turnos — linhas alinhadas, seleção via clique, 2 botões abaixo
        form.addRow(QLabel("Turnos ( Dias + Horário ):"))
        self._turnos_container = QWidget()
        self._turnos_layout = QVBoxLayout(self._turnos_container)
        self._turnos_layout.setContentsMargins(0, 0, 0, 0)
        self._turnos_layout.setSpacing(4)
        self._turnos_rows: list[dict] = []
        self._turno_selected: int | None = None
        # uma linha inicial
        self._add_turno_row()
        form.addRow(self._turnos_container)
        # dois botões abaixo, com ícones
        h_turnos_btn = QHBoxLayout()
        self.btn_add_turno = QPushButton(
            icone_preto(self.style(), QStyle.StandardPixmap.SP_FileDialogNewFolder),
            "Adicionar turno",
        )
        self.btn_add_turno.setToolTip("Adiciona um novo turno")
        self.btn_add_turno.clicked.connect(lambda: self._add_turno_row())
        self.btn_remove_turno = QPushButton(
            icone_preto(self.style(), QStyle.StandardPixmap.SP_TrashIcon), "Remover selecionado"
        )
        self.btn_remove_turno.setToolTip(
            "Remove o turno selecionado (clique na linha para selecionar)"
        )
        self.btn_remove_turno.clicked.connect(self._remove_selected)
        h_turnos_btn.addWidget(self.btn_add_turno)
        h_turnos_btn.addWidget(self.btn_remove_turno)
        h_turnos_btn.addStretch(1)
        form.addRow(h_turnos_btn)

        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        form.addRow(botoes)
        left = QWidget()
        left.setLayout(form)
        root.addWidget(left, 1)
        # foto quadrada à direita
        foto_wrap = QVBoxLayout()
        foto_wrap.setContentsMargins(0, 0, 0, 0)
        self.lbl_foto = QLabel()
        self.lbl_foto.setFixedSize(110, 110)
        self.lbl_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        self._aplicar_tema_foto(False)

    def _add_turno_row(
        self, dias: str = "Seg-Sex", inicio: str = "08:00", fim: str = "12:00"
    ) -> None:
        row = _create_turno_row(self._turnos_container, dias=dias, inicio=inicio, fim=fim)

        # seleção por clique na linha
        def _sel(_e, r=row):  # type: ignore[no-untyped-def]
            try:
                idx = (
                    self._turnos_rows.index(r) if r in self._turnos_rows else len(self._turnos_rows)
                )
                # para linha ainda não adicionada, será o último
                if r not in self._turnos_rows:
                    idx = len(self._turnos_rows)
                self._select_turno(idx)
            except Exception:
                pass

        row["widget"].mousePressEvent = _sel  # type: ignore[method-assign,assignment]
        self._turnos_layout.addWidget(row["widget"])
        self._turnos_rows.append(row)
        # auto-seleciona o novo
        self._select_turno(len(self._turnos_rows) - 1)

    def _select_turno(self, idx: int | None) -> None:
        self._turno_selected = idx
        for i, r in enumerate(self._turnos_rows):
            w = r["widget"]
            if i == idx:
                w.setStyleSheet(
                    "QWidget#TurnoRow { border: 1px solid #5AC8FA; border-radius: 6px; background: rgba(90,200,250,18%); }"  # noqa: E501
                )
            else:
                w.setStyleSheet(
                    "QWidget#TurnoRow { border: 1px solid transparent; border-radius: 6px; }"
                )

    def _remove_selected(self) -> None:
        if self._turno_selected is None or self._turno_selected >= len(self._turnos_rows):
            if len(self._turnos_rows) <= 1:
                return
            # sem seleção: remove último
            idx = len(self._turnos_rows) - 1
        else:
            idx = self._turno_selected
        if len(self._turnos_rows) <= 1:
            return
        row = self._turnos_rows[idx]
        self._turnos_layout.removeWidget(row["widget"])
        row["widget"].deleteLater()
        self._turnos_rows.pop(idx)
        # ajusta seleção
        if self._turnos_rows:
            self._select_turno(min(idx, len(self._turnos_rows) - 1))
        else:
            self._turno_selected = None

    def _remove_turno_row(self, row: dict) -> None:
        if row in self._turnos_rows:
            idx = self._turnos_rows.index(row)
            self._turno_selected = idx
            self._remove_selected()

    def horarios_text(self) -> str | None:
        return _horarios_text_from_rows(self._turnos_rows)

    # compat: alguns callers antigos leem edt_horarios (agora via turnos)
    @property
    def edt_horarios(self):  # type: ignore[no-untyped-def]
        class _Fake:
            def __init__(self, dlg):
                self._dlg = dlg

            def text(self):
                return self._dlg.horarios_text() or ""

            def setText(self, v):
                pass

        return _Fake(self)

    @property
    def edt_dias(self):  # type: ignore[no-untyped-def]
        class _Fake:
            def __init__(self, dlg):
                self._dlg = dlg

            def text(self):
                return ""

            def setText(self, v):
                pass

        return _Fake(self)

    def preencher(self, nome: str, horarios: str | None = None, dias: str | None = None) -> None:
        self.edt_nome.setText(nome)
        self.edt_senha.clear()
        self.edt_senha.setPlaceholderText("")
        # recria turnos a partir de horarios
        for r in list(self._turnos_rows):
            self._remove_turno_row(r) if len(self._turnos_rows) > 1 else None
        # limpa restante
        for r in list(self._turnos_rows):
            self._turnos_layout.removeWidget(r["widget"])
            r["widget"].deleteLater()
        self._turnos_rows.clear()
        turnos = parse_turnos_tolerante(horarios, dias)
        if not turnos:
            self._add_turno_row()
        else:
            for t in turnos:
                self._add_turno_row(dias=t.dias, inicio=t.inicio, fim=t.fim)

    def _detectar_tema(self):  # type: ignore[no-untyped-def]
        from gymflux.ui.theme import ModoTema

        tema = ModoTema.ESCURO
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            ss = ""
            if isinstance(app, QApplication):
                ss = app.styleSheet()
            if "#E8EDF1" in ss:
                tema = ModoTema.CLARO
        except Exception:
            pass
        return tema

    def _aplicar_tema_foto(self, tem_foto: bool) -> None:
        from gymflux.ui.theme import paleta_do_modo

        try:
            paleta = paleta_do_modo(self._detectar_tema())
        except Exception:
            from gymflux.ui.theme import PALETA_ESCURA

            paleta = PALETA_ESCURA
        is_claro = paleta.texto == "#1A1E22"
        bg = paleta.painel if is_claro else "#0F1113"
        border = "#C8D0D8" if is_claro else "#5AC8FA"
        if tem_foto:
            self.lbl_foto.setStyleSheet(
                f"QLabel {{ border: 2px solid {border}; border-radius: 8px;"
                f" background-color: {bg}; }}"
            )
        else:
            self.lbl_foto.setStyleSheet(
                f"QLabel {{ border: 2px dashed {border}; border-radius: 8px;"
                f" background-color: {bg}; color: {paleta.suave}; }}"
            )

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
        self._aplicar_tema_foto(False)

    def _atualizar_foto(self) -> None:
        if not self._foto_path or not Path(self._foto_path).exists():
            self.lbl_foto.clear()
            self.lbl_foto.setText("Foto\n(clique)")
            self._aplicar_tema_foto(False)
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
        self._aplicar_tema_foto(True)


class PerfilFuncionarioDialog(QDialog):
    """Perfil simples: dados + senha visível + turnos + foto."""

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
        self.resize(600, 380)
        main = QVBoxLayout(self)
        top = QHBoxLayout()
        form = QFormLayout()
        self.edt_nome = QLineEdit()
        self.edt_nome.setText(func.nome)
        self.edt_nome.setReadOnly(read_only)
        self.edt_senha = QLineEdit()
        self.edt_senha.setEchoMode(QLineEdit.EchoMode.Normal)
        self.edt_senha.setPlaceholderText("")
        senha_atual = getattr(func, "senha", None) or ""
        self.edt_senha.setText(senha_atual)
        self.edt_senha.setReadOnly(read_only)
        form.addRow("Nome*:", self.edt_nome)
        form.addRow("Senha numérica:", self.edt_senha)

        # turnos editor (read_only desabilita) — 2 botões abaixo
        form.addRow(QLabel("Turnos:"))
        self._turnos_container = QWidget()
        self._turnos_layout = QVBoxLayout(self._turnos_container)
        self._turnos_layout.setContentsMargins(0, 0, 0, 0)
        self._turnos_layout.setSpacing(4)
        self._turnos_rows: list[dict] = []
        self._turno_selected: int | None = None
        turnos = parse_turnos_tolerante(func.horarios, func.dias)
        if not turnos:
            self._add_turno_row(read_only=read_only)
        else:
            for t in turnos:
                self._add_turno_row(dias=t.dias, inicio=t.inicio, fim=t.fim, read_only=read_only)
        if not read_only:
            h_turnos_btn = QHBoxLayout()
            self.btn_add_turno = QPushButton(
                icone_preto(self.style(), QStyle.StandardPixmap.SP_FileDialogNewFolder),
                "Adicionar turno",
            )
            self.btn_add_turno.clicked.connect(lambda: self._add_turno_row(read_only=False))
            self.btn_remove_turno = QPushButton(
                icone_preto(self.style(), QStyle.StandardPixmap.SP_TrashIcon), "Remover selecionado"
            )
            self.btn_remove_turno.setToolTip("Remover turno selecionado (clique na linha)")
            self.btn_remove_turno.clicked.connect(self._remove_selected)
            h_turnos_btn.addWidget(self.btn_add_turno)
            h_turnos_btn.addWidget(self.btn_remove_turno)
            h_turnos_btn.addStretch(1)
            self._turnos_layout.addLayout(h_turnos_btn)
        form.addRow(self._turnos_container)
        top.addLayout(form, 1)
        # foto quadrada à direita
        foto_wrap = QVBoxLayout()
        foto_wrap.setContentsMargins(0, 0, 0, 0)
        self.lbl_foto = QLabel()
        self.lbl_foto.setFixedSize(120, 120)
        self.lbl_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_foto.setText("Sem foto")
        if not read_only:
            self.lbl_foto.setCursor(Qt.CursorShape.PointingHandCursor)
            self.lbl_foto.mousePressEvent = lambda e: self._escolher_foto()  # type: ignore[method-assign]
        self._foto_path: str | None = getattr(func, "foto", None)
        foto_wrap.addWidget(self.lbl_foto, 0, Qt.AlignmentFlag.AlignTop)
        if not read_only:
            self.btn_remover_foto = QPushButton("Remover foto")
            self.btn_remover_foto.setMaximumWidth(120)
            self.btn_remover_foto.clicked.connect(self._remover_foto)
            foto_wrap.addWidget(self.btn_remover_foto)
        foto_wrap.addStretch(1)
        top.addLayout(foto_wrap)
        main.addLayout(top, 1)
        self._aplicar_tema_foto(self._foto_path is not None and Path(self._foto_path).exists())  # type: ignore[arg-type]
        if self._foto_path and Path(self._foto_path).exists():  # type: ignore[arg-type]
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
        # botões
        if read_only:
            botoes = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            botoes.rejected.connect(self.reject)
            self.edt_nome.setStyleSheet("QLineEdit { background: transparent; border: none; }")
        else:
            botoes = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
            )
            btn_save = botoes.button(QDialogButtonBox.StandardButton.Save)
            if btn_save is not None:
                btn_save.setText("Salvar")
                btn_save.setStyleSheet(
                    "QPushButton { background-color: #5AC8FA; color: #0F1113;"
                    " border-radius: 6px; padding: 6px 14px; font-weight: bold; }"
                )
            btn_cancel = botoes.button(QDialogButtonBox.StandardButton.Cancel)
            if btn_cancel is not None:
                btn_cancel.setText("Cancelar")
                btn_cancel.setStyleSheet(
                    "QPushButton { background-color: transparent;"
                    " border: 1px solid #5AC8FA; color: #5AC8FA;"
                    " border-radius: 6px; padding: 6px 14px; }"
                )
            botoes.accepted.connect(self._salvar)
            botoes.rejected.connect(self.reject)
        h_botoes = QHBoxLayout()
        h_botoes.addStretch(1)
        h_botoes.addWidget(botoes)
        main.addLayout(h_botoes)

    def _add_turno_row(
        self,
        dias: str = "Seg-Sex",
        inicio: str = "08:00",
        fim: str = "12:00",
        read_only: bool = False,
    ) -> None:
        row = _create_turno_row(self._turnos_container, dias=dias, inicio=inicio, fim=fim)
        if read_only:
            row["cmb"].setEnabled(False)
            row["edt_custom"].setReadOnly(True)
            row["t_ini"].setReadOnly(True)
            row["t_ini"].setEnabled(False)
            row["t_fim"].setReadOnly(True)
            row["t_fim"].setEnabled(False)
        else:
            # seleção por clique
            def _sel(_e, r=row):  # type: ignore[no-untyped-def]
                try:
                    idx = (
                        self._turnos_rows.index(r)
                        if r in self._turnos_rows
                        else len(self._turnos_rows)
                    )
                    if r not in self._turnos_rows:
                        idx = len(self._turnos_rows)
                    self._select_turno(idx)
                except Exception:
                    pass

            row["widget"].mousePressEvent = _sel  # type: ignore[method-assign,assignment]
            # insere antes dos botões (último item é layout dos botões)
            # encontra índice do layout de botões se existir
            insert_at = len(self._turnos_rows)
            # se houver layout de botões no final, mantém botões no fim
            self._turnos_layout.insertWidget(insert_at, row["widget"])
            self._turnos_rows.append(row)
            self._select_turno(len(self._turnos_rows) - 1)
            return
        # read_only: apenas adiciona
        self._turnos_layout.insertWidget(len(self._turnos_rows), row["widget"])
        self._turnos_rows.append(row)

    def _select_turno(self, idx: int | None) -> None:
        if getattr(self, "_read_only", False):
            return
        self._turno_selected = idx
        for i, r in enumerate(self._turnos_rows):
            w = r["widget"]
            if i == idx:
                w.setStyleSheet(
                    "QWidget#TurnoRow { border: 1px solid #5AC8FA; border-radius: 6px; background: rgba(90,200,250,18%); }"  # noqa: E501
                )
            else:
                w.setStyleSheet(
                    "QWidget#TurnoRow { border: 1px solid transparent; border-radius: 6px; }"
                )

    def _remove_selected(self) -> None:
        if getattr(self, "_read_only", False):
            return
        if self._turno_selected is None or self._turno_selected >= len(self._turnos_rows):
            if len(self._turnos_rows) <= 1:
                return
            idx = len(self._turnos_rows) - 1
        else:
            idx = self._turno_selected
        if len(self._turnos_rows) <= 1:
            return
        row = self._turnos_rows[idx]
        self._turnos_layout.removeWidget(row["widget"])
        row["widget"].deleteLater()
        self._turnos_rows.pop(idx)
        if self._turnos_rows:
            self._select_turno(min(idx, len(self._turnos_rows) - 1))
        else:
            self._turno_selected = None

    def _remove_turno_row(self, row: dict) -> None:
        if row in self._turnos_rows:
            idx = self._turnos_rows.index(row)
            self._turno_selected = idx
            self._remove_selected()

    def horarios_text(self) -> str | None:
        return _horarios_text_from_rows(self._turnos_rows)

    @property
    def edt_horarios(self):  # type: ignore[no-untyped-def]
        class _Fake:
            def __init__(self, dlg):
                self._dlg = dlg

            def text(self):
                return self._dlg.horarios_text() or ""

            def setText(self, v):
                pass

            def setReadOnly(self, v):
                pass

        return _Fake(self)

    @property
    def edt_dias(self):  # type: ignore[no-untyped-def]
        class _Fake:
            def __init__(self, dlg):
                self._dlg = dlg

            def text(self):
                return ""

            def setText(self, v):
                pass

            def setReadOnly(self, v):
                pass

        return _Fake(self)

    def _detectar_tema(self):  # type: ignore[no-untyped-def]
        from gymflux.ui.theme import ModoTema

        tema = ModoTema.ESCURO
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            ss = ""
            if isinstance(app, QApplication):
                ss = app.styleSheet()
            if "#E8EDF1" in ss:
                tema = ModoTema.CLARO
        except Exception:
            pass
        return tema

    def _aplicar_tema_foto(self, tem_foto: bool) -> None:
        from gymflux.ui.theme import paleta_do_modo

        try:
            paleta = paleta_do_modo(self._detectar_tema())
        except Exception:
            from gymflux.ui.theme import PALETA_ESCURA

            paleta = PALETA_ESCURA
        is_claro = paleta.texto == "#1A1E22"
        bg = paleta.painel if is_claro else "#0F1113"
        border = "#C8D0D8" if is_claro else "#5AC8FA"
        if tem_foto:
            self.lbl_foto.setStyleSheet(
                f"QLabel {{ border: 2px solid {border}; border-radius: 8px;"
                f" background-color: {bg}; }}"
            )
        else:
            self.lbl_foto.setStyleSheet(
                f"QLabel {{ border: 2px dashed {border}; border-radius: 8px;"
                f" background-color: {bg}; color: {paleta.suave}; }}"
            )

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
        foto_src_str = str(foto_src).strip() if foto_src else ""
        foto_atual_str = str(foto_atual).strip() if foto_atual else ""
        if foto_src_str and Path(foto_src_str).exists():
            is_same = False
            try:
                if foto_atual_str and Path(foto_atual_str).exists():
                    is_same = Path(foto_src_str).resolve() == Path(foto_atual_str).resolve()
            except Exception:
                is_same = False
            if is_same:
                foto_final = foto_atual_str
            else:
                try:
                    dst_dir = Path("data/fotos/funcionarios")
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    ext = Path(foto_src_str).suffix or ".jpg"
                    dst = dst_dir / f"{self._func_id}{ext}"
                    import shutil

                    shutil.copy2(foto_src_str, dst)
                    foto_final = str(dst)
                except Exception:
                    foto_final = foto_src_str
        elif not foto_src_str and foto_atual_str:
            foto_final = None
        else:
            foto_final = foto_atual_str or None
        # horarios via turnos editor
        horarios_txt = self.horarios_text()
        try:
            self._vm.atualizar(
                self._func_id,
                nome=self.edt_nome.text(),
                senha=self.edt_senha.text(),
                horarios=horarios_txt,
                dias=None,
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
        central = QHBoxLayout()
        central.setSpacing(12)
        self.tbl = QTableWidget(0, len(self.COLUNAS))
        self.tbl.setHorizontalHeaderLabels(list(self.COLUNAS))
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setColumnHidden(0, True)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        # legibilidade turnos: wrap + largura fixa + resize mode
        self.tbl.setWordWrap(True)
        self.tbl.verticalHeader().setDefaultSectionSize(44)
        self.tbl.horizontalHeader().setSectionResizeMode(
            3, self.tbl.horizontalHeader().ResizeMode.Fixed
        )
        self.tbl.setColumnWidth(3, 200)
        self.tbl.horizontalHeader().setSectionResizeMode(
            4, self.tbl.horizontalHeader().ResizeMode.Fixed
        )
        self.tbl.setColumnWidth(4, 90)
        central.addWidget(self.tbl, 3)
        from PySide6.QtWidgets import QFrame

        self.detalhes_frame = QFrame()
        self.detalhes_frame.setObjectName("DetalhesFuncFrame")
        self.detalhes_frame.setMinimumWidth(280)
        self.detalhes_frame.setMaximumWidth(340)
        det_lay = QVBoxLayout(self.detalhes_frame)
        det_lay.setContentsMargins(12, 12, 12, 12)
        det_lay.setSpacing(8)
        self.lbl_detalhes_foto = QLabel()
        self.lbl_detalhes_foto.setFixedSize(140, 140)
        self.lbl_detalhes_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_detalhes_foto.setText("Sem foto")
        det_lay.addWidget(self.lbl_detalhes_foto, 0, Qt.AlignmentFlag.AlignHCenter)
        self.lbl_detalhes_nome = QLabel("Selecione um funcionário")
        self.lbl_detalhes_nome.setWordWrap(True)
        det_lay.addWidget(self.lbl_detalhes_nome)
        self.lbl_detalhes_info = QLabel("Detalhes aparecerão aqui")
        self.lbl_detalhes_info.setWordWrap(True)
        self.lbl_detalhes_info.setTextFormat(Qt.TextFormat.PlainText)
        det_lay.addWidget(self.lbl_detalhes_info)
        det_lay.addStretch(1)
        central.addWidget(self.detalhes_frame, 1)
        layout.addLayout(central, 1)
        self._aplicar_tema_detalhes()
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
        self.tbl.cellDoubleClicked.connect(lambda _r, _c: self._editar())
        self.tbl.itemSelectionChanged.connect(self._atualizar_detalhes)
        self.tbl.customContextMenuRequested.connect(self._menu_contexto)
        self.recarregar()

    def recarregar(self) -> None:
        funcs = self.vm.listar()
        self.tbl.setRowCount(len(funcs))
        for row, f in enumerate(funcs):
            horarios_compacto = format_turnos_compacto(f.horarios, f.dias)
            # tooltip com texto completo
            tooltip_full = f.horarios or f.dias or "—"
            if f.horarios and f.dias and f.dias not in f.horarios:
                tooltip_full = f"{f.horarios} ({f.dias})"
            vals = (
                f.id,
                f.nome,
                "SIM" if f.ativo else "não",
                horarios_compacto,
                f.dias or "—",
            )
            for col, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if col == 3:
                    item.setToolTip(tooltip_full)
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                    )
                self.tbl.setItem(row, col, item)
        # ajusta altura das linhas para wrap
        self.tbl.resizeRowsToContents()
        self._atualizar_detalhes()

    def _atualizar_detalhes(self) -> None:
        row = self.tbl.currentRow()
        if row < 0:
            self.lbl_detalhes_foto.clear()
            self.lbl_detalhes_foto.setText("Sem foto")
            self.lbl_detalhes_nome.setText("Selecione um funcionário")
            self.lbl_detalhes_info.setText("Detalhes aparecerão aqui")
            self._aplicar_tema_detalhes()
            return
        item_id = self.tbl.item(row, 0)
        if item_id is None:
            return
        func = self.vm.buscar(item_id.text())
        if func is None:
            return
        foto_path = getattr(func, "foto", None)
        if foto_path and Path(foto_path).exists():  # type: ignore[arg-type]
            pix = QPixmap(foto_path)
            if not pix.isNull():
                scaled = pix.scaled(
                    QSize(140, 140),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                x = max(0, (scaled.width() - 140) // 2)
                y = max(0, (scaled.height() - 140) // 2)
                cropped = scaled.copy(x, y, 140, 140)
                self.lbl_detalhes_foto.setPixmap(cropped)
            else:
                self.lbl_detalhes_foto.clear()
                self.lbl_detalhes_foto.setText("Sem foto")
        else:
            self.lbl_detalhes_foto.clear()
            self.lbl_detalhes_foto.setText("Sem foto")
        self.lbl_detalhes_nome.setText(func.nome)
        # detalhe com horários compacto + original
        horarios_linha = format_turnos_compacto(func.horarios, func.dias).replace("\n", " | ")
        info = (
            f"Nome: {func.nome}\n"
            f"Ativo: {'SIM' if func.ativo else 'não'}\n"
            f"Horários: {horarios_linha}\n"
            f"Dias: {func.dias or '—'}"
        )
        self.lbl_detalhes_info.setText(info)
        self._aplicar_tema_detalhes()

    def _aplicar_tema_detalhes(self, tema=None) -> None:  # type: ignore[no-untyped-def]
        from gymflux.ui.theme import ModoTema, paleta_do_modo

        if tema is None:
            tema = ModoTema.ESCURO
            try:
                from PySide6.QtWidgets import QApplication

                app = QApplication.instance()
                ss = ""
                if isinstance(app, QApplication):
                    ss = app.styleSheet()
                if "#E8EDF1" in ss:
                    tema = ModoTema.CLARO
            except Exception:
                pass
        try:
            paleta = paleta_do_modo(tema)
        except Exception:
            from gymflux.ui.theme import PALETA_ESCURA

            paleta = PALETA_ESCURA
        self.detalhes_frame.setStyleSheet(
            f"QFrame {{ border: 1px solid {paleta.borda}; border-radius: 8px;"
            f" background-color: {paleta.painel}; }}"
        )
        is_claro = paleta.texto == "#1A1E22"
        foto_bg = paleta.painel if is_claro else "#0F1113"
        foto_border = "#C8D0D8" if is_claro else "#5AC8FA"
        pm = self.lbl_detalhes_foto.pixmap()
        if pm is None or pm.isNull():
            self.lbl_detalhes_foto.setStyleSheet(
                f"QLabel {{ border: 2px dashed {foto_border}; border-radius: 8px;"
                f" background-color: {foto_bg}; color: {paleta.suave}; }}"
            )
        else:
            self.lbl_detalhes_foto.setStyleSheet(
                f"QLabel {{ border: 2px solid {foto_border}; border-radius: 8px;"
                f" background-color: {foto_bg}; }}"
            )
        self.lbl_detalhes_nome.setStyleSheet(
            f"font-weight: bold; font-size: 14px; color: {paleta.texto}; background: transparent;"
        )
        self.lbl_detalhes_info.setStyleSheet(f"color: {paleta.suave}; background: transparent;")

    def sincronizar_tema(self, tema) -> None:
        self._aplicar_tema_detalhes(tema)

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
        horarios_txt = dlg.horarios_text()
        try:
            func = self.vm.cadastrar(
                nome=dlg.edt_nome.text(),
                senha=dlg.edt_senha.text(),
                horarios=horarios_txt,
                dias=None,
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
                    self.vm.atualizar(
                        func.id,
                        nome=func.nome,
                        senha="",
                        horarios=func.horarios,
                        dias=func.dias,
                        foto=str(dst),
                    )
                except Exception:
                    pass
        except ValueError as e:
            QMessageBox.warning(self, "Funcionários", str(e))
            return
        self.recarregar()

    def _editar(self) -> None:
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
        a_editar = menu.addAction(
            icone_preto(self.style(), QStyle.StandardPixmap.SP_FileDialogDetailedView),
            "Editar",
        )
        a_ativar = menu.addAction("Ativar/Inativar")
        acao = menu.exec(self.tbl.viewport().mapToGlobal(pos))
        if acao == a_editar:
            self._editar()
        elif acao == a_ativar:
            self._alternar_ativo()
