"""Abstração biometria — mock agora, Henry real depois."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TemplateBiometrico:
    aluno_id: int
    template: bytes  # bytes opacos do Henry
    qualidade: int = 0


class BiometricDriver(ABC):
    is_mock: bool = False

    @abstractmethod
    def cadastrar(self, aluno_id: int) -> TemplateBiometrico:
        """Captura digital e retorna template (mock gera bytes fake)."""
        ...

    @abstractmethod
    def verificar(self, template: bytes) -> int | None:
        """1:N — retorna aluno_id ou None se não encontrado."""
        ...

    @abstractmethod
    def remover(self, aluno_id: int) -> None: ...
