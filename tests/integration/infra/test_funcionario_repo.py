"""Funcionario repository SQLAlchemy."""

from __future__ import annotations

from sqlalchemy.orm import Session

from gymflux.core.funcionario import Funcionario
from gymflux.infra.repositories.funcionario import FuncionarioRepositorySQLAlchemy


def test_funcionario_crud_sql(session: Session):
    repo = FuncionarioRepositorySQLAlchemy(session)
    func = Funcionario(id="f1", nome="Zé Porteira")
    func.definir_senha("1234")
    repo.salvar(func)
    session.commit()

    lido = repo.buscar_por_id("f1")
    assert lido is not None
    assert lido.nome == "Zé Porteira"
    assert lido.ativo is True
    assert lido.senha_hash is not None and "1234" not in lido.senha_hash
    assert lido.verificar_senha("1234") is True
    assert lido.verificar_senha("0000") is False

    lido.inativar()
    repo.salvar(lido)
    session.commit()
    assert repo.buscar_por_id("f1").ativo is False  # type: ignore[union-attr]
    assert repo.total() == 1
    repo.remover("f1")
    session.commit()
    assert repo.buscar_por_id("f1") is None
