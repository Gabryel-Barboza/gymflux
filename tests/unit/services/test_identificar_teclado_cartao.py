"""IdentificarAcessoService — teclado/cartão do aluno (sem funcionário)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from gymflow.core.acesso import DirecaoAcesso, MotivoNegado, ResultadoAcesso
from gymflow.core.aluno import Aluno
from gymflow.core.pagamento import Pagamento
from gymflow.core.plano import Matricula, Plano, Vigencia
from gymflow.hardware.henry7x.mock import MockHenry7x
from gymflow.infra.repositories.acesso_log import AcessoLogRepositoryMemoria
from gymflow.infra.repositories.aluno import AlunoRepositoryMemoria
from gymflow.infra.repositories.matricula import MatriculaRepositoryMemoria
from gymflow.infra.repositories.pagamento import PagamentoRepositoryMemoria
from gymflow.services.identificar_acesso import (
    Identificacao,
    IdentificarAcessoService,
    OrigemIdentificacao,
)
from gymflow.services.liberar_acesso import LiberarAcessoService

HOJE = date.today()


def _svc() -> IdentificarAcessoService:
    driver = MockHenry7x(auto_giro=False)
    driver.conectar("MOCK:1")
    acesso = LiberarAcessoService(
        driver=driver,
        aluno_repo=AlunoRepositoryMemoria(),
        matricula_repo=MatriculaRepositoryMemoria(),
        pagamento_repo=PagamentoRepositoryMemoria(),
        acesso_repo=AcessoLogRepositoryMemoria(),
    )
    repo = acesso.aluno_repo
    assert repo is not None
    return IdentificarAcessoService(acesso=acesso, aluno_repo=repo)


def _adimplente(svc: IdentificarAcessoService, senha: str = "1234") -> Aluno:
    aluno = Aluno(id="a1", nome="Ana Silva", cpf="11144477735")
    aluno.definir_senha(senha)
    aluno.definir_cartao("TAG-42")
    svc.aluno_repo.salvar(aluno)
    plano = Plano.criar_mensal(id="mensal", nome="Mensal", valor=Decimal("99.90"))
    mat_repo = svc.acesso.matricula_repo
    assert mat_repo is not None
    mat_repo.salvar(
        Matricula(
            aluno_id=aluno.id,
            plano=plano,
            vigencia=Vigencia.a_partir_de(HOJE, 30),
            ativa=True,
        ),
        matricula_id="mat-1",
    )
    pag_repo = svc.acesso.pagamento_repo
    assert pag_repo is not None
    pag_repo.salvar(
        Pagamento(
            id="pag-1",
            aluno_id=aluno.id,
            valor=Decimal("99.90"),
            data_vencimento=HOJE,
            data_pagamento=HOJE,
        )
    )
    return aluno


def test_teclado_correto_libera_e_retorna_aluno():
    svc = _svc()
    aluno = _adimplente(svc)
    decisao, achado = svc.identificar(Identificacao.por_teclado("1234"))
    assert decisao.liberado is True
    assert decisao.resultado == ResultadoAcesso.LIBERADO
    assert achado is not None and achado.id == aluno.id


def test_teclado_errado_nega_sem_vazar_motivo_interno():
    svc = _svc()
    _adimplente(svc)
    decisao, achado = svc.identificar(Identificacao.por_teclado("0000"))
    assert decisao.liberado is False
    assert achado is None
    assert decisao.motivo == MotivoNegado.ALUNO_NAO_ENCONTRADO


def test_cartao_correto_libera():
    svc = _svc()
    _adimplente(svc)
    decisao, achado = svc.identificar(Identificacao.por_cartao("TAG-42"))
    assert decisao.liberado is True
    assert achado is not None and achado.nome == "Ana Silva"


def test_cartao_desconhecido_nega():
    svc = _svc()
    _adimplente(svc)
    decisao, achado = svc.identificar(Identificacao.por_cartao("TAG-99"))
    assert decisao.liberado is False
    assert achado is None


def test_aluno_sem_matricula_nega_mas_retorna_aluno():
    svc = _svc()
    aluno = Aluno(id="a9", nome="Sem Plano")
    aluno.definir_senha("5555")
    svc.aluno_repo.salvar(aluno)
    decisao, achado = svc.identificar(
        Identificacao.por_teclado("5555"), direcao=DirecaoAcesso.SAIDA
    )
    assert decisao.liberado is False
    assert decisao.motivo == MotivoNegado.SEM_MATRICULA
    assert achado is not None and achado.id == "a9"


def test_identificacao_invalida_rejeita_na_fabrica():
    with pytest.raises(ValueError):
        Identificacao.por_teclado("12")
    with pytest.raises(ValueError):
        Identificacao.por_cartao("   ")
    assert OrigemIdentificacao("TECLADO") == OrigemIdentificacao.TECLADO
