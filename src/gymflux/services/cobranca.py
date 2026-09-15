"""Cobrança recorrente — vencimento ancorado no dia da matrícula (Fase 4.15).

Regra operacional (NÃO é RB01-RB05): para cada aluno ATIVO com matrícula
ativa e vigente, o vencimento do mês é ``vencimento_no_mes(hoje.ano,
hoje.mês, dia_base)`` onde ``dia_base = mat.vigencia.inicio.day``
(com clamp via ``calendar.monthrange``: dia 31 em fev → 28/29). Se
``venc_mes > hoje``, ainda não venceu este mês → pula. Se a
competência ``venc_mes YYYY-MM`` já tem pagamento ou o ciclo
``(venc_mes - ultimo_venc).days < duracao`` não venceu, pula. Senão
cria ``Pagamento`` pendente com ``vencimento=venc_mes`` e
``competencia=venc_mes``.

Ex: matrícula dia 10 trimestral paga em Set → Out/Nov pulam, Dez gera;
matrícula dia 31 em Jan → venc fev 28 (clamp).

Otimizado para startup: 3 listagens + agrupamento em memória, sem N+1.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Protocol

from loguru import logger

from gymflux.core.aluno import Aluno
from gymflux.core.pagamento import Pagamento
from gymflux.core.plano import Matricula, vencimento_no_mes


class _AlunoRepoProto(Protocol):
    def listar(self) -> list[Aluno]: ...


class _MatriculaRepoProto(Protocol):
    def listar(self) -> list[Matricula]: ...


class _PagamentoRepoProto(Protocol):
    def listar(self) -> list[Pagamento]: ...
    def salvar(self, pagamento: Pagamento) -> Pagamento | None: ...


def _competencia(ref: date) -> str:
    return ref.strftime("%Y-%m")


def _mes_de(p: Pagamento) -> str:
    return p.competencia or p.data_vencimento.strftime("%Y-%m")


def aplicar_cobranca_mensal(
    aluno_repo: _AlunoRepoProto,
    matricula_repo: _MatriculaRepoProto,
    pagamento_repo: _PagamentoRepoProto,
    ref: date | None = None,
) -> int:
    """Varre alunos e cria pendências do mês atual. Retorna qtd criada."""
    hoje = ref or date.today()

    try:
        alunos = aluno_repo.listar()
    except Exception as e:
        logger.warning(f"[Cobrança] listar alunos falhou ({e})")
        return 0
    try:
        matriculas = matricula_repo.listar()
    except Exception as e:
        logger.warning(f"[Cobrança] listar matrículas falhou ({e})")
        return 0
    try:
        pagamentos = pagamento_repo.listar()
    except Exception as e:
        logger.warning(f"[Cobrança] listar pagamentos falhou ({e})")
        return 0

    mats_por_aluno: dict[str, list[Matricula]] = {}
    for m in matriculas:
        mats_por_aluno.setdefault(m.aluno_id, []).append(m)

    comps_por_aluno: dict[str, set[str]] = {}
    ultimo_venc: dict[str, date] = {}
    for p in pagamentos:
        comps_por_aluno.setdefault(p.aluno_id, set()).add(_mes_de(p))
        prev = ultimo_venc.get(p.aluno_id)
        if prev is None or p.data_vencimento > prev:
            ultimo_venc[p.aluno_id] = p.data_vencimento

    criados = 0
    for aluno in alunos:
        try:
            if not aluno.esta_ativo:
                continue
            mats = mats_por_aluno.get(aluno.id, [])
            vigentes = [m for m in mats if m.ativa and m.vigencia.contem(hoje)]
            if not vigentes:
                continue
            mat = max(vigentes, key=lambda m: m.vigencia.inicio)
            # vencimento ancorado no dia da matrícula
            try:
                venc_mes = vencimento_no_mes(hoje.year, hoje.month, mat.vigencia.inicio.day)
            except ValueError:
                continue
            if venc_mes > hoje:
                continue
            comp_venc = _competencia(venc_mes)
            if comp_venc in comps_por_aluno.get(aluno.id, set()):
                continue
            duracao = max(1, int(mat.plano.duracao_dias))
            ult = ultimo_venc.get(aluno.id)
            if ult is not None and (venc_mes - ult).days < duracao:
                continue
            novo = Pagamento(
                id=f"pag-{uuid.uuid4().hex[:8]}",
                aluno_id=aluno.id,
                valor=mat.plano.valor,
                data_vencimento=venc_mes,
                data_pagamento=None,
                forma=None,
                competencia=comp_venc,
            )
            pagamento_repo.salvar(novo)
            criados += 1
            logger.info(
                f"[Cobrança] pendente {comp_venc} aluno={aluno.id} "
                f"plano={mat.plano.nome} venc={venc_mes} valor={mat.plano.valor}"
            )
        except Exception as e:
            logger.warning(f"[Cobrança] aluno {aluno.id} pulado ({e})")
            continue
    return criados
