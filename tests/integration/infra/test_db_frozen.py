"""DB frozen Fase 5.4: init_db cria gymflux.db no dir de dados (%APPDATA%).

Simula o exe instalado (``sys.frozen``) com o dir de dados em ``tmp_path``.
Vale p/ qualquer modo de catraca (real/mock) — o DB independe do helper.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import text


@pytest.fixture
def _frozen_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import gymflux.infra.db as db_mod
    from gymflux.config.settings import get_settings
    from gymflux.infra.db import reset_engine

    appdata = tmp_path / "GymFlux"
    monkeypatch.setattr(db_mod, "_frozen_data_dir", lambda: appdata)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    if hasattr(sys, "_MEIPASS"):
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    reset_engine()
    get_settings.cache_clear()
    try:
        yield appdata
    finally:
        reset_engine()
        get_settings.cache_clear()


def test_db_frozen_cria_em_appdata(_frozen_appdata: Path):
    from gymflux.infra.db import get_default_db_path, init_db

    alvo = get_default_db_path()
    assert alvo == _frozen_appdata / "gymflux.db"
    assert alvo.parent.exists()  # mkdir antes de qualquer acesso
    init_db()
    assert alvo.exists()
    import gymflux.infra.db as db_mod

    with db_mod.get_engine().connect() as conn:
        tabelas = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master"))}
    assert "alunos" in tabelas
    assert "pagamentos" in tabelas


def test_db_frozen_url_default_vira_appdata(_frozen_appdata: Path):
    """Todos os caminhos (get_engine/init_db) resolvem p/ o dir de dados."""
    from gymflux.infra.db import _effective_db_url, get_default_db_url

    url = get_default_db_url()
    assert "GymFlux" in url and url.endswith("gymflux.db")
    assert _effective_db_url("sqlite:///data/gymflux.db") == url
    assert _effective_db_url(f"sqlite:///{_frozen_appdata}/outro.db").endswith("outro.db")


@pytest.mark.slow
def test_ensure_schema_frozen_cria_db_sem_catraca(_frozen_appdata: Path, monkeypatch):
    """Reproduz o bug do instalado: frozen + upgrade => .db em %APPDATA%.

    Roda sem helper/DLL e com modo real — o DB independe da catraca.
    """
    from gymflux.config.settings import get_settings
    from gymflux.ui.app import _ensure_schema

    monkeypatch.setenv("GYMFLUX_DB_URL", "sqlite:///data/gymflux.db")
    get_settings.cache_clear()
    try:
        _ensure_schema()  # nunca propaga: upgrade ou create_all
        assert (_frozen_appdata / "gymflux.db").exists()
    finally:
        get_settings.cache_clear()
