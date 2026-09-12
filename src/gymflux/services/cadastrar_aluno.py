"""CadastrarAlunoService — Fase 2 com injeção de repositório (memória ou SQLAlchemy).

Compat: se repo None, usa memória Fase 1. Em produção, injetar AlunoRepositorySQLAlchemy(session).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from loguru import logger

from gymflux.core.aluno import Aluno


class AlunoRepoProtocol(Protocol):
    def salvar(self, aluno: Aluno) -> Aluno | None: ...
    def buscar_por_id(self, aluno_id: str) -> Aluno | None: ...
    def buscar_por_cpf(self, cpf: str) -> Aluno | None: ...
    def buscar_por_senha(self, senha: str) -> Aluno | None: ...
    def listar(self) -> list[Aluno]: ...


@dataclass(slots=True)
class RepositorioAlunosMemoria:
    _alunos: dict[str, Aluno] = field(default_factory=dict)

    def salvar(self, aluno: Aluno) -> Aluno:
        self._alunos[aluno.id] = aluno
        return aluno

    def buscar_por_id(self, aluno_id: str) -> Aluno | None:
        return self._alunos.get(aluno_id)

    def buscar_por_cpf(self, cpf: str) -> Aluno | None:
        digits = "".join(c for c in cpf if c.isdigit())
        for a in self._alunos.values():
            if a.cpf and "".join(c for c in a.cpf if c.isdigit()) == digits:
                return a
        return None

    def buscar_por_senha(self, senha: str) -> Aluno | None:
        codigo = senha.strip()
        if not codigo:
            return None
        for a in self._alunos.values():
            if a.senha == codigo:
                return a
        return None

    def listar(self) -> list[Aluno]:
        return list(self._alunos.values())

    def total(self) -> int:
        return len(self._alunos)

    def limpar(self) -> None:
        self._alunos.clear()

    def remover(self, aluno_id: str) -> None:
        self._alunos.pop(aluno_id, None)


@dataclass(slots=True)
class CadastrarAlunoService:
    repo: AlunoRepoProtocol = field(default_factory=RepositorioAlunosMemoria)

    def cadastrar(self, aluno: Aluno) -> Aluno:
        if self.repo.buscar_por_id(aluno.id) is not None:
            raise ValueError(f"Aluno id={aluno.id} já existe")
        if aluno.cpf and self.repo.buscar_por_cpf(aluno.cpf) is not None:
            raise ValueError(f"CPF {aluno.cpf} já cadastrado")
        result = self.repo.salvar(aluno)
        logger.info(f"[CadastrarAluno] id={aluno.id} nome={aluno.nome}")
        return result if result is not None else aluno

    def atualizar(self, aluno: Aluno) -> Aluno:
        if self.repo.buscar_por_id(aluno.id) is None:
            raise ValueError(f"Aluno id={aluno.id} não encontrado")
        result = self.repo.salvar(aluno)
        return result if result is not None else aluno

    def buscar(self, aluno_id: str) -> Aluno | None:
        return self.repo.buscar_por_id(aluno_id)

    def bloquear(self, aluno_id: str) -> Aluno:
        aluno = self.repo.buscar_por_id(aluno_id)
        if aluno is None:
            raise ValueError(f"Aluno id={aluno_id} não encontrado")
        aluno.bloquear_manual()
        result = self.repo.salvar(aluno)
        return result if result is not None else aluno

    def desbloquear(self, aluno_id: str) -> Aluno:
        aluno = self.repo.buscar_por_id(aluno_id)
        if aluno is None:
            raise ValueError(f"Aluno id={aluno_id} não encontrado")
        aluno.desbloquear_manual()
        result = self.repo.salvar(aluno)
        return result if result is not None else aluno

    def inativar(self, aluno_id: str) -> Aluno:
        aluno = self.repo.buscar_por_id(aluno_id)
        if aluno is None:
            raise ValueError(f"Aluno id={aluno_id} não encontrado")
        aluno.inativar()
        result = self.repo.salvar(aluno)
        return result if result is not None else aluno

    def listar(self) -> list[Aluno]:
        return self.repo.listar()
