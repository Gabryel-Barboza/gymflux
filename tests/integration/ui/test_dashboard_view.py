"""DashboardView — status, liberação, painel senha/cartão, click-through.

Usa a fixture ``dash`` (view direta, sem montar as 7 abas); só o teste de
click-through fim a fim monta a janela real.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from gymflux.core.plano import TipoPlano
from gymflux.ui.app import AppContext, build_window
from gymflux.ui.views.dashboard import DashboardView


def _valor_status(view: DashboardView, campo: str) -> str:
    for row in range(view.tbl_status.rowCount()):
        item_campo = view.tbl_status.item(row, 0)
        if item_campo is not None and item_campo.text() == campo:
            item_valor = view.tbl_status.item(row, 1)
            assert item_valor is not None
            return item_valor.text()
    raise AssertionError(f"campo {campo} ausente no status")


def _adimplente_com_senha(ctx: AppContext, senha: str = "1234"):
    aluno = ctx.alunos_vm.cadastrar(
        nome="Ana Silva", cpf="11144477735", senha=senha, cartao_id="TAG-42"
    )
    plano = ctx.planos_vm.salvar(nome="Mensal", tipo=TipoPlano.MENSAL, valor=Decimal("99.90"))
    ctx.alunos_vm.matricular(aluno.id, plano.id)
    ctx.caixa_vm.registrar(
        aluno_id=aluno.id,
        valor=Decimal("99.90"),
        data_vencimento=date.today(),
        pago=True,
    )
    return aluno


def test_dashboard_renderiza_status_mock(dash: DashboardView, ctx: AppContext):
    dash._refresh_status()
    assert _valor_status(dash, "Online") == "SIM"
    assert "MockHenry7x" in _valor_status(dash, "Driver")
    assert _valor_status(dash, "Porta") == ctx.dashboard_vm.ui_config.porta_catraca


def test_fluxo_completo_pela_ui_cadastra_e_libera(dash: DashboardView, ctx: AppContext):
    aluno = ctx.alunos_vm.cadastrar(nome="Ana Silva", cpf="11144477735")
    plano = ctx.planos_vm.salvar(nome="Mensal", tipo=TipoPlano.MENSAL, valor=Decimal("99.90"))
    ctx.alunos_vm.matricular(aluno.id, plano.id)
    ctx.caixa_vm.registrar(
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


def test_dashboard_negado_mostra_motivo(dash: DashboardView, ctx: AppContext):
    aluno = ctx.alunos_vm.cadastrar(nome="Sem Pagar", cpf="22255588846")
    dash.edt_aluno.setText(aluno.id)
    dash._liberar("ENTRADA")
    assert dash.lbl_resultado.text().startswith("NEGADO")


def test_dashboard_painel_verificacao_senha(dash: DashboardView, ctx: AppContext):
    _adimplente_com_senha(ctx)

    dash.edt_codigo.setText("1234")
    dash._identificar()
    assert dash.lbl_verificacao.text() == "Ana Silva — LIBERADO"
    assert dash.edt_codigo.text() == ""

    dash.edt_codigo.setText("0000")
    dash._identificar()
    assert dash.lbl_verificacao.text().startswith("NÃO IDENTIFICADO — NEGADO")


def test_dashboard_painel_verificacao_cartao(dash: DashboardView, ctx: AppContext):
    _adimplente_com_senha(ctx)

    dash.cmb_origem.setCurrentIndex(1)  # Cartão
    dash.edt_codigo.setText("TAG-42")
    dash._identificar()
    assert dash.lbl_verificacao.text() == "Ana Silva — LIBERADO"


def test_dashboard_enxuto_alturas_e_icones(dash: DashboardView):
    # log e giros: viewport p/ ~5 itens (altura limitada, com scroll)
    assert 0 < dash.tbl_log.maximumHeight() < 1000
    assert 0 < dash.lst_giros.maximumHeight() < 1000
    assert dash.tbl_log.rowCount() == 0  # vazio, sem erro
    # botões com ícones do sistema (sem assets binários)
    for btn in (dash.btn_entrada, dash.btn_saida, dash.btn_bloquear, dash.btn_identificar):
        assert not btn.icon().isNull()


def test_dashboard_status_tabela_compacta(dash: DashboardView):
    assert dash.tbl_status.columnCount() == 2
    assert dash.tbl_status.rowCount() == 6
    assert dash.tbl_status.maximumHeight() < 1000


def test_painel_senha_curta_e_direcao_bloqueada(dash: DashboardView, ctx: AppContext):
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


def test_resultado_liberado_verde_negado_vermelho(dash: DashboardView, ctx: AppContext):
    from gymflux.ui.theme import LIMA, VERMELHO

    aluno = ctx.alunos_vm.cadastrar(nome="Ana Silva", cpf="11144477735")
    dash.edt_aluno.setText(aluno.id)
    dash._liberar("ENTRADA")  # sem matrícula => NEGADO
    assert dash.lbl_resultado.text().startswith("NEGADO")
    assert VERMELHO in dash.lbl_resultado.styleSheet()

    plano = ctx.planos_vm.salvar(nome="Mensal", tipo=TipoPlano.MENSAL, valor=Decimal("99.90"))
    ctx.alunos_vm.matricular(aluno.id, plano.id)
    ctx.caixa_vm.registrar(
        aluno_id=aluno.id, valor=Decimal("99.90"), data_vencimento=date.today(), pago=True
    )
    dash._liberar("ENTRADA")
    assert dash.lbl_resultado.text().startswith("LIBERADO")
    assert LIMA in dash.lbl_resultado.styleSheet()


def test_click_no_registro_abre_perfil(qtbot, ctx: AppContext, mocker):
    from PySide6.QtWidgets import QDialog

    from gymflux.ui.views.alunos import PerfilAlunoDialog

    win = build_window(ctx)
    qtbot.addWidget(win)
    dash = win.tabs.widget(0)
    assert isinstance(dash, DashboardView)
    aluno = ctx.alunos_vm.cadastrar(nome="Ana Silva", cpf="11144477735")
    dash.edt_aluno.setText(aluno.id)
    dash._liberar("ENTRADA")
    assert dash.tbl_log.rowCount() == 1

    # mock antes: o emit dispara o slot real da janela (modal)
    mocker.patch.object(PerfilAlunoDialog, "exec", return_value=QDialog.DialogCode.Accepted)
    emitidos: list[str] = []
    dash.perfil_solicitado.connect(emitidos.append)
    dash._registro_clicado(0, 1)
    assert emitidos == [aluno.id]

    # click-through fim a fim: troca p/ aba Alunos e abre o modal
    win._abrir_perfil_aluno(aluno.id)
    assert win.tabs.tabText(win.tabs.currentIndex()) == "Alunos"


def test_click_em_registro_funcionario_nao_abre_perfil(dash: DashboardView, ctx: AppContext):
    from gymflux.services.identificar_acesso import Identificacao

    ctx.funcionarios_vm.cadastrar(nome="Zé Porteira", senha="1234")
    decisao, _ = ctx.dashboard_vm.identificar.identificar(Identificacao.por_teclado("1234"))
    assert decisao.liberado is True
    dash._refresh_log()
    assert dash.tbl_log.rowCount() >= 1
    emitidos: list[str] = []
    dash.perfil_solicitado.connect(emitidos.append)
    dash._registro_clicado(0, 1)  # linha mais recente = funcionário
    assert emitidos == []
