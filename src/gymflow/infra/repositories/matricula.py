"""MatriculaRepository — Protocol + SQLAlchemy."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from gymflow.core.plano import Matricula, Plano, TipoPlano, Vigencia
from gymflow.infra.models.matricula import MatriculaModel
from gymflow.infra.models.plano import PlanoModel


class MatriculaRepository(Protocol):
    def salvar(self, matricula: Matricula, matricula_id: str | None = None) -> Matricula: ...
    def buscar_por_id(self, matricula_id: str) -> Matricula | None: ...
    def listar_por_aluno(self, aluno_id: str) -> list[Matricula]: ...
    def buscar_vigente(self, aluno_id: str, data: date) -> Matricula | None: ...
    def listar(self) -> list[Matricula]: ...
    def remover(self, matricula_id: str) -> None: ...


def _model_to_domain(m: MatriculaModel, plano: Plano | None = None) -> Matricula:
    # plano deve ser carregado via PlanoModel se não fornecido
    vigencia = Vigencia(inicio=m.inicio, fim=m.fim)
    # se plano não fornecido, cria stub; idealmente repo carrega plano
    if plano is None:
        # fallback: tenta criar plano mínimo a partir do FK; mas sem dados completos
        # para testes, buscamos via sessão externa se possível
        raise ValueError("plano não carregado para converter MatriculaModel -> Matricula")
    mat = Matricula(aluno_id=m.aluno_id, plano=plano, vigencia=vigencia, ativa=bool(m.ativa))
    return mat


class MatriculaRepositorySQLAlchemy:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _get_plano_domain(self, plano_id: str) -> Plano | None:
        pm = self.session.get(PlanoModel, plano_id)
        if not pm:
            return None
        tipo = (
            TipoPlano(pm.tipo)
            if pm.tipo in TipoPlano._value2member_map_
            else TipoPlano.PERSONALIZADO
        )
        return Plano(
            id=pm.id,
            nome=pm.nome,
            duracao_dias=int(pm.duracao_dias),
            valor=Decimal(str(pm.valor)),
            tolerancia_dias=int(pm.tolerancia_dias),
            tipo=tipo,
        )

    def salvar(self, matricula: Matricula, matricula_id: str | None = None) -> Matricula:
        # id handling: domain Matricula não tem id, então usa matricula_id ou gera uuid
        mid = matricula_id or str(uuid.uuid4())
        # tenta buscar existente se id fornecido e já existe
        existing = self.session.get(MatriculaModel, mid) if matricula_id else None
        # se não tem id mas já existe matricula para aluno+plano? não deduplica, cria nova
        if existing is None:
            # verifica se matricula_id corresponde a existente, senão cria
            # se matricula_id None, cria novo
            model = MatriculaModel(
                id=mid,
                aluno_id=matricula.aluno_id,
                plano_id=matricula.plano.id,
                inicio=matricula.vigencia.inicio,
                fim=matricula.vigencia.fim,
                ativa=bool(matricula.ativa),
            )
            self.session.add(model)
        else:
            existing.aluno_id = matricula.aluno_id
            existing.plano_id = matricula.plano.id
            existing.inicio = matricula.vigencia.inicio
            existing.fim = matricula.vigencia.fim
            existing.ativa = bool(matricula.ativa)
        self.session.flush()
        return matricula

    def salvar_com_id(self, matricula_id: str, matricula: Matricula) -> Matricula:
        return self.salvar(matricula, matricula_id=matricula_id)

    def buscar_por_id(self, matricula_id: str) -> Matricula | None:
        m = self.session.get(MatriculaModel, matricula_id)
        if not m:
            return None
        plano = self._get_plano_domain(m.plano_id)
        if not plano:
            return None
        vigencia = Vigencia(inicio=m.inicio, fim=m.fim)
        return Matricula(aluno_id=m.aluno_id, plano=plano, vigencia=vigencia, ativa=bool(m.ativa))

    def listar_por_aluno(self, aluno_id: str) -> list[Matricula]:
        stmt = select(MatriculaModel).where(MatriculaModel.aluno_id == aluno_id)
        result: list[Matricula] = []
        for m in self.session.execute(stmt).scalars().all():
            plano = self._get_plano_domain(m.plano_id)
            if plano:
                vigencia = Vigencia(inicio=m.inicio, fim=m.fim)
                result.append(
                    Matricula(
                        aluno_id=m.aluno_id, plano=plano, vigencia=vigencia, ativa=bool(m.ativa)
                    )
                )
        return result

    def buscar_vigente(self, aluno_id: str, data: date) -> Matricula | None:
        # Busca matriculas ativas do aluno e filtra por vigência em memória (simples) ou SQL
        stmt = select(MatriculaModel).where(
            MatriculaModel.aluno_id == aluno_id,
            MatriculaModel.ativa.is_(True),
            MatriculaModel.inicio <= data,
            MatriculaModel.fim >= data,
        )
        m = self.session.execute(stmt).scalars().first()
        if not m:
            return None
        plano = self._get_plano_domain(m.plano_id)
        if not plano:
            return None
        vigencia = Vigencia(inicio=m.inicio, fim=m.fim)
        return Matricula(aluno_id=m.aluno_id, plano=plano, vigencia=vigencia, ativa=bool(m.ativa))

    def listar(self) -> list[Matricula]:
        stmt = select(MatriculaModel)
        result: list[Matricula] = []
        for m in self.session.execute(stmt).scalars().all():
            plano = self._get_plano_domain(m.plano_id)
            if plano:
                vigencia = Vigencia(inicio=m.inicio, fim=m.fim)
                result.append(
                    Matricula(
                        aluno_id=m.aluno_id, plano=plano, vigencia=vigencia, ativa=bool(m.ativa)
                    )
                )
        return result

    def remover(self, matricula_id: str) -> None:
        m = self.session.get(MatriculaModel, matricula_id)
        if m:
            self.session.delete(m)
            self.session.flush()

    def total(self) -> int:
        stmt = select(MatriculaModel)
        return len(self.session.execute(stmt).scalars().all())

    def limpar(self) -> None:
        self.session.query(MatriculaModel).delete()
        self.session.flush()


class MatriculaRepositoryMemoria:
    def __init__(self) -> None:
        self._matriculas: dict[str, Matricula] = {}
        self._ids: dict[str, str] = {}  # map id -> key

    def salvar(self, matricula: Matricula, matricula_id: str | None = None) -> Matricula:
        mid = matricula_id or str(uuid.uuid4())
        self._matriculas[mid] = matricula
        self._ids[mid] = mid
        return matricula

    def buscar_por_id(self, matricula_id: str) -> Matricula | None:
        return self._matriculas.get(matricula_id)

    def listar_por_aluno(self, aluno_id: str) -> list[Matricula]:
        return [m for m in self._matriculas.values() if m.aluno_id == aluno_id]

    def buscar_vigente(self, aluno_id: str, data: date) -> Matricula | None:
        for m in self._matriculas.values():
            if m.aluno_id == aluno_id and m.vigente_em(data):
                return m
        return None

    def listar(self) -> list[Matricula]:
        return list(self._matriculas.values())

    def remover(self, matricula_id: str) -> None:
        self._matriculas.pop(matricula_id, None)

    def total(self) -> int:
        return len(self._matriculas)

    def limpar(self) -> None:
        self._matriculas.clear()
