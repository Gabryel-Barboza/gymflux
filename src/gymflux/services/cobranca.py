"""Cobrança recorrente — gera pendências mensais automaticamente (startup).

Regra operacional (NÃO é RB01-RB05): para cada aluno ATIVO com matrícula
ativa e vigente, se o mês atual (competência ``YYYY-MM``) ainda não tem
pagamento e o intervalo do plano já venceu desde o último vencimento,
cria um ``Pagamento`` pendente (``data_pagamento=None``) com
``valor=plano.valor``, ``vencimento=dia 10`` e ``competencia=YYYY-MM``.

Exemplo do dono: plano MENSAL (30d) com último pagamento mês passado
→ este mês ganha um pendente. Plano ANUAL (365d) pago mês passado
→ não gera nada este mês.

Otimizado para o startup: 3 listagens (alunos, matrículas, pagamentos)
+ agrupamento em memória, sem N+1 e sem commit próprio (padrão Fase 4.1:
quem chama commita). Nunca aborta a varredura por causa de um aluno.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Protocol

from loguru import logger

from gymflux.core.aluno import Aluno
from gymflux.core.pagamento import Pagamento
from gymflux.core.plano import Matricula


class _AlunoRepoProto(Protocol):
    def listar(self) -> list[Aluno]: ...


class _MatriculaRepoProto(Protocol):
    def listar(self) -> list[Matricula]: ...


class _PagamentoRepoProto(Protocol):
    def listar(self) -> list[Pagamento]: ...
    def salvar(self, pagamento: Pagamento) -> Pagamento | None: ...


def _competencia(ref: date) -> str:
    return ref.strftime("%Y-%m")


def _vencimento_competencia(ref: date, dia: int = 10) -> date:
    return date(ref.year, ref.month, dia)


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
    comp_atual = _competencia(hoje)
    venc_atual = _vencimento_competencia(hoje)

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
            # só matrículas ativas e vigentes no mês atual (original)
            # evita cobrar mensalmente quem tem plano trimestral/anual expirado
            # ou ainda não vigente — respeita vigência + duracao
            vigentes = [m for m in mats if m.ativa and m.vigencia.contem(hoje)]
            if not vigentes:
                continue
            # usa a vigência mais recente como referência de plano/valor
            mat = max(vigentes, key=lambda m: m.vigencia.inicio)
            if comp_atual in comps_por_aluno.get(aluno.id, set()):
                continue
            duracao = max(1, int(mat.plano.duracao_dias))
            ult = ultimo_venc.get(aluno.id)
            # só gera se o ciclo do plano já virou desde o último vencimento
            if ult is not None and (hoje - ult).days < duracao:
                continue
            # sem pagamentos anteriores: gera para o mês atual (primeira cobrança)
            novo = Pagamento(
                id=f"pag-{uuid.uuid4().hex[:8]}",
                aluno_id=aluno.id,
                valor=mat.plano.valor,
                data_vencimento=venc_atual,
                data_pagamento=None,
                forma=None,
                competencia=comp_atual,
            )
            pagamento_repo.salvar(novo)
            criados += 1
            logger.info(
                f"[Cobrança] pendente {comp_atual} aluno={aluno.id} "
                f"plano={mat.plano.nome} valor={mat.plano.valor}"
            )
        except Exception as e:
            logger.warning(f"[Cobrança] aluno {aluno.id} pulado ({e})")
            continue
    return criados
