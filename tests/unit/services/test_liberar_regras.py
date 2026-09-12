"""LiberarAcessoService — timeout RB04 + anti-passback RB05 (autocontido)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from gymflow.core.acesso import DirecaoAcesso, MotivoNegado, ResultadoAcesso
from gymflow.core.aluno import Aluno
from gymflow.core.pagamento import Pagamento
from gymflow.core.plano import Matricula, Plano, Vigencia
from gymflow.core.regras import RegraAcesso, RegraAcessoConfig
from gymflow.hardware.henry7x.mock import MockHenry7x
from gymflow.services.liberar_acesso import LiberarAcessoService

HOJE = date(2026, 9, 11)
VIG = Vigencia(inicio=date(2026, 8, 11), fim=date(2026, 9, 30))
PLANO = Plano(id="p1", nome="Mensal", duracao_dias=30, valor=Decimal("99.90"), tolerancia_dias=3)


def _aluno(id_: str = "a1", bloqueado: bool = False) -> Aluno:
    return Aluno(id=id_, nome="Maria", bloqueado_manual=bloqueado)


def _matricula(aluno_id: str) -> Matricula:
    return Matricula(aluno_id=aluno_id, plano=PLANO, vigencia=VIG)


def _pg_ok(aluno_id: str) -> list[Pagamento]:
    return [
        Pagamento(
            id="pg1",
            aluno_id=aluno_id,
            valor=Decimal("99.90"),
            data_vencimento=HOJE,
            data_pagamento=HOJE,
        )
    ]


def _service(auto_giro: bool = False) -> LiberarAcessoService:
    driver = MockHenry7x(auto_giro=auto_giro, giro_delay_s=0.1)
    driver.conectar("MOCK:1")
    regra = RegraAcesso(RegraAcessoConfig(tolerancia_dias=3, timeout_giro_s=7))
    return LiberarAcessoService(driver=driver, regra=regra)


def test_timeout_rb04_bloqueia_e_loga():
    svc = _service(auto_giro=False)
    aluno = _aluno("a1")
    decisao = svc.tentar_acesso(
        aluno=aluno, matricula=_matricula(aluno.id), pagamentos=_pg_ok(aluno.id), agora=HOJE
    )
    assert decisao.liberado is True
    # simula que liberou às 10:00 e agora são 10:00:08 sem giro
    liberado_em = datetime(2026, 9, 11, 10, 0, 0)
    agora = liberado_em + timedelta(seconds=8)
    timeout_decisao = svc.verificar_timeout(
        liberado_em, agora, aluno_id=aluno.id, direcao=DirecaoAcesso.ENTRADA
    )
    assert timeout_decisao is not None
    assert timeout_decisao.resultado == ResultadoAcesso.TIMEOUT
    # último registro deve ser TIMEOUT e catraca bloqueada
    assert svc.registro.tentativas[-1].resultado == ResultadoAcesso.TIMEOUT
    assert svc.driver.status()["bloqueada"] is True


def test_timeout_nao_aciona_se_dentro_limite():
    svc = _service()
    liberado_em = datetime(2026, 9, 11, 10, 0, 0)
    agora = liberado_em + timedelta(seconds=5)
    assert svc.verificar_timeout(liberado_em, agora, aluno_id="a1") is None
    # só 1 registro? actually we didn't create initial liberado, so zero. Test that no new registro
    assert svc.registro.total() == 0


def test_anti_passback_via_servico():
    driver = MockHenry7x(auto_giro=False)
    driver.conectar("MOCK:1")
    regra = RegraAcesso(RegraAcessoConfig(tolerancia_dias=3, anti_passback=True))
    svc = LiberarAcessoService(driver=driver, regra=regra)
    aluno = _aluno("a1")
    d1 = svc.tentar_acesso(
        aluno=aluno,
        matricula=_matricula(aluno.id),
        pagamentos=_pg_ok(aluno.id),
        direcao=DirecaoAcesso.ENTRADA,
        agora=HOJE,
    )
    assert d1.liberado is True
    d2 = svc.tentar_acesso(
        aluno=aluno,
        matricula=_matricula(aluno.id),
        pagamentos=_pg_ok(aluno.id),
        direcao=DirecaoAcesso.ENTRADA,
        agora=HOJE,
        ultimo_acesso_direcao=DirecaoAcesso.ENTRADA,
    )
    assert d2.liberado is False
    assert d2.motivo == MotivoNegado.ANTI_PASSBACK
