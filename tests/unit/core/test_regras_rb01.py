"""RB01 — tolerância de inadimplência (helpers locais, arquivo autocontido)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from gymflux.core.acesso import MotivoNegado, ResultadoAcesso
from gymflux.core.aluno import Aluno, StatusAluno
from gymflux.core.pagamento import Pagamento
from gymflux.core.plano import Matricula, Plano, Vigencia
from gymflux.core.regras import RegraAcesso, RegraAcessoConfig

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


def test_rb01_liberado_dentro_tolerancia():
    regra = RegraAcesso(RegraAcessoConfig(tolerancia_dias=3))
    aluno = _aluno()
    plano = _plano(tolerancia=3)
    matricula = _matricula(aluno.id, plano, _vigencia(VIG_INICIO, VIG_FIM))
    # venceu há 2 dias (dentro tolerância 3) ainda não pago
    # atraso 2 <=3 => adimplente
    pagamentos = [_pg("pg1", aluno.id, venc=HOJE - timedelta(days=2), pag=None)]
    decisao = regra.avaliar(aluno=aluno, matricula=matricula, pagamentos=pagamentos, agora=HOJE)
    assert decisao.liberado is True
    assert decisao.resultado == ResultadoAcesso.LIBERADO


def test_rb01_negado_apos_tolerancia():
    regra = RegraAcesso(RegraAcessoConfig(tolerancia_dias=3))
    aluno = _aluno()
    plano = _plano(tolerancia=3)
    matricula = _matricula(aluno.id, plano, _vigencia(VIG_INICIO, VIG_FIM))
    # venceu há 4 dias (>3) sem pagamento => negado
    pagamentos = [_pg("pg1", aluno.id, venc=HOJE - timedelta(days=4), pag=None)]
    decisao = regra.avaliar(aluno=aluno, matricula=matricula, pagamentos=pagamentos, agora=HOJE)
    assert decisao.liberado is False
    assert decisao.motivo == MotivoNegado.INADIMPLENTE
    assert decisao.resultado == ResultadoAcesso.NEGADO


def test_rb01_liberado_pagamento_dentro_tolerancia():
    regra = RegraAcesso(RegraAcessoConfig(tolerancia_dias=3))
    aluno = _aluno()
    matricula = _matricula(aluno.id, _plano(), _vigencia(VIG_INICIO, VIG_FIM))
    # venceu dia 01, pagou dia 03 (atraso 2) => dentro
    pagamentos = [_pg("pg1", aluno.id, venc=date(2026, 9, 1), pag=date(2026, 9, 3))]
    decisao = regra.avaliar(aluno=aluno, matricula=matricula, pagamentos=pagamentos, agora=HOJE)
    assert decisao.liberado is True


def test_rb01_negado_pagamento_fora_tolerancia():
    regra = RegraAcesso(RegraAcessoConfig(tolerancia_dias=3))
    aluno = _aluno()
    matricula = _matricula(aluno.id, _plano(), _vigencia(VIG_INICIO, VIG_FIM))
    pagamentos = [_pg("pg1", aluno.id, venc=date(2026, 9, 1), pag=date(2026, 9, 5))]  # atraso 4
    decisao = regra.avaliar(aluno=aluno, matricula=matricula, pagamentos=pagamentos, agora=HOJE)
    assert decisao.liberado is False
    assert decisao.motivo == MotivoNegado.INADIMPLENTE


def test_rb01_sem_pagamentos_negado():
    regra = RegraAcesso()
    aluno = _aluno()
    matricula = _matricula(aluno.id, _plano(), _vigencia(VIG_INICIO, VIG_FIM))
    decisao = regra.avaliar(aluno=aluno, matricula=matricula, pagamentos=[], agora=HOJE)
    assert decisao.liberado is False
    assert decisao.motivo == MotivoNegado.INADIMPLENTE


def test_rb01_vencimento_futuro_liberado():
    regra = RegraAcesso(RegraAcessoConfig(tolerancia_dias=3))
    aluno = _aluno()
    matricula = _matricula(aluno.id, _plano(), _vigencia(VIG_INICIO, VIG_FIM))
    pagamentos = [_pg("pg1", aluno.id, venc=HOJE + timedelta(days=5), pag=None)]
    decisao = regra.avaliar(aluno=aluno, matricula=matricula, pagamentos=pagamentos, agora=HOJE)
    assert decisao.liberado is True


def test_rb01_tolerancia_zero():
    regra = RegraAcesso(RegraAcessoConfig(tolerancia_dias=0))
    aluno = _aluno()
    matricula = _matricula(aluno.id, _plano(tolerancia=0), _vigencia(VIG_INICIO, VIG_FIM))
    # venceu ontem, sem pagamento => negado se tolerancia 0
    pagamentos = [_pg("pg1", aluno.id, venc=HOJE - timedelta(days=1), pag=None)]
    decisao = regra.avaliar(
        aluno=aluno, matricula=matricula, pagamentos=pagamentos, agora=HOJE, tolerancia_dias=0
    )
    assert decisao.liberado is False
