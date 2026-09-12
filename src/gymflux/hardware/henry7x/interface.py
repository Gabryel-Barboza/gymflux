"""Contrato abstrato da catraca Henry 7x — usado por mock e real."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum


class Direcao(Enum):
    ENTRADA = 1
    SAIDA = 2


class ResultadoCatraca(Enum):
    LIBERADO = "LIBERADO"
    BLOQUEADO = "BLOQUEADO"
    TIMEOUT = "TIMEOUT"
    ERRO = "ERRO"


GiroCallback = Callable[[Direcao, float], None]  # direcao, timestamp


class Henry7xDriver(ABC):
    """ABC que isola o domínio de ctypes/pywin32/PySide6.

    Todo acesso à DLL passa por aqui. `core` e `services` dependem só desta ABC.
    """

    is_mock: bool = False  # sobrescrito nas implementações

    @abstractmethod
    def conectar(self, porta: str | int, timeout_ms: int = 5000) -> bool:
        """Conecta à catraca. Retorna True se ok. Pode levantar RuntimeError."""
        ...

    @abstractmethod
    def desconectar(self) -> None: ...

    @abstractmethod
    def liberar(self, direcao: Direcao) -> ResultadoCatraca:
        """Libera giro na direção. Deve respeitar timeout_giro internamente."""
        ...

    @abstractmethod
    def bloquear(self) -> None:
        """Bloqueia catraca (fecha solenoide)."""
        ...

    @abstractmethod
    def on_giro(self, callback: GiroCallback) -> None:
        """Registra callback chamado quando giro físico é detectado."""
        ...

    @abstractmethod
    def off_giro(self, callback: GiroCallback) -> None:
        """Remove callback registrado."""
        ...

    @abstractmethod
    def status(self) -> dict:
        """Retorna dict com chaves livres: online, firmware, contador, etc."""
        ...

    # helpers opcionais já com default
    def is_conectado(self) -> bool:
        return bool(self.status().get("online"))
