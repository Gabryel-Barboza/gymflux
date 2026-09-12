"""Aba Configurações — preferências operacionais da recepção."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from gymflow.ui.config_store import UiConfig
from gymflow.ui.theme import estilo_resultado
from gymflow.ui.viewmodels.config import ConfigViewModel


class ConfigView(QWidget):
    """Checkboxes + spins + porta; Salvar persiste e aplica na sessão."""

    def __init__(self, vm: ConfigViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.vm = vm
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.chk_bloq_entrada = QCheckBox("Bloquear entrada (NEGADO direto)")
        self.chk_bloq_saida = QCheckBox("Bloquear saída (NEGADO direto)")
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
        self.edt_porta = QLineEdit()
        self.edt_porta.setPlaceholderText("Ex.: 1, COM3, MOCK:1")
        form.addRow(self.chk_bloq_entrada)
        form.addRow(self.chk_bloq_saida)
        form.addRow("Senha mínima:", self.spn_senha_min)
        form.addRow("Tolerância:", self.spn_tolerancia)
        form.addRow("Timeout giro:", self.spn_timeout)
        form.addRow(self.chk_passback)
        form.addRow("Porta catraca:", self.edt_porta)
        layout.addLayout(form)

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

    def _salvar(self) -> None:
        cfg = UiConfig(
            bloquear_entrada=self.chk_bloq_entrada.isChecked(),
            bloquear_saida=self.chk_bloq_saida.isChecked(),
            senha_min_digitos=self.spn_senha_min.value(),
            tolerancia_dias=self.spn_tolerancia.value(),
            timeout_giro_s=self.spn_timeout.value(),
            anti_passback=self.chk_passback.isChecked(),
            porta_catraca=self.edt_porta.text(),
        )
        try:
            self.vm.salvar(cfg)
        except OSError as e:
            self.lbl_status.setText(f"Erro ao salvar: {e}")
            self.lbl_status.setStyleSheet(estilo_resultado(False))
            return
        self._carregar(self.vm.config)
        self.lbl_status.setText("Configurações salvas e aplicadas.")
        self.lbl_status.setStyleSheet(estilo_resultado(True))
