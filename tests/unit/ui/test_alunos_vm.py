"""AlunosViewModel — cadastro, busca, bloqueio, matrícula, atualização."""

from __future__ import annotations

from datetime import date

import pytest

from gymflux.core.aluno import StatusAluno
from gymflux.hardware.henry7x.mock import MockHenry7x
from gymflux.infra.repositories.acesso_log import AcessoLogRepositoryMemoria
from gymflux.infra.repositories.fechamento_caixa import FechamentoCaixaRepositoryMemoria
from gymflux.infra.repositories.matricula import MatriculaRepositoryMemoria
from gymflux.infra.repositories.plano import PlanoRepositoryMemoria
from gymflux.services.cadastrar_aluno import (
    CadastrarAlunoService,
    RepositorioAlunosMemoria,
)
from gymflux.services.liberar_acesso import LiberarAcessoService
from gymflux.services.registrar_pagamento import (
    RegistrarPagamentoService,
    RepositorioPagamentosMemoria,
)
from gymflux.ui.viewmodels.alunos import AlunosViewModel
from gymflux.ui.viewmodels.caixa import CaixaViewModel
from gymflux.ui.viewmodels.dashboard import DashboardViewModel
from gymflux.ui.viewmodels.planos import PlanosViewModel


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


def test_alunos_busca_bloqueio_e_resolver():
    w = _wired()
    a1 = w["alunos"].cadastrar(nome="Ana Silva", cpf="11144477735")
    w["alunos"].cadastrar(nome="Bruno Souza", cpf="22255588846")
    assert [a.nome for a in w["alunos"].listar(busca="ana")] == ["Ana Silva"]
    assert [a.nome for a in w["alunos"].listar(busca="22255588846")] == ["Bruno Souza"]
    assert len(w["alunos"].listar(status=StatusAluno.ATIVO)) == 2
    w["alunos"].bloquear(a1.id)
    bloqueado = w["alunos"].alunos.buscar(a1.id)
    assert bloqueado is not None
    assert bloqueado.esta_bloqueado is True
    assert bloqueado.status == StatusAluno.ATIVO  # bloqueio manual não muda status
    w["alunos"].desbloquear(a1.id)
    desbloqueado = w["alunos"].alunos.buscar(a1.id)
    assert desbloqueado is not None
    assert desbloqueado.esta_bloqueado is False
    # resolver por id e por cpf (uso do dashboard)
    assert w["dashboard"].resolver_aluno(a1.id) is not None
    assert w["dashboard"].resolver_aluno("111.444.777-35") is not None
    assert w["dashboard"].resolver_aluno("   ") is None
    assert w["dashboard"].resolver_aluno("inexistente") is None


def test_alunos_cpf_duplicado_rejeita():
    w = _wired()
    w["alunos"].cadastrar(nome="Um", cpf="11144477735")
    with pytest.raises(ValueError, match="CPF"):
        w["alunos"].cadastrar(nome="Dois", cpf="11144477735")


def test_matricular_sem_plano_da_erro_amigavel():
    w = _wired()
    aluno = w["alunos"].cadastrar(nome="Ana", cpf="11144477735")
    with pytest.raises(ValueError, match="Plano"):
        w["alunos"].matricular(aluno.id, "plano-inexistente")


def test_cadastrar_senha_invalida_rejeita():
    w = _wired()
    with pytest.raises(ValueError):
        w["alunos"].cadastrar(nome="Ana", cpf="11144477735", senha="12")


def test_alunos_atualizar_tudo():
    w = _wired()
    aluno = w["alunos"].cadastrar(nome="Ana", cpf="11144477735", senha="1234")
    hash_antes = aluno.senha_hash
    atualizado = w["alunos"].atualizar(
        aluno.id,
        nome="Ana Silva",
        cpf="11144477735",
        data_nasc=date(1990, 5, 1),
        telefone="11999990000",
        email="ana@mail.com",
        observacoes="obs",
        senha="",
        cartao_id="TAG-1",
        status=StatusAluno.INATIVO,
    )
    assert atualizado.nome == "Ana Silva"
    assert atualizado.telefone == "11999990000"
    assert atualizado.senha_hash == hash_antes  # vazia mantém
    assert atualizado.cartao_id == "TAG-1"
    assert atualizado.status == StatusAluno.INATIVO
    # nova senha troca o hash
    atualizado2 = w["alunos"].atualizar(aluno.id, nome="Ana Silva", senha="5678")
    assert atualizado2.senha_hash != hash_antes
    assert atualizado2.verificar_senha("5678") is True


def test_alunos_atualizar_erros():
    w = _wired()
    aluno = w["alunos"].cadastrar(nome="Ana")
    with pytest.raises(ValueError, match="não encontrado"):
        w["alunos"].atualizar("inexistente", nome="X")
    with pytest.raises(ValueError, match="nome não pode ser vazio"):
        w["alunos"].atualizar(aluno.id, nome="  ")
    with pytest.raises(ValueError, match="dígitos"):
        w["alunos"].atualizar(aluno.id, nome="Ana", senha="12")
