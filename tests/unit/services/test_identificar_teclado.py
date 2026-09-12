"""IdentificarAcessoService — teclado do aluno (cartão removido na Fase 4.8)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from gymflux.core.acesso import DirecaoAcesso, MotivoNegado, ResultadoAcesso
from gymflux.core.aluno import Aluno
from gymflux.core.pagamento import Pagamento
from gymflux.core.plano import Matricula, Plano, Vigencia
from gymflux.hardware.henry7x.mock import MockHenry7x
from gymflux.infra.repositories.acesso_log import AcessoLogRepositoryMemoria
from gymflux.infra.repositories.aluno import AlunoRepositoryMemoria
from gymflux.infra.repositories.matricula import MatriculaRepositoryMemoria
from gymflux.infra.repositories.pagamento import PagamentoRepositoryMemoria
from gymflux.services.identificar_acesso import (
    Identificacao,
    IdentificarAcessoService,
    OrigemIdentificacao,
)
from gymflux.services.liberar_acesso import LiberarAcessoService

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


def test_lookup_direto_por_senha():
    svc = _svc()
    _adimplente(svc)
    assert svc.aluno_repo.buscar_por_senha("1234") is not None
    assert svc.aluno_repo.buscar_por_senha("0000") is None
    assert svc.aluno_repo.buscar_por_senha("   ") is None


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
    assert OrigemIdentificacao("TECLADO") == OrigemIdentificacao.TECLADO
    with pytest.raises(ValueError):
        OrigemIdentificacao("CARTAO")  # removido na Fase 4.8
