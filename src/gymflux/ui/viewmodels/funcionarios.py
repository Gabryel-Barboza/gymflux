"""FuncionariosViewModel — CRUD + ativar/inativar (Qt-free, sem service dedicado)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from gymflux.core.funcionario import Funcionario


class FuncionarioRepoProto(Protocol):
    def salvar(self, funcionario: Funcionario) -> Funcionario: ...
    def buscar_por_id(self, funcionario_id: str) -> Funcionario | None: ...
    def listar(self) -> list[Funcionario]: ...
    def remover(self, funcionario_id: str) -> None: ...


class AlunoRepoProto(Protocol):
    def listar(self) -> list[Any]: ...


@dataclass
class FuncionariosViewModel:
    repo: FuncionarioRepoProto
    commit: Callable[[], None] | None = None
    aluno_repo: Any | None = None

    def _commit(self) -> None:
        if self.commit is not None:
            self.commit()

    def _senha_duplicada(self, senha: str, ignore_func_id: str | None = None) -> bool:
        if not senha or not senha.strip():
            return False
        codigo = senha.strip()
        for f in self.repo.listar():
            if ignore_func_id and f.id == ignore_func_id:
                continue
            if getattr(f, "senha", None) == codigo:
                return True
            try:
                if hasattr(f, "verificar_senha") and f.verificar_senha(codigo):  # type: ignore[attr-defined]
                    return True
            except Exception:
                pass
        if self.aluno_repo is not None:
            try:
                for a in self.aluno_repo.listar():  # type: ignore[attr-defined]
                    if getattr(a, "senha", None) == codigo:
                        return True
            except Exception:
                pass
        return False

    def listar(self) -> list[Funcionario]:
        return sorted(self.repo.listar(), key=lambda f: f.nome.lower())

    def buscar(self, funcionario_id: str) -> Funcionario | None:
        return self.repo.buscar_por_id(funcionario_id)

    def _norm_horarios(self, horarios: str | None) -> str | None:
        if horarios is None:
            return None
        txt = horarios.strip()
        if not txt:
            return None
        from gymflux.core.funcionario import format_turnos, parse_turnos

        try:
            turnos = parse_turnos(txt)
            return format_turnos(turnos)
        except ValueError as e:
            raise ValueError(str(e)) from e

    def cadastrar(
        self,
        *,
        nome: str,
        senha: str,
        horarios: str | None = None,
        dias: str | None = None,
        foto: str | None = None,
    ) -> Funcionario:
        if not nome or not nome.strip():
            raise ValueError("Nome não pode ser vazio.")
        if senha and senha.strip() and self._senha_duplicada(senha):
            raise ValueError("Senha já cadastrada para outro aluno ou funcionário.")
        horarios_norm = self._norm_horarios(horarios)
        func = Funcionario(
            id=f"func-{uuid.uuid4().hex[:8]}",
            nome=nome.strip(),
            horarios=horarios_norm,
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
            raise ValueError(f"Funcionário id={funcionario_id} não encontrado.")
        if not nome or not nome.strip():
            raise ValueError("Nome não pode ser vazio.")
        func.nome = nome.strip()
        if senha and senha.strip():
            if self._senha_duplicada(senha, ignore_func_id=funcionario_id):
                raise ValueError("Senha já cadastrada para outro aluno ou funcionário.")
            func.definir_senha(senha)  # vazia mantém o hash atual
        if horarios is not None:
            func.horarios = self._norm_horarios(horarios)
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
            raise ValueError(f"Funcionário id={funcionario_id} não encontrado.")
        func.ativo = ativo
        self.repo.salvar(func)
        self._commit()
        return func
