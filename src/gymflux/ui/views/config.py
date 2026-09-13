"""Aba Configurações — categorias Catraca / Personalização / Regras."""

from __future__ import annotations

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
from gymflux.ui.theme import ModoTema, estilo_resultado, modo_de
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
        self.cmb_entrada_modo.addItem("LIVRE (passa sem senha)", ModoAcesso.LIVRE)
        self.cmb_entrada_modo.addItem("SENHA (exige identificação)", ModoAcesso.SENHA)
        self.cmb_saida_modo = QComboBox()
        self.cmb_saida_modo.addItem("LIVRE (passa sem senha)", ModoAcesso.LIVRE)
        self.cmb_saida_modo.addItem("SENHA (exige identificação)", ModoAcesso.SENHA)
        # legado: mantém checkboxes para compat testes antigos (ocultos mas funcionais)
        self.chk_bloq_entrada = QCheckBox("Bloquear entrada (NEGADO direto) [legado]")
        self.chk_bloq_saida = QCheckBox("Bloquear saída (NEGADO direto) [legado]")
        self.chk_bloq_entrada.setVisible(False)
        self.chk_bloq_saida.setVisible(False)
        form_catraca.addRow("Porta catraca:", self.edt_porta)
        form_catraca.addRow("Entrada:", self.cmb_entrada_modo)
        form_catraca.addRow("Saída:", self.cmb_saida_modo)
        form_catraca.addRow(self.chk_bloq_entrada)
        form_catraca.addRow(self.chk_bloq_saida)
        layout.addWidget(grp_catraca)

        # -- Categoria: Personalização ------------------------------------------
        grp_pers = QGroupBox("Personalização")
        form_pers = QFormLayout(grp_pers)
        self.cmb_tema = QComboBox()
        self.cmb_tema.addItem("Escuro", ModoTema.ESCURO)
        self.cmb_tema.addItem("Claro", ModoTema.CLARO)
        form_pers.addRow("Tema:", self.cmb_tema)
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
        form_regras.addRow("Senha mínima:", self.spn_senha_min)
        form_regras.addRow("Tolerância:", self.spn_tolerancia)
        form_regras.addRow("Timeout giro:", self.spn_timeout)
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

        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)
        layout.addStretch(1)

        self.btn_salvar.clicked.connect(self._salvar)
        self._carregar(self.vm.config)

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
            self.lbl_status.setText(f"Erro ao salvar: {e}")
            self.lbl_status.setStyleSheet(estilo_resultado(False, self.vm.config.tema))
            return
        self._carregar(self.vm.config)
        self.lbl_status.setText("Configurações salvas e aplicadas.")
        self.lbl_status.setStyleSheet(estilo_resultado(True, self.vm.config.tema))
