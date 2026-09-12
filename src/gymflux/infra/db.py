"""Engine + Base + Session — SQLAlchemy 2.0 SQLite GymFlux.

- URL vem de GYMFLUX_DB_URL (default sqlite:///data/gymflux.db).
- WAL + synchronous=NORMAL otimizados para SQLite local (ADR-002 bench 2.5ms).
- Sessões não autocommit; caller deve commit/rollback.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from gymflux.config.settings import get_settings


class Base(DeclarativeBase):
    """Base tipada p/ todos os models (sqlalchemy 2.0 Mapped[])."""


def _configure_sqlite(dbapi_conn, _conn_record) -> None:
    """Listener: ativa WAL + synchronous NORMAL + foreign_keys ON para SQLite."""
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        # cache_size negativo = KB; 8MB razoável p/ academia pequena
        cursor.execute("PRAGMA cache_size=-8192;")
    finally:
        cursor.close()


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine(db_url: str | None = None, echo: bool = False) -> Engine:
    """Retorna Engine singleton (ou cria novo se db_url diferente)."""
    global _engine, _session_factory
    url = db_url or get_settings().db_url
    # singleton simples: se URL mudou, recria
    if _engine is not None and str(_engine.url) == url and _engine.echo == echo:
        return _engine

    connect_args: dict = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(url, echo=echo, connect_args=connect_args, future=True)

    if url.startswith("sqlite"):
        event.listen(engine, "connect", _configure_sqlite)
        # garante diretório existe p/ arquivo sqlite (ignora :memory:)
        if ":memory:" not in url:
            try:
                # extrai path p/ sqlite:///data/gymflux.db ou sqlite:////abs/path
                raw = url.split("sqlite:///")[-1].split("?")[0]
                if raw and raw != ":memory:":
                    p = Path(raw)
                    if not p.is_absolute():
                        # relativo ao cwd (raiz do projeto)
                        p.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

    _engine = engine
    _session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return engine


def get_session_factory(db_url: str | None = None, echo: bool = False) -> sessionmaker[Session]:
    get_engine(db_url, echo=echo)
    assert _session_factory is not None
    return _session_factory


def get_session(db_url: str | None = None, echo: bool = False) -> Session:
    """Cria nova Session (caller deve close/commit)."""
    factory = get_session_factory(db_url, echo=echo)
    return factory()


@contextmanager
def session_scope(db_url: str | None = None) -> Iterator[Session]:
    """Context manager (uso: with session_scope() as s)."""
    session = get_session(db_url)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(db_url: str | None = None, echo: bool = False) -> Engine:
    """Cria todas as tabelas via Base.metadata (sem alembic). Útil p/ testes/demo."""
    engine = get_engine(db_url, echo=echo)
    # importa models para registrar no metadata
    from gymflux.infra import models as _models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    return engine


def reset_engine() -> None:
    """Reseta singleton — útil em testes com :memory: ou URL alternativa."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
