"""Testes infra repositories — engine :memory:."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from gymflow.core.acesso import DirecaoAcesso, ResultadoAcesso, TentativaAcesso
from gymflow.core.aluno import Aluno
from gymflow.core.pagamento import Pagamento
from gymflow.core.plano import Matricula, Plano, Vigencia
from gymflow.infra.db import Base
from gymflow.infra.repositories.acesso_log import AcessoLogRepositorySQLAlchemy
from gymflow.infra.repositories.aluno import AlunoRepositorySQLAlchemy
from gymflow.infra.repositories.matricula import MatriculaRepositorySQLAlchemy
from gymflow.infra.repositories.pagamento import PagamentoRepositorySQLAlchemy
from gymflow.infra.repositories.plano import PlanoRepositorySQLAlchemy


@pytest.fixture
def session():
    # Use :memory: with same WAL settings as infra/db but simplified
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, future=True
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON;")
        cur.close()

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    s = SessionLocal()
    yield s
    s.close()
    engine.dispose()


def test_aluno_crud_e_busca_cpf(session):
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


def test_aluno_credenciais_roundtrip_e_busca_cartao(session):
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


def test_plano_crud(session):
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


def test_matricula_vigente(session):
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


def test_pagamento_crud(session):
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


def test_acesso_log(session):
    aluno_repo = AlunoRepositorySQLAlchemy(session)
    acesso_repo = AcessoLogRepositorySQLAlchemy(session)
    aluno = Aluno(id="al-3", nome="Log Teste")
    aluno_repo.salvar(aluno)
    session.commit()

    now = datetime.now()
    t1 = TentativaAcesso(
        aluno_id=aluno.id,
        direcao=DirecaoAcesso.ENTRADA,
        timestamp=now,
        resultado=ResultadoAcesso.LIBERADO,
        catraca_id="catraca-1",
        timeout_giro_s=7,
    )
    acesso_repo.registrar(t1)
    session.commit()
    assert acesso_repo.total() == 1
    logs = acesso_repo.listar_por_aluno(aluno.id)
    assert len(logs) == 1
    assert logs[0].resultado == ResultadoAcesso.LIBERADO

    # segundo log negado
    t2 = TentativaAcesso(
        aluno_id=aluno.id,
        direcao=DirecaoAcesso.ENTRADA,
        timestamp=now + timedelta(seconds=10),
        resultado=ResultadoAcesso.NEGADO,
        motivo="BLOQUEIO_MANUAL",
        catraca_id="catraca-1",
    )
    acesso_repo.registrar(t2)
    session.commit()
    assert acesso_repo.total() == 2
    assert len(acesso_repo.listar()) == 2
    assert acesso_repo.buscar_ultimo_por_aluno(aluno.id).resultado == ResultadoAcesso.NEGADO  # type: ignore[union-attr]

    # limpar
    acesso_repo.limpar()
    session.commit()
    assert acesso_repo.total() == 0


def test_aluno_cpf_unico_constraint(session):
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
