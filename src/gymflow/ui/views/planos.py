"""Tela de planos — tabela + dialog (tipo, valor, tolerância)."""

from __future__ import annotations

from decimal import Decimal

from loguru import logger
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gymflow.core.plano import TipoPlano
from gymflow.ui.viewmodels.planos import DURACAO_POR_TIPO, PlanosViewModel


class NovoPlanoDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Novo plano")
        form = QFormLayout(self)
        self.edt_nome = QLineEdit()
        self.cmb_tipo = QComboBox()
        for t in TipoPlano:
            self.cmb_tipo.addItem(t.value, t)
        self.spn_valor = QDoubleSpinBox()
        self.spn_valor.setRange(0.0, 100000.0)
        self.spn_valor.setDecimals(2)
        self.spn_valor.setValue(99.90)
        self.spn_tol = QSpinBox()
        self.spn_tol.setRange(0, 90)
        self.spn_tol.setValue(3)
        self.spn_dur = QSpinBox()
        self.spn_dur.setRange(1, 3650)
        self.spn_dur.setValue(30)
        form.addRow("Nome*:", self.edt_nome)
        form.addRow("Tipo:", self.cmb_tipo)
        form.addRow("Valor (R$):", self.spn_valor)
        form.addRow("Tolerância (dias):", self.spn_tol)
        form.addRow("Duração (dias):", self.spn_dur)
        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        form.addRow(botoes)
        self.cmb_tipo.currentIndexChanged.connect(self._tipo_mudou)
        self._tipo_mudou(0)

    def _tipo_mudou(self, _i: int) -> None:
        tipo = self.cmb_tipo.currentData()
        if isinstance(tipo, TipoPlano) and tipo in DURACAO_POR_TIPO:
            self.spn_dur.setValue(DURACAO_POR_TIPO[tipo])


class PlanosView(QWidget):
    COLUNAS = ("ID", "Nome", "Tipo", "Duração (dias)", "Valor (R$)", "Tolerância (dias)")

    def __init__(self, vm: PlanosViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.vm = vm
        layout = QVBoxLayout(self)

        self.tbl = QTableWidget(0, len(self.COLUNAS))
        self.tbl.setHorizontalHeaderLabels(list(self.COLUNAS))
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setColumnHidden(0, True)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tbl, 1)

        hbtn = QHBoxLayout()
        self.btn_novo = QPushButton("Novo plano")
        self.btn_remover = QPushButton("Remover")
        hbtn.addWidget(self.btn_novo)
        hbtn.addWidget(self.btn_remover)
        hbtn.addStretch(1)
        layout.addLayout(hbtn)

        self.btn_novo.clicked.connect(self._novo)
        self.btn_remover.clicked.connect(self._remover)
        self.recarregar()

    def recarregar(self) -> None:
        planos = self.vm.listar()
        self.tbl.setRowCount(len(planos))
        for row, p in enumerate(planos):
            vals = (
                p.id,
                p.nome,
                str(p.tipo),
                str(p.duracao_dias),
                f"{Decimal(str(p.valor)):.2f}",
                str(p.tolerancia_dias),
            )
            for col, v in enumerate(vals):
                self.tbl.setItem(row, col, QTableWidgetItem(v))

    def _novo(self) -> None:
        dlg = NovoPlanoDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if not dlg.edt_nome.text().strip():
            QMessageBox.warning(self, "Planos", "Nome é obrigatório.")
            return
        try:
            plano = self.vm.salvar(
                nome=dlg.edt_nome.text(),
                tipo=dlg.cmb_tipo.currentData(),
                valor=Decimal(str(dlg.spn_valor.value())),
                tolerancia_dias=dlg.spn_tol.value(),
                duracao_dias=dlg.spn_dur.value(),
            )
        except ValueError as e:
            QMessageBox.warning(self, "Planos", str(e))
            return
        logger.info(f"[UI] plano salvo id={plano.id}")
        self.recarregar()

    def _remover(self) -> None:
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.information(self, "Planos", "Selecione um plano na tabela.")
            return
        item = self.tbl.item(row, 0)
        nome_item = self.tbl.item(row, 1)
        if item is None:
            return
        nome = nome_item.text() if nome_item else item.text()
        confirma = QMessageBox.question(
            self, "Planos", f"Remover o plano '{nome}'?", QMessageBox.StandardButton.Yes
        )
        if confirma != QMessageBox.StandardButton.Yes:
            return
        self.vm.remover(item.text())
        self.recarregar()
