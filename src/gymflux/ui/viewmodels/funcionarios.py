"""FuncionariosViewModel — CRUD + ativar/inativar (Qt-free, sem service dedicado)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from gymflux.core.funcionario import Funcionario


class FuncionarioRepoProto(Protocol):
    def salvar(self, funcionario: Funcionario) -> Funcionario: ...
    def buscar_por_id(self, funcionario_id: str) -> Funcionario | None: ...
    def listar(self) -> list[Funcionario]: ...
    def remover(self, funcionario_id: str) -> None: ...


@dataclass
class FuncionariosViewModel:
    repo: FuncionarioRepoProto
    commit: Callable[[], None] | None = None

    def _commit(self) -> None:
        if self.commit is not None:
            self.commit()

    def listar(self) -> list[Funcionario]:
        return sorted(self.repo.listar(), key=lambda f: f.nome.lower())

    def buscar(self, funcionario_id: str) -> Funcionario | None:
        return self.repo.buscar_por_id(funcionario_id)

    def cadastrar(
        self,
        *,
        nome: str,
        senha: str,
        horarios: str | None = None,
        dias: str | None = None,
        foto: str | None = None,
    ) -> Funcionario:
        func = Funcionario(
            id=f"func-{uuid.uuid4().hex[:8]}",
            nome=nome.strip(),
            horarios=(horarios.strip() or None) if horarios else None,
            dias=(dias.strip() or None) if dias else None,
            foto=(foto.strip() or None) if foto else None,
        )
        func.definir_senha(senha)  # ValueError se fora de 4-8 dígitos
        self.repo.salvar(func)
        self._commit()
        return func

    def atualizar(
        self,
        funcionario_id: str,
        *,
        nome: str,
        senha: str | None = None,
        horarios: str | None = None,
        dias: str | None = None,
        foto: str | None = None,
    ) -> Funcionario:
        func = self.repo.buscar_por_id(funcionario_id)
        if func is None:
            raise ValueError(f"Funcionário id={funcionario_id} não encontrado")
        if not nome or not nome.strip():
            raise ValueError("nome não pode ser vazio")
        func.nome = nome.strip()
        if senha and senha.strip():
            func.definir_senha(senha)  # vazia mantém o hash atual
        if horarios is not None:
            func.horarios = horarios.strip() or None
        if dias is not None:
            func.dias = dias.strip() or None
        if foto is not None:
            func.foto = foto.strip() or None
        self.repo.salvar(func)
        self._commit()
        return func

    def definir_ativo(self, funcionario_id: str, ativo: bool) -> Funcionario:
        func = self.repo.buscar_por_id(funcionario_id)
        if func is None:
            raise ValueError(f"Funcionário id={funcionario_id} não encontrado")
        func.ativo = ativo
        self.repo.salvar(func)
        self._commit()
        return func
