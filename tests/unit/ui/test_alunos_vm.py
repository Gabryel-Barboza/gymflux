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


def _wired_com_pagamento() -> dict:
    from gymflux.core.plano import Plano

    base = _wired()
    # plano mensal para matrícula + pagamento_repo injetado
    plano = Plano.criar_mensal(id="mensal", nome="Mensal")
    base["alunos"].plano_repo.salvar(plano)  # type: ignore[attr-defined]
    # injeta pagamento_repo (memória do _wired não expõe, recria via pagamentos VM)
    pag_repo = base["pagamentos"].pagamentos.repo  # type: ignore[attr-defined]
    base["alunos"].pagamento_repo = pag_repo  # type: ignore[attr-defined]
    return base


def test_matricular_gera_primeiro_pagamento():
    from datetime import date
    from decimal import Decimal

    w = _wired_com_pagamento()
    aluno = w["alunos"].cadastrar(nome="Novo", cpf="11144477735")
    w["alunos"].matricular(aluno.id, "mensal", inicio=date(2026, 9, 15))
    pags = w["pagamentos"].pagamentos.repo.listar_por_aluno(aluno.id)  # type: ignore[attr-defined]
    assert len(pags) == 1
    pag = pags[0]
    assert pag.competencia == "2026-09"
    assert pag.valor == Decimal("99.90")
    assert pag.data_vencimento == date(2026, 9, 10)
    assert pag.data_pagamento is None


def test_matricular_nao_duplica_mesma_competencia():
    from datetime import date

    w = _wired_com_pagamento()
    aluno = w["alunos"].cadastrar(nome="Novo", cpf="11144477735")
    w["alunos"].matricular(aluno.id, "mensal", inicio=date(2026, 9, 15))
    w["alunos"].matricular(aluno.id, "mensal", inicio=date(2026, 9, 20))
    pags = w["pagamentos"].pagamentos.repo.listar_por_aluno(aluno.id)  # type: ignore[attr-defined]
    assert len(pags) == 1


def test_matricular_trimestral_valor_do_plano():
    from datetime import date
    from decimal import Decimal

    from gymflux.core.plano import Plano

    w = _wired_com_pagamento()
    tri = Plano.criar_trimestral(id="tri", nome="Tri")
    w["alunos"].plano_repo.salvar(tri)  # type: ignore[attr-defined]
    aluno = w["alunos"].cadastrar(nome="Tri Aluno", cpf="22255588846")
    w["alunos"].matricular(aluno.id, "tri", inicio=date(2026, 9, 15))
    pags = w["pagamentos"].pagamentos.repo.listar_por_aluno(aluno.id)  # type: ignore[attr-defined]
    assert len(pags) == 1
    assert pags[0].valor == Decimal("259.90")
    assert pags[0].competencia == "2026-09"


def test_cadastrar_senha_invalida_rejeita():
    w = _wired()
    with pytest.raises(ValueError):
        w["alunos"].cadastrar(nome="Ana", cpf="11144477735", senha="12")


def test_alunos_atualizar_tudo():
    w = _wired()
    aluno = w["alunos"].cadastrar(nome="Ana", cpf="11144477735", senha="1234")
    senha_antes = aluno.senha
    atualizado = w["alunos"].atualizar(
        aluno.id,
        nome="Ana Silva",
        cpf="11144477735",
        data_nasc=date(1990, 5, 1),
        telefone="11999990000",
        email="ana@mail.com",
        observacoes="obs",
        senha="",
        status=StatusAluno.INATIVO,
    )
    assert atualizado.nome == "Ana Silva"
    assert atualizado.telefone == "11999990000"
    assert atualizado.senha == senha_antes  # vazia mantém
    assert atualizado.status == StatusAluno.INATIVO
    # nova senha troca o PIN visível
    atualizado2 = w["alunos"].atualizar(aluno.id, nome="Ana Silva", senha="5678")
    assert atualizado2.senha == "5678"
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
