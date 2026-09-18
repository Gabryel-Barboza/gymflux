"""FuncionariosView + NovoFuncionarioDialog (construção direta)."""

from __future__ import annotations

from gymflux.ui.app import AppContext
from gymflux.ui.views.funcionarios import FuncionariosView, NovoFuncionarioDialog


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


def test_botao_senha_tem_icone_e_alterna(qtbot):
    """Fase 5.4-B: olho com QIcon moderno (sem emoji) mostra/oculta a senha."""
    from PySide6.QtCore import QSize
    from PySide6.QtWidgets import QLineEdit

    from gymflux.ui.theme import icon_size
    from gymflux.ui.views.funcionarios import NovoFuncionarioDialog

    dlg = NovoFuncionarioDialog()
    qtbot.addWidget(dlg)
    btn = dlg.btn_ver_senha
    assert btn.text() == ""  # sem emoji: só ícone
    assert not btn.icon().isNull()
    assert btn.iconSize() == QSize(icon_size(), icon_size())
    assert btn.objectName() == "VerSenha"
    assert dlg.edt_senha.echoMode() == QLineEdit.EchoMode.Normal
    btn.setChecked(False)
    assert dlg.edt_senha.echoMode() == QLineEdit.EchoMode.Password
    btn.setChecked(True)
    assert dlg.edt_senha.echoMode() == QLineEdit.EchoMode.Normal
