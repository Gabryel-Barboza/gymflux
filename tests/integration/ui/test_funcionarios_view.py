"""FuncionariosView + NovoFuncionarioDialog (construção direta)."""

from __future__ import annotations

from gymflow.ui.app import AppContext
from gymflow.ui.views.funcionarios import FuncionariosView, NovoFuncionarioDialog


def test_funcionarios_aba_e_dialog(qtbot, ctx: AppContext):
    view = FuncionariosView(ctx.funcionarios_vm)
    qtbot.addWidget(view)
    assert view.tbl.rowCount() == 0

    dlg = NovoFuncionarioDialog()
    qtbot.addWidget(dlg)
    dlg.edt_nome.setText("Zé Porteira")
    dlg.edt_senha.setText("1234")
    dlg.accept()
    assert dlg.result() == NovoFuncionarioDialog.DialogCode.Accepted

    func = ctx.funcionarios_vm.cadastrar(nome="Zé Porteira", senha="1234")
    view.recarregar()
    assert view.tbl.rowCount() == 1
    ctx.funcionarios_vm.definir_ativo(func.id, False)
    view.recarregar()
    item = view.tbl.item(0, 2)
    assert item is not None and item.text() == "não"
