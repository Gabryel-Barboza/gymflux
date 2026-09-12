"""Migrations: metadata cria tabelas + alembic upgrade head isolado em tmp.

O teste de upgrade NÃO toca mais ``data/gymflux.db``: aponta
``GYMFLUX_DB_URL`` p/ um arquivo em ``tmp_path`` (com ``cache_clear`` no
``get_settings`` e restauração em ``finally``). Marcado ``slow`` p/ opt-out:
``uv run pytest -m "not slow"``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

import gymflux.infra.models  # noqa: F401 — registra os models no metadata
from gymflux.infra.db import Base


def test_migrations_criam_tabelas():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = {r[0] for r in res.fetchall()}
        assert "alunos" in tables
        assert "planos" in tables
        assert "matriculas" in tables
        assert "pagamentos" in tables
        assert "acesso_logs" in tables
    engine.dispose()


@pytest.mark.slow
def test_alembic_upgrade_head_isolado_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Isola do DB real: alembic lê a URL via get_settings().db_url
    from alembic import command
    from alembic.config import Config

    from gymflux.config.settings import get_settings

    db = tmp_path / "isolado.db"
    monkeypatch.setenv("GYMFLUX_DB_URL", f"sqlite:///{db}")
    get_settings.cache_clear()
    try:
        ini = Path("alembic.ini")
        if not ini.exists():
            pytest.skip("alembic.ini não encontrado")
        cfg = Config(str(ini))
        # deve rodar sem erro num banco vazio
        command.upgrade(cfg, "head")
        # verifica tabela existe no banco isolado
        from sqlalchemy import create_engine as ce

        eng = ce(f"sqlite:///{db}", future=True)
        with eng.connect() as conn:
            res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = {r[0] for r in res.fetchall()}
            assert "alunos" in tables
        eng.dispose()
    finally:
        get_settings.cache_clear()
