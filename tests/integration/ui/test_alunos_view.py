"""AlunosView + PerfilAlunoDialog + NovoAlunoDialog (construção direta)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from gymflux.core.acesso import DirecaoAcesso, ResultadoAcesso, TentativaAcesso
from gymflux.ui.app import AppContext
from gymflux.ui.views.alunos import AlunosView, NovoAlunoDialog, PerfilAlunoDialog


def test_alunos_view_busca_filtra(qtbot, ctx: AppContext):
    view = AlunosView(ctx.alunos_vm, ctx.caixa_vm)
    qtbot.addWidget(view)
    ctx.alunos_vm.cadastrar(nome="Ana Silva", cpf="11144477735")
    ctx.alunos_vm.cadastrar(nome="Bruno Souza", cpf="22255588846")
    view.edt_busca.setText("ana")
    qtbot.wait(1100)  # debounce 1s igual CaixaView
    assert view.tbl.rowCount() == 1
    view.edt_busca.clear()
    qtbot.wait(1100)
    assert view.tbl.rowCount() == 2


def test_dialog_aluno_tem_senha_visivel(qtbot):
    dlg = NovoAlunoDialog()
    qtbot.addWidget(dlg)
    dlg.edt_nome.setText("Ana")
    dlg.edt_senha.setText("1234")
    dados = dlg.dados()
    assert dados["senha"] == "1234"
    assert "cartao_id" not in dados  # cartão removido na Fase 4.8


def test_perfil_modal_edita_e_lista_pagamentos(qtbot, ctx: AppContext, tmp_path, monkeypatch, mocker):  # noqa: E501
    # isola ConfigStore: cpf obrigatório no disco real travava este teste
    # (QMessageBox.warning modal bloqueia offscreen) — usa config vazia
    from gymflux.ui.config_store import ConfigStore, UiConfig

    mocker.patch("gymflux.ui.views.alunos.QMessageBox.warning")
    cfg_path = tmp_path / "gymflux_config.json"
    store = ConfigStore(cfg_path)
    store.save(UiConfig(cadastro_obrigatorios={}))
    monkeypatch.setattr("gymflux.ui.views.alunos.ConfigStore", lambda *a, **kw: store)
    aluno = ctx.alunos_vm.cadastrar(nome="Ana", senha="1234", cpf="11144477735")
    ctx.caixa_vm.registrar(
        aluno_id=aluno.id,
        valor=Decimal("99.90"),
        data_vencimento=date.today(),
        pago=True,
    )
    dlg = PerfilAlunoDialog(ctx.alunos_vm, ctx.caixa_vm, aluno.id)
    qtbot.addWidget(dlg)
    assert dlg.form.edt_nome.text() == "Ana"
    assert dlg.form.edt_senha.text() == "1234"  # PIN visível (Fase 4.8)
    assert dlg.tbl_pag.rowCount() == 1
    dlg.form.edt_nome.setText("Ana Silva")
    dlg.form.edt_senha.setText("")  # mantém a atual
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
    assert dlg.tbl_freq.item(0, 0).text() == ontem.strftime("%d/%m/%Y")  # type: ignore[union-attr]


def test_form_aplica_obrigatorios_asterisco(qtbot):
    from gymflux.ui.views.alunos import _AlunoForm

    form = _AlunoForm()
    qtbot.addWidget(form)
    # default tudo sem *
    form.aplicar_obrigatorios({})
    assert form.lbl_cpf.text() == "CPF:"
    assert form.lbl_nome.text() == "Nome*:"
    # marca CPF e data_nasc
    form.aplicar_obrigatorios({"cpf": True, "data_nasc": True})
    assert form.lbl_cpf.text() == "CPF*:"
    assert form.lbl_nasc.text() == "Nascimento*:"
    assert form.lbl_tel.text() == "Telefone:"
    # via UiConfig persistido
    from gymflux.ui.config_store import UiConfig

    cfg = UiConfig(cadastro_obrigatorios={"telefone": True, "email": True})
    form.aplicar_obrigatorios(cfg)
    assert form.lbl_tel.text() == "Telefone*:"
    assert form.lbl_email.text() == "E-mail*:"
    # desconhecido ignorado
    form.aplicar_obrigatorios({"invalido": True, "cpf": False})
    assert form.lbl_cpf.text() == "CPF:"


def test_novo_dialog_carrega_obrigatorios_do_disco(qtbot, tmp_path, monkeypatch):
    from gymflux.ui.config_store import ConfigStore
    from gymflux.ui.views.alunos import NovoAlunoDialog

    cfg_path = tmp_path / "gymflux_config.json"
    store = ConfigStore(cfg_path)
    from gymflux.ui.config_store import UiConfig

    store.save(UiConfig(cadastro_obrigatorios={"cpf": True}))
    monkeypatch.setattr("gymflux.ui.views.alunos.ConfigStore", lambda *a, **kw: store)
    dlg = NovoAlunoDialog()
    qtbot.addWidget(dlg)
    assert dlg.form.lbl_cpf.text() == "CPF*:"


def test_perfil_salvar_valida_obrigatorios_via_vm(
    qtbot, ctx: AppContext, tmp_path, monkeypatch, mocker
):
    from gymflux.ui.config_store import ConfigStore, UiConfig
    from gymflux.ui.views.alunos import PerfilAlunoDialog

    mocker.patch("gymflux.ui.views.alunos.QMessageBox.warning")
    cfg_path = tmp_path / "gymflux_config.json"
    store = ConfigStore(cfg_path)
    store.save(UiConfig(cadastro_obrigatorios={"cpf": True}))
    monkeypatch.setattr("gymflux.ui.views.alunos.ConfigStore", lambda *a, **kw: store)
    aluno = ctx.alunos_vm.cadastrar(nome="Ana", cpf="11144477735")
    dlg = PerfilAlunoDialog(ctx.alunos_vm, ctx.caixa_vm, aluno.id)
    qtbot.addWidget(dlg)
    # limpa CPF obrigatório
    dlg.form.edt_cpf.setText("")
    # _salvar deve falhar via VM e não aceitar
    dlg._salvar()
    assert dlg.result() != 1  # não Accepted
    # preenche e deve passar
    dlg.form.edt_cpf.setText("11144477735")
    dlg._salvar()
    assert dlg.result() == 1
