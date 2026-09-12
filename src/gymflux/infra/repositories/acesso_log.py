"""AcessoLogRepository — Protocol + SQLAlchemy."""

from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from gymflux.core.acesso import DirecaoAcesso, ResultadoAcesso, TentativaAcesso
from gymflux.infra.models.acesso_log import AcessoLogModel


class AcessoLogRepository(Protocol):
    def registrar(self, tentativa: TentativaAcesso) -> TentativaAcesso: ...
    def listar_por_aluno(self, aluno_id: str) -> list[TentativaAcesso]: ...
    def buscar_ultimo_por_aluno(self, aluno_id: str) -> TentativaAcesso | None: ...
    def listar(self) -> list[TentativaAcesso]: ...
    def total(self) -> int: ...
    def limpar(self) -> None: ...


def _model_to_domain(m: AcessoLogModel) -> TentativaAcesso:
    direcao = (
        DirecaoAcesso(m.direcao)
        if m.direcao in DirecaoAcesso._value2member_map_
        else DirecaoAcesso.ENTRADA
    )
    resultado = (
        ResultadoAcesso(m.resultado)
        if m.resultado in ResultadoAcesso._value2member_map_
        else ResultadoAcesso.LIBERADO
    )
    return TentativaAcesso(
        aluno_id=m.aluno_id,
        direcao=direcao,
        timestamp=m.timestamp,
        resultado=resultado,
        motivo=m.motivo,
        detalhes=m.detalhes,
        catraca_id=m.catraca_id,
        timeout_giro_s=m.timeout,
        funcionario_id=m.funcionario_id,
    )


def _domain_to_model(t: TentativaAcesso, log_id: str | None = None) -> AcessoLogModel:
    lid = log_id or str(uuid.uuid4())
    return AcessoLogModel(
        id=lid,
        aluno_id=t.aluno_id,
        funcionario_id=t.funcionario_id,
        timestamp=t.timestamp,
        direcao=t.direcao.value if isinstance(t.direcao, DirecaoAcesso) else str(t.direcao),
        resultado=t.resultado.value
        if isinstance(t.resultado, ResultadoAcesso)
        else str(t.resultado),
        motivo=str(t.motivo) if t.motivo else None,
        detalhes=t.detalhes,
        catraca_id=t.catraca_id,
        timeout=t.timeout_giro_s,
    )


class AcessoLogRepositorySQLAlchemy:
    def __init__(self, session: Session) -> None:
        self.session = session

    def registrar(self, tentativa: TentativaAcesso) -> TentativaAcesso:
        model = _domain_to_model(tentativa)
        self.session.add(model)
        self.session.flush()
        return tentativa

    def registrar_com_id(self, log_id: str, tentativa: TentativaAcesso) -> TentativaAcesso:
        model = _domain_to_model(tentativa, log_id=log_id)
        self.session.add(model)
        self.session.flush()
        return tentativa

    def listar_por_aluno(self, aluno_id: str) -> list[TentativaAcesso]:
        stmt = (
            select(AcessoLogModel)
            .where(AcessoLogModel.aluno_id == aluno_id)
            .order_by(AcessoLogModel.timestamp)
        )
        return [_model_to_domain(m) for m in self.session.execute(stmt).scalars().all()]

    def listar(self) -> list[TentativaAcesso]:
        stmt = select(AcessoLogModel).order_by(AcessoLogModel.timestamp)
        return [_model_to_domain(m) for m in self.session.execute(stmt).scalars().all()]

    def total(self) -> int:
        stmt = select(AcessoLogModel)
        return len(self.session.execute(stmt).scalars().all())

    def limpar(self) -> None:
        self.session.query(AcessoLogModel).delete()
        self.session.flush()

    def buscar_ultimo_por_aluno(self, aluno_id: str) -> TentativaAcesso | None:
        stmt = (
            select(AcessoLogModel)
            .where(AcessoLogModel.aluno_id == aluno_id)
            .order_by(AcessoLogModel.timestamp.desc())
            .limit(1)
        )
        m = self.session.execute(stmt).scalars().first()
        return _model_to_domain(m) if m else None


class AcessoLogRepositoryMemoria:
    def __init__(self) -> None:
        self._logs: list[TentativaAcesso] = []

    def registrar(self, tentativa: TentativaAcesso) -> TentativaAcesso:
        self._logs.append(tentativa)
        return tentativa

    def listar_por_aluno(self, aluno_id: str) -> list[TentativaAcesso]:
        return [t for t in self._logs if t.aluno_id == aluno_id]

    def buscar_ultimo_por_aluno(self, aluno_id: str) -> TentativaAcesso | None:
        logs = self.listar_por_aluno(aluno_id)
        if not logs:
            return None
        return max(logs, key=lambda t: t.timestamp)

    def listar(self) -> list[TentativaAcesso]:
        return list(self._logs)

    def total(self) -> int:
        return len(self._logs)

    def limpar(self) -> None:
        self._logs.clear()
