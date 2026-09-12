"""DashboardViewModel — liberação, identificação, direção bloqueada, log do dia."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from gymflux.core.acesso import (
    DirecaoAcesso,
    MotivoNegado,
    ResultadoAcesso,
    TentativaAcesso,
)
from gymflux.core.funcionario import Funcionario
from gymflux.core.plano import TipoPlano
from gymflux.hardware.henry7x.mock import MockHenry7x
from gymflux.infra.repositories.acesso_log import AcessoLogRepositoryMemoria
from gymflux.infra.repositories.fechamento_caixa import FechamentoCaixaRepositoryMemoria
from gymflux.infra.repositories.funcionario import FuncionarioRepositoryMemoria
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
from gymflux.ui.config_store import UiConfig
from gymflux.ui.viewmodels.dashboard import DashboardViewModel

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
    from gymflux.ui.viewmodels.alunos import AlunosViewModel
    from gymflux.ui.viewmodels.caixa import CaixaViewModel
    from gymflux.ui.viewmodels.planos import PlanosViewModel

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
    from gymflux.services.identificar_acesso import IdentificarAcessoService

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


def test_direcao_bloqueada_nega_direto_sem_hardware():
    w = _wired()
    aluno_id = _fluxo_adimplente(w)
    w["dashboard"].ui_config = UiConfig(bloquear_entrada=True)
    antes = w["driver"].status()["bloqueada"]
    decisao = w["dashboard"].liberar_entrada(aluno_id)
    assert decisao.liberado is False
    assert decisao.motivo == MotivoNegado.BLOQUEIO_MANUAL
    assert w["driver"].status()["bloqueada"] == antes  # hardware nem acionado
    # saída segue liberando
    assert w["dashboard"].liberar_saida(aluno_id).liberado is True


def test_direcao_bloqueada_vale_para_identificar():
    w = _wired()
    _com_identificar(w)
    w["dashboard"].ui_config = UiConfig(bloquear_saida=True)
    decisao, achado = w["dashboard"].identificar_acesso(
        "0000", "TECLADO", direcao=DirecaoAcesso.SAIDA
    )
    assert decisao.liberado is False
    assert decisao.motivo == MotivoNegado.BLOQUEIO_MANUAL
    assert achado is None


def test_senha_curta_nega_direto():
    w = _wired()
    _com_identificar(w)
    aluno = w["alunos"].cadastrar(
        nome="Ana Silva", cpf="11144477735", senha="123456", cartao_id="TAG-42"
    )
    plano = w["planos"].salvar(nome="Mensal", tipo=TipoPlano.MENSAL, valor=Decimal("99.90"))
    w["alunos"].matricular(aluno.id, plano.id)
    w["pagamentos"].registrar(
        aluno_id=aluno.id, valor=Decimal("99.90"), data_vencimento=HOJE, pago=True
    )
    w["dashboard"].ui_config = UiConfig(senha_min_digitos=6)
    decisao, achado = w["dashboard"].identificar_acesso("1234", "TECLADO")
    assert decisao.liberado is False
    assert decisao.motivo == "SENHA_CURTA"
    assert achado is None
    # senha de 6 dígitos passa; cartão ignora o mínimo
    decisao_ok, _ = w["dashboard"].identificar_acesso("123456", "TECLADO")
    assert decisao_ok.liberado is True
    decisao_cartao, achado_cartao = w["dashboard"].identificar_acesso("TAG-42", "CARTAO")
    assert decisao_cartao.liberado is True
    assert achado_cartao is not None and achado_cartao.id == aluno.id


def _tentativa(aluno_id, dia, hora=9, resultado=None, funcionario_id=None):
    return TentativaAcesso(
        aluno_id=aluno_id,
        funcionario_id=funcionario_id,
        direcao=DirecaoAcesso.ENTRADA,
        timestamp=datetime(dia.year, dia.month, dia.day, hora, 0),
        resultado=resultado or ResultadoAcesso.LIBERADO,
    )


def test_log_do_dia_filtra_ontem_e_mostra_funcionario():
    w = _wired()
    aluno_id = _fluxo_adimplente(w)
    repo = w["dashboard"].acesso.acesso_repo
    assert repo is not None
    ontem = HOJE - timedelta(days=1)
    repo.registrar(_tentativa(aluno_id, ontem))
    repo.registrar(_tentativa(aluno_id, HOJE))
    # funcionário logado ontem não aparece no filtro de hoje
    func_repo = FuncionarioRepositoryMemoria()
    func = Funcionario(id="f1", nome="Zé Porteira")
    func_repo.salvar(func)
    w["dashboard"].funcionario_repo = func_repo
    repo.registrar(_tentativa(None, HOJE, hora=10, funcionario_id="f1"))
    repo.registrar(_tentativa(None, ontem, hora=10, funcionario_id="f1"))

    do_dia = w["dashboard"].tentativas_do_dia(HOJE)
    assert len(do_dia) == 2
    assert all(t.timestamp.date() == HOJE for t in do_dia)
    nomes = [w["dashboard"].nome_tentativa(t) for t in do_dia]
    assert "Ana Silva" in nomes
    assert "Zé Porteira" in nomes
    # fallback p/ ids desconhecidos
    assert w["dashboard"].nome_tentativa(_tentativa("x-desconhecido", HOJE)) == "x-desconhecido"
    assert w["dashboard"].nome_tentativa(_tentativa(None, HOJE, funcionario_id="f-?")) == "f-?"
