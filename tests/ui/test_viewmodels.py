"""Testes dos ViewModels (Qt-free) — fluxo da recepção com repos memória."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from gymflow.core.acesso import ResultadoAcesso
from gymflow.core.aluno import StatusAluno
from gymflow.core.plano import TipoPlano
from gymflow.hardware.henry7x.mock import MockHenry7x
from gymflow.infra.repositories.acesso_log import AcessoLogRepositoryMemoria
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
from gymflow.ui.viewmodels.dashboard import DashboardViewModel
from gymflow.ui.viewmodels.pagamentos import PagamentosViewModel
from gymflow.ui.viewmodels.planos import PlanosViewModel

HOJE = date.today()


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
        "pagamentos": PagamentosViewModel(pagamentos=pagamentos, alunos=cadastrar),
    }


def _fluxo_adimplente(w: dict, cpf: str = "11144477735") -> str:
    aluno = w["alunos"].cadastrar(nome="Ana Silva", cpf=cpf)
    plano = w["planos"].salvar(nome="Mensal", tipo=TipoPlano.MENSAL, valor=Decimal("99.90"))
    w["alunos"].matricular(aluno.id, plano.id)
    w["pagamentos"].registrar(
        aluno_id=aluno.id, valor=Decimal("99.90"), data_vencimento=HOJE, pago=True
    )
    return aluno.id


def test_fluxo_recepcao_completo_libera():
    w = _wired()
    aluno_id = _fluxo_adimplente(w)
    decisao = w["dashboard"].liberar_entrada(aluno_id)
    assert decisao.liberado is True
    assert decisao.resultado == ResultadoAcesso.LIBERADO
    logs = w["dashboard"].ultimas_tentativas()
    assert len(logs) == 1
    assert logs[0].resultado == ResultadoAcesso.LIBERADO
    assert "LIBERADO" in DashboardViewModel.resume_decisao(decisao)


def test_dashboard_negado_sem_pagamento_nao_aciona():
    w = _wired()
    aluno = w["alunos"].cadastrar(nome="Sem Pagar", cpf="22255588846")
    plano = w["planos"].salvar(nome="Mensal", tipo=TipoPlano.MENSAL, valor=Decimal("99.90"))
    w["alunos"].matricular(aluno.id, plano.id)
    decisao = w["dashboard"].liberar_entrada(aluno.id)
    assert decisao.liberado is False
    assert w["driver"].status()["bloqueada"] is True
    assert "NEGADO" in DashboardViewModel.resume_decisao(decisao)


def test_dashboard_saida_e_giro():
    w = _wired()
    aluno_id = _fluxo_adimplente(w)
    decisao = w["dashboard"].liberar_saida(aluno_id)
    assert decisao.liberado is True
    w["dashboard"].registrar_giro("SAIDA", 123.0)
    assert w["dashboard"].giros == [("SAIDA", 123.0)]


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


def test_pagamentos_situacao_rb01():
    w = _wired()
    aluno = w["alunos"].cadastrar(nome="Ana", cpf="11144477735")
    assert w["pagamentos"].situacao(aluno.id) == ("SEM PAGAMENTOS", 0)
    # vencido há 10 dias, pendente => inadimplente (tolerância 3)
    w["pagamentos"].registrar(
        aluno_id=aluno.id, valor="99.90", data_vencimento=HOJE - timedelta(days=10)
    )
    rotulo, atraso = w["pagamentos"].situacao(aluno.id)
    assert rotulo == "INADIMPLENTE"
    assert atraso == 10
    # pagamento novo pago hoje volta a adimplente (considera o mais recente)
    w["pagamentos"].registrar(aluno_id=aluno.id, valor="99.90", data_vencimento=HOJE, pago=True)
    assert w["pagamentos"].situacao(aluno.id)[0] == "ADIMPLENTE"


def test_matricular_sem_plano_da_erro_amigavel():
    w = _wired()
    aluno = w["alunos"].cadastrar(nome="Ana", cpf="11144477735")
    with pytest.raises(ValueError, match="Plano"):
        w["alunos"].matricular(aluno.id, "plano-inexistente")


def test_dashboard_commit_apos_liberacao():
    w = _wired()
    chamadas: list[str] = []
    w["dashboard"].commit = lambda: chamadas.append("commit")
    aluno_id = _fluxo_adimplente(w)
    w["dashboard"].liberar_entrada(aluno_id)
    w["dashboard"].liberar_saida(aluno_id)
    assert chamadas == ["commit", "commit"]


def test_dashboard_log_exibe_nome_com_fallback_id():
    w = _wired()
    aluno_id = _fluxo_adimplente(w)
    assert w["dashboard"].nome_aluno(aluno_id) == "Ana Silva"
    assert w["dashboard"].nome_aluno("aluno-inexistente") == "aluno-inexistente"


def _com_identificar(w: dict) -> list[str]:
    from gymflow.services.identificar_acesso import IdentificarAcessoService

    repo = w["dashboard"].acesso.aluno_repo
    assert repo is not None
    w["dashboard"].identificar = IdentificarAcessoService(
        acesso=w["dashboard"].acesso, aluno_repo=repo
    )
    chamadas: list[str] = []
    w["dashboard"].commit = lambda: chamadas.append("commit")
    return chamadas


def test_dashboard_identificar_por_senha_libera_e_commita():
    w = _wired()
    chamadas = _com_identificar(w)
    aluno = w["alunos"].cadastrar(
        nome="Ana Silva", cpf="11144477735", senha="1234", cartao_id="TAG-42"
    )
    assert aluno.senha_hash is not None and "1234" not in aluno.senha_hash
    assert aluno.cartao_id == "TAG-42"
    plano = w["planos"].salvar(nome="Mensal", tipo=TipoPlano.MENSAL, valor=Decimal("99.90"))
    w["alunos"].matricular(aluno.id, plano.id)
    w["pagamentos"].registrar(
        aluno_id=aluno.id, valor=Decimal("99.90"), data_vencimento=HOJE, pago=True
    )
    decisao, achado = w["dashboard"].identificar_acesso("1234", "TECLADO")
    assert decisao.liberado is True
    assert achado is not None and achado.id == aluno.id
    assert chamadas == ["commit"]
    decisao2, achado2 = w["dashboard"].identificar_acesso("TAG-42", "CARTAO")
    assert decisao2.liberado is True
    assert achado2 is not None and achado2.id == aluno.id


def test_dashboard_identificar_desconhecido_nega():
    w = _wired()
    chamadas = _com_identificar(w)
    _fluxo_adimplente(w)
    decisao, achado = w["dashboard"].identificar_acesso("0000", "TECLADO")
    assert decisao.liberado is False
    assert achado is None
    assert chamadas == ["commit"]


def test_dashboard_identificar_sem_servico_erro_amigavel():
    w = _wired()
    with pytest.raises(RuntimeError, match="não injetado"):
        w["dashboard"].identificar_acesso("1234", "TECLADO")


def test_cadastrar_senha_invalida_rejeita():
    w = _wired()
    with pytest.raises(ValueError):
        w["alunos"].cadastrar(nome="Ana", cpf="11144477735", senha="12")
