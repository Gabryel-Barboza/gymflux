"""FuncionarioRepository — Protocol + SQLAlchemy impl + Memória."""

# ruff: noqa: SIM105
from __future__ import annotations

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from gymflux.core.funcionario import Funcionario
from gymflux.infra.models.funcionario import FuncionarioModel


class FuncionarioRepository(Protocol):
    def salvar(self, funcionario: Funcionario) -> Funcionario: ...
    def buscar_por_id(self, funcionario_id: str) -> Funcionario | None: ...
    def listar(self) -> list[Funcionario]: ...
    def remover(self, funcionario_id: str) -> None: ...
    def total(self) -> int: ...


def _model_to_domain(m: FuncionarioModel) -> Funcionario:
    return Funcionario(
        id=m.id,
        nome=m.nome,
        senha_hash=m.senha_hash,
        ativo=bool(m.ativo),
        horarios=m.horarios,
        dias=m.dias,
    )


def _domain_to_model(f: Funcionario) -> FuncionarioModel:
    return FuncionarioModel(
        id=f.id,
        nome=f.nome,
        senha_hash=f.senha_hash,
        ativo=bool(f.ativo),
        horarios=f.horarios,
        dias=f.dias,
    )


class FuncionarioRepositorySQLAlchemy:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _ensure_clean(self) -> None:
        try:
            if not self.session.is_active:
                self.session.rollback()
        except Exception:
            try:
                self.session.rollback()
            except Exception:
                pass

    def salvar(self, funcionario: Funcionario) -> Funcionario:
        self._ensure_clean()
        try:
            existing = self.session.get(FuncionarioModel, funcionario.id)
            if existing is None:
                self.session.add(_domain_to_model(funcionario))
            else:
                existing.nome = funcionario.nome
                existing.senha_hash = funcionario.senha_hash
                existing.ativo = bool(funcionario.ativo)
                existing.horarios = funcionario.horarios
                existing.dias = funcionario.dias
            self.session.flush()
        except Exception:
            try:
                self.session.rollback()
            except Exception:
                pass
            raise
        return funcionario

    def buscar_por_id(self, funcionario_id: str) -> Funcionario | None:
        self._ensure_clean()
        try:
            m = self.session.get(FuncionarioModel, funcionario_id)
            return _model_to_domain(m) if m else None
        except Exception as e:
            from sqlalchemy.exc import PendingRollbackError

            if isinstance(e, PendingRollbackError):
                try:
                    self.session.rollback()
                except Exception:
                    pass
                m = self.session.get(FuncionarioModel, funcionario_id)
                return _model_to_domain(m) if m else None
            raise

    def listar(self) -> list[Funcionario]:
        self._ensure_clean()
        try:
            stmt = select(FuncionarioModel)
            return [_model_to_domain(m) for m in self.session.execute(stmt).scalars().all()]
        except Exception as e:
            from sqlalchemy.exc import PendingRollbackError

            if isinstance(e, PendingRollbackError):
                try:
                    self.session.rollback()
                except Exception:
                    pass
                stmt = select(FuncionarioModel)
                return [_model_to_domain(m) for m in self.session.execute(stmt).scalars().all()]
            raise

    def remover(self, funcionario_id: str) -> None:
        self._ensure_clean()
        try:
            m = self.session.get(FuncionarioModel, funcionario_id)
            if m:
                self.session.delete(m)
                self.session.flush()
        except Exception:
            try:
                self.session.rollback()
            except Exception:
                pass
            raise

    def total(self) -> int:
        self._ensure_clean()
        try:
            stmt = select(FuncionarioModel)
            return len(self.session.execute(stmt).scalars().all())
        except Exception as e:
            from sqlalchemy.exc import PendingRollbackError

            if isinstance(e, PendingRollbackError):
                try:
                    self.session.rollback()
                except Exception:
                    pass
                stmt = select(FuncionarioModel)
                return len(self.session.execute(stmt).scalars().all())
            raise

    def limpar(self) -> None:
        self._ensure_clean()
        try:
            self.session.query(FuncionarioModel).delete()
            self.session.flush()
        except Exception:
            try:
                self.session.rollback()
            except Exception:
                pass
            raise


class FuncionarioRepositoryMemoria:
    def __init__(self) -> None:
        self._funcionarios: dict[str, Funcionario] = {}

    def salvar(self, funcionario: Funcionario) -> Funcionario:
        self._funcionarios[funcionario.id] = funcionario
        return funcionario

    def buscar_por_id(self, funcionario_id: str) -> Funcionario | None:
        return self._funcionarios.get(funcionario_id)

    def listar(self) -> list[Funcionario]:
        return list(self._funcionarios.values())

    def remover(self, funcionario_id: str) -> None:
        self._funcionarios.pop(funcionario_id, None)

    def total(self) -> int:
        return len(self._funcionarios)

    def limpar(self) -> None:
        self._funcionarios.clear()
