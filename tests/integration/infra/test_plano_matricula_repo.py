"""Plano + Matrícula repositories SQLAlchemy."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from gymflow.core.aluno import Aluno
from gymflow.core.plano import Matricula, Plano, Vigencia
from gymflow.infra.repositories.aluno import AlunoRepositorySQLAlchemy
from gymflow.infra.repositories.matricula import MatriculaRepositorySQLAlchemy
from gymflow.infra.repositories.plano import PlanoRepositorySQLAlchemy


def test_plano_crud(session: Session):
    repo = PlanoRepositorySQLAlchemy(session)
    plano = Plano.criar_mensal(id="mensal", nome="Mensal", valor=Decimal("99.90"))
    repo.salvar(plano)
    session.commit()
    assert repo.buscar_por_id("mensal") is not None
    assert repo.buscar_por_id("mensal").valor == Decimal("99.90")  # type: ignore[union-attr]
    assert repo.total() == 1
    # update valor
    plano2 = Plano(
        id="mensal",
        nome="Mensal Atualizado",
        duracao_dias=30,
        valor=Decimal("109.90"),
        tolerancia_dias=3,
        tipo=plano.tipo,
    )
    repo.salvar(plano2)
    session.commit()
    assert repo.buscar_por_id("mensal").nome == "Mensal Atualizado"  # type: ignore[union-attr]

    # trimestral
    tri = Plano.criar_trimestral()
    repo.salvar(tri)
    session.commit()
    assert repo.total() == 2


def test_matricula_vigente(session: Session):
    plano_repo = PlanoRepositorySQLAlchemy(session)
    aluno_repo = AlunoRepositorySQLAlchemy(session)
    mat_repo = MatriculaRepositorySQLAlchemy(session)

    plano = Plano.criar_mensal(id="mensal")
    plano_repo.salvar(plano)
    aluno = Aluno(id="al-1", nome="Teste", cpf="12345678901")
    aluno_repo.salvar(aluno)
    session.commit()

    hoje = date.today()
    vigencia = Vigencia.a_partir_de(hoje, duracao_dias=30)
    mat = Matricula(aluno_id=aluno.id, plano=plano, vigencia=vigencia, ativa=True)
    mat_repo.salvar(mat, matricula_id="mat-1")
    session.commit()

    # vigente hoje
    vigente = mat_repo.buscar_vigente(aluno.id, hoje)
    assert vigente is not None
    assert vigente.aluno_id == aluno.id

    # fora vigência (após fim)
    futuro = vigencia.fim + timedelta(days=1)
    assert mat_repo.buscar_vigente(aluno.id, futuro) is None

    # antes do inicio
    antes = vigencia.inicio - timedelta(days=1)
    assert mat_repo.buscar_vigente(aluno.id, antes) is None

    # inativa não vigente
    # cria matricula inativa
    vigencia2 = Vigencia.a_partir_de(hoje, duracao_dias=30)
    mat2 = Matricula(aluno_id=aluno.id, plano=plano, vigencia=vigencia2, ativa=False)
    mat_repo.salvar(mat2, matricula_id="mat-2")
    session.commit()
    # buscar vigente ainda deve retornar mat-1 (ativa), não mat-2
    assert mat_repo.buscar_vigente(aluno.id, hoje).ativa is True  # type: ignore[union-attr]

    # listar por aluno
    assert len(mat_repo.listar_por_aluno(aluno.id)) == 2
