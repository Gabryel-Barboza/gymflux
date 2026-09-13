"""Aba Configurações — categorias Catraca / Personalização / Regras."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from gymflux.ui.config_store import ModoAcesso, UiConfig
from gymflux.ui.theme import ModoTema, modo_de
from gymflux.ui.viewmodels.config import ConfigViewModel


class ConfigView(QWidget):
    """Categorias + combos LIVRE/SENHA por direção; Salvar persiste e aplica."""

    def __init__(self, vm: ConfigViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.vm = vm
        layout = QVBoxLayout(self)

        # -- Categoria: Catraca -------------------------------------------------
        grp_catraca = QGroupBox("Catraca")
        form_catraca = QFormLayout(grp_catraca)
        self.edt_porta = QLineEdit()
        self.edt_porta.setPlaceholderText("Ex.: 1, COM3, MOCK:1")
        self.cmb_entrada_modo = QComboBox()
        self.cmb_entrada_modo.addItem("LIVRE", ModoAcesso.LIVRE)
        self.cmb_entrada_modo.addItem("SENHA", ModoAcesso.SENHA)
        self.cmb_saida_modo = QComboBox()
        self.cmb_saida_modo.addItem("LIVRE", ModoAcesso.LIVRE)
        self.cmb_saida_modo.addItem("SENHA", ModoAcesso.SENHA)
        # legado: mantém checkboxes para compat testes antigos (ocultos mas funcionais)
        self.chk_bloq_entrada = QCheckBox("Bloquear entrada (NEGADO direto) [legado]")
        self.chk_bloq_saida = QCheckBox("Bloquear saída (NEGADO direto) [legado]")
        self.chk_bloq_entrada.setVisible(False)
        self.chk_bloq_saida.setVisible(False)
        lbl_porta = QLabel("Porta catraca:")
        lbl_porta.setToolTip("Porta serial da catraca (ex: 1, COM3, MOCK:1)")
        lbl_porta.setWhatsThis("Porta serial da catraca (ex: 1, COM3, MOCK:1)")
        lbl_entrada = QLabel("Entrada:")
        lbl_entrada.setToolTip("Modo de acesso na entrada")
        lbl_entrada.setWhatsThis(
            "Modo de acesso na entrada: LIVRE passa sem senha, SENHA exige identificação"
        )
        lbl_saida = QLabel("Saída:")
        lbl_saida.setToolTip("Modo de acesso na saída")
        lbl_saida.setWhatsThis(
            "Modo de acesso na saída: LIVRE passa sem senha, SENHA exige identificação"
        )
        form_catraca.addRow(lbl_porta, self.edt_porta)
        form_catraca.addRow(lbl_entrada, self.cmb_entrada_modo)
        form_catraca.addRow(lbl_saida, self.cmb_saida_modo)
        form_catraca.addRow(self.chk_bloq_entrada)
        form_catraca.addRow(self.chk_bloq_saida)
        layout.addWidget(grp_catraca)

        # -- Categoria: Personalização ------------------------------------------
        grp_pers = QGroupBox("Personalização")
        form_pers = QFormLayout(grp_pers)
        self.cmb_tema = QComboBox()
        self.cmb_tema.addItem("Escuro", ModoTema.ESCURO)
        self.cmb_tema.addItem("Claro", ModoTema.CLARO)
        lbl_tema = QLabel("Tema:")
        lbl_tema.setToolTip("Tema visual da interface")
        lbl_tema.setWhatsThis("Tema visual da interface: escuro ou claro")
        form_pers.addRow(lbl_tema, self.cmb_tema)
        layout.addWidget(grp_pers)

        # -- Categoria: Regras / Operação ---------------------------------------
        grp_regras = QGroupBox("Regras")
        form_regras = QFormLayout(grp_regras)
        self.spn_senha_min = QSpinBox()
        self.spn_senha_min.setRange(4, 8)
        self.spn_senha_min.setSuffix(" dígitos")
        self.spn_tolerancia = QSpinBox()
        self.spn_tolerancia.setRange(0, 30)
        self.spn_tolerancia.setSuffix(" dias")
        self.spn_timeout = QSpinBox()
        self.spn_timeout.setRange(1, 60)
        self.spn_timeout.setSuffix(" s")
        self.chk_passback = QCheckBox("Anti-passback (RB05)")
        self.chk_passback.setToolTip("impede dupla entrada")
        self.chk_passback.setWhatsThis("impede dupla entrada: bloqueia segunda entrada sem saída")
        lbl_senha_min = QLabel("Senha mínima:")
        lbl_senha_min.setToolTip("Mínimo de dígitos da senha numérica")
        lbl_senha_min.setWhatsThis("Mínimo de dígitos da senha numérica (4-8)")
        lbl_tol = QLabel("Tolerância:")
        lbl_tol.setToolTip("dias após vencimento ainda libera")
        lbl_tol.setWhatsThis("dias após vencimento ainda libera (RB01)")
        lbl_timeout = QLabel("Timeout giro:")
        lbl_timeout.setToolTip("Tempo máximo para girar a catraca após liberar")
        lbl_timeout.setWhatsThis("Tempo máximo para girar a catraca após liberar (segundos)")
        form_regras.addRow(lbl_senha_min, self.spn_senha_min)
        form_regras.addRow(lbl_tol, self.spn_tolerancia)
        form_regras.addRow(lbl_timeout, self.spn_timeout)
        form_regras.addRow(self.chk_passback)
        layout.addWidget(grp_regras)

        botoes = QHBoxLayout()
        self.btn_salvar = QPushButton("Salvar e aplicar")
        self.btn_salvar.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        )
        botoes.addWidget(self.btn_salvar)
        botoes.addStretch(1)
        layout.addLayout(botoes)
        layout.addStretch(1)

        # toast overlay (não ocupa linha, width proporcional ao texto, centered, verde #A3D65C)
        self.lbl_status = QLabel("", self)
        self.lbl_status.setVisible(False)
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.lbl_status.setStyleSheet(
            "background-color: #A3D65C; color: #0F1113; "
            "padding: 6px 12px; border-radius: 6px; font-weight: bold;"
        )
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(lambda: self.lbl_status.setVisible(False))

        self.btn_salvar.clicked.connect(self._salvar)
        self._carregar(self.vm.config)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self.lbl_status.isVisible():
            self.lbl_status.adjustSize()
            x = (self.width() - self.lbl_status.width()) // 2
            y = (self.height() - self.lbl_status.height()) // 2
            self.lbl_status.move(max(0, x), max(12, y))

    def _mostrar_toast(self, texto: str, ok: bool) -> None:
        self.lbl_status.setText(texto)
        if ok:
            self.lbl_status.setStyleSheet(
                "background-color: #A3D65C; color: #0F1113; "
                "padding: 6px 12px; border-radius: 6px; font-weight: bold;"
            )
        else:
            self.lbl_status.setStyleSheet(
                "background-color: #E57373; color: #0F1113; "
                "padding: 6px 12px; border-radius: 6px; font-weight: bold;"
            )
        self.lbl_status.adjustSize()
        x = (self.width() - self.lbl_status.width()) // 2
        y = (self.height() - self.lbl_status.height()) // 2
        if x < 0:
            x = 8
        if y < 0:
            y = 12
        self.lbl_status.move(x, y)
        self.lbl_status.setVisible(True)
        self.lbl_status.raise_()
        self._toast_timer.start(3000)

    # -- slots -----------------------------------------------------------------
    def _carregar(self, cfg: UiConfig) -> None:
        self.chk_bloq_entrada.setChecked(cfg.bloquear_entrada)
        self.chk_bloq_saida.setChecked(cfg.bloquear_saida)
        self.spn_senha_min.setValue(cfg.senha_min_digitos)
        self.spn_tolerancia.setValue(cfg.tolerancia_dias)
        self.spn_timeout.setValue(cfg.timeout_giro_s)
        self.chk_passback.setChecked(cfg.anti_passback)
        self.edt_porta.setText(cfg.porta_catraca)
        idx = self.cmb_tema.findData(cfg.tema)
        self.cmb_tema.setCurrentIndex(idx if idx >= 0 else 0)
        idx_e = self.cmb_entrada_modo.findData(cfg.entrada_modo)
        self.cmb_entrada_modo.setCurrentIndex(idx_e if idx_e >= 0 else 1)
        idx_s = self.cmb_saida_modo.findData(cfg.saida_modo)
        self.cmb_saida_modo.setCurrentIndex(idx_s if idx_s >= 0 else 0)

    def _salvar(self) -> None:
        # currentData volta como str puro do QVariant: normaliza
        cfg = UiConfig(
            bloquear_entrada=self.chk_bloq_entrada.isChecked(),
            bloquear_saida=self.chk_bloq_saida.isChecked(),
            senha_min_digitos=self.spn_senha_min.value(),
            tolerancia_dias=self.spn_tolerancia.value(),
            timeout_giro_s=self.spn_timeout.value(),
            anti_passback=self.chk_passback.isChecked(),
            porta_catraca=self.edt_porta.text(),
            tema=modo_de(self.cmb_tema.currentData()),
            entrada_modo=self.cmb_entrada_modo.currentData() or ModoAcesso.SENHA,
            saida_modo=self.cmb_saida_modo.currentData() or ModoAcesso.LIVRE,
        )
        # normaliza enum caso venha str
        if isinstance(cfg.entrada_modo, str):
            try:
                cfg.entrada_modo = ModoAcesso(cfg.entrada_modo)
            except ValueError:
                cfg.entrada_modo = ModoAcesso.SENHA
        if isinstance(cfg.saida_modo, str):
            try:
                cfg.saida_modo = ModoAcesso(cfg.saida_modo)
            except ValueError:
                cfg.saida_modo = ModoAcesso.LIVRE
        try:
            self.vm.salvar(cfg)
        except OSError as e:
            self._mostrar_toast(f"Erro ao salvar: {e}", False)
            return
        self._carregar(self.vm.config)
        self._mostrar_toast("Configurações salvas e aplicadas.", True)
