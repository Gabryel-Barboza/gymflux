"""Cobrança recorrente — geração otimizada de pendências mensais."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from gymflux.core.aluno import Aluno
from gymflux.core.pagamento import Pagamento
from gymflux.core.plano import Matricula, Plano, Vigencia
from gymflux.services.cobranca import aplicar_cobranca_mensal


class _Alunos:
    def __init__(self, alunos: list[Aluno]) -> None:
        self._a = {a.id: a for a in alunos}

    def listar(self) -> list[Aluno]:
        return list(self._a.values())

    def salvar(self, aluno: Aluno) -> Aluno:
        self._a[aluno.id] = aluno
        return aluno


class _Mats:
    def __init__(self, mats: list[Matricula]) -> None:
        self._m = list(mats)

    def listar(self) -> list[Matricula]:
        return list(self._m)


class _Pags:
    def __init__(self, pags: list[Pagamento] | None = None) -> None:
        self._p: dict[str, Pagamento] = {p.id: p for p in (pags or [])}

    def listar(self) -> list[Pagamento]:
        return list(self._p.values())

    def salvar(self, pag: Pagamento) -> Pagamento:
        self._p[pag.id] = pag
        return pag


def _aluno(aluno_id: str = "al-1") -> Aluno:
    return Aluno(id=aluno_id, nome="Aluno")


def _mat(aluno_id: str = "al-1", inicio: date = date(2026, 9, 1)) -> Matricula:
    plano = Plano.criar_mensal()
    return Matricula(
        aluno_id=aluno_id, plano=plano, vigencia=Vigencia(inicio, date(2026, 12, 31))
    )


def test_gera_pendente_quando_mes_atual_sem_pagamento() -> None:
    ref = date(2026, 9, 14)
    alunos = _Alunos([_aluno()])
    mats = _Mats([_mat(inicio=date(2026, 9, 1))])
    pags = _Pags(
        [
            Pagamento(
                id="pag-1",
                aluno_id="al-1",
                valor=Decimal("99.90"),
                data_vencimento=date(2026, 8, 10),
                data_pagamento=date(2026, 8, 9),
                competencia="2026-08",
            )
        ]
    )
    n = aplicar_cobranca_mensal(alunos, mats, pags, ref=ref)
    assert n == 1
    novos = [p for p in pags.listar() if p.competencia == "2026-09"]
    assert len(novos) == 1
    assert novos[0].data_pagamento is None
    assert novos[0].valor == Decimal("99.90")


def test_nao_duplica_quando_ja_tem_competencia() -> None:
    ref = date(2026, 9, 14)
    alunos = _Alunos([_aluno()])
    mats = _Mats([_mat()])
    pags = _Pags(
        [
            Pagamento(
                id="pag-1",
                aluno_id="al-1",
                valor=Decimal("99.90"),
                data_vencimento=date(2026, 9, 10),
                data_pagamento=None,
                competencia="2026-09",
            )
        ]
    )
    assert aplicar_cobranca_mensal(alunos, mats, pags, ref=ref) == 0
    assert len(pags.listar()) == 1


def test_plano_anual_nao_gera_todo_mes() -> None:
    ref = date(2026, 9, 14)
    alunos = _Alunos([_aluno()])
    plano_anual = Plano.criar_anual()
    mat = Matricula(
        aluno_id="al-1",
        plano=plano_anual,
        vigencia=Vigencia(date(2026, 1, 1), date(2026, 12, 31)),
    )
    pags = _Pags(
        [
            Pagamento(
                id="pag-1",
                aluno_id="al-1",
                valor=plano_anual.valor,
                data_vencimento=date(2026, 8, 10),
                data_pagamento=date(2026, 8, 9),
                competencia="2026-08",
            )
        ]
    )
    assert aplicar_cobranca_mensal(alunos, _Mats([mat]), pags, ref=ref) == 0


def test_pula_inativo_e_sem_matricula() -> None:
    from gymflux.core.aluno import StatusAluno

    ref = date(2026, 9, 14)
    a1 = Aluno(id="al-1", nome="A", status=StatusAluno.INATIVO)
    a2 = _aluno("al-2")
    alunos = _Alunos([a1, a2])
    mats = _Mats([_mat("al-1"), _mat("al-2")])
    pags = _Pags([])
    n = aplicar_cobranca_mensal(alunos, mats, pags, ref=ref)
    # só al-2 gera (al-1 inativo pula)
    assert n == 1
    assert {p.aluno_id for p in pags.listar()} == {"al-2"}


def test_trimestral_so_gera_a_cada_90d() -> None:
    ref_out = date(2026, 10, 14)
    ref_dez = date(2026, 12, 20)
    plano_tri = Plano.criar_trimestral()
    mat_tri = Matricula(aluno_id="al-1", plano=plano_tri, vigencia=Vigencia(date(2026, 9, 1), date(2026, 12, 31)))
    # último venc em Set
    pag_set = Pagamento(
        id="pag-set",
        aluno_id="al-1",
        valor=plano_tri.valor,
        data_vencimento=date(2026, 9, 10),
        data_pagamento=date(2026, 9, 10),
        competencia="2026-09",
    )
    # Outubro não deve gerar (34d <90)
    alunos = _Alunos([_aluno()])
    assert aplicar_cobranca_mensal(alunos, _Mats([mat_tri]), _Pags([pag_set]), ref=ref_out) == 0
    # Dezembro deve gerar (101d >=90)
    pags_dez = _Pags([pag_set])
    assert aplicar_cobranca_mensal(alunos, _Mats([mat_tri]), pags_dez, ref=ref_dez) == 1
    assert any(p.competencia == "2026-12" for p in pags_dez.listar())


def test_matricula_nao_gera_se_ja_tem_competencia() -> None:
    # garante idempotência da primeira cobrança (matricular gera, cobrança não duplica)
    ref = date(2026, 9, 14)
    alunos = _Alunos([_aluno()])
    mats = _Mats([_mat(inicio=date(2026, 9, 1))])
    # já existe pendente de Set
    pag_set = Pagamento(
        id="pag-set",
        aluno_id="al-1",
        valor=Decimal("99.90"),
        data_vencimento=date(2026, 9, 10),
        data_pagamento=None,
        competencia="2026-09",
    )
    assert aplicar_cobranca_mensal(alunos, mats, _Pags([pag_set]), ref=ref) == 0


def test_mensal_gera_no_mes_seguinte_se_vencido() -> None:
    # mensal pago em Ago, sem pagamento de Set → deve gerar Set
    ref = date(2026, 9, 14)
    pag_ago = Pagamento(
        id="pag-ago",
        aluno_id="al-1",
        valor=Decimal("99.90"),
        data_vencimento=date(2026, 8, 10),
        data_pagamento=date(2026, 8, 9),
        competencia="2026-08",
    )
    alunos = _Alunos([_aluno()])
    mats = _Mats([_mat(inicio=date(2026, 9, 1))])
    pags = _Pags([pag_ago])
    assert aplicar_cobranca_mensal(alunos, mats, pags, ref=ref) == 1
    assert any(p.competencia == "2026-09" for p in pags.listar())
