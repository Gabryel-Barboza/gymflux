"""ConfigStore + ConfigViewModel — Qt-free, JSON local em tmp_path."""

from __future__ import annotations

import json

from gymflux.ui.config_store import ConfigStore, UiConfig
from gymflux.ui.viewmodels.config import ConfigViewModel


def test_defaults_sensatos():
    cfg = UiConfig()
    assert cfg.bloquear_entrada is False
    assert cfg.bloquear_saida is False
    assert cfg.senha_min_digitos == 4
    assert cfg.tolerancia_dias == 3
    assert cfg.timeout_giro_s == 7
    assert cfg.anti_passback is False
    assert cfg.porta_catraca == "1"


def test_normalizacao_limites():
    cfg = UiConfig(senha_min_digitos=99, tolerancia_dias=-5, timeout_giro_s=0, porta_catraca="  ")
    assert cfg.senha_min_digitos == 8
    assert cfg.tolerancia_dias == 0
    assert cfg.timeout_giro_s == 1
    assert cfg.porta_catraca == "1"


def test_from_dict_tolera_lixo():
    cfg = UiConfig.from_dict({"senha_min_digitos": "6", "chave_futura": 1, "anti_passback": "sim"})
    assert cfg.senha_min_digitos == 6
    assert cfg.anti_passback is True
    assert cfg.tolerancia_dias == 3


def test_to_regra_config_espelha_dominio():
    regra = UiConfig(tolerancia_dias=5, timeout_giro_s=10, anti_passback=True).to_regra_config()
    assert regra.tolerancia_dias == 5
    assert regra.timeout_giro_s == 10
    assert regra.anti_passback is True


def test_store_roundtrip(tmp_path):
    store = ConfigStore(tmp_path / "cfg.json")
    assert store.exists() is False
    cfg = UiConfig(bloquear_entrada=True, senha_min_digitos=6, porta_catraca="COM3")
    store.save(cfg)
    assert store.exists() is True
    lido = store.load()
    assert lido == cfg


def test_store_arquivo_ausente_usa_fallback_porta(tmp_path):
    store = ConfigStore(tmp_path / "ausente.json", fallback_porta="COM7")
    cfg = store.load()
    assert cfg.porta_catraca == "COM7"
    assert cfg.senha_min_digitos == 4


def test_store_corrompido_volta_aos_padroes(tmp_path):
    caminho = tmp_path / "cfg.json"
    caminho.write_text("{json quebrado", encoding="utf-8")
    loaded = ConfigStore(caminho).load()
    # wallpaper default pode estar setado se assets existir
    expected = UiConfig()
    expected.wallpaper = ConfigStore(caminho)._default_wallpaper()
    assert loaded == expected
    caminho.write_text(json.dumps(["lista", "nao", "dict"]), encoding="utf-8")
    loaded2 = ConfigStore(caminho).load()
    expected2 = UiConfig()
    expected2.wallpaper = ConfigStore(caminho)._default_wallpaper()
    assert loaded2 == expected2


def test_viewmodel_salvar_persiste_e_aplica(tmp_path):
    aplicadas: list[UiConfig] = []
    vm = ConfigViewModel(store=ConfigStore(tmp_path / "cfg.json"), on_aplicar=aplicadas.append)
    assert vm.config.bloquear_saida is False
    vm.salvar(UiConfig(bloquear_saida=True, tolerancia_dias=9, porta_catraca="COM3"))
    assert vm.config.bloquear_saida is True
    assert len(aplicadas) == 1 and aplicadas[0].tolerancia_dias == 9
    # recarregar em outra instância lê do disco
    vm2 = ConfigViewModel(store=ConfigStore(tmp_path / "cfg.json"))
    assert vm2.config.porta_catraca == "COM3"
    assert vm2.config.tolerancia_dias == 9


def test_tema_default_e_roundtrip(tmp_path):
    from gymflux.ui.theme import ModoTema

    assert UiConfig().tema == ModoTema.ESCURO
    store = ConfigStore(tmp_path / "cfg.json")
    store.save(UiConfig(tema=ModoTema.CLARO))
    assert store.load().tema == ModoTema.CLARO
    assert UiConfig.from_dict({"tema": "CLARO"}).tema == ModoTema.CLARO
    assert UiConfig.from_dict({"tema": "escuro"}).tema == ModoTema.ESCURO
    assert UiConfig.from_dict({"tema": "rosa"}).tema == ModoTema.ESCURO
    assert UiConfig.from_dict({}).tema == ModoTema.ESCURO
