"""Marca com ``integration`` só os testes sob tests/integration (SQLite/Qt/alembic)."""

from __future__ import annotations

from pathlib import Path

import pytest

_AQUI = Path(__file__).parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        try:
            item.path.relative_to(_AQUI)
        except ValueError:
            continue
        item.add_marker(pytest.mark.integration)
