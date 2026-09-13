"""Catraca — status compacto + Detalhes, toast, log com vermelho, campo único."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
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

LINHAS_VISIVEIS = 5


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
    """Status compacto + campo único CPF/senha + toast; log com vermelho."""

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
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        estilo = self.style()

        # -- toast (overlay, auto-hide) -----------------------------------------
        self.toast = QLabel("", self)
        self.toast.setVisible(False)
        self.toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.toast.setStyleSheet("padding: 8px; border-radius: 6px;")
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(lambda: self.toast.setVisible(False))

        # -- status compacto ----------------------------------------------------
        hstatus = QHBoxLayout()
        self.lbl_compacto = QLabel("—")
        self.btn_detalhes = QPushButton("Detalhes")
        self.btn_detalhes.setIcon(
            estilo.standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        )
        hstatus.addWidget(self.lbl_compacto, 1)
        hstatus.addWidget(self.btn_detalhes)
        layout.addLayout(hstatus)

        # tabela detalhada (mantida oculta p/ compat testes, mas compacto é o visível)
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
        # para Fase 4.9, tabela fica oculta (compacto + modal), mas mantém p/ teste
        self.tbl_status.setVisible(False)
        layout.addWidget(self.tbl_status)

        # -- lado direito: campo único CPF/senha + botão único -----------------
        huni = QHBoxLayout()
        self.edt_unico = QLineEdit()
        self.edt_unico.setPlaceholderText("CPF ou senha")
        self.edt_unico.setClearButtonEnabled(True)
        self.btn_liberar = QPushButton("Liberar catraca")
        self.btn_liberar.setIcon(estilo.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        huni.addWidget(self.edt_unico, 2)
        huni.addWidget(self.btn_liberar)
        layout.addLayout(huni)

        # compat: mantém edt_aluno/edt_codigo/btn_entrada/btn_saida/bloquear mas ocultos
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
        # mantém no layout mas ocultos (não ocupam espaço visível)
        layout.addWidget(self.edt_aluno)
        layout.addWidget(self.edt_codigo)
        layout.addWidget(self.btn_identificar)
        layout.addWidget(self.btn_entrada)
        layout.addWidget(self.btn_saida)
        layout.addWidget(self.btn_bloquear)

        self.lbl_resultado = QLabel("Informe o aluno e escolha a direção.")
        self.lbl_resultado.setVisible(False)  # agora via toast
        layout.addWidget(self.lbl_resultado)
        self.lbl_verificacao = QLabel("Aguardando identificação...")
        fonte = self.lbl_verificacao.font()
        fonte.setPointSize(14)
        fonte.setBold(True)
        self.lbl_verificacao.setFont(fonte)
        self.lbl_verificacao.setVisible(False)  # também via toast
        layout.addWidget(self.lbl_verificacao)

        # -- log + giros (altura p/ ~5 itens, com scroll) ------------------------
        hmid = QHBoxLayout()
        self.tbl_log = QTableWidget(0, len(self.COLUNAS_LOG))
        self.tbl_log.setHorizontalHeaderLabels(list(self.COLUNAS_LOG))
        self.tbl_log.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_log.verticalHeader().setVisible(False)
        self.tbl_log.horizontalHeader().setStretchLastSection(True)
        self.tbl_log.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tbl_log.setMaximumHeight(self._altura_tabela(self.tbl_log, LINHAS_VISIVEIS))
        hmid.addWidget(self.tbl_log, 3)

        self.lst_giros = QListWidget()
        self.lst_giros.setMaximumHeight(self._altura_lista(LINHAS_VISIVEIS))
        hmid.addWidget(self.lst_giros, 1)
        layout.addLayout(hmid, 1)

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
        """Estilo de resultado no tema atual (claro usa selos legíveis)."""
        return estilo_resultado(liberado, self.vm.ui_config.tema)

    def _mostrar_toast(self, texto: str, liberado: bool | None) -> None:
        self.toast.setText(texto)
        self.toast.setStyleSheet(self._estilo(liberado))
        self.toast.setVisible(True)
        self.toast.raise_()
        self._toast_timer.start(4000)
        # também atualiza labels legados p/ testes
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
            # se LIVRE, permite vazio
            from gymflux.core.acesso import DirecaoAcesso
            from gymflux.ui.config_store import ModoAcesso

            modo_e = self.vm.ui_config.entrada_modo
            modo_s = self.vm.ui_config.saida_modo
            if modo_e == ModoAcesso.LIVRE or modo_s == ModoAcesso.LIVRE:
                # escolhe direção livre
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
        # mantém compat: limpa ambos
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
        # compat: usa edt_unico se edt_codigo vazio
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
        # compacto
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
                # linha vermelha p/ NEGADO (fundo suave vermelho)
                if str(t.resultado) == "NEGADO":
                    item.setBackground(
                        QColor("#3a1a1a" if self.vm.ui_config.tema.value == "ESCURO" else "#ffe0e0")
                    )
                    item.setForeground(QBrush(QColor(VERMELHO)))
                self.tbl_log.setItem(row, col, item)

    def _registro_clicado(self, row: int, _col: int) -> None:
        """Click-through: abre o perfil do aluno (funcionário não tem perfil)."""
        visiveis = list(reversed(self._tentativas_visiveis))
        if 0 <= row < len(visiveis):
            tentativa = visiveis[row]
            if tentativa.aluno_id:
                self.perfil_solicitado.emit(tentativa.aluno_id)
