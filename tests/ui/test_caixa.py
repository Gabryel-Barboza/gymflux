"""CaixaViewModel — filtro por mês, totais, selo e bloqueio de mês fechado."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from gymflow.core.aluno import Aluno
from gymflow.core.caixa import validar_mes
from gymflow.infra.repositories.fechamento_caixa import FechamentoCaixaRepositoryMemoria
from gymflow.services.cadastrar_aluno import (
    CadastrarAlunoService,
    RepositorioAlunosMemoria,
)
from gymflow.services.registrar_pagamento import (
    RegistrarPagamentoService,
    RepositorioPagamentosMemoria,
)
from gymflow.ui.viewmodels.caixa import CaixaViewModel
from gymflow.ui.viewmodels.pagamentos import PagamentosViewModel


def _caixa() -> CaixaViewModel:
    alunos = CadastrarAlunoService(repo=RepositorioAlunosMemoria())
    pagamentos = PagamentosViewModel(
        pagamentos=RegistrarPagamentoService(repo=RepositorioPagamentosMemoria()),
        alunos=alunos,
    )
    return CaixaViewModel(pagamentos=pagamentos, fechamentos=FechamentoCaixaRepositoryMemoria())


def _aluno(vm: CaixaViewModel, nome: str = "Ana") -> str:
    return vm.pagamentos.alunos.cadastrar(Aluno(id=f"aluno-{nome.lower()}", nome=nome)).id


def test_validar_mes():
    assert validar_mes("2026-09") == "2026-09"
    assert validar_mes(" 2026-01 ") == "2026-01"
    with pytest.raises(ValueError):
        validar_mes("09/2026")
    with pytest.raises(ValueError):
        validar_mes("2026-13")
    with pytest.raises(ValueError):
        validar_mes("")


def test_meses_totais_e_filtro():
    vm = _caixa()
    deAluno = _aluno(vm)
    vm.registrar(
        aluno_id=deAluno,
        valor="100.00",
        data_vencimento=date(2026, 9, 10),
        pago=True,
        competencia="2026-09",
    )
    vm.registrar(
        aluno_id=deAluno,
        valor="50.00",
        data_vencimento=date(2026, 10, 5),
        competencia="2026-10",
    )
    assert vm.meses_disponiveis() == ["2026-10", "2026-09"]
    recebido, pendente, total = vm.totais_mes("2026-09")
    assert (recebido, pendente, total) == (Decimal("100.00"), Decimal("0"), Decimal("100.00"))
    recebido, pendente, total = vm.totais_mes(None)
    assert (recebido, pendente, total) == (Decimal("100.00"), Decimal("50.00"), Decimal("150.00"))
    linhas = vm.por_mes("2026-10")
    assert len(linhas) == 1 and linhas[0][1] == "Ana"
    assert len(vm.por_mes(None)) == 2


def test_fechar_bloqueia_registro_e_selo():
    vm = _caixa()
    aluno_id = _aluno(vm)
    vm.registrar(
        aluno_id=aluno_id,
        valor="100.00",
        data_vencimento=date(2026, 9, 10),
        pago=True,
        competencia="2026-09",
    )
    assert vm.mes_fechado("2026-09") is False
    fechamento = vm.fechar_mes("2026-09")
    assert fechamento.total == Decimal("100.00")
    assert fechamento.fechado_em is not None
    assert vm.mes_fechado("2026-09") is True
    assert vm.fechado_em("2026-09") == fechamento.fechado_em
    with pytest.raises(ValueError, match="FECHADO"):
        vm.registrar(
            aluno_id=aluno_id,
            valor="10.00",
            data_vencimento=date(2026, 9, 20),
            competencia="2026-09",
        )
    with pytest.raises(ValueError, match="já está fechado"):
        vm.fechar_mes("2026-09")
    # outro mês segue livre
    vm.registrar(
        aluno_id=aluno_id,
        valor="10.00",
        data_vencimento=date(2026, 10, 1),
        competencia="2026-10",
    )
    assert len(vm.por_mes("2026-10")) == 1


def test_mes_derivado_do_vencimento_quando_sem_competencia():
    vm = _caixa()
    aluno_id = _aluno(vm)
    vm.registrar(aluno_id=aluno_id, valor="30.00", data_vencimento=date(2026, 8, 15))
    assert vm.meses_disponiveis() == ["2026-08"]
    with pytest.raises(ValueError, match="AAAA-MM"):
        vm.registrar(
            aluno_id=aluno_id,
            valor="30.00",
            data_vencimento=date(2026, 8, 15),
            competencia="agosto",
        )
