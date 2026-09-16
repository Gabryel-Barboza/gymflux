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
    with pytest.raises(ValueError, match="fechado"):
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


def test_buscar_fallback_memoria_filtra_por_nome():
    vm = _caixa()
    ana = _aluno(vm, "Ana Souza")
    bruno = _aluno(vm, "Bruno Lima")
    vm.registrar(
        aluno_id=ana,
        valor="100.00",
        data_vencimento=date(2026, 9, 10),
        competencia="2026-09",
    )
    vm.registrar(
        aluno_id=bruno,
        valor="50.00",
        data_vencimento=date(2026, 9, 5),
        competencia="2026-09",
    )
    rows = vm.buscar("2026-09", "ana")
    assert [n for _, n in rows] == ["Ana Souza"]
    assert vm.contar_busca("2026-09", "ana") == 1
    assert vm.buscar("2026-09", "zzz") == []
    assert vm.contar_busca("2026-09", "zzz") == 0
    # termo vazio = por_mes normal
    assert len(vm.buscar("2026-09", "  ")) == 2
    # case-insensitive + paginação do fallback
    assert len(vm.buscar("2026-09", "A", limit=1, offset=1)) == 1


def test_buscar_sql_join_paridade(tmp_path):
    """JOIN+LIKE retorna o mesmo que o filtro Python (paridade SQL x fallback)."""
    from gymflux.infra.db import get_session, init_db, reset_engine
    from gymflux.infra.models.aluno import AlunoModel
    from gymflux.infra.models.pagamento import PagamentoModel
    from gymflux.infra.repositories.aluno import AlunoRepositorySQLAlchemy
    from gymflux.infra.repositories.fechamento_caixa import (
        FechamentoCaixaRepositorySQLAlchemy,
    )
    from gymflux.infra.repositories.pagamento import PagamentoRepositorySQLAlchemy

    url = f"sqlite:///{tmp_path}/busca.db"
    reset_engine()
    init_db(url)
    sess = get_session(url)
    try:
        for i, nome in enumerate(["Ana Souza", "Bruno Lima", "Anacleto Silva"]):
            aid = f"aluno-busca-{i}"
            sess.add(
                AlunoModel(
                    id=aid,
                    nome=nome,
                    status="ATIVO",
                    bloqueado_manual=False,
                )
            )
            sess.add(
                PagamentoModel(
                    id=f"pag-busca-{i}",
                    aluno_id=aid,
                    valor=Decimal("10.00"),
                    vencimento=date(2026, 9, 10),
                    competencia="2026-09",
                )
            )
        sess.commit()
        vm = CaixaViewModel(
            pagamentos=RegistrarPagamentoService(repo=PagamentoRepositorySQLAlchemy(sess)),
            alunos=CadastrarAlunoService(repo=AlunoRepositorySQLAlchemy(sess)),
            fechamentos=FechamentoCaixaRepositorySQLAlchemy(sess),
        )
        rows = vm.buscar("2026-09", "ana")
        assert sorted(n for _, n in rows) == ["Ana Souza", "Anacleto Silva"]
        assert vm.contar_busca("2026-09", "ana") == 2
        # ordenado por vencimento desc + paginação
        pag1 = vm.buscar("2026-09", "ana", limit=1, offset=0)
        pag2 = vm.buscar("2026-09", "ana", limit=1, offset=1)
        assert len(pag1) == len(pag2) == 1
        assert pag1[0][0].id != pag2[0][0].id
        assert vm.contar_busca("2026-08", "ana") == 0
    finally:
        sess.close()
        reset_engine()


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
