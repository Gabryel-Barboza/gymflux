"""RB02 — vigência da matrícula (helpers locais, arquivo autocontido)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from gymflow.core.acesso import MotivoNegado
from gymflow.core.aluno import Aluno, StatusAluno
from gymflow.core.pagamento import Pagamento
from gymflow.core.plano import Matricula, Plano, Vigencia
from gymflow.core.regras import RegraAcesso

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


def test_rb02_vigente_liberado():
    regra = RegraAcesso()
    aluno = _aluno()
    matricula = _matricula(
        aluno.id, _plano(), _vigencia(HOJE - timedelta(days=5), HOJE + timedelta(days=10))
    )
    pagamentos = [_pg("pg1", aluno.id, venc=HOJE, pag=HOJE)]
    decisao = regra.avaliar(aluno=aluno, matricula=matricula, pagamentos=pagamentos, agora=HOJE)
    assert decisao.liberado is True


def test_rb02_expirada_negado_mesmo_com_pagamento():
    regra = RegraAcesso()
    aluno = _aluno()
    # matrícula expirou ontem
    matricula = _matricula(
        aluno.id, _plano(), _vigencia(date(2026, 8, 1), HOJE - timedelta(days=1))
    )
    pagamentos = [_pg("pg1", aluno.id, venc=HOJE, pag=HOJE)]
    decisao = regra.avaliar(aluno=aluno, matricula=matricula, pagamentos=pagamentos, agora=HOJE)
    assert decisao.liberado is False
    assert decisao.motivo == MotivoNegado.MATRICULA_EXPIRADA


def test_rb02_matricula_inativa_negado():
    regra = RegraAcesso()
    aluno = _aluno()
    matricula = _matricula(aluno.id, _plano(), _vigencia(VIG_INICIO, VIG_FIM), ativa=False)
    pagamentos = [_pg("pg1", aluno.id, venc=HOJE, pag=HOJE)]
    decisao = regra.avaliar(aluno=aluno, matricula=matricula, pagamentos=pagamentos, agora=HOJE)
    assert decisao.liberado is False
    assert decisao.motivo == MotivoNegado.MATRICULA_INATIVA


def test_rb02_sem_matricula_negado():
    regra = RegraAcesso()
    aluno = _aluno()
    pagamentos = [_pg("pg1", aluno.id, venc=HOJE, pag=HOJE)]
    decisao = regra.avaliar(aluno=aluno, matricula=None, pagamentos=pagamentos, agora=HOJE)
    assert decisao.liberado is False
    assert decisao.motivo == MotivoNegado.SEM_MATRICULA


def test_rb02_fora_vigencia_antes_inicio():
    regra = RegraAcesso()
    aluno = _aluno()
    matricula = _matricula(
        aluno.id, _plano(), _vigencia(HOJE + timedelta(days=1), HOJE + timedelta(days=30))
    )
    pagamentos = [_pg("pg1", aluno.id, venc=HOJE, pag=HOJE)]
    decisao = regra.avaliar(aluno=aluno, matricula=matricula, pagamentos=pagamentos, agora=HOJE)
    assert decisao.liberado is False
