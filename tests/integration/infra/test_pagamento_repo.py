"""Pagamento repository SQLAlchemy."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from gymflow.core.aluno import Aluno
from gymflow.core.pagamento import Pagamento
from gymflow.infra.repositories.aluno import AlunoRepositorySQLAlchemy
from gymflow.infra.repositories.pagamento import PagamentoRepositorySQLAlchemy


def test_pagamento_crud(session: Session):
    aluno_repo = AlunoRepositorySQLAlchemy(session)
    pag_repo = PagamentoRepositorySQLAlchemy(session)
    aluno = Aluno(id="al-2", nome="Pag Teste", cpf="11122233344")
    aluno_repo.salvar(aluno)
    session.commit()

    hoje = date.today()
    pag = Pagamento(
        id="pag-1",
        aluno_id=aluno.id,
        valor=Decimal("99.90"),
        data_vencimento=hoje,
        data_pagamento=hoje,
    )
    pag_repo.salvar(pag)
    session.commit()
    assert pag_repo.buscar_por_id("pag-1") is not None
    lst = pag_repo.listar_por_aluno(aluno.id)
    assert len(lst) == 1
    assert lst[0].valor == Decimal("99.90")

    # update: muda pagamento para pendente (None)
    pag2 = Pagamento(
        id="pag-1",
        aluno_id=aluno.id,
        valor=Decimal("99.90"),
        data_vencimento=hoje,
        data_pagamento=None,
    )
    pag_repo.salvar(pag2)
    session.commit()
    assert pag_repo.buscar_por_id("pag-1").data_pagamento is None  # type: ignore[union-attr]

    # segundo pagamento
    pag3 = Pagamento(
        id="pag-2",
        aluno_id=aluno.id,
        valor=Decimal("99.90"),
        data_vencimento=hoje + timedelta(days=30),
    )
    pag_repo.salvar(pag3)
    session.commit()
    assert pag_repo.total() == 2
    assert len(pag_repo.listar_por_aluno(aluno.id)) == 2
