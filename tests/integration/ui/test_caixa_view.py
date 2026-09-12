"""CaixaView — render, fechamento e selo FECHADO (construção direta)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from PySide6.QtWidgets import QMessageBox

from gymflux.ui.app import AppContext
from gymflux.ui.views.caixa import CaixaView


def test_caixa_renderiza_fecha_e_selo(qtbot, ctx: AppContext, mocker):
    aluno = ctx.alunos_vm.cadastrar(nome="Ana")
    ctx.caixa_vm.registrar(
        aluno_id=aluno.id,
        valor=Decimal("100.00"),
        data_vencimento=date(2026, 9, 10),
        pago=True,
        competencia="2026-09",
    )
    view = CaixaView(ctx.caixa_vm)
    qtbot.addWidget(view)
    meses = [view.cmb_mes.itemData(i) for i in range(view.cmb_mes.count())]
    assert "2026-09" in meses
    view.cmb_mes.setCurrentIndex(view.cmb_mes.findData("2026-09"))
    assert "Recebido R$ 100.00" in view.lbl_totais.text()
    assert "Pendente R$ 0.00" in view.lbl_totais.text()
    assert view.tbl.rowCount() == 1
    assert view.lbl_fechado.isHidden() is True

    mocker.patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes)
    mocker.patch.object(QMessageBox, "information", return_value=QMessageBox.StandardButton.Ok)
    view._fechar()
    assert view.lbl_fechado.isHidden() is False
    assert ctx.caixa_vm.mes_fechado("2026-09") is True
