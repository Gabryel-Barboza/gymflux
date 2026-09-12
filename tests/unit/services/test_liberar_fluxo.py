"""LiberarAcessoService — fluxo de liberação/negação com MockHenry7x."""

from __future__ import annotations

from datetime import date, timedelta
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
