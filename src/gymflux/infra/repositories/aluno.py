"""AlunoRepository — Protocol + SQLAlchemy impl + Memória fallback."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from gymflux.core.aluno import Aluno, StatusAluno
from gymflux.infra.models.aluno import AlunoModel


class AlunoRepository(Protocol):
    def salvar(self, aluno: Aluno) -> Aluno: ...
    def buscar_por_id(self, aluno_id: str) -> Aluno | None: ...
    def buscar_por_cpf(self, cpf: str) -> Aluno | None: ...
    def buscar_por_cartao(self, cartao_id: str) -> Aluno | None: ...
    def listar(self) -> list[Aluno]: ...
    def remover(self, aluno_id: str) -> None: ...
    def total(self) -> int: ...


def _model_to_domain(m: AlunoModel) -> Aluno:
    # cpf já vem como string ou None
    status = (
        StatusAluno(m.status) if m.status in StatusAluno._value2member_map_ else StatusAluno.ATIVO
    )
    return Aluno(
        id=m.id,
        nome=m.nome,
        cpf=m.cpf,
        data_nasc=m.data_nasc,
        telefone=m.telefone,
        email=m.email,
        status=status,
        observacoes=m.observacoes,
        bloqueado_manual=bool(m.bloqueado_manual),
        senha_hash=m.senha_hash,
        cartao_id=m.cartao_id,
    )


def _domain_to_model(aluno: Aluno) -> AlunoModel:
    return AlunoModel(
        id=aluno.id,
        nome=aluno.nome,
        cpf=aluno.cpf,
        data_nasc=aluno.data_nasc,
        telefone=aluno.telefone,
        email=aluno.email,
        status=aluno.status.value if isinstance(aluno.status, StatusAluno) else str(aluno.status),
        observacoes=aluno.observacoes,
        bloqueado_manual=bool(aluno.bloqueado_manual),
        senha_hash=aluno.senha_hash,
        cartao_id=aluno.cartao_id,
    )


class AlunoRepositorySQLAlchemy:
    """Impl SQLAlchemy — injeção de Session."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def salvar(self, aluno: Aluno) -> Aluno:
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
                aluno.status.value if isinstance(aluno.status, StatusAluno) else str(aluno.status)
            )
            existing.observacoes = aluno.observacoes
            existing.bloqueado_manual = bool(aluno.bloqueado_manual)
            existing.senha_hash = aluno.senha_hash
            existing.cartao_id = aluno.cartao_id
        self.session.flush()
        return aluno

    def buscar_por_id(self, aluno_id: str) -> Aluno | None:
        m = self.session.get(AlunoModel, aluno_id)
        return _model_to_domain(m) if m else None

    def buscar_por_cpf(self, cpf: str) -> Aluno | None:
        digits = "".join(c for c in cpf if c.isdigit())
        # busca normalizada: compara digits
        # como DB armazena cpf como está, fazemos loop ou like
        # para performance aceitável em <5k registros, busca via SQL + filtra
        stmt = select(AlunoModel).where(AlunoModel.cpf.isnot(None))
        for row in self.session.execute(stmt).scalars():
            if row.cpf and "".join(c for c in row.cpf if c.isdigit()) == digits:
                return _model_to_domain(row)
        return None

    def buscar_por_cartao(self, cartao_id: str) -> Aluno | None:
        cid = cartao_id.strip()
        if not cid:
            return None
        stmt = select(AlunoModel).where(AlunoModel.cartao_id == cid)
        m = self.session.execute(stmt).scalars().first()
        return _model_to_domain(m) if m else None

    def listar(self) -> list[Aluno]:
        stmt = select(AlunoModel)
        return [_model_to_domain(m) for m in self.session.execute(stmt).scalars().all()]

    def remover(self, aluno_id: str) -> None:
        m = self.session.get(AlunoModel, aluno_id)
        if m:
            self.session.delete(m)
            self.session.flush()

    def total(self) -> int:
        stmt = select(AlunoModel)
        return len(self.session.execute(stmt).scalars().all())

    def limpar(self) -> None:
        self.session.query(AlunoModel).delete()
        self.session.flush()


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

    def buscar_por_cartao(self, cartao_id: str) -> Aluno | None:
        cid = cartao_id.strip()
        if not cid:
            return None
        for a in self._alunos.values():
            if a.cartao_id == cid:
                return a
        return None

    def listar(self) -> list[Aluno]:
        return list(self._alunos.values())

    def remover(self, aluno_id: str) -> None:
        self._alunos.pop(aluno_id, None)

    def total(self) -> int:
        return len(self._alunos)

    def limpar(self) -> None:
        self._alunos.clear()
