"""ConfigView — salvar aplica regra/porta/tema sem restart (construção direta)."""

from __future__ import annotations

from gymflux.core.acesso import DirecaoAcesso
from gymflux.ui.app import AppContext
from gymflux.ui.config_store import ConfigStore
from gymflux.ui.theme import LIMA, VERMELHO, ModoTema
from gymflux.ui.views.config import ConfigView
from gymflux.ui.views.dashboard import DashboardView


def test_config_salvar_aplica_regra_porta_e_persiste(qtbot, ctx: AppContext, tmp_path):
    view = ConfigView(ctx.config_vm)
    qtbot.addWidget(view)
    # isola o arquivo p/ não sujar data/
    ctx.config_vm.store = ConfigStore(tmp_path / "gymflux_config.json")
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
    assert ConfigStore(tmp_path / "gymflux_config.json").load().bloquear_saida is True
    # bloqueio de saída vale na hora
    dash = DashboardView(ctx.dashboard_vm, ctx.bridge)
    qtbot.addWidget(dash)
    dash.edt_codigo.setText("1234")
    decisao, _ = ctx.dashboard_vm.identificar_acesso("1234", "TECLADO", direcao=DirecaoAcesso.SAIDA)
    assert decisao.liberado is False


def test_config_alternar_tema_aplica_sem_restart(qtbot, ctx: AppContext, tmp_path, qapp):
    view = ConfigView(ctx.config_vm)
    qtbot.addWidget(view)
    # isola o arquivo p/ não sujar data/
    ctx.config_vm.store = ConfigStore(tmp_path / "gymflux_config.json")
    # garante estado inicial escuro independente do data/gymflux_config.json do host
    view.cmb_tema.setCurrentIndex(view.cmb_tema.findData(ModoTema.ESCURO))
    view._salvar()
    assert view.cmb_tema.currentData() == ModoTema.ESCURO

    view.cmb_tema.setCurrentIndex(view.cmb_tema.findData(ModoTema.CLARO))
    view._salvar()
    assert view.lbl_status.text() == "Configurações salvas e aplicadas."
    assert ConfigStore(tmp_path / "gymflux_config.json").load().tema == ModoTema.CLARO
    assert "background-color: #E8EDF1" in qapp.styleSheet()
    assert "border: 1px solid #C8D0D8" in qapp.styleSheet()

    # rótulos passam a usar selo legível no claro
    dash = DashboardView(ctx.dashboard_vm, ctx.bridge)
    qtbot.addWidget(dash)
    assert isinstance(dash, DashboardView)
    dash.edt_codigo.setText("0000")
    dash._identificar()
    assert "Negado" in dash.lbl_verificacao.text()
    assert VERMELHO in dash.lbl_verificacao.styleSheet()

    # volta p/ escuro sem restart
    view.cmb_tema.setCurrentIndex(view.cmb_tema.findData(ModoTema.ESCURO))
    view._salvar()
    assert ConfigStore(tmp_path / "gymflux_config.json").load().tema == ModoTema.ESCURO
    assert "background-color: #0F1113" in qapp.styleSheet()
    dash.edt_codigo.setText("0000")
    dash._identificar()
    assert LIMA not in dash.lbl_verificacao.styleSheet()  # negado: sem lima


def test_config_cadastro_obrigatorios_salva_e_aplica(qtbot, ctx: AppContext, tmp_path):
    ctx.config_vm.store = ConfigStore(tmp_path / "gymflux_config.json")
    ctx.config_vm.recarregar()
    view = ConfigView(ctx.config_vm)
    qtbot.addWidget(view)
    # default tudo False
    assert view.chk_cpf_obr.isChecked() is False
    assert view.chk_email_obr.isChecked() is False
    # marca CPF e E-mail
    view.chk_cpf_obr.setChecked(True)
    view.chk_email_obr.setChecked(True)
    view.chk_nasc_obr.setChecked(True)
    view._salvar()
    assert view.lbl_status.text() == "Configurações salvas e aplicadas."
    loaded = ConfigStore(tmp_path / "gymflux_config.json").load()
    assert loaded.cadastro_obrigatorios["cpf"] is True
    assert loaded.cadastro_obrigatorios["email"] is True
    assert loaded.cadastro_obrigatorios["data_nasc"] is True
    assert loaded.cadastro_obrigatorios["telefone"] is False
    assert loaded.cadastro_obrigatorios["endereco"] is False
    # desmarca e persiste
    view.chk_cpf_obr.setChecked(False)
    view._salvar()
    loaded2 = ConfigStore(tmp_path / "gymflux_config.json").load()
    assert loaded2.cadastro_obrigatorios["cpf"] is False


def test_config_tem_scroll_e_toast_fora(qtbot, ctx: AppContext):
    """Fase 5.3: conteúdo rola (inputs não espremem) e o toast fica fora do scroll."""
    from PySide6.QtWidgets import QScrollArea

    view = ConfigView(ctx.config_vm)
    qtbot.addWidget(view)
    assert isinstance(view.area_rolagem, QScrollArea)
    assert view.area_rolagem.widgetResizable()
    assert view.area_rolagem.widget() is not None
    # toast continua filho direto da view (não rola junto)
    assert view.lbl_status.parent() is view
    # modo catraca: labels exatos + roundtrip real/mock
    assert view.cmb_modo_catraca.itemText(0) == "Equipamento"
    assert view.cmb_modo_catraca.itemText(1) == "Demonstração"
