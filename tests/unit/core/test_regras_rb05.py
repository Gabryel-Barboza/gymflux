"""RB05 anti-passback + compat pode_acessar + precedência RB03 (autocontido)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from gymflow.core.acesso import DirecaoAcesso, MotivoNegado
from gymflow.core.aluno import Aluno, StatusAluno
from gymflow.core.pagamento import Pagamento
from gymflow.core.plano import Matricula, Plano, Vigencia
from gymflow.core.regras import RegraAcesso, RegraAcessoConfig

HOJE = date(2026, 9, 11)
VIG_INICIO = date(2026, 8, 11)
VIG_FIM = date(2026, 9, 20)


def _aluno(
    id_: str = "a1", status: StatusAluno = StatusAluno.ATIVO, bloqueado: bool = False
) -> Aluno:
    return Aluno(id=id_, nome="João Silva", status=status, bloqueado_manual=bloqueado)


def _plano(tolerancia: int = 3) -> Plano:
    return Plano(
        id="p1", nome="Mensal", duracao_dias=30, valor=Decimal("99.90"), tolerancia_dias=tolerancia
    )


def _matricula(aluno_id: str, plano: Plano, vigencia: Vigencia, ativa: bool = True) -> Matricula:
    return Matricula(aluno_id=aluno_id, plano=plano, vigencia=vigencia, ativa=ativa)


def _pg(id_: str, aluno_id: str, venc: date, pag: date | None) -> Pagamento:
    return Pagamento(
        id=id_, aluno_id=aluno_id, valor=Decimal("99.90"), data_vencimento=venc, data_pagamento=pag
    )


def _vigencia(inicio: date, fim: date) -> Vigencia:
    return Vigencia(inicio=inicio, fim=fim)


def test_rb05_anti_passback_bloqueia_entrada_repetida():
    regra = RegraAcesso(RegraAcessoConfig(anti_passback=True))
    aluno = _aluno()
    matricula = _matricula(aluno.id, _plano(), _vigencia(VIG_INICIO, VIG_FIM))
    pagamentos = [_pg("pg1", aluno.id, venc=HOJE, pag=HOJE)]
    decisao = regra.avaliar(
        aluno=aluno,
        matricula=matricula,
        pagamentos=pagamentos,
        agora=HOJE,
        direcao=DirecaoAcesso.ENTRADA,
        ultimo_acesso_direcao=DirecaoAcesso.ENTRADA,
    )
    assert decisao.liberado is False
    assert decisao.motivo == MotivoNegado.ANTI_PASSBACK


def test_rb05_anti_passback_permite_alternado():
    regra = RegraAcesso(RegraAcessoConfig(anti_passback=True))
    aluno = _aluno()
    matricula = _matricula(aluno.id, _plano(), _vigencia(VIG_INICIO, VIG_FIM))
    pagamentos = [_pg("pg1", aluno.id, venc=HOJE, pag=HOJE)]
    decisao = regra.avaliar(
        aluno=aluno,
        matricula=matricula,
        pagamentos=pagamentos,
        agora=HOJE,
        direcao=DirecaoAcesso.SAIDA,
        ultimo_acesso_direcao=DirecaoAcesso.ENTRADA,
    )
    assert decisao.liberado is True


def test_pode_acessar_compat():
    regra = RegraAcesso()
    aluno = _aluno()
    matricula = _matricula(aluno.id, _plano(), _vigencia(VIG_INICIO, VIG_FIM))
    pagamentos = [_pg("pg1", aluno.id, venc=HOJE, pag=HOJE)]
    ok, motivo = regra.pode_acessar(aluno, matricula, pagamentos, HOJE)
    assert ok is True
    assert motivo is None


def test_precedencia_rb03_sobre_rb02():
    regra = RegraAcesso()
    aluno = _aluno(bloqueado=True)
    # matrícula expirada, mas bloqueio manual deve ser motivo
    matricula = _matricula(aluno.id, _plano(), _vigencia(date(2026, 1, 1), date(2026, 1, 31)))
    decisao = regra.avaliar(aluno=aluno, matricula=matricula, pagamentos=[], agora=HOJE)
    assert decisao.motivo == MotivoNegado.BLOQUEIO_MANUAL
