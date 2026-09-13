"""Catraca — layout moderno: header compacto + centro CPF/senha + logs lado a lado."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

from loguru import logger
from PySide6.QtCore import QEvent, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gymflux.core.acesso import TentativaAcesso
from gymflux.ui.catraca_bridge import CatracaBridge
from gymflux.ui.theme import VERMELHO, cores_indicador, estilo_resultado
from gymflux.ui.viewmodels.dashboard import DashboardViewModel

LINHAS_VISIVEIS = 3
LINHAS_MAX_TABELA = 8


class DetalhesDialog(QDialog):
    def __init__(self, status: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Detalhes da catraca")
        self.resize(420, 320)
        lay = QVBoxLayout(self)
        tbl = QTableWidget(len(status), 2)
        tbl.setHorizontalHeaderLabels(["Campo", "Valor"])
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setStretchLastSection(True)
        for row, (k, v) in enumerate(sorted(status.items())):
            tbl.setItem(row, 0, QTableWidgetItem(str(k)))
            tbl.setItem(row, 1, QTableWidgetItem(str(v)))
        lay.addWidget(tbl)
        botoes = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        botoes.rejected.connect(self.reject)
        botoes.accepted.connect(self.accept)
        lay.addWidget(botoes)


class DashboardView(QWidget):
    """Header + centro + logs/giros lado a lado com headers fixos; toast 4s."""

    COLUNAS_LOG = ("Hora", "Aluno", "Direção", "Resultado", "Motivo")
    LINHAS_STATUS = ("Online", "Bloqueada", "Giros", "Firmware", "Driver", "Porta")

    perfil_solicitado = Signal(str)

    def __init__(
        self,
        vm: DashboardViewModel,
        bridge: CatracaBridge,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.vm = vm
        self.bridge = bridge
        self._tentativas_visiveis: list[TentativaAcesso] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        estilo = self.style()

        # -- toast overlay centralizado e destacado (modal) -----------------------
        self.toast = QLabel("", self)
        self.toast.setVisible(False)
        self.toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.toast.setWordWrap(True)
        self.toast.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # sombra para destacar sobre o fundo
        try:
            from PySide6.QtWidgets import QGraphicsDropShadowEffect

            _shadow = QGraphicsDropShadowEffect(self.toast)
            _shadow.setBlurRadius(18)
            _shadow.setOffset(0, 4)
            _shadow.setColor(QColor(0, 0, 0, 110))
            self.toast.setGraphicsEffect(_shadow)
        except Exception:
            pass
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(lambda: self.toast.setVisible(False))

        # -- header moderno: status compacto + Detalhes à direita ---------------
        header = QFrame(self)
        header.setObjectName("CatracaHeader")
        header.setStyleSheet(
            "QFrame#CatracaHeader { border: 1px solid #C8D0D8; border-radius: 8px; padding: 4px; }"
        )
        hstatus = QHBoxLayout(header)
        hstatus.setContentsMargins(8, 6, 8, 6)
        self.lbl_compacto = QLabel("—")
        self.lbl_compacto.setTextFormat(Qt.TextFormat.PlainText)
        self.btn_detalhes = QPushButton("Detalhes")
        self.btn_detalhes.setIcon(
            estilo.standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        )
        self.btn_detalhes.setMinimumHeight(28)
        hstatus.addWidget(self.lbl_compacto, 1)
        hstatus.addWidget(self.btn_detalhes)
        layout.addWidget(header)
        self.header = header

        # tabela detalhada oculta (compat)
        self.tbl_status = QTableWidget(len(self.LINHAS_STATUS), 2)
        self.tbl_status.setHorizontalHeaderLabels(["Campo", "Valor"])
        self.tbl_status.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_status.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tbl_status.verticalHeader().setVisible(False)
        self.tbl_status.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tbl_status.horizontalHeader().setStretchLastSection(True)
        self._itens_status: dict[str, QTableWidgetItem] = {}
        for row, campo in enumerate(self.LINHAS_STATUS):
            self.tbl_status.setItem(row, 0, QTableWidgetItem(campo))
            item = QTableWidgetItem("—")
            self.tbl_status.setItem(row, 1, item)
            self._itens_status[campo] = item
        linha_status = self._altura_tabela(self.tbl_status, len(self.LINHAS_STATUS))
        self.tbl_status.setMaximumHeight(linha_status)
        self.tbl_status.setVisible(False)
        layout.addWidget(self.tbl_status)

        # -- centro: campo CPF/senha + Liberar único (moderno, à direita) ---
        centro = QFrame(self)
        centro.setObjectName("CatracaCentro")
        # sem fundo sólido quando wallpaper ativo (wallpaper fica atrás)
        centro.setStyleSheet(
            "QFrame#CatracaCentro { border: 1px solid #C8D0D8; border-radius: 8px; }"
        )
        huni = QHBoxLayout(centro)
        huni.setContentsMargins(12, 12, 12, 12)
        huni.setSpacing(12)
        huni.addStretch(1)
        self.edt_unico = QLineEdit()
        self.edt_unico.setPlaceholderText("CPF ou senha")
        self.edt_unico.setClearButtonEnabled(True)
        self.edt_unico.setMinimumHeight(32)
        self.edt_unico.setMaximumWidth(310)
        self.edt_unico.setStyleSheet("font-size: 14px; padding: 6px;")
        self.btn_liberar = QPushButton("Liberar catraca")
        # ícone mais destacado: maior, com tint para contraste
        try:
            from gymflux.ui.app import _tint_icon
            from gymflux.ui.theme import AZUL

            _icon_base = estilo.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
            _icon_dest = _tint_icon(_icon_base, AZUL)
            self.btn_liberar.setIcon(_icon_dest)
        except Exception:
            self.btn_liberar.setIcon(estilo.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.btn_liberar.setIconSize(QSize(22, 22))
        self.btn_liberar.setMinimumHeight(32)
        self.btn_liberar.setMinimumWidth(150)
        self.btn_liberar.setStyleSheet(
            "font-size: 14px; font-weight: bold; padding: 6px 20px; "
            "border: 2px solid #5AC8FA;"
        )
        huni.addWidget(self.edt_unico)
        huni.addWidget(self.btn_liberar)
        layout.addWidget(centro)
        self.centro = centro

        # compat antigos (ocultos)
        self.edt_aluno = QLineEdit()
        self.edt_aluno.setPlaceholderText("ID ou CPF")
        self.edt_aluno.setVisible(False)
        self.edt_codigo = QLineEdit()
        self.edt_codigo.setPlaceholderText("Senha (teclado)")
        self.edt_codigo.setEchoMode(QLineEdit.EchoMode.Password)
        self.edt_codigo.setVisible(False)
        self.btn_identificar = QPushButton("Identificar")
        self.btn_identificar.setIcon(
            estilo.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        )
        self.btn_identificar.setVisible(False)
        self.btn_entrada = QPushButton("Liberar Entrada")
        self.btn_entrada.setIcon(estilo.standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.btn_entrada.setVisible(False)
        self.btn_saida = QPushButton("Liberar Saída")
        self.btn_saida.setIcon(estilo.standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.btn_saida.setVisible(False)
        self.btn_bloquear = QPushButton("Bloquear")
        self.btn_bloquear.setIcon(estilo.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        self.btn_bloquear.setVisible(False)
        layout.addWidget(self.edt_aluno)
        layout.addWidget(self.edt_codigo)
        layout.addWidget(self.btn_identificar)
        layout.addWidget(self.btn_entrada)
        layout.addWidget(self.btn_saida)
        layout.addWidget(self.btn_bloquear)

        self.lbl_resultado = QLabel("Informe o aluno e escolha a direção.")
        self.lbl_resultado.setVisible(False)
        layout.addWidget(self.lbl_resultado)
        self.lbl_verificacao = QLabel("Aguardando identificação...")
        fonte = self.lbl_verificacao.font()
        fonte.setPointSize(14)
        fonte.setBold(True)
        self.lbl_verificacao.setFont(fonte)
        self.lbl_verificacao.setVisible(False)
        layout.addWidget(self.lbl_verificacao)

        # -- logs / giros lado a lado — QFrame hugging tabela (borda cola no conteudo) --
        # empurra containers para baixo, sem centro vertical
        layout.addStretch(1)
        hmid = QHBoxLayout()
        hmid.setSpacing(12)
        hmid.setAlignment(Qt.AlignmentFlag.AlignBottom)
        frame_log = QFrame()
        frame_log.setObjectName("CatracaFrameLog")
        frame_log.setStyleSheet(
            "QFrame#CatracaFrameLog { border: 1px solid #2A3138; "
            "border-radius: 8px; padding: 6px; }"
        )
        frame_log.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        lay_log = QVBoxLayout(frame_log)
        lay_log.setContentsMargins(6, 6, 6, 6)
        lay_log.setSpacing(6)
        lay_log.setAlignment(Qt.AlignmentFlag.AlignTop)
        lbl_log = QLabel("Acessos de hoje")
        lbl_log.setStyleSheet("font-weight: bold; border: none;")
        lay_log.addWidget(lbl_log)
        self.tbl_log = QTableWidget(0, len(self.COLUNAS_LOG))
        self.tbl_log.setHorizontalHeaderLabels(list(self.COLUNAS_LOG))
        self.tbl_log.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_log.verticalHeader().setVisible(False)
        self.tbl_log.horizontalHeader().setStretchLastSection(True)
        self.tbl_log.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tbl_log.horizontalHeader().setHighlightSections(False)
        self.tbl_log.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # borda cola no conteudo: maxHeight = cabecalho + 8 linhas apenas
        tbl_h = self._altura_tabela(self.tbl_log, LINHAS_MAX_TABELA)
        self.tbl_log.setMaximumHeight(tbl_h)
        self.tbl_log.setMinimumHeight(tbl_h)
        lay_log.addWidget(self.tbl_log)
        # frame hugging: header + tabela + margins
        frame_log.setMaximumHeight(tbl_h + 30 + 12)
        hmid.addWidget(frame_log, 3)
        self.frame_log = frame_log

        frame_giros = QFrame()
        frame_giros.setObjectName("CatracaFrameGiros")
        frame_giros.setStyleSheet(
            "QFrame#CatracaFrameGiros { border: 1px solid #2A3138; "
            "border-radius: 8px; padding: 6px; }"
        )
        frame_giros.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        lay_giros = QVBoxLayout(frame_giros)
        lay_giros.setContentsMargins(6, 6, 6, 6)
        lay_giros.setSpacing(6)
        lay_giros.setAlignment(Qt.AlignmentFlag.AlignTop)
        lbl_giros = QLabel("Giros")
        lbl_giros.setStyleSheet("font-weight: bold; border: none;")
        lay_giros.addWidget(lbl_giros)
        self.lst_giros = QListWidget()
        lst_h = self._altura_lista(LINHAS_MAX_TABELA)
        self.lst_giros.setMaximumHeight(lst_h)
        self.lst_giros.setMinimumHeight(lst_h)
        lay_giros.addWidget(self.lst_giros)
        frame_giros.setMaximumHeight(lst_h + 30 + 12)
        hmid.addWidget(frame_giros, 1)
        self.frame_giros = frame_giros
        layout.addLayout(hmid)

        # -- wallpaper só atrás dos containers (não no fundo global) --
        # fundo um nível acima do CatracaCentro: DashboardView, não CatracaCentro
        self._wallpaper_pixmap: QPixmap | None = None
        self._wallpaper_path: str | None = None
        self._wallpaper_labels: dict[QFrame, QLabel] = {}
        # CatracaCentro fica com fundo transparente e mostra wallpaper do dashboard
        self._wallpaper_frames: list[QFrame] = [header, frame_log, frame_giros]
        for frm in self._wallpaper_frames:
            bg = QLabel(frm)
            bg.setObjectName(f"WallpaperBg_{frm.objectName()}")
            bg.setScaledContents(True)
            bg.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            bg.setStyleSheet("border: none; background: transparent; border-radius: 8px;")
            bg.lower()
            bg.hide()
            self._wallpaper_labels[frm] = bg
            frm.installEventFilter(self)
        # wallpaper de fundo do Dashboard (um nível acima do centro)
        self._wallpaper_bg_dashboard = QLabel(self)
        self._wallpaper_bg_dashboard.setObjectName("WallpaperBg_Dashboard")
        self._wallpaper_bg_dashboard.setScaledContents(True)
        self._wallpaper_bg_dashboard.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._wallpaper_bg_dashboard.setStyleSheet("border: none; background: transparent;")
        self._wallpaper_bg_dashboard.lower()
        self._wallpaper_bg_dashboard.hide()
        # CatracaCentro transparente para mostrar fundo do dashboard
        self.centro.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # -- sinais ------------------------------------------------------------
        self.btn_entrada.clicked.connect(lambda: self._liberar("ENTRADA"))
        self.btn_saida.clicked.connect(lambda: self._liberar("SAIDA"))
        self.btn_bloquear.clicked.connect(self._bloquear)
        self.btn_identificar.clicked.connect(self._identificar)
        self.btn_liberar.clicked.connect(self._liberar_unico)
        self.edt_unico.returnPressed.connect(self._liberar_unico)
        self.btn_detalhes.clicked.connect(self._mostrar_detalhes)
        self.tbl_log.cellClicked.connect(self._registro_clicado)
        self.bridge.giro_detectado.connect(self._on_giro)
        self.bridge.status_changed.connect(self._on_status_changed)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start()

        self._refresh_status()
        self._refresh_log()

    # -- medidas -----------------------------------------------------------------
    @staticmethod
    def _passo_linha(tbl: QTableWidget) -> int:
        return tbl.verticalHeader().defaultSectionSize()

    def _altura_tabela(self, tbl: QTableWidget, linhas: int) -> int:
        cab = tbl.horizontalHeader()
        h_cab = cab.height() or cab.defaultSectionSize()
        return h_cab + linhas * self._passo_linha(tbl) + 2 * tbl.frameWidth() + 2

    def _altura_lista(self, itens: int) -> int:
        passo = self.tbl_log.verticalHeader().defaultSectionSize()
        return itens * passo + 2 * self.lst_giros.frameWidth() + 2

    def _estilo(self, liberado: bool | None) -> str:
        return estilo_resultado(liberado, self.vm.ui_config.tema)

    # -- wallpaper por container -------------------------------------------------
    def eventFilter(self, obj, event) -> bool:  # type: ignore[override]
        if obj in getattr(self, "_wallpaper_frames", []) and event.type() == QEvent.Type.Resize:
            self._atualizar_wallpaper_frame(obj)  # type: ignore[arg-type]
        return super().eventFilter(obj, event)

    def aplicar_wallpaper(self, path: str | None) -> None:
        """Aplica wallpaper: dashboard (um nível acima do centro) + 3 containers."""
        # esconde se sem path
        if not path:
            self._wallpaper_pixmap = None
            self._wallpaper_path = None
            for lbl in getattr(self, "_wallpaper_labels", {}).values():
                lbl.hide()
            with contextlib.suppress(Exception):
                self._wallpaper_bg_dashboard.hide()
            return
        p = Path(path)
        if not p.exists():
            logger.warning(f"[UI] wallpaper não encontrado: {path}")
            self._wallpaper_pixmap = None
            self._wallpaper_path = None
            for lbl in self._wallpaper_labels.values():
                lbl.hide()
            with contextlib.suppress(Exception):
                self._wallpaper_bg_dashboard.hide()
            return
        pix = QPixmap(str(p))
        if pix.isNull():
            logger.warning(f"[UI] wallpaper inválido: {path}")
            self._wallpaper_pixmap = None
            self._wallpaper_path = None
            for lbl in self._wallpaper_labels.values():
                lbl.hide()
            with contextlib.suppress(Exception):
                self._wallpaper_bg_dashboard.hide()
            return
        self._wallpaper_pixmap = pix
        self._wallpaper_path = str(p)
        self._atualizar_todos_wallpapers()
        for lbl in self._wallpaper_labels.values():
            lbl.show()
            lbl.lower()
        # mostra fundo do dashboard (atrás do centro)
        with contextlib.suppress(Exception):
            self._wallpaper_bg_dashboard.show()
            self._wallpaper_bg_dashboard.lower()
            # garante que toast fique acima
            self.toast.raise_()

    def _atualizar_wallpaper_frame(self, frame: QFrame) -> None:
        if self._wallpaper_pixmap is None or self._wallpaper_pixmap.isNull():
            return
        lbl = self._wallpaper_labels.get(frame)
        if lbl is None:
            return
        # cobre todo o frame (dentro da borda)
        lbl.setGeometry(frame.rect())
        # escala cobrindo o frame, cortando excesso
        scaled = self._wallpaper_pixmap.scaled(
            frame.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        # centraliza corte: QPixmap.scaled já expande, Label com AlignCenter corta
        lbl.setPixmap(scaled)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.lower()

    def _atualizar_wallpaper_dashboard(self) -> None:
        if self._wallpaper_pixmap is None or self._wallpaper_pixmap.isNull():
            return
        lbl = getattr(self, "_wallpaper_bg_dashboard", None)
        if lbl is None:
            return
        lbl.setGeometry(self.rect())
        scaled = self._wallpaper_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        lbl.setPixmap(scaled)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.lower()
        # toast sempre acima
        with contextlib.suppress(Exception):
            self.toast.raise_()

    def _atualizar_todos_wallpapers(self) -> None:
        for frm in getattr(self, "_wallpaper_frames", []):
            self._atualizar_wallpaper_frame(frm)
        self._atualizar_wallpaper_dashboard()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        # centraliza toast no meio da tela
        if self.toast.isVisible():
            self.toast.adjustSize()
            # largura proporcional, max 70% da largura
            max_w = int(self.width() * 0.7)
            if self.toast.width() > max_w:
                self.toast.setMaximumWidth(max_w)
                self.toast.adjustSize()
            x = (self.width() - self.toast.width()) // 2
            y = (self.height() - self.toast.height()) // 2
            self.toast.move(max(8, x), max(8, y))
        # mantém wallpaper cobrindo cada container ao redimensionar
        with contextlib.suppress(Exception):
            self._atualizar_todos_wallpapers()

    def _mostrar_toast(self, texto: str, liberado: bool | None) -> None:
        self.toast.setText(texto)
        # modal destacado: padding grande, borda, fonte maior
        extra = (
            " padding: 18px 32px; border-radius: 12px; "
            "border: 2px solid #2A3138; font-size: 16px; font-weight: bold; "
            "min-width: 260px; max-width: 600px; "
        )
        base = self._estilo(liberado)
        # garante contraste: adiciona borda e padding ao estilo base
        self.toast.setStyleSheet(base + extra)
        # fonte maior e bold
        f = QFont(self.toast.font())
        f.setPointSize(13)
        f.setBold(True)
        self.toast.setFont(f)
        self.toast.adjustSize()
        # largura proporcional ao texto, max 70% da tela
        max_w = int(self.width() * 0.7) if self.width() > 0 else 560
        if self.toast.width() > max_w:
            self.toast.setMaximumWidth(max_w)
            self.toast.adjustSize()
        else:
            self.toast.setMaximumWidth(16777215)
        x = (self.width() - self.toast.width()) // 2
        y = (self.height() - self.toast.height()) // 2
        if x < 0:
            x = 8
        if y < 0:
            y = 8
        self.toast.move(x, y)
        self.toast.setVisible(True)
        self.toast.raise_()
        self._toast_timer.start(4000)
        self.lbl_resultado.setText(texto)
        self.lbl_resultado.setStyleSheet(self._estilo(liberado))
        self.lbl_verificacao.setText(texto)
        self.lbl_verificacao.setStyleSheet(self._estilo(liberado))

    # -- slots ---------------------------------------------------------------
    def _aluno_id_ou_erro(self) -> str | None:
        texto = self.edt_aluno.text().strip() or self.edt_unico.text().strip()
        if not texto:
            self._mostrar_toast("Informe o ID ou CPF do aluno.", None)
            return None
        aluno = self.vm.resolver_aluno(texto)
        if aluno is None:
            self._mostrar_toast(f"Aluno '{texto}' não encontrado.", None)
            return None
        return aluno.id

    def _liberar(self, direcao: str) -> None:
        aluno_id = self._aluno_id_ou_erro()
        if aluno_id is None:
            return
        decisao = (
            self.vm.liberar_entrada(aluno_id)
            if direcao == "ENTRADA"
            else self.vm.liberar_saida(aluno_id)
        )
        self._mostrar_toast(self.vm.resume_decisao(decisao), decisao.liberado)
        self._refresh_status()
        self._refresh_log()

    def _liberar_unico(self) -> None:
        codigo = (
            self.edt_unico.text().strip()
            or self.edt_codigo.text().strip()
            or self.edt_aluno.text().strip()
        )
        if not codigo:
            from gymflux.core.acesso import DirecaoAcesso
            from gymflux.ui.config_store import ModoAcesso

            modo_e = self.vm.ui_config.entrada_modo
            modo_s = self.vm.ui_config.saida_modo
            ambos_livre = modo_e == ModoAcesso.LIVRE or modo_s == ModoAcesso.LIVRE
            if ambos_livre:
                direcao = (
                    DirecaoAcesso.SAIDA if modo_s == ModoAcesso.LIVRE else DirecaoAcesso.ENTRADA
                )
                decisao = self.vm._livre_liberar_direto(direcao)
                self._mostrar_toast(self.vm.resume_decisao(decisao), decisao.liberado)
                self._refresh_status()
                self._refresh_log()
                return
            self._mostrar_toast("Informe CPF ou senha.", None)
            return
        try:
            decisao, aluno = self.vm.liberar_catraca_unico(codigo)
        except (ValueError, RuntimeError) as e:
            self._mostrar_toast(f"NÃO IDENTIFICADO — {e}", None)
            return
        nome = self.vm.nome_aluno(aluno.id) if aluno is not None else "NÃO IDENTIFICADO"
        if decisao.liberado:
            self._mostrar_toast(f"{nome} — LIBERADO", True)
        else:
            motivo = str(decisao.motivo) if decisao.motivo else "negado"
            extra = f" ({decisao.detalhes})" if decisao.detalhes else ""
            self._mostrar_toast(f"{nome} — NEGADO · {motivo}{extra}", False)
        self.edt_unico.clear()
        self.edt_codigo.clear()
        self.edt_aluno.clear()
        self._refresh_status()
        self._refresh_log()

    def _bloquear(self) -> None:
        self.bridge.bloquear()
        self._mostrar_toast("Catraca bloqueada.", None)
        self._refresh_status()

    def _identificar(self) -> None:
        codigo = self.edt_codigo.text() or self.edt_unico.text()
        if not codigo.strip():
            self._mostrar_toast("NÃO IDENTIFICADO — informe o código", None)
            return
        try:
            decisao, aluno = self.vm.identificar_acesso(codigo, "TECLADO")
        except (ValueError, RuntimeError) as e:
            self._mostrar_toast(f"NÃO IDENTIFICADO — {e}", None)
            return
        nome = self.vm.nome_aluno(aluno.id) if aluno is not None else "NÃO IDENTIFICADO"
        if decisao.liberado:
            self._mostrar_toast(f"{nome} — LIBERADO", True)
        else:
            motivo = str(decisao.motivo) if decisao.motivo else "negado"
            extra = f" ({decisao.detalhes})" if decisao.detalhes else ""
            self._mostrar_toast(f"{nome} — NEGADO · {motivo}{extra}", False)
        self.edt_codigo.clear()
        self.edt_unico.clear()
        self._refresh_status()
        self._refresh_log()

    def _on_giro(self, direcao_nome: str, ts: float) -> None:
        self.vm.registrar_giro(direcao_nome, ts)
        self.lst_giros.addItem(f"giro {direcao_nome}")
        while self.lst_giros.count() > 50:
            self.lst_giros.takeItem(0)
        self._refresh_status()
        self._refresh_log()

    def _on_status_changed(self, _st: dict[str, Any]) -> None:
        self._refresh_status()

    def _mostrar_detalhes(self) -> None:
        dlg = DetalhesDialog(self.bridge.status(), self)
        dlg.exec()

    # -- refresh ---------------------------------------------------------------
    def _refresh_status(self) -> None:
        st = self.bridge.status()
        online = bool(st.get("online"))
        bloqueada = bool(st.get("bloqueada", True))
        driver = str(st.get("driver", "?"))
        porta = str(st.get("porta", "?"))
        mock = " (mock)" if st.get("mock") else ""
        valores = {
            "Online": "SIM" if online else "NÃO",
            "Bloqueada": "SIM" if bloqueada else "NÃO",
            "Giros": str(st.get("contador_giros", "—")),
            "Firmware": str(st.get("firmware", "—")),
            "Driver": f"{driver}{mock}",
            "Porta": porta,
        }
        compacto = (
            f"Online: {'SIM' if online else 'NÃO'} • "
            f"Bloqueada: {'SIM' if bloqueada else 'NÃO'} • "
            f"Giros: {valores['Giros']}"
        )
        self.lbl_compacto.setText(compacto)
        fg, bg = cores_indicador(online, self.vm.ui_config.tema)
        self.lbl_compacto.setStyleSheet(
            f"color: {fg};" + (f" background-color: {bg};" if bg else "")
        )
        for campo, valor in valores.items():
            item = self._itens_status[campo]
            item.setText(valor)
            if campo == "Online":
                fg2, bg2 = cores_indicador(online, self.vm.ui_config.tema)
                item.setForeground(QBrush(QColor(fg2)))
                item.setBackground(
                    QBrush(QColor(bg2)) if bg2 is not None else QBrush(Qt.BrushStyle.NoBrush)
                )

    def _refresh_log(self) -> None:
        tentativas = self.vm.tentativas_do_dia()
        self._tentativas_visiveis = tentativas
        self.tbl_log.setRowCount(len(tentativas))
        for row, t in enumerate(reversed(tentativas)):
            vals = (
                t.timestamp.strftime("%H:%M:%S"),
                self.vm.nome_tentativa(t),
                str(t.direcao),
                str(t.resultado),
                str(t.motivo or "—"),
            )
            for col, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if str(t.resultado) == "NEGADO":
                    item.setBackground(
                        QColor("#3a1a1a" if self.vm.ui_config.tema.value == "ESCURO" else "#ffe0e0")
                    )
                    item.setForeground(QBrush(QColor(VERMELHO)))
                self.tbl_log.setItem(row, col, item)

    def _registro_clicado(self, row: int, _col: int) -> None:
        visiveis = list(reversed(self._tentativas_visiveis))
        if 0 <= row < len(visiveis):
            tentativa = visiveis[row]
            if tentativa.aluno_id:
                self.perfil_solicitado.emit(tentativa.aluno_id)
