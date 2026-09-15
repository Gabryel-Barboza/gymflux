"""Aba Configurações — categorias Catraca / Personalização / Regras."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
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

from gymflux.ui.config_store import ModoAcesso, ModoFundo, UiConfig
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
        # wallpaper com opção sólido vs wallpaper
        self.cmb_fundo = QComboBox()
        self.cmb_fundo.addItem("Cor sólida", ModoFundo.SOLIDO)
        self.cmb_fundo.addItem("Wallpaper", ModoFundo.WALLPAPER)
        lbl_fundo = QLabel("Fundo:")
        lbl_fundo.setToolTip("Escolha entre cor sólida do tema ou imagem de wallpaper")
        lbl_fundo.setWhatsThis(
            "Fundo: Cor sólida usa a cor do tema, Wallpaper exibe imagem ao fundo"
        )
        form_pers.addRow(lbl_fundo, self.cmb_fundo)
        self.edt_wallpaper = QLineEdit()
        self.edt_wallpaper.setPlaceholderText("auto")
        self.edt_wallpaper.setReadOnly(True)
        self.edt_wallpaper.setToolTip("Imagem de fundo — vazio = automático por tema (preto/branco)")  # noqa: E501
        self.btn_wallpaper = QPushButton("Escolher...")
        self.btn_wallpaper.setToolTip("Escolher imagem de wallpaper")
        self.btn_wallpaper_limpar = QPushButton("Limpar")
        self.btn_wallpaper_limpar.setToolTip("Usar wallpaper automático por tema (vazio)")
        hwall = QHBoxLayout()
        hwall.addWidget(self.edt_wallpaper, 1)
        hwall.addWidget(self.btn_wallpaper)
        hwall.addWidget(self.btn_wallpaper_limpar)
        lbl_wall = QLabel("Wallpaper:")
        lbl_wall.setToolTip("Imagem de fundo — vazio = automático por tema")
        lbl_wall.setWhatsThis(
            "Wallpaper: vazio usa preto no escuro e branco no claro; escolha um arquivo para fixo"
        )
        form_pers.addRow(lbl_wall, hwall)
        layout.addWidget(grp_pers)

        # -- Categoria: Cadastro (obrigatoriedade configurável) -----------------
        grp_cadastro = QGroupBox("Cadastro")
        form_cad = QFormLayout(grp_cadastro)
        self.chk_cpf_obr = QCheckBox("CPF obrigatório")
        self.chk_tel_obr = QCheckBox("Telefone obrigatório")
        self.chk_email_obr = QCheckBox("E-mail obrigatório")
        self.chk_nasc_obr = QCheckBox("Nascimento obrigatório")
        self.chk_end_obr = QCheckBox("Endereço obrigatório")
        for chk in (
            self.chk_cpf_obr,
            self.chk_tel_obr,
            self.chk_email_obr,
            self.chk_nasc_obr,
            self.chk_end_obr,
        ):
            chk.setToolTip("Se marcado, o campo passa a ser obrigatório no cadastro")
        form_cad.addRow(self.chk_cpf_obr)
        form_cad.addRow(self.chk_tel_obr)
        form_cad.addRow(self.chk_email_obr)
        form_cad.addRow(self.chk_nasc_obr)
        form_cad.addRow(self.chk_end_obr)
        layout.addWidget(grp_cadastro)

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
        self.btn_wallpaper.clicked.connect(self._escolher_wallpaper)
        self.btn_wallpaper_limpar.clicked.connect(self._limpar_wallpaper)
        self.cmb_fundo.currentIndexChanged.connect(self._atualizar_fundo_estado)
        self._carregar(self.vm.config)
        self._atualizar_fundo_estado()

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
        self.edt_wallpaper.setText(cfg.wallpaper or "")
        idx_f = self.cmb_fundo.findData(cfg.fundo_modo)
        self.cmb_fundo.setCurrentIndex(idx_f if idx_f >= 0 else 1)
        # cadastro obrigatórios
        obr = getattr(cfg, "cadastro_obrigatorios", {}) or {}
        self.chk_cpf_obr.setChecked(bool(obr.get("cpf", False)))
        self.chk_tel_obr.setChecked(bool(obr.get("telefone", False)))
        self.chk_email_obr.setChecked(bool(obr.get("email", False)))
        self.chk_nasc_obr.setChecked(bool(obr.get("data_nasc", False)))
        self.chk_end_obr.setChecked(bool(obr.get("endereco", False)))
        self._atualizar_fundo_estado()

    def _escolher_wallpaper(self) -> None:
        caminho, _ = QFileDialog.getOpenFileName(
            self,
            "Escolher wallpaper",
            self.edt_wallpaper.text() or "src/gymflux/ui/assets",
            "Imagens (*.png *.jpg *.jpeg *.bmp *.gif);;Todos (*)",
        )
        if caminho:
            self.edt_wallpaper.setText(caminho)

    def _limpar_wallpaper(self) -> None:
        self.edt_wallpaper.clear()

    def _atualizar_fundo_estado(self) -> None:
        modo = self.cmb_fundo.currentData()
        is_wall = modo == ModoFundo.WALLPAPER
        self.edt_wallpaper.setEnabled(is_wall)
        self.btn_wallpaper.setEnabled(is_wall)
        self.btn_wallpaper_limpar.setEnabled(is_wall)

    def _salvar(self) -> None:
        # currentData volta como str puro do QVariant: normaliza
        wall = self.edt_wallpaper.text().strip() or None
        fundo = self.cmb_fundo.currentData() or ModoFundo.WALLPAPER
        if isinstance(fundo, str):
            try:
                fundo = ModoFundo(fundo)
            except ValueError:
                fundo = ModoFundo.WALLPAPER
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
            wallpaper=wall,
            fundo_modo=fundo,
            cadastro_obrigatorios={
                "cpf": self.chk_cpf_obr.isChecked(),
                "telefone": self.chk_tel_obr.isChecked(),
                "email": self.chk_email_obr.isChecked(),
                "data_nasc": self.chk_nasc_obr.isChecked(),
                "endereco": self.chk_end_obr.isChecked(),
            },
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
