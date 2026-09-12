"""PlanosView — cards + dialog de edição (construção direta)."""

from __future__ import annotations

from decimal import Decimal

from PySide6.QtWidgets import QMessageBox

from gymflux.core.plano import TipoPlano
from gymflux.ui.app import AppContext
from gymflux.ui.views.planos import NovoPlanoDialog, PlanosView


def test_planos_cards_renderizam_editar_excluir(qtbot, ctx: AppContext, mocker):
    plano = ctx.planos_vm.salvar(nome="Mensal", tipo=TipoPlano.MENSAL, valor=Decimal("99.90"))
    view = PlanosView(ctx.planos_vm)
    qtbot.addWidget(view)
    assert len(view.cards) == 1

    dlg = NovoPlanoDialog()
    qtbot.addWidget(dlg)
    dlg.preencher(plano)
    assert dlg.edt_nome.text() == "Mensal"
    assert dlg.spn_tol.value() == plano.tolerancia_dias

    editado = ctx.planos_vm.salvar(
        nome="Mensal Plus",
        tipo=TipoPlano.MENSAL,
        valor=Decimal("119.90"),
        tolerancia_dias=5,
        duracao_dias=30,
        plano_id=plano.id,
    )
    assert editado.nome == "Mensal Plus"
    view.recarregar()
    assert len(view.cards) == 1

    mocker.patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes)
    view._excluir(plano.id, plano.nome)
    assert len(view.cards) == 0
    assert ctx.planos_vm.listar() == []
