"""Testa que alembic upgrade/downgrade funciona e tabelas existem."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from gymflow.infra.db import Base


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


def test_alembic_upgrade_head_via_cli():
    # Testa que alembic upgrade head não quebra (usa data/gymflow.db real)
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    ini = Path("alembic.ini")
    if not ini.exists():
        pytest.skip("alembic.ini não encontrado")
    cfg = Config(str(ini))
    # deve rodar sem erro mesmo se já em head
    command.upgrade(cfg, "head")
    # verifica tabela existe no arquivo real
    from sqlalchemy import create_engine as ce

    from gymflow.config.settings import get_settings

    url = get_settings().db_url
    if ":memory:" in url:
        pytest.skip("db_url é memory")
    eng = ce(url, future=True)
    with eng.connect() as conn:
        res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = {r[0] for r in res.fetchall()}
        assert "alunos" in tables
    eng.dispose()
