"""PlanosViewModel — CRUD + personalizado (usa repos memória via _wired local)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from gymflow.core.plano import TipoPlano
from gymflow.hardware.henry7x.mock import MockHenry7x
from gymflow.infra.repositories.acesso_log import AcessoLogRepositoryMemoria
from gymflow.infra.repositories.fechamento_caixa import FechamentoCaixaRepositoryMemoria
from gymflow.infra.repositories.matricula import MatriculaRepositoryMemoria
from gymflow.infra.repositories.plano import PlanoRepositoryMemoria
from gymflow.services.cadastrar_aluno import (
    CadastrarAlunoService,
    RepositorioAlunosMemoria,
)
from gymflow.services.liberar_acesso import LiberarAcessoService
from gymflow.services.registrar_pagamento import (
    RegistrarPagamentoService,
    RepositorioPagamentosMemoria,
)
from gymflow.ui.viewmodels.alunos import AlunosViewModel
from gymflow.ui.viewmodels.caixa import CaixaViewModel
from gymflow.ui.viewmodels.dashboard import DashboardViewModel
from gymflow.ui.viewmodels.planos import PlanosViewModel


def _wired(auto_giro: bool = False) -> dict:
    driver = MockHenry7x(auto_giro=auto_giro, giro_delay_s=0.01)
    driver.conectar("MOCK:1")
    aluno_repo = RepositorioAlunosMemoria()
    plano_repo = PlanoRepositoryMemoria()
    mat_repo = MatriculaRepositoryMemoria()
    pag_repo = RepositorioPagamentosMemoria()
    acesso_repo = AcessoLogRepositoryMemoria()
    cadastrar = CadastrarAlunoService(repo=aluno_repo)
    pagamentos = RegistrarPagamentoService(repo=pag_repo)
    liberar = LiberarAcessoService(
        driver=driver,
        aluno_repo=aluno_repo,
        matricula_repo=mat_repo,
        pagamento_repo=pag_repo,
        acesso_repo=acesso_repo,
    )
    return {
        "driver": driver,
        "dashboard": DashboardViewModel(acesso=liberar, log_repo=acesso_repo),
        "alunos": AlunosViewModel(alunos=cadastrar, matricula_repo=mat_repo, plano_repo=plano_repo),
        "planos": PlanosViewModel(repo=plano_repo),
        "pagamentos": CaixaViewModel(
            pagamentos=pagamentos,
            alunos=cadastrar,
            fechamentos=FechamentoCaixaRepositoryMemoria(),
        ),
    }


def test_planos_crud_e_personalizado():
    w = _wired()
    mensal = w["planos"].salvar(nome="Mensal", tipo="MENSAL", valor="99.90")
    assert mensal.duracao_dias == 30
    assert mensal.tipo == TipoPlano.MENSAL
    with pytest.raises(ValueError, match="duracao_dias"):
        w["planos"].salvar(nome="X", tipo=TipoPlano.PERSONALIZADO, valor="10")
    pers = w["planos"].salvar(
        nome="15 dias", tipo=TipoPlano.PERSONALIZADO, valor=Decimal("49.90"), duracao_dias=15
    )
    assert pers.duracao_dias == 15
    assert len(w["planos"].listar()) == 2
    w["planos"].remover(mensal.id)
    assert [p.nome for p in w["planos"].listar()] == ["15 dias"]
