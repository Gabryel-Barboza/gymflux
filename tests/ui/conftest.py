"""Fixtures compartilhadas dos testes de UI (offscreen, mock)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6", reason="UI requer extra ui: uv sync --extra ui")

from gymflow.ui.app import create_context


@pytest.fixture
def ctx():
    context = create_context(use_db=False)
    context.bridge.driver.conectar("MOCK:1")
    yield context
    context.bridge.driver.desconectar()
    context.close()
