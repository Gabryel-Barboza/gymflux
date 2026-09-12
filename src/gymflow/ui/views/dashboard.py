"""Dashboard da catraca — status tempo real, liberação e log de tentativas."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gymflow.ui.catraca_bridge import CatracaBridge
from gymflow.ui.theme import estilo_resultado
from gymflow.ui.viewmodels.dashboard import DashboardViewModel


class DashboardView(QWidget):
    """Status (QTimer 1s) + Liberar Entrada/Saída + Bloquear + log + giros."""

    COLUNAS_LOG = ("Hora", "Aluno", "Direção", "Resultado", "Motivo")

    def __init__(
        self,
        vm: DashboardViewModel,
        bridge: CatracaBridge,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.vm = vm
        self.bridge = bridge

        layout = QVBoxLayout(self)

        # -- status ---------------------------------------------------------
        gb_status = QGroupBox("Status da catraca")
        grid = QGridLayout(gb_status)
        self.lbl_online = QLabel("—")
        self.lbl_bloqueada = QLabel("—")
        self.lbl_contador = QLabel("—")
        self.lbl_firmware = QLabel("—")
        self.lbl_driver = QLabel("—")
        grid.addWidget(QLabel("Online:"), 0, 0)
        grid.addWidget(self.lbl_online, 0, 1)
        grid.addWidget(QLabel("Bloqueada:"), 0, 2)
        grid.addWidget(self.lbl_bloqueada, 0, 3)
        grid.addWidget(QLabel("Giros:"), 1, 0)
        grid.addWidget(self.lbl_contador, 1, 1)
        grid.addWidget(QLabel("Firmware:"), 1, 2)
        grid.addWidget(self.lbl_firmware, 1, 3)
        grid.addWidget(QLabel("Driver:"), 2, 0)
        grid.addWidget(self.lbl_driver, 2, 1, 1, 3)
        layout.addWidget(gb_status)

        # -- liberação -------------------------------------------------------
        gb_lib = QGroupBox("Liberar acesso")
        hlib = QHBoxLayout(gb_lib)
        self.edt_aluno = QLineEdit()
        self.edt_aluno.setPlaceholderText("ID ou CPF do aluno")
        self.btn_entrada = QPushButton("Liberar Entrada")
        self.btn_saida = QPushButton("Liberar Saída")
        self.btn_bloquear = QPushButton("Bloquear")
        hlib.addWidget(self.edt_aluno, 2)
        hlib.addWidget(self.btn_entrada)
        hlib.addWidget(self.btn_saida)
        hlib.addWidget(self.btn_bloquear)
        layout.addWidget(gb_lib)

        self.lbl_resultado = QLabel("Informe o aluno e escolha a direção.")
        layout.addWidget(self.lbl_resultado)

        # -- log + giros ------------------------------------------------------
        hmid = QHBoxLayout()
        self.tbl_log = QTableWidget(0, len(self.COLUNAS_LOG))
        self.tbl_log.setHorizontalHeaderLabels(list(self.COLUNAS_LOG))
        self.tbl_log.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_log.horizontalHeader().setStretchLastSection(True)
        hmid.addWidget(self.tbl_log, 3)

        gb_giros = QGroupBox("Giros detectados")
        vg = QVBoxLayout(gb_giros)
        self.lst_giros = QListWidget()
        vg.addWidget(self.lst_giros)
        hmid.addWidget(gb_giros, 1)
        layout.addLayout(hmid, 1)

        # -- sinais ------------------------------------------------------------
        self.btn_entrada.clicked.connect(lambda: self._liberar("ENTRADA"))
        self.btn_saida.clicked.connect(lambda: self._liberar("SAIDA"))
        self.btn_bloquear.clicked.connect(self._bloquear)
        self.bridge.giro_detectado.connect(self._on_giro)
        self.bridge.status_changed.connect(self._on_status_changed)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start()

        self._refresh_status()
        self._refresh_log()

    # -- slots ---------------------------------------------------------------
    def _aluno_id_ou_erro(self) -> str | None:
        texto = self.edt_aluno.text().strip()
        if not texto:
            self.lbl_resultado.setText("Informe o ID ou CPF do aluno.")
            self.lbl_resultado.setStyleSheet(estilo_resultado(None))
            return None
        aluno = self.vm.resolver_aluno(texto)
        if aluno is None:
            self.lbl_resultado.setText(f"Aluno '{texto}' não encontrado.")
            self.lbl_resultado.setStyleSheet(estilo_resultado(None))
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
        self.lbl_resultado.setStyleSheet(estilo_resultado(decisao.liberado))
        self._refresh_status()
        self._refresh_log()

    def _bloquear(self) -> None:
        self.bridge.bloquear()
        self.lbl_resultado.setText("Catraca bloqueada.")
        self.lbl_resultado.setStyleSheet(estilo_resultado(None))
        self._refresh_status()

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
        self.lbl_online.setText("SIM" if online else "NÃO")
        self.lbl_online.setStyleSheet(estilo_resultado(online))
        self.lbl_bloqueada.setText("SIM" if bloqueada else "NÃO")
        self.lbl_contador.setText(str(st.get("contador_giros", "—")))
        self.lbl_firmware.setText(str(st.get("firmware", "—")))
        driver = str(st.get("driver", "?"))
        porta = str(st.get("porta", "?"))
        mock = " (mock)" if st.get("mock") else ""
        self.lbl_driver.setText(f"{driver} @ {porta}{mock}")

    def _refresh_log(self) -> None:
        tentativas = self.vm.ultimas_tentativas(50)
        self.tbl_log.setRowCount(len(tentativas))
        for row, t in enumerate(reversed(tentativas)):
            vals = (
                t.timestamp.strftime("%d/%m %H:%M:%S"),
                self.vm.nome_aluno(t.aluno_id),
                str(t.direcao),
                str(t.resultado),
                str(t.motivo or "—"),
            )
            for col, v in enumerate(vals):
                self.tbl_log.setItem(row, col, QTableWidgetItem(v))
