"""Catraca — ação em linhas compactas, status em tabela, log/giros enxutos."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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

from gymflow.core.acesso import TentativaAcesso
from gymflow.ui.catraca_bridge import CatracaBridge
from gymflow.ui.theme import cores_indicador, estilo_resultado
from gymflow.ui.viewmodels.dashboard import DashboardViewModel

LINHAS_VISIVEIS = 5


class DashboardView(QWidget):
    """Duas linhas de ação + status compacto + log/giros com altura p/ ~5 itens."""

    COLUNAS_LOG = ("Hora", "Aluno", "Direção", "Resultado", "Motivo")
    LINHAS_STATUS = ("Online", "Bloqueada", "Giros", "Firmware", "Driver", "Porta")

    perfil_solicitado = Signal(str)  # aluno_id clicado no log do dia

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

        # -- linha 1: identificação -------------------------------------------
        linha1 = QHBoxLayout()
        self.edt_aluno = QLineEdit()
        self.edt_aluno.setPlaceholderText("ID ou CPF")
        self.edt_codigo = QLineEdit()
        self.edt_codigo.setPlaceholderText("Senha ou cartão")
        self.edt_codigo.setEchoMode(QLineEdit.EchoMode.Password)
        self.cmb_origem = QComboBox()
        self.cmb_origem.addItem("Teclado", "TECLADO")
        self.cmb_origem.addItem("Cartão", "CARTAO")
        self.btn_identificar = QPushButton("Identificar")
        self.btn_identificar.setIcon(
            estilo.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        )
        linha1.addWidget(self.edt_aluno, 2)
        linha1.addWidget(self.edt_codigo, 2)
        linha1.addWidget(self.cmb_origem)
        linha1.addWidget(self.btn_identificar)
        layout.addLayout(linha1)

        # -- linha 2: ações ----------------------------------------------------
        linha2 = QHBoxLayout()
        self.btn_entrada = QPushButton("Liberar Entrada")
        self.btn_entrada.setIcon(estilo.standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.btn_saida = QPushButton("Liberar Saída")
        self.btn_saida.setIcon(estilo.standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.btn_bloquear = QPushButton("Bloquear")
        self.btn_bloquear.setIcon(estilo.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        linha2.addWidget(self.btn_entrada)
        linha2.addWidget(self.btn_saida)
        linha2.addWidget(self.btn_bloquear)
        linha2.addStretch(1)
        layout.addLayout(linha2)

        self.lbl_resultado = QLabel("Informe o aluno e escolha a direção.")
        layout.addWidget(self.lbl_resultado)
        self.lbl_verificacao = QLabel("Aguardando identificação...")
        fonte = self.lbl_verificacao.font()
        fonte.setPointSize(14)
        fonte.setBold(True)
        self.lbl_verificacao.setFont(fonte)
        layout.addWidget(self.lbl_verificacao)

        # -- status compacto (tabela Campo|Valor) -------------------------------
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
        layout.addWidget(self.tbl_status)

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
        self.cmb_origem.currentIndexChanged.connect(self._origem_mudou)
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

    # -- slots ---------------------------------------------------------------
    def _aluno_id_ou_erro(self) -> str | None:
        texto = self.edt_aluno.text().strip()
        if not texto:
            self.lbl_resultado.setText("Informe o ID ou CPF do aluno.")
            self.lbl_resultado.setStyleSheet(self._estilo(None))
            return None
        aluno = self.vm.resolver_aluno(texto)
        if aluno is None:
            self.lbl_resultado.setText(f"Aluno '{texto}' não encontrado.")
            self.lbl_resultado.setStyleSheet(self._estilo(None))
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
        self.lbl_resultado.setText(self.vm.resume_decisao(decisao))
        self.lbl_resultado.setStyleSheet(self._estilo(decisao.liberado))
        self._refresh_status()
        self._refresh_log()

    def _bloquear(self) -> None:
        self.bridge.bloquear()
        self.lbl_resultado.setText("Catraca bloqueada.")
        self.lbl_resultado.setStyleSheet(self._estilo(None))
        self._refresh_status()

    def _origem_mudou(self) -> None:
        # cartão legível p/ conferência; senha sempre oculta
        if str(self.cmb_origem.currentData()) == "CARTAO":
            self.edt_codigo.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.edt_codigo.setEchoMode(QLineEdit.EchoMode.Password)

    def _identificar(self) -> None:
        codigo = self.edt_codigo.text()
        origem = str(self.cmb_origem.currentData())
        if not codigo.strip():
            self.lbl_verificacao.setText("NÃO IDENTIFICADO — informe o código")
            self.lbl_verificacao.setStyleSheet(self._estilo(None))
            return
        try:
            decisao, aluno = self.vm.identificar_acesso(codigo, origem)
        except (ValueError, RuntimeError) as e:
            self.lbl_verificacao.setText(f"NÃO IDENTIFICADO — {e}")
            self.lbl_verificacao.setStyleSheet(self._estilo(None))
            return
        nome = self.vm.nome_aluno(aluno.id) if aluno is not None else "NÃO IDENTIFICADO"
        if decisao.liberado:
            self.lbl_verificacao.setText(f"{nome} — LIBERADO")
        else:
            motivo = str(decisao.motivo) if decisao.motivo else "negado"
            extra = f" ({decisao.detalhes})" if decisao.detalhes else ""
            self.lbl_verificacao.setText(f"{nome} — NEGADO · {motivo}{extra}")
        self.lbl_verificacao.setStyleSheet(self._estilo(decisao.liberado))
        self.edt_codigo.clear()
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
        for campo, valor in valores.items():
            item = self._itens_status[campo]
            item.setText(valor)
            if campo == "Online":
                fg, bg = cores_indicador(online, self.vm.ui_config.tema)
                item.setForeground(QBrush(QColor(fg)))
                item.setBackground(
                    QBrush(QColor(bg)) if bg is not None else QBrush(Qt.BrushStyle.NoBrush)
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
                self.tbl_log.setItem(row, col, QTableWidgetItem(v))

    def _registro_clicado(self, row: int, _col: int) -> None:
        """Click-through: abre o perfil do aluno (funcionário não tem perfil)."""
        visiveis = list(reversed(self._tentativas_visiveis))
        if 0 <= row < len(visiveis):
            tentativa = visiveis[row]
            if tentativa.aluno_id:
                self.perfil_solicitado.emit(tentativa.aluno_id)
