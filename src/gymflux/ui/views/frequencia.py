"""Aba Frequência — presença global com filtros dia/mês/aluno (antifraude)."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gymflux.ui.viewmodels.frequencia import FrequenciaViewModel


class FrequenciaView(QWidget):
    COLUNAS = ("Data/Hora", "Pessoa", "Direção", "Resultado", "Motivo")

    def __init__(self, vm: FrequenciaViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.vm = vm
        layout = QVBoxLayout(self)

        filtros = QHBoxLayout()
        filtros.addWidget(QLabel("Aluno:"))
        self.cmb_aluno = QComboBox()
        filtros.addWidget(self.cmb_aluno, 2)
        filtros.addWidget(QLabel("Mês:"))
        self.cmb_mes = QComboBox()
        filtros.addWidget(self.cmb_mes, 1)
        self.chk_dia = QCheckBox("Dia:")
        self.chk_dia.setChecked(True)
        self.dat_dia = QDateEdit(QDate.currentDate())
        self.dat_dia.setCalendarPopup(True)
        filtros.addWidget(self.chk_dia)
        filtros.addWidget(self.dat_dia)
        filtros.addStretch(1)
        layout.addLayout(filtros)

        self.lbl_total = QLabel("")
        layout.addWidget(self.lbl_total)

        self.tbl = QTableWidget(0, len(self.COLUNAS))
        self.tbl.setHorizontalHeaderLabels(list(self.COLUNAS))
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tbl, 1)

        self.cmb_aluno.currentIndexChanged.connect(lambda _i: self.recarregar())
        self.cmb_mes.currentIndexChanged.connect(lambda _i: self.recarregar())
        self.chk_dia.toggled.connect(lambda _c: self.recarregar())
        self.dat_dia.dateChanged.connect(lambda _d: self.recarregar())
        self.recarregar()

    # -- helpers ---------------------------------------------------------------
    @staticmethod
    def _qdate_para_date(qd: QDate) -> date:
        return date(qd.year(), qd.month(), qd.day())

    def _recarregar_combos(self) -> None:
        aluno_atual = self.cmb_aluno.currentData()
        self.cmb_aluno.blockSignals(True)
        try:
            self.cmb_aluno.clear()
            self.cmb_aluno.addItem("Todos", None)
            for a in self.vm.listar_alunos():
                self.cmb_aluno.addItem(a.nome, a.id)
            if aluno_atual is not None:
                idx = self.cmb_aluno.findData(aluno_atual)
                if idx >= 0:
                    self.cmb_aluno.setCurrentIndex(idx)
        finally:
            self.cmb_aluno.blockSignals(False)

        mes_atual = self.cmb_mes.currentData()
        self.cmb_mes.blockSignals(True)
        try:
            self.cmb_mes.clear()
            self.cmb_mes.addItem("Todos", None)
            for m in self.vm.meses_disponiveis():
                self.cmb_mes.addItem(m, m)
            if mes_atual is not None:
                idx = self.cmb_mes.findData(mes_atual)
                if idx >= 0:
                    self.cmb_mes.setCurrentIndex(idx)
        finally:
            self.cmb_mes.blockSignals(False)

    def recarregar(self) -> None:
        self._recarregar_combos()
        aluno_id = self.cmb_aluno.currentData()
        mes = self.cmb_mes.currentData()
        dia = self._qdate_para_date(self.dat_dia.date()) if self.chk_dia.isChecked() else None
        linhas = self.vm.filtrar(
            dia=dia,
            mes=str(mes) if mes is not None else None,
            aluno_id=str(aluno_id) if aluno_id is not None else None,
        )
        self.lbl_total.setText(f"{len(linhas)} registro(s)")
        self.tbl.setRowCount(len(linhas))
        for row, t in enumerate(reversed(linhas)):
            vals = (
                t.timestamp.strftime("%d/%m %H:%M:%S"),
                self.vm.nome_tentativa(t),
                str(t.direcao),
                str(t.resultado),
                str(t.motivo or "—"),
            )
            for col, v in enumerate(vals):
                self.tbl.setItem(row, col, QTableWidgetItem(v))
