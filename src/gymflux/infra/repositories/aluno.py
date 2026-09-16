"""AlunoRepository — Protocol + SQLAlchemy impl + Memória fallback."""

# ruff: noqa: SIM105
from __future__ import annotations

from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gymflux.core.aluno import Aluno, StatusAluno
from gymflux.infra.models.aluno import AlunoModel


class AlunoRepository(Protocol):
    def salvar(self, aluno: Aluno) -> Aluno: ...
    def buscar_por_id(self, aluno_id: str) -> Aluno | None: ...
    def buscar_por_cpf(self, cpf: str) -> Aluno | None: ...
    def buscar_por_senha(self, senha: str) -> Aluno | None: ...
    def listar(self) -> list[Aluno]: ...
    def remover(self, aluno_id: str) -> None: ...
    def total(self) -> int: ...
    def mapa_nomes(self, ids: list[str]) -> dict[str, str]: ...
    def listar_ordenado(
        self, limit: int | None = None, offset: int = 0, busca: str | None = None
    ) -> list[Aluno]: ...


def _model_to_domain(m: AlunoModel) -> Aluno:
    # cpf já vem como string ou None
    status = (
        StatusAluno(m.status) if m.status in StatusAluno._value2member_map_ else StatusAluno.ATIVO
    )
    created = getattr(m, "created_at", None)
    created_date = None
    if created is not None:
        try:
            created_date = created.date() if hasattr(created, "date") else created
        except Exception:
            created_date = None
    return Aluno(
        id=m.id,
        nome=m.nome,
        cpf=m.cpf,
        data_nasc=m.data_nasc,
        telefone=m.telefone,
        email=m.email,
        status=status,
        observacoes=m.observacoes,
        endereco=m.endereco,
        bloqueado_manual=bool(m.bloqueado_manual),
        senha=m.senha,
        foto=getattr(m, "foto", None),
        created_at=created_date,
    )


def _domain_to_model(aluno: Aluno) -> AlunoModel:
    from datetime import datetime

    created_dt = None
    if getattr(aluno, "created_at", None) is not None:
        try:
            c = aluno.created_at  # type: ignore[attr-defined]
            if hasattr(c, "year"):
                # date or datetime -> ternary
                created_dt = (
                    c  # type: ignore[assignment]
                    if hasattr(c, "hour")
                    else datetime.combine(c, datetime.min.time())  # type: ignore[arg-type]
                )
        except Exception:
            created_dt = None
    # se tiver created_dt, passa; senão deixa server_default (now)
    if created_dt is not None:
        return AlunoModel(
            id=aluno.id,
            nome=aluno.nome,
            cpf=aluno.cpf,
            data_nasc=aluno.data_nasc,
            telefone=aluno.telefone,
            email=aluno.email,
            status=aluno.status.value
            if isinstance(aluno.status, StatusAluno)
            else str(aluno.status),
            observacoes=aluno.observacoes,
            endereco=aluno.endereco,
            bloqueado_manual=bool(aluno.bloqueado_manual),
            senha=aluno.senha,
            foto=getattr(aluno, "foto", None),
            created_at=created_dt,
        )
    return AlunoModel(
        id=aluno.id,
        nome=aluno.nome,
        cpf=aluno.cpf,
        data_nasc=aluno.data_nasc,
        telefone=aluno.telefone,
        email=aluno.email,
        status=aluno.status.value if isinstance(aluno.status, StatusAluno) else str(aluno.status),
        observacoes=aluno.observacoes,
        endereco=aluno.endereco,
        bloqueado_manual=bool(aluno.bloqueado_manual),
        senha=aluno.senha,
        foto=getattr(aluno, "foto", None),
    )


