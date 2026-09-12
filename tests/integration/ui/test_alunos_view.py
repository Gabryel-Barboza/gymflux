"""AlunosView + PerfilAlunoDialog + NovoAlunoDialog (construção direta)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from gymflow.core.acesso import DirecaoAcesso, ResultadoAcesso, TentativaAcesso
from gymflow.ui.app import AppContext
from gymflow.ui.views.alunos import AlunosView, NovoAlunoDialog, PerfilAlunoDialog


def test_alunos_view_busca_filtra(qtbot, ctx: AppContext):
    view = AlunosView(ctx.alunos_vm, ctx.caixa_vm)
    qtbot.addWidget(view)
    ctx.alunos_vm.cadastrar(nome="Ana Silva", cpf="11144477735")
    ctx.alunos_vm.cadastrar(nome="Bruno Souza", cpf="22255588846")
    view.edt_busca.setText("ana")
    assert view.tbl.rowCount() == 1
    view.edt_busca.clear()
    assert view.tbl.rowCount() == 2


def test_dialog_aluno_tem_senha_e_cartao(qtbot):
    dlg = NovoAlunoDialog()
    qtbot.addWidget(dlg)
    dlg.edt_nome.setText("Ana")
    dlg.edt_senha.setText("1234")
    dlg.edt_cartao.setText("TAG-42")
    dados = dlg.dados()
    assert dados["senha"] == "1234"
    assert dados["cartao_id"] == "TAG-42"


def test_perfil_modal_edita_e_lista_pagamentos(qtbot, ctx: AppContext):
    aluno = ctx.alunos_vm.cadastrar(nome="Ana", senha="1234")
    ctx.caixa_vm.registrar(
        aluno_id=aluno.id,
        valor=Decimal("99.90"),
        data_vencimento=date.today(),
        pago=True,
    )
    dlg = PerfilAlunoDialog(ctx.alunos_vm, ctx.caixa_vm, aluno.id)
    qtbot.addWidget(dlg)
    assert dlg.form.edt_nome.text() == "Ana"
    assert dlg.tbl_pag.rowCount() == 1
    dlg.form.edt_nome.setText("Ana Silva")
    dlg.form.edt_senha.setText("")  # mantém hash
    dlg._salvar()
    assert dlg.result() == QDialog.DialogCode.Accepted
    atual = ctx.alunos_vm.alunos.buscar(aluno.id)
    assert atual is not None and atual.nome == "Ana Silva"
    assert atual.verificar_senha("1234") is True


def test_alunos_duplo_clique_e_menu_abrem_perfil(qtbot, ctx: AppContext, mocker):
    view = AlunosView(ctx.alunos_vm, ctx.caixa_vm)
    qtbot.addWidget(view)
    ctx.alunos_vm.cadastrar(nome="Ana")
    view.recarregar()
    assert view.tbl.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu
    view.tbl.selectRow(0)
    mocker.patch.object(PerfilAlunoDialog, "exec", return_value=QDialog.DialogCode.Accepted)
    view._abrir_perfil()  # via duplo-clique/menu, sem travar
    assert view.tbl.rowCount() == 1


def test_perfil_mostra_frequencia_outros_dias(qtbot, ctx: AppContext):
    aluno = ctx.alunos_vm.cadastrar(nome="Ana", senha="1234")
    repo = ctx.dashboard_vm.acesso.acesso_repo
    assert repo is not None
    hoje = date.today()
    ontem = hoje - timedelta(days=1)
    repo.registrar(
        TentativaAcesso(
            aluno_id=aluno.id,
            direcao=DirecaoAcesso.ENTRADA,
            timestamp=datetime(ontem.year, ontem.month, ontem.day, 8, 0),
            resultado=ResultadoAcesso.LIBERADO,
        )
    )
    repo.registrar(
        TentativaAcesso(
            aluno_id=aluno.id,
            direcao=DirecaoAcesso.ENTRADA,
            timestamp=datetime(hoje.year, hoje.month, hoje.day, 8, 0),
            resultado=ResultadoAcesso.LIBERADO,
        )
    )
    dlg = PerfilAlunoDialog(ctx.alunos_vm, ctx.caixa_vm, aluno.id, frequencia_vm=ctx.frequencia_vm)
    qtbot.addWidget(dlg)
    assert dlg.tbl_freq.rowCount() == 1  # só ontem; hoje fica no dashboard
    assert dlg.tbl_freq.item(0, 0) is not None
    assert dlg.tbl_freq.item(0, 0).text() == ontem.isoformat()  # type: ignore[union-attr]
