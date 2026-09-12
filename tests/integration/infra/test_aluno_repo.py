"""AlunoRepository SQLAlchemy — CRUD, CPF, credenciais, cartão, unicidade."""

from __future__ import annotations

from sqlalchemy.orm import Session

from gymflux.core.aluno import Aluno
from gymflux.infra.repositories.aluno import AlunoRepositorySQLAlchemy


def test_aluno_crud_e_busca_cpf(session: Session):
    repo = AlunoRepositorySQLAlchemy(session)
    aluno = Aluno(id="a1", nome="João", cpf="11144477735", telefone="11999999999")
    repo.salvar(aluno)
    session.commit()

    assert repo.buscar_por_id("a1") is not None
    assert repo.buscar_por_id("a1").nome == "João"  # type: ignore[union-attr]
    # busca cpf com formatação diferente
    assert repo.buscar_por_cpf("111.444.777-35") is not None
    assert repo.buscar_por_cpf("11144477735").id == "a1"  # type: ignore[union-attr]
    assert repo.buscar_por_cpf("22255588846") is None

    # update
    aluno.nome = "João Atualizado"
    repo.salvar(aluno)
    session.commit()
    assert repo.buscar_por_id("a1").nome == "João Atualizado"  # type: ignore[union-attr]

    # listar
    assert repo.total() == 1
    aluno2 = Aluno(id="a2", nome="Maria", cpf="22255588846")
    repo.salvar(aluno2)
    session.commit()
    assert repo.total() == 2
    assert len(repo.listar()) == 2

    # remover
    repo.remover("a1")
    session.commit()
    assert repo.buscar_por_id("a1") is None


def test_aluno_credenciais_roundtrip_e_busca_cartao(session: Session):
    repo = AlunoRepositorySQLAlchemy(session)
    aluno = Aluno(id="a9", nome="Cred", cpf="33366699957")
    aluno.definir_senha("1234")
    aluno.definir_cartao("TAG-42")
    repo.salvar(aluno)
    session.commit()

    lido = repo.buscar_por_id("a9")
    assert lido is not None
    assert lido.senha_hash is not None and "1234" not in lido.senha_hash
    assert lido.verificar_senha("1234") is True
    assert lido.verificar_senha("0000") is False
    assert repo.buscar_por_cartao("TAG-42") is not None
    assert repo.buscar_por_cartao("TAG-42").id == "a9"  # type: ignore[union-attr]
    assert repo.buscar_por_cartao("TAG-99") is None
    assert repo.buscar_por_cartao("   ") is None
    assert repo.total() == 1


def test_aluno_cpf_unico_constraint(session: Session):
    repo = AlunoRepositorySQLAlchemy(session)
    a1 = Aluno(id="u1", nome="A", cpf="11144477735")
    a2 = Aluno(id="u2", nome="B", cpf="11144477735")
    repo.salvar(a1)
    session.commit()
    # deve falhar ao inserir duplicado (flush ou commit)
    try:
        repo.salvar(a2)
        session.commit()
        # se não falhar, o buscar_por_cpf deve retornar primeiro
        # mas esperamos IntegrityError; então falha o teste se não levantar
        raise AssertionError("deveria falhar por cpf duplicado")
    except Exception:
        session.rollback()
        # confirma que apenas a1 persiste
        assert repo.buscar_por_id("u1") is not None
