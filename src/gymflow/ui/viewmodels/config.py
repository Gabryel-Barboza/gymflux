"""ConfigViewModel — lê/salva preferências via ConfigStore (Qt-free)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from gymflow.ui.config_store import ConfigStore, UiConfig


@dataclass
class ConfigViewModel:
    """Expõe ``config`` editável; ``salvar`` persiste e notifica via callback."""

    store: ConfigStore
    on_aplicar: Callable[[UiConfig], None] | None = None
    config: UiConfig = field(init=False)

    def __post_init__(self) -> None:
        self.config = self.store.load()

    def recarregar(self) -> UiConfig:
        """Relê do disco (descarta edições não salvas)."""
        self.config = self.store.load()
        return self.config

    def salvar(self, cfg: UiConfig) -> UiConfig:
        """Valida (normaliza), persiste, atualiza e aplica na sessão."""
        normalizado = UiConfig.from_dict(cfg.to_dict())
        self.store.save(normalizado)
        self.config = normalizado
        if self.on_aplicar is not None:
            self.on_aplicar(normalizado)
        return normalizado
