"""Tela de pagamentos — registro + lista por aluno + destaque inadimplente."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import ClassVar

from loguru import logger
from PySide6.QtCore import QDate
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gymflow.core.pagamento import FormaPagamento
from gymflow.ui.viewmodels.pagamentos import PagamentosViewModel


class NovoPagamentoDialog(QDialog):
    FORMAS: ClassVar[list[str]] = ["—", *[f.value for f in FormaPagamento]]

    def __init__(self, aluno_nome: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Novo pagamento — {aluno_nome}")
        form = QFormLayout(self)
        self.spn_valor = QDoubleSpinBox()
        self.spn_valor.setRange(0.01, 100000.0)
        self.spn_valor.setDecimals(2)
        self.spn_valor.setValue(99.90)
        self.dat_venc = QDateEdit(QDate.currentDate())
        self.dat_venc.setCalendarPopup(True)
        self.cmb_forma = QComboBox()
        self.cmb_forma.addItems(self.FORMAS)
        self.chk_pago = QCheckBox("Pago hoje")
        self.chk_pago.setChecked(True)
        self.edt_comp = QLineEdit()
        self.edt_comp.setPlaceholderText("AAAA-MM (opcional)")
        form.addRow("Valor (R$)*:", self.spn_valor)
        form.addRow("Vencimento:", self.dat_venc)
        form.addRow("Forma:", self.cmb_forma)
        form.addRow(self.chk_pago)
        form.addRow("Competência:", self.edt_comp)
        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        form.addRow(botoes)

    def forma(self) -> str | None:
        v = self.cmb_forma.currentText()
        return None if v == "—" else v

    def vencimento(self) -> date:
        qd = self.dat_venc.date()
        return date(qd.year(), qd.month(), qd.day())


class PagamentosView(QWidget):
    COLUNAS = ("Vencimento", "Valor (R$)", "Pagamento", "Forma", "Competência", "Situação")

    def __init__(self, vm: PagamentosViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.vm = vm
        layout = QVBoxLayout(self)

        htopo = QHBoxLayout()
        htopo.addWidget(QLabel("Aluno:"))
        self.cmb_aluno = QComboBox()
        self.btn_atualizar = QPushButton("Atualizar")
        htopo.addWidget(self.cmb_aluno, 3)
        htopo.addWidget(self.btn_atualizar)
        layout.addLayout(htopo)

        self.lbl_situacao = QLabel("Selecione um aluno.")
        layout.addWidget(self.lbl_situacao)

        self.tbl = QTableWidget(0, len(self.COLUNAS))
        self.tbl.setHorizontalHeaderLabels(list(self.COLUNAS))
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tbl, 1)

        hbtn = QHBoxLayout()
        self.btn_novo = QPushButton("Registrar pagamento")
        hbtn.addWidget(self.btn_novo)
        hbtn.addStretch(1)
        layout.addLayout(hbtn)

        self.cmb_aluno.currentIndexChanged.connect(lambda _i: self.recarregar())
        self.btn_atualizar.clicked.connect(self._recarregar_alunos)
        self.btn_novo.clicked.connect(self._novo)

        self._recarregar_alunos()

    # -- helpers ---------------------------------------------------------------
    def _aluno_atual(self) -> tuple[str, str] | None:
        data = self.cmb_aluno.currentData()
        if data is None:
            return None
        return (str(data), self.cmb_aluno.currentText())

    def _recarregar_alunos(self) -> None:
        atual = self.cmb_aluno.currentData()
        self.cmb_aluno.blockSignals(True)
        try:
            self.cmb_aluno.clear()
            for a in self.vm.listar_alunos():
                self.cmb_aluno.addItem(a.nome, a.id)
            if atual is not None:
                idx = self.cmb_aluno.findData(atual)
                if idx >= 0:
                    self.cmb_aluno.setCurrentIndex(idx)
        finally:
            self.cmb_aluno.blockSignals(False)
        self.recarregar()

    def recarregar(self) -> None:
        sel = self._aluno_atual()
        if sel is None:
            self.lbl_situacao.setText("Nenhum aluno cadastrado.")
            self.tbl.setRowCount(0)
            return
        aluno_id, _nome = sel
        hoje = date.today()
        rotulo, atraso = self.vm.situacao(aluno_id, hoje)
        if rotulo == "ADIMPLENTE":
            self.lbl_situacao.setText("Situação: ADIMPLENTE")
            self.lbl_situacao.setStyleSheet("color: green; font-weight: bold;")
        elif rotulo == "INADIMPLENTE":
            self.lbl_situacao.setText(f"Situação: INADIMPLENTE ({atraso} dias em atraso)")
            self.lbl_situacao.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.lbl_situacao.setText("Situação: SEM PAGAMENTOS")
            self.lbl_situacao.setStyleSheet("color: orange; font-weight: bold;")

        pags = self.vm.do_aluno(aluno_id)
        self.tbl.setRowCount(len(pags))
        for row, p in enumerate(pags):
            if p.pago:
                sit = "PAGO"
            elif p.dias_atraso(hoje) > 0:
                sit = f"ATRASADO {p.dias_atraso(hoje)}d"
            else:
                sit = "PENDENTE"
            vals = (
                p.data_vencimento.isoformat(),
                f"{Decimal(str(p.valor)):.2f}",
                p.data_pagamento.isoformat() if p.data_pagamento else "—",
                str(p.forma) if p.forma else "—",
                p.competencia or "—",
                sit,
            )
            for col, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if not p.pago and p.dias_atraso(hoje) > 0:
                    item.setBackground(QColor("#ffe0e0"))
                self.tbl.setItem(row, col, item)

    def _novo(self) -> None:
        sel = self._aluno_atual()
        if sel is None:
            QMessageBox.information(self, "Pagamentos", "Cadastre um aluno primeiro.")
            return
        aluno_id, aluno_nome = sel
        dlg = NovoPagamentoDialog(aluno_nome, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            pag = self.vm.registrar(
                aluno_id=aluno_id,
                valor=Decimal(str(dlg.spn_valor.value())),
                data_vencimento=dlg.vencimento(),
                forma=dlg.forma(),
                pago=dlg.chk_pago.isChecked(),
                competencia=dlg.edt_comp.text(),
            )
        except ValueError as e:
            QMessageBox.warning(self, "Pagamentos", str(e))
            return
        logger.info(f"[UI] pagamento registrado id={pag.id}")
        self.recarregar()
