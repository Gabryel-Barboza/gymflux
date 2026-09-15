"""AvaliacaoFisicaRepository — SQL + memória."""

from __future__ import annotations

import json
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from gymflux.core.ficha import AvaliacaoFisica
from gymflux.infra.models.avaliacao_fisica import AvaliacaoFisicaModel


class AvaliacaoRepository(Protocol):
    def salvar(self, avaliacao: AvaliacaoFisica) -> AvaliacaoFisica: ...
    def buscar_por_id(self, avaliacao_id: str) -> AvaliacaoFisica | None: ...
    def listar_por_aluno(self, aluno_id: str) -> list[AvaliacaoFisica]: ...
    def listar(self) -> list[AvaliacaoFisica]: ...
    def remover(self, avaliacao_id: str) -> None: ...


def _model_to_domain(m: AvaliacaoFisicaModel) -> AvaliacaoFisica:
    medidas = {}
    if m.medidas:
        try:
            medidas = json.loads(m.medidas)
            if not isinstance(medidas, dict):
                medidas = {}
        except (json.JSONDecodeError, TypeError):
            medidas = {}
    # normaliza valores para float
    norm: dict[str, float] = {}
    for k, v in medidas.items():
        try:
            norm[str(k)] = float(v)
        except (TypeError, ValueError):
            continue
    return AvaliacaoFisica(
        id=m.id,
        aluno_id=m.aluno_id,
        data=m.data,
        peso_kg=m.peso_kg,
        altura_cm=m.altura_cm,
        gordura_pct=m.gordura_pct,
        medidas=norm,
        problemas_saude=m.problemas_saude,
        restricoes=m.restricoes,
        medicamentos=m.medicamentos,
        contato_emergencia=m.contato_emergencia,
    )


def _domain_to_model(a: AvaliacaoFisica) -> AvaliacaoFisicaModel:
    medidas_json = None
    if a.medidas:
        try:
            medidas_json = json.dumps(a.medidas, ensure_ascii=False)
        except (TypeError, ValueError):
            medidas_json = None
    return AvaliacaoFisicaModel(
        id=a.id,
        aluno_id=a.aluno_id,
        data=a.data,
        peso_kg=a.peso_kg,
        altura_cm=a.altura_cm,
        gordura_pct=a.gordura_pct,
        medidas=medidas_json,
        problemas_saude=a.problemas_saude,
        restricoes=a.restricoes,
        medicamentos=a.medicamentos,
        contato_emergencia=a.contato_emergencia,
    )


class AvaliacaoFisicaRepositorySQLAlchemy:
    def __init__(self, session: Session) -> None:
        self.session = session

    def salvar(self, avaliacao: AvaliacaoFisica) -> AvaliacaoFisica:
        existing = self.session.get(AvaliacaoFisicaModel, avaliacao.id)
        if existing is None:
            model = _domain_to_model(avaliacao)
            self.session.add(model)
        else:
            # atualiza
            existing.aluno_id = avaliacao.aluno_id
            existing.data = avaliacao.data
            existing.peso_kg = avaliacao.peso_kg
            existing.altura_cm = avaliacao.altura_cm
            existing.gordura_pct = avaliacao.gordura_pct
            try:
                existing.medidas = (
                    json.dumps(avaliacao.medidas, ensure_ascii=False) if avaliacao.medidas else None
                )
            except (TypeError, ValueError):
                existing.medidas = None
            existing.problemas_saude = avaliacao.problemas_saude
            existing.restricoes = avaliacao.restricoes
            existing.medicamentos = avaliacao.medicamentos
            existing.contato_emergencia = avaliacao.contato_emergencia
        self.session.flush()
        return avaliacao

    def buscar_por_id(self, avaliacao_id: str) -> AvaliacaoFisica | None:
        m = self.session.get(AvaliacaoFisicaModel, avaliacao_id)
        return _model_to_domain(m) if m else None

    def listar_por_aluno(self, aluno_id: str) -> list[AvaliacaoFisica]:
        stmt = (
            select(AvaliacaoFisicaModel)
            .where(AvaliacaoFisicaModel.aluno_id == aluno_id)
            .order_by(AvaliacaoFisicaModel.data.desc())
        )
        return [_model_to_domain(m) for m in self.session.execute(stmt).scalars().all()]

    def listar(self) -> list[AvaliacaoFisica]:
        stmt = select(AvaliacaoFisicaModel).order_by(AvaliacaoFisicaModel.data.desc())
        return [_model_to_domain(m) for m in self.session.execute(stmt).scalars().all()]

    def remover(self, avaliacao_id: str) -> None:
        m = self.session.get(AvaliacaoFisicaModel, avaliacao_id)
        if m:
            self.session.delete(m)
            self.session.flush()


class AvaliacaoFisicaRepositoryMemoria:
    def __init__(self) -> None:
        self._dados: dict[str, AvaliacaoFisica] = {}

    def salvar(self, avaliacao: AvaliacaoFisica) -> AvaliacaoFisica:
        self._dados[avaliacao.id] = avaliacao
        return avaliacao

    def buscar_por_id(self, avaliacao_id: str) -> AvaliacaoFisica | None:
        return self._dados.get(avaliacao_id)

    def listar_por_aluno(self, aluno_id: str) -> list[AvaliacaoFisica]:
        lst = [a for a in self._dados.values() if a.aluno_id == aluno_id]
        return sorted(lst, key=lambda a: a.data, reverse=True)

    def listar(self) -> list[AvaliacaoFisica]:
        return sorted(self._dados.values(), key=lambda a: a.data, reverse=True)

    def remover(self, avaliacao_id: str) -> None:
        self._dados.pop(avaliacao_id, None)
