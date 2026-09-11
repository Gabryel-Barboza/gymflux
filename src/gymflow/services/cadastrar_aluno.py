"""CadastrarAlunoService — caso de uso mínimo em memória (Fase 1)."""

from __future__ import annotations

from dataclasses import dataclass, field

from loguru import logger

from gymflow.core.aluno import Aluno


@dataclass(slots=True)
class RepositorioAlunosMemoria:
    _alunos: dict[str, Aluno] = field(default_factory=dict)

    def salvar(self, aluno: Aluno) -> None:
        self._alunos[aluno.id] = aluno

    def buscar_por_id(self, aluno_id: str) -> Aluno | None:
        return self._alunos.get(aluno_id)

    def buscar_por_cpf(self, cpf: str) -> Aluno | None:
        digits = "".join(c for c in cpf if c.isdigit())
        for a in self._alunos.values():
            if a.cpf and "".join(c for c in a.cpf if c.isdigit()) == digits:
                return a
        return None

    def listar(self) -> list[Aluno]:
        return list(self._alunos.values())

    def total(self) -> int:
        return len(self._alunos)

    def limpar(self) -> None:
        self._alunos.clear()


@dataclass(slots=True)
class CadastrarAlunoService:
    repo: RepositorioAlunosMemoria = field(default_factory=RepositorioAlunosMemoria)

    def cadastrar(self, aluno: Aluno) -> Aluno:
        if self.repo.buscar_por_id(aluno.id) is not None:
            raise ValueError(f"Aluno id={aluno.id} já existe")
        if aluno.cpf and self.repo.buscar_por_cpf(aluno.cpf) is not None:
            raise ValueError(f"CPF {aluno.cpf} já cadastrado")
        self.repo.salvar(aluno)
        logger.info(f"[CadastrarAluno] id={aluno.id} nome={aluno.nome}")
        return aluno

    def atualizar(self, aluno: Aluno) -> Aluno:
        if self.repo.buscar_por_id(aluno.id) is None:
            raise ValueError(f"Aluno id={aluno.id} não encontrado")
        self.repo.salvar(aluno)
        return aluno

    def bloquear(self, aluno_id: str) -> Aluno:
        aluno = self.repo.buscar_por_id(aluno_id)
        if aluno is None:
            raise ValueError(f"Aluno id={aluno_id} não encontrado")
        aluno.bloquear_manual()
        self.repo.salvar(aluno)
        return aluno

    def desbloquear(self, aluno_id: str) -> Aluno:
        aluno = self.repo.buscar_por_id(aluno_id)
        if aluno is None:
            raise ValueError(f"Aluno id={aluno_id} não encontrado")
        aluno.desbloquear_manual()
        self.repo.salvar(aluno)
        return aluno

    def inativar(self, aluno_id: str) -> Aluno:
        aluno = self.repo.buscar_por_id(aluno_id)
        if aluno is None:
            raise ValueError(f"Aluno id={aluno_id} não encontrado")
        aluno.inativar()
        self.repo.salvar(aluno)
        return aluno
