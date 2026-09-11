"""Entidade Aluno — domínio puro, sem I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class StatusAluno(StrEnum):
    ATIVO = "ATIVO"
    INATIVO = "INATIVO"
    BLOQUEADO = "BLOQUEADO"


@dataclass(slots=True)
class Aluno:
    """Aluno da academia.

    - `bloqueado_manual` sobrepõe qualquer liberação (RB03).
    - `status == BLOQUEADO` também é bloqueio manual (compat).
    """

    id: str
    nome: str
    cpf: str | None = None
    data_nasc: date | None = None
    telefone: str | None = None
    email: str | None = None
    status: StatusAluno = StatusAluno.ATIVO
    observacoes: str | None = None
    bloqueado_manual: bool = False

    def __post_init__(self) -> None:
        if not self.nome or not self.nome.strip():
            raise ValueError("nome não pode ser vazio")
        if self.cpf is not None:
            cpf_digits = "".join(c for c in self.cpf if c.isdigit())
            if cpf_digits and len(cpf_digits) != 11:
                raise ValueError("CPF deve ter 11 dígitos quando informado")

    @property
    def esta_bloqueado(self) -> bool:
        return self.bloqueado_manual or self.status == StatusAluno.BLOQUEADO

    @property
    def esta_ativo(self) -> bool:
        return self.status == StatusAluno.ATIVO and not self.bloqueado_manual

    def bloquear_manual(self) -> None:
        self.bloqueado_manual = True

    def desbloquear_manual(self) -> None:
        self.bloqueado_manual = False
        if self.status == StatusAluno.BLOQUEADO:
            self.status = StatusAluno.ATIVO

    def inativar(self) -> None:
        self.status = StatusAluno.INATIVO

    def reativar(self) -> None:
        if self.status == StatusAluno.INATIVO:
            self.status = StatusAluno.ATIVO
