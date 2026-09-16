"""Perf Caixa — pushdown mede refresh <1s com 2k pagamentos."""

from __future__ import annotations

import calendar
import random
import time
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from gymflux.core.pagamento import FormaPagamento
from gymflux.core.plano import Plano
from gymflux.infra.db import get_session, init_db, reset_engine
from gymflux.infra.models.aluno import AlunoModel
from gymflux.infra.models.pagamento import PagamentoModel
from gymflux.infra.models.plano import PlanoModel
from gymflux.infra.repositories.aluno import AlunoRepositorySQLAlchemy
from gymflux.infra.repositories.fechamento_caixa import FechamentoCaixaRepositorySQLAlchemy
from gymflux.infra.repositories.pagamento import PagamentoRepositorySQLAlchemy
from gymflux.services.cadastrar_aluno import CadastrarAlunoService
from gymflux.services.registrar_pagamento import RegistrarPagamentoService
from gymflux.ui.viewmodels.caixa import CaixaViewModel


@pytest.mark.slow
def test_caixa_refresh_pushdown_2k_menos_1s(tmp_path):  # type: ignore[no-untyped-def]
    # DB isolado :memory: via arquivo tmp
    db_path = tmp_path / "perf.db"
    url = f"sqlite:///{db_path}"
    reset_engine()
    init_db(url)
    sess = get_session(url)
    # planos
    for p in [Plano.criar_mensal(), Plano.criar_trimestral(), Plano.criar_anual()]:
        sess.add(
            PlanoModel(
                id=p.id,
                nome=p.nome,
                duracao_dias=p.duracao_dias,
                valor=p.valor,
                tolerancia_dias=p.tolerancia_dias,
                tipo=p.tipo.value,
            )
        )
    sess.commit()
    qtd = 2000
    formas = [f.value for f in FormaPagamento]
    hoje = date.today()
    venc = date(hoje.year, hoje.month, min(15, calendar.monthrange(hoje.year, hoje.month)[1]))
    comp = venc.strftime("%Y-%m")
    for i in range(qtd):
        seq = i + 1000
        aluno_id = f"aluno-perf-{seq:05d}-{uuid.uuid4().hex[:4]}"
        sess.add(
            AlunoModel(
                id=aluno_id,
                nome=f"Aluno Perf {seq:05d}",
                cpf=str(10000000000 + seq).zfill(11),
                telefone="11999999999",
                email=f"p{i}@t.test",
                data_nasc=date(1990, 1, 1),
                status="ATIVO",
                bloqueado_manual=False,
                senha=f"{random.randint(1000, 9999):04d}",
            )
        )
        # pagamento pendente
        sess.add(
            PagamentoModel(
                id=f"pag-{uuid.uuid4().hex[:8]}",
                aluno_id=aluno_id,
                valor=Decimal("99.90"),
                vencimento=venc,
                data_pagamento=None,
                forma=None,
                competencia=comp,
            )
        )
        if i % 3 == 0:
            venc2 = venc - timedelta(days=30)
            sess.add(
                PagamentoModel(
                    id=f"pag-{uuid.uuid4().hex[:8]}",
                    aluno_id=aluno_id,
                    valor=Decimal("99.90"),
                    vencimento=venc2,
                    data_pagamento=venc2,
                    forma=random.choice(formas),
                    competencia=venc2.strftime("%Y-%m"),
                )
            )
        if (i + 1) % 500 == 0:
            sess.commit()
    sess.commit()

    pag_repo = PagamentoRepositorySQLAlchemy(sess)
    alu_repo = AlunoRepositorySQLAlchemy(sess)
    pag_svc = RegistrarPagamentoService(repo=pag_repo)
    alu_svc = CadastrarAlunoService(repo=alu_repo)
    fec_repo = FechamentoCaixaRepositorySQLAlchemy(sess)
    vm = CaixaViewModel(pagamentos=pag_svc, alunos=alu_svc, fechamentos=fec_repo)

    # warmup
    vm.meses_disponiveis()
    vm.totais_mes(None)
    vm.por_mes(None, limit=500, offset=0)
    vm.contar_por_mes(None)

    t0 = time.perf_counter()
    vm.meses_disponiveis()
    t1 = time.perf_counter()
    vm.totais_mes(None)
    t2 = time.perf_counter()
    vm.contar_por_mes(None)
    t3 = time.perf_counter()
    vm.por_mes(None, limit=500, offset=0)
    t4 = time.perf_counter()
    total = t4 - t0
    print(
        f"perf 2k: meses {(t1 - t0) * 1000:.0f} totais {(t2 - t1) * 1000:.0f} "
        f"contar {(t3 - t2) * 1000:.0f} por_mes {(t4 - t3) * 1000:.0f} total {total * 1000:.0f}ms"
    )
    # meta task: <1s (pushdown) e ideal <200ms no real 7k; com 2k já deve ficar <500ms
    assert total < 1.0, f"refresh 2k demorou {total:.2f}s esperado <1s (pushdown falhou)"
    # também testa paginação offset
    segunda = vm.por_mes(None, limit=500, offset=500)
    assert len(segunda) > 0
    # totais via SUM deve bater com cálculo manual da página? verifica não-break
    recebido, pendente, geral = vm.totais_mes(None)
    assert geral == recebido + pendente
    sess.close()
    reset_engine()
