"""SQLite :memory: compartilhado por sessão (rápido) + limpeza por teste.

- Um único engine + ``create_all`` por sessão: economiza ~0,3s vs recriar
  o schema em cada teste.
- Isolamento mantido: teardown apaga todas as linhas (filhas antes das
  mães via ``sorted_tables`` reverso), então cada teste começa vazio.
- Seguro sob xdist: cada worker tem seu próprio processo/engine.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import gymflux.infra.models  # noqa: F401 — registra os models no metadata
from gymflux.infra.db import Base


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    eng = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, future=True
    )

    @event.listens_for(eng, "connect")
    def _fk_on(dbapi_conn, _rec) -> None:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON;")
        cur.close()

    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    s = SessionLocal()
    yield s
    s.close()
    # limpa tudo p/ o próximo teste (ordes reversa = filhas primeiro)
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
