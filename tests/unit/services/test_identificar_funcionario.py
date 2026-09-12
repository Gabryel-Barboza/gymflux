"""IdentificarAcessoService — bypass de funcionário (prioridade, pulso, log)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from gymflux.core.acesso import MotivoNegado, ResultadoAcesso
from gymflux.core.aluno import Aluno
from gymflux.core.funcionario import Funcionario
from gymflux.core.pagamento import Pagamento
from gymflux.core.plano import Matricula, Plano, Vigencia
from gymflux.hardware.henry7x.mock import MockHenry7x
from gymflux.infra.repositories.acesso_log import AcessoLogRepositoryMemoria
from gymflux.infra.repositories.aluno import AlunoRepositoryMemoria
from gymflux.infra.repositories.funcionario import FuncionarioRepositoryMemoria
from gymflux.infra.repositories.matricula import MatriculaRepositoryMemoria
from gymflux.infra.repositories.pagamento import PagamentoRepositoryMemoria
from gymflux.services.identificar_acesso import Identificacao, IdentificarAcessoService
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


def _com_funcionario(svc: IdentificarAcessoService, senha: str = "9999") -> None:
    repo = FuncionarioRepositoryMemoria()
    func = Funcionario(id="f1", nome="Zé Porteira")
    func.definir_senha(senha)
    repo.salvar(func)
    svc.funcionario_repo = repo


def test_funcionario_bypassa_matricula_e_mensalidade():
    svc = _svc()
    _com_funcionario(svc)
    # sem matrícula, sem pagamento: funcionário libera mesmo assim
    decisao, achado = svc.identificar(Identificacao.por_teclado("9999"))
    assert decisao.liberado is True
    assert decisao.resultado == ResultadoAcesso.LIBERADO
    assert "Funcionário" in (decisao.detalhes or "")
    assert achado is None
    # pulso chegou ao hardware (mock sem auto-giro fica desbloqueada)
    assert svc.acesso.driver.status()["bloqueada"] is False


def test_funcionario_inativo_nega_sem_pulsar():
    svc = _svc()
    _com_funcionario(svc)
    repo = svc.funcionario_repo
    assert repo is not None
    func = repo.listar()[0]
    func.inativar()
    repo.salvar(func)
    decisao, achado = svc.identificar(Identificacao.por_teclado("9999"))
    assert decisao.liberado is False
    assert decisao.motivo == MotivoNegado.BLOQUEIO_MANUAL
    assert achado is None
    assert svc.acesso.driver.status()["bloqueada"] is True


def test_funcionario_tem_prioridade_sobre_aluno():
    svc = _svc()
    _adimplente(svc, senha="1234")
    repo = FuncionarioRepositoryMemoria()
    func = Funcionario(id="f1", nome="Zé Porteira")
    func.definir_senha("1234")  # mesma senha do aluno
    repo.salvar(func)
    svc.funcionario_repo = repo
    decisao, achado = svc.identificar(Identificacao.por_teclado("1234"))
    assert decisao.liberado is True
    assert "Funcionário" in (decisao.detalhes or "")
    assert achado is None


def test_sem_repo_funcionario_mantem_fluxo_aluno():
    svc = _svc()
    assert svc.funcionario_repo is None
    _adimplente(svc)
    decisao, achado = svc.identificar(Identificacao.por_teclado("1234"))
    assert decisao.liberado is True
    assert achado is not None and achado.id == "a1"


def test_funcionario_persiste_tentativa_com_funcionario_id():
    svc = _svc()
    _com_funcionario(svc)
    ts = datetime.now()
    decisao, achado = svc.identificar(Identificacao.por_teclado("9999"), timestamp=ts)
    assert decisao.liberado is True
    assert achado is None
    # memória do serviço
    mem = [t for t in svc.acesso.registro.tentativas if t.funcionario_id == "f1"]
    assert len(mem) == 1
    assert mem[0].aluno_id is None
    assert mem[0].timestamp == ts
    # repo injetado (persistido)
    repo = svc.acesso.acesso_repo
    assert repo is not None
    logs = [t for t in repo.listar() if t.funcionario_id == "f1"]
    assert len(logs) == 1
    assert logs[0].resultado == ResultadoAcesso.LIBERADO
