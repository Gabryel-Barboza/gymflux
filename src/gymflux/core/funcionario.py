"""Funcionário — domínio puro, sem I/O.

Entrada indefinida na catraca (sem matrícula/plano/pagamento); autentica
por senha numérica como aluno (mesmo hash PBKDF2+salt, nunca texto puro).
"""

from __future__ import annotations

from dataclasses import dataclass

from gymflux.core.aluno import conferir_senha, gerar_senha_hash


@dataclass(slots=True)
class Funcionario:
    """Colaborador com acesso livre; `ativo=False` bloqueia (manual)."""

    id: str
    nome: str
    senha_hash: str | None = None
    ativo: bool = True

    def __post_init__(self) -> None:
        if not self.nome or not self.nome.strip():
            raise ValueError("nome não pode ser vazio")

    def definir_senha(self, senha: str) -> None:
        """Define senha numérica (4-8 dígitos); armazena só o hash com salt."""
        self.senha_hash = gerar_senha_hash(senha)

    def verificar_senha(self, senha: str) -> bool:
        return conferir_senha(senha, self.senha_hash)

    def ativar(self) -> None:
        self.ativo = True

    def inativar(self) -> None:
        self.ativo = False
