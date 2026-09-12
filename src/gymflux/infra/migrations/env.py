from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure src is on sys.path for `import gymflux` when alembic runs from project root
# env.py is at src/gymflux/infra/migrations/env.py -> parents[3] is `src`
_src = Path(__file__).resolve().parents[3]
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
# also ensure project root on path for edge cases
_root = Path(__file__).resolve().parents[4]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# GymFlux metadata
import gymflux.infra.models  # noqa: F401,E402  # ensure models registered
from gymflux.config.settings import get_settings  # noqa: E402
from gymflux.infra.db import Base  # noqa: E402

target_metadata = Base.metadata


def _get_url() -> str:
    # Prefer GYMFLUX_DB_URL via settings; fallback to alembic.ini
    try:
        settings_url = get_settings().db_url
        if settings_url:
            return settings_url
    except Exception:
        pass
    ini_url: str | None = config.get_main_option("sqlalchemy.url")
    return ini_url or "sqlite:///data/gymflux.db"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Override sqlalchemy.url in config so engine_from_config picks GYMFLUX_DB_URL
    url = _get_url()
    config.set_main_option("sqlalchemy.url", url)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
