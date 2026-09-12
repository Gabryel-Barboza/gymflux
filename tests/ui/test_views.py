"""Testes das telas com pytest-qt headless (offscreen, mock, sem hardware real)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6", reason="UI requer extra ui: uv sync --extra ui")

from datetime import date
from decimal import Decimal

from PySide6.QtWidgets import QWidget

from gymflow.core.acesso import DirecaoAcesso
from gymflow.core.plano import TipoPlano
from gymflow.hardware.henry7x.interface import Direcao
from gymflow.hardware.henry7x.mock import MockHenry7x
from gymflow.ui.app import build_window
from gymflow.ui.catraca_bridge import CatracaBridge
from gymflow.ui.views.dashboard import DashboardView


def test_janela_principal_abas(qtbot, ctx):
    win = build_window(ctx)
    qtbot.addWidget(win)
    textos = [win.tabs.tabText(i) for i in range(win.tabs.count())]
    assert textos == ["Catraca", "Alunos", "Planos", "Caixa", "Funcionários", "Configurações"]


def _valor_status(view, campo):
    for row in range(view.tbl_status.rowCount()):
        item_campo = view.tbl_status.item(row, 0)
        if item_campo is not None and item_campo.text() == campo:
            item_valor = view.tbl_status.item(row, 1)
            assert item_valor is not None
            return item_valor.text()
    raise AssertionError(f"campo {campo} ausente no status")


def test_dashboard_renderiza_status_mock(qtbot, ctx):
    win = build_window(ctx)
    qtbot.addWidget(win)
    view = win.tabs.widget(0)
    assert isinstance(view, DashboardView)
    view._refresh_status()
    assert _valor_status(view, "Online") == "SIM"
    assert "MockHenry7x" in _valor_status(view, "Driver")
    assert _valor_status(view, "Porta") == ctx.dashboard_vm.ui_config.porta_catraca


def test_fluxo_completo_pela_ui_cadastra_e_libera(qtbot, ctx):
    win = build_window(ctx)
    qtbot.addWidget(win)
    dash = win.tabs.widget(0)
    assert isinstance(dash, DashboardView)

    aluno = ctx.alunos_vm.cadastrar(nome="Ana Silva", cpf="11144477735")
    plano = ctx.planos_vm.salvar(nome="Mensal", tipo=TipoPlano.MENSAL, valor=Decimal("99.90"))
    ctx.alunos_vm.matricular(aluno.id, plano.id)
    ctx.pagamentos_vm.registrar(
        aluno_id=aluno.id,
        valor=Decimal("99.90"),
        data_vencimento=date.today(),
        pago=True,
    )

    dash.edt_aluno.setText(aluno.id)
    dash._liberar("ENTRADA")
    assert dash.lbl_resultado.text().startswith("LIBERADO")
    assert dash.tbl_log.rowCount() == 1
    item_nome = dash.tbl_log.item(0, 1)
    assert item_nome is not None
    assert item_nome.text() == "Ana Silva"


def test_dashboard_negado_mostra_motivo(qtbot, ctx):
    win = build_window(ctx)
    qtbot.addWidget(win)
    dash = win.tabs.widget(0)
    assert isinstance(dash, DashboardView)
    aluno = ctx.alunos_vm.cadastrar(nome="Sem Pagar", cpf="22255588846")
    dash.edt_aluno.setText(aluno.id)
    dash._liberar("ENTRADA")
    assert dash.lbl_resultado.text().startswith("NEGADO")


def test_alunos_view_busca_filtra(qtbot, ctx):
    win = build_window(ctx)
    qtbot.addWidget(win)
    view = win.tabs.widget(1)
    ctx.alunos_vm.cadastrar(nome="Ana Silva", cpf="11144477735")
    ctx.alunos_vm.cadastrar(nome="Bruno Souza", cpf="22255588846")
    view.edt_busca.setText("ana")
    assert view.tbl.rowCount() == 1
    view.edt_busca.clear()
    assert view.tbl.rowCount() == 2


def test_bridge_giro_chega_como_signal(qtbot):
    mock = MockHenry7x(auto_giro=False)
    bridge = CatracaBridge(driver=mock, porta="MOCK:1")
    qtbot.addWidget(QWidget())
    bridge.conectar()
    bridge.liberar_entrada()
    with qtbot.waitSignal(bridge.giro_detectado, timeout=2000) as blocker:
        mock.simular_giro(Direcao.ENTRADA)
    assert blocker.args[0] == "ENTRADA"
    bridge.desconectar()


def _adimplente_com_senha(ctx, senha="1234"):
    aluno = ctx.alunos_vm.cadastrar(
        nome="Ana Silva", cpf="11144477735", senha=senha, cartao_id="TAG-42"
    )
    plano = ctx.planos_vm.salvar(nome="Mensal", tipo=TipoPlano.MENSAL, valor=Decimal("99.90"))
    ctx.alunos_vm.matricular(aluno.id, plano.id)
    ctx.pagamentos_vm.registrar(
        aluno_id=aluno.id,
        valor=Decimal("99.90"),
        data_vencimento=date.today(),
        pago=True,
    )
    return aluno


def test_dashboard_painel_verificacao_senha(qtbot, ctx):
    win = build_window(ctx)
    qtbot.addWidget(win)
    dash = win.tabs.widget(0)
    assert isinstance(dash, DashboardView)
    _adimplente_com_senha(ctx)

    dash.edt_codigo.setText("1234")
    dash._identificar()
    assert dash.lbl_verificacao.text() == "Ana Silva — LIBERADO"
    assert dash.edt_codigo.text() == ""

    dash.edt_codigo.setText("0000")
    dash._identificar()
    assert dash.lbl_verificacao.text().startswith("NÃO IDENTIFICADO — NEGADO")


def test_dashboard_painel_verificacao_cartao(qtbot, ctx):
    win = build_window(ctx)
    qtbot.addWidget(win)
    dash = win.tabs.widget(0)
    assert isinstance(dash, DashboardView)
    _adimplente_com_senha(ctx)

    dash.cmb_origem.setCurrentIndex(1)  # Cartão
    dash.edt_codigo.setText("TAG-42")
    dash._identificar()
    assert dash.lbl_verificacao.text() == "Ana Silva — LIBERADO"


def test_dialog_aluno_tem_senha_e_cartao(qtbot):
    from gymflow.ui.views.alunos import NovoAlunoDialog

    dlg = NovoAlunoDialog()
    qtbot.addWidget(dlg)
    dlg.edt_nome.setText("Ana")
    dlg.edt_senha.setText("1234")
    dlg.edt_cartao.setText("TAG-42")
    dados = dlg.dados()
    assert dados["senha"] == "1234"
    assert dados["cartao_id"] == "TAG-42"


def test_dashboard_enxuto_alturas_e_icones(qtbot, ctx):
    win = build_window(ctx)
    qtbot.addWidget(win)
    dash = win.tabs.widget(0)
    assert isinstance(dash, DashboardView)
    # log e giros: viewport p/ ~5 itens (altura limitada, com scroll)
    assert 0 < dash.tbl_log.maximumHeight() < 1000
    assert 0 < dash.lst_giros.maximumHeight() < 1000
    assert dash.tbl_log.rowCount() == 0  # vazio, sem erro
    # botões com ícones do sistema (sem assets binários)
    for btn in (dash.btn_entrada, dash.btn_saida, dash.btn_bloquear, dash.btn_identificar):
        assert not btn.icon().isNull()
    # abas com ícones
    for i in range(win.tabs.count()):
        assert not win.tabs.tabIcon(i).isNull()


def test_dashboard_status_tabela_compacta(qtbot, ctx):
    win = build_window(ctx)
    qtbot.addWidget(win)
    dash = win.tabs.widget(0)
    assert isinstance(dash, DashboardView)
    assert dash.tbl_status.columnCount() == 2
    assert dash.tbl_status.rowCount() == 6
    assert dash.tbl_status.maximumHeight() < 1000


def test_painel_senha_curta_e_direcao_bloqueada(qtbot, ctx):
    win = build_window(ctx)
    qtbot.addWidget(win)
    dash = win.tabs.widget(0)
    assert isinstance(dash, DashboardView)
    _adimplente_com_senha(ctx, senha="123456")
    ctx.dashboard_vm.ui_config.senha_min_digitos = 6

    dash.edt_codigo.setText("1234")
    dash._identificar()
    assert "SENHA_CURTA" in dash.lbl_verificacao.text()
    assert "NEGADO" in dash.lbl_verificacao.text()

    ctx.dashboard_vm.ui_config.senha_min_digitos = 4
    ctx.dashboard_vm.ui_config.bloquear_entrada = True
    dash.edt_codigo.setText("123456")
    dash._identificar()
    assert "BLOQUEIO_MANUAL" in dash.lbl_verificacao.text()


def test_config_salvar_aplica_regra_porta_e_persiste(qtbot, ctx, tmp_path):
    from gymflow.ui.config_store import ConfigStore

    win = build_window(ctx)
    qtbot.addWidget(win)
    # isola o arquivo p/ não sujar data/
    ctx.config_vm.store = ConfigStore(tmp_path / "gymflow_config.json")
    idx = [win.tabs.tabText(i) for i in range(win.tabs.count())].index("Configurações")
    view = win.tabs.widget(idx)
    assert view.lbl_status.text() == ""

    view.spn_tolerancia.setValue(9)
    view.spn_timeout.setValue(12)
    view.chk_passback.setChecked(True)
    view.chk_bloq_saida.setChecked(True)
    view.edt_porta.setText("COM9")
    view._salvar()

    assert view.lbl_status.text() == "Configurações salvas e aplicadas."
    # aplicada na sessão: regra do domínio + porta do bridge
    regra_cfg = ctx.dashboard_vm.acesso.regra.config
    assert regra_cfg.tolerancia_dias == 9
    assert regra_cfg.timeout_giro_s == 12
    assert regra_cfg.anti_passback is True
    assert ctx.bridge.porta == "COM9"
    # persistida: nova VM lê do disco
    assert ConfigStore(tmp_path / "gymflow_config.json").load().bloquear_saida is True
    # bloqueio de saída vale na hora
    dash = win.tabs.widget(0)
    assert isinstance(dash, DashboardView)
    dash.edt_codigo.setText("1234")
    decisao, _ = ctx.dashboard_vm.identificar_acesso("1234", "TECLADO", direcao=DirecaoAcesso.SAIDA)
    assert decisao.liberado is False


def test_perfil_modal_edita_e_lista_pagamentos(qtbot, ctx):
    from PySide6.QtWidgets import QDialog

    from gymflow.ui.views.alunos import PerfilAlunoDialog

    aluno = ctx.alunos_vm.cadastrar(nome="Ana", senha="1234")
    ctx.pagamentos_vm.registrar(
        aluno_id=aluno.id,
        valor=Decimal("99.90"),
        data_vencimento=date.today(),
        pago=True,
    )
    dlg = PerfilAlunoDialog(ctx.alunos_vm, ctx.pagamentos_vm, aluno.id)
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


def test_alunos_duplo_clique_e_menu_abrem_perfil(qtbot, ctx, mocker):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDialog

    from gymflow.ui.views.alunos import AlunosView, PerfilAlunoDialog

    view = AlunosView(ctx.alunos_vm, ctx.pagamentos_vm)
    qtbot.addWidget(view)
    ctx.alunos_vm.cadastrar(nome="Ana")
    view.recarregar()
    assert view.tbl.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu
    view.tbl.selectRow(0)
    mocker.patch.object(PerfilAlunoDialog, "exec", return_value=QDialog.DialogCode.Accepted)
    view._abrir_perfil()  # via duplo-clique/menu, sem travar
    assert view.tbl.rowCount() == 1


def test_caixa_renderiza_fecha_e_selo(qtbot, ctx, mocker):
    from PySide6.QtWidgets import QMessageBox

    from gymflow.ui.views.caixa import CaixaView

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


def test_planos_cards_renderizam_editar_excluir(qtbot, ctx, mocker):
    from PySide6.QtWidgets import QMessageBox

    from gymflow.ui.views.planos import NovoPlanoDialog, PlanosView

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


def test_funcionarios_aba_e_dialog(qtbot, ctx):
    from gymflow.ui.views.funcionarios import FuncionariosView, NovoFuncionarioDialog

    win = build_window(ctx)
    qtbot.addWidget(win)
    idx = [win.tabs.tabText(i) for i in range(win.tabs.count())].index("Funcionários")
    view = win.tabs.widget(idx)
    assert isinstance(view, FuncionariosView)
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
