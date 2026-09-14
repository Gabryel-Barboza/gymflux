"""CaixaViewModel — filtro por mês, totais, selo e bloqueio de mês fechado."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from gymflux.core.aluno import Aluno
from gymflux.core.caixa import validar_mes
from gymflux.infra.repositories.fechamento_caixa import FechamentoCaixaRepositoryMemoria
from gymflux.services.cadastrar_aluno import (
    CadastrarAlunoService,
    RepositorioAlunosMemoria,
)
from gymflux.services.registrar_pagamento import (
    RegistrarPagamentoService,
    RepositorioPagamentosMemoria,
)
from gymflux.ui.viewmodels.caixa import CaixaViewModel


def _caixa() -> CaixaViewModel:
    alunos = CadastrarAlunoService(repo=RepositorioAlunosMemoria())
    pagamentos = RegistrarPagamentoService(repo=RepositorioPagamentosMemoria())
    return CaixaViewModel(
        pagamentos=pagamentos,
        alunos=alunos,
        fechamentos=FechamentoCaixaRepositoryMemoria(),
    )


def _aluno(vm: CaixaViewModel, nome: str = "Ana") -> str:
    return vm.alunos.cadastrar(Aluno(id=f"aluno-{nome.lower()}", nome=nome)).id


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


def test_reabrir_mes_e_reusar_competencia():
    vm = _caixa()
    aluno_id = _aluno(vm)
    vm.registrar(
        aluno_id=aluno_id,
        valor="100.00",
        data_vencimento=date(2026, 9, 10),
        competencia="2026-09",
    )
    vm.fechar_mes("2026-09")
    assert vm.mes_fechado("2026-09") is True
    vm.reabrir_mes("2026-09")
    assert vm.mes_fechado("2026-09") is False
    # após reabrir, registra de novo na mesma competência
    vm.registrar(
        aluno_id=aluno_id,
        valor="10.00",
        data_vencimento=date(2026, 9, 20),
        competencia="2026-09",
    )
    assert len(vm.por_mes("2026-09")) == 2
    # reabrir mês não fechado deve falhar
    with pytest.raises(ValueError, match="não está fechado"):
        vm.reabrir_mes("2026-09")


def test_forma_none_default_pix():
    vm = _caixa()
    aluno_id = _aluno(vm)
    pag = vm.registrar(
        aluno_id=aluno_id,
        valor="50.00",
        data_vencimento=date(2026, 9, 10),
        forma=None,
    )
    # bug que quebrou 20 testes: forma=None deve virar PIX, não None
    assert pag.forma == "PIX" or str(pag.forma) == "PIX"
    # forma vazia string deve falhar (não cair no default)
    with pytest.raises(ValueError):
        vm.registrar(aluno_id=aluno_id, valor="50.00", data_vencimento=date(2026, 9, 10), forma="")
