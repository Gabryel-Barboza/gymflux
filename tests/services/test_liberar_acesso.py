"""Testes LiberarAcessoService com MockHenry7x."""

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


def test_liberar_acesso_sucesso_mock():
    svc = _service()
    aluno = _aluno("a1")
    decisao = svc.tentar_acesso(
        aluno=aluno,
        matricula=_matricula(aluno.id),
        pagamentos=_pg_ok(aluno.id),
        direcao=DirecaoAcesso.ENTRADA,
        agora=HOJE,
    )
    assert decisao.liberado is True
    assert decisao.resultado == ResultadoAcesso.LIBERADO
    assert svc.registro.total() == 1
    assert svc.registro.tentativas[0].resultado == ResultadoAcesso.LIBERADO
    # hardware foi liberado
    assert svc.driver.status()["bloqueada"] is False  # liberou, ainda não girou (auto_giro False)
    assert svc.driver.status()["online"] is True


def test_liberar_acesso_negado_inadimplente_nao_aciona_hardware():
    svc = _service()
    aluno = _aluno("a1")
    # vencido há 10 dias sem pagamento => inadimplente
    pagamentos = [
        Pagamento(
            id="pg1",
            aluno_id=aluno.id,
            valor=Decimal("99.90"),
            data_vencimento=HOJE - timedelta(days=10),
            data_pagamento=None,
        )
    ]
    decisao = svc.tentar_acesso(
        aluno=aluno, matricula=_matricula(aluno.id), pagamentos=pagamentos, agora=HOJE
    )
    assert decisao.liberado is False
    assert decisao.motivo == MotivoNegado.INADIMPLENTE
    assert svc.registro.tentativas[0].resultado == ResultadoAcesso.NEGADO
    # catraca deve continuar bloqueada (não liberou)
    assert svc.driver.status()["bloqueada"] is True


def test_liberar_acesso_bloqueio_manual():
    svc = _service()
    aluno = _aluno("a1", bloqueado=True)
    decisao = svc.tentar_acesso(
        aluno=aluno, matricula=_matricula(aluno.id), pagamentos=_pg_ok(aluno.id), agora=HOJE
    )
    assert decisao.liberado is False
    assert decisao.motivo == MotivoNegado.BLOQUEIO_MANUAL
    assert svc.driver.status()["bloqueada"] is True


def test_liberar_acesso_matricula_expirada():
    svc = _service()
    aluno = _aluno("a1")
    mat_expirada = Matricula(
        aluno_id=aluno.id,
        plano=PLANO,
        vigencia=Vigencia(inicio=date(2026, 1, 1), fim=date(2026, 1, 31)),
    )
    decisao = svc.tentar_acesso(
        aluno=aluno, matricula=mat_expirada, pagamentos=_pg_ok(aluno.id), agora=HOJE
    )
    assert decisao.liberado is False
    assert decisao.motivo == MotivoNegado.MATRICULA_EXPIRADA


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


def test_saida_e_entrada_direcoes_distintas():
    svc = _service()
    aluno = _aluno("a1")
    for direcao in (DirecaoAcesso.ENTRADA, DirecaoAcesso.SAIDA):
        svc.driver.bloquear()
        decisao = svc.tentar_acesso(
            aluno=aluno,
            matricula=_matricula(aluno.id),
            pagamentos=_pg_ok(aluno.id),
            direcao=direcao,
            agora=HOJE,
        )
        assert decisao.liberado is True


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


def test_registro_memoria_por_aluno():
    svc = _service()
    a1 = _aluno("a1")
    a2 = Aluno(id="a2", nome="João")
    svc.tentar_acesso(aluno=a1, matricula=_matricula(a1.id), pagamentos=_pg_ok(a1.id), agora=HOJE)
    svc.tentar_acesso(
        aluno=a2, matricula=_matricula(a2.id), pagamentos=[], agora=HOJE
    )  # inadimplente
    assert len(svc.registro.por_aluno("a1")) == 1
    assert len(svc.registro.por_aluno("a2")) == 1


def test_hardware_erro_gracioso():
    from gymflow.hardware.henry7x.interface import Direcao, Henry7xDriver

    class BrokenDriver(Henry7xDriver):
        is_mock = True

        def conectar(self, porta, timeout_ms=5000):
            return True

        def desconectar(self):
            pass

        def liberar(self, direcao: Direcao):
            raise RuntimeError("falha serial")

        def bloquear(self):
            pass

        def on_giro(self, cb):
            pass

        def off_giro(self, cb):
            pass

        def status(self):
            return {"online": True}

    svc = LiberarAcessoService(driver=BrokenDriver(), regra=RegraAcesso())
    aluno = _aluno("a1")
    decisao = svc.tentar_acesso(
        aluno=aluno, matricula=_matricula(aluno.id), pagamentos=_pg_ok(aluno.id), agora=HOJE
    )
    assert decisao.liberado is False
    assert decisao.motivo == MotivoNegado.ERRO_HARDWARE


def test_com_mock_factory_helper():
    svc = LiberarAcessoService.com_mock()
    assert svc.driver.is_mock is True
    assert svc.driver.is_conectado() is True