class AlunoRepositorySQLAlchemy:
    """Impl SQLAlchemy — injeção de Session."""

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

    def salvar(self, aluno: Aluno) -> Aluno:
        self._ensure_clean()
        try:
            existing = self.session.get(AlunoModel, aluno.id)
            if existing is None:
                model = _domain_to_model(aluno)
                self.session.add(model)
            else:
                existing.nome = aluno.nome
                existing.cpf = aluno.cpf
                existing.data_nasc = aluno.data_nasc
                existing.telefone = aluno.telefone
                existing.email = aluno.email
                existing.status = (
                    aluno.status.value
                    if isinstance(aluno.status, StatusAluno)
                    else str(aluno.status)
                )
                existing.observacoes = aluno.observacoes
                existing.endereco = aluno.endereco
                existing.bloqueado_manual = bool(aluno.bloqueado_manual)
                existing.senha = aluno.senha
                existing.foto = getattr(aluno, "foto", None)
        except Exception:
            try:
                self.session.rollback()
            except Exception:
                pass
            raise
        return aluno

    def buscar_por_id(self, aluno_id: str) -> Aluno | None:
        self._ensure_clean()
        try:
            m = self.session.get(AlunoModel, aluno_id)
            return _model_to_domain(m) if m else None
        except Exception as e:
            from sqlalchemy.exc import PendingRollbackError

            if isinstance(e, PendingRollbackError):
                try:
                    self.session.rollback()
                except Exception:
                    pass
                m = self.session.get(AlunoModel, aluno_id)
                return _model_to_domain(m) if m else None
            raise

    def buscar_por_cpf(self, cpf: str) -> Aluno | None:
        self._ensure_clean()
        try:
            digits = "".join(c for c in cpf if c.isdigit())
            stmt = select(AlunoModel).where(AlunoModel.cpf.isnot(None))
            for row in self.session.execute(stmt).scalars():
                if row.cpf and "".join(c for c in row.cpf if c.isdigit()) == digits:
                    return _model_to_domain(row)
            return None
        except Exception as e:
            from sqlalchemy.exc import PendingRollbackError

            if isinstance(e, PendingRollbackError):
                try:
                    self.session.rollback()
                except Exception:
                    pass
                digits = "".join(c for c in cpf if c.isdigit())
                stmt = select(AlunoModel).where(AlunoModel.cpf.isnot(None))
                for row in self.session.execute(stmt).scalars():
                    if row.cpf and "".join(c for c in row.cpf if c.isdigit()) == digits:
                        return _model_to_domain(row)
                return None
            raise

    def buscar_por_senha(self, senha: str) -> Aluno | None:
        """Lookup direto pelo PIN (texto) — Fase 4.8, sem varredura."""
        self._ensure_clean()
        try:
            codigo = senha.strip()
            if not codigo:
                return None
            stmt = select(AlunoModel).where(AlunoModel.senha == codigo)
            m = self.session.execute(stmt).scalars().first()
            return _model_to_domain(m) if m else None
        except Exception as e:
            from sqlalchemy.exc import PendingRollbackError

            if isinstance(e, PendingRollbackError):
                try:
                    self.session.rollback()
                except Exception:
                    pass
                codigo = senha.strip()
                if not codigo:
                    return None
                stmt = select(AlunoModel).where(AlunoModel.senha == codigo)
                m = self.session.execute(stmt).scalars().first()
                return _model_to_domain(m) if m else None
            raise

    def listar(self) -> list[Aluno]:
        self._ensure_clean()
        try:
            stmt = select(AlunoModel)
            return [_model_to_domain(m) for m in self.session.execute(stmt).scalars().all()]
        except Exception as e:
            from sqlalchemy.exc import PendingRollbackError

            if isinstance(e, PendingRollbackError):
                try:
                    self.session.rollback()
                except Exception:
                    pass
                stmt = select(AlunoModel)
                return [_model_to_domain(m) for m in self.session.execute(stmt).scalars().all()]
            raise

    def mapa_nomes(self, ids: list[str]) -> dict[str, str]:
        if not ids:
            return {}
        self._ensure_clean()
        try:
            stmt = select(AlunoModel.id, AlunoModel.nome).where(AlunoModel.id.in_(ids))
            return {str(r[0]): str(r[1]) for r in self.session.execute(stmt).all()}
        except Exception as e:
            from sqlalchemy.exc import PendingRollbackError

            if isinstance(e, PendingRollbackError):
                try:
                    self.session.rollback()
                except Exception:
                    pass
                stmt = select(AlunoModel.id, AlunoModel.nome).where(AlunoModel.id.in_(ids))
                return {str(r[0]): str(r[1]) for r in self.session.execute(stmt).all()}
            raise

    def listar_ordenado(
        self, limit: int | None = None, offset: int = 0, busca: str | None = None
    ) -> list[Aluno]:
        self._ensure_clean()
        try:
            stmt = select(AlunoModel).order_by(func.lower(AlunoModel.nome))
            if busca and busca.strip():
                termo = f"%{busca.strip().lower()}%"
                stmt = stmt.where(func.lower(AlunoModel.nome).like(termo))
            if limit is not None:
                stmt = stmt.limit(limit).offset(offset)
            elif offset:
                stmt = stmt.offset(offset)
            return [_model_to_domain(m) for m in self.session.execute(stmt).scalars().all()]
        except Exception as e:
            from sqlalchemy.exc import PendingRollbackError

            if isinstance(e, PendingRollbackError):
                try:
                    self.session.rollback()
                except Exception:
                    pass
                stmt = select(AlunoModel).order_by(func.lower(AlunoModel.nome))
                if busca and busca.strip():
                    termo = f"%{busca.strip().lower()}%"
                    stmt = stmt.where(func.lower(AlunoModel.nome).like(termo))
                if limit is not None:
                    stmt = stmt.limit(limit).offset(offset)
                elif offset:
                    stmt = stmt.offset(offset)
                return [_model_to_domain(m) for m in self.session.execute(stmt).scalars().all()]
            raise

    def remover(self, aluno_id: str) -> None:
        self._ensure_clean()
        try:
            m = self.session.get(AlunoModel, aluno_id)
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
            stmt = select(AlunoModel)
            return len(self.session.execute(stmt).scalars().all())
        except Exception as e:
            from sqlalchemy.exc import PendingRollbackError

            if isinstance(e, PendingRollbackError):
                try:
                    self.session.rollback()
                except Exception:
                    pass
                stmt = select(AlunoModel)
                return len(self.session.execute(stmt).scalars().all())
            raise

    def limpar(self) -> None:
        self._ensure_clean()
        try:
            self.session.query(AlunoModel).delete()
            self.session.flush()
        except Exception:
            try:
                self.session.rollback()
            except Exception:
                pass
            raise


# Mantido para fallback testes — re-exporta memória da Fase 1 se necessário
# (services/cadastrar_aluno.py também mantém sua versão)
class AlunoRepositoryMemoria:
    def __init__(self) -> None:
        self._alunos: dict[str, Aluno] = {}

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

    def mapa_nomes(self, ids: list[str]) -> dict[str, str]:
        if not ids:
            return {}
        ids_set = set(ids)
        return {a.id: a.nome for a in self._alunos.values() if a.id in ids_set}

    def listar_ordenado(
        self, limit: int | None = None, offset: int = 0, busca: str | None = None
    ) -> list[Aluno]:
        vals = list(self._alunos.values())
        if busca and busca.strip():
            termo = busca.strip().lower()
            vals = [a for a in vals if termo in a.nome.lower()]
        vals.sort(key=lambda a: a.nome.lower())
        if offset:
            vals = vals[offset:]
        if limit is not None:
            vals = vals[:limit]
        return vals

    def remover(self, aluno_id: str) -> None:
        self._alunos.pop(aluno_id, None)

    def total(self) -> int:
        return len(self._alunos)

    def limpar(self) -> None:
        self._alunos.clear()
