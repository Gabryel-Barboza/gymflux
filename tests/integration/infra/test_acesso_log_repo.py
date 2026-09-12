"""AcessoLog repository SQLAlchemy (aluno + funcionário)."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from gymflow.core.acesso import DirecaoAcesso, ResultadoAcesso, TentativaAcesso
from gymflow.core.aluno import Aluno
from gymflow.core.funcionario import Funcionario
from gymflow.infra.repositories.acesso_log import AcessoLogRepositorySQLAlchemy
from gymflow.infra.repositories.aluno import AlunoRepositorySQLAlchemy
from gymflow.infra.repositories.funcionario import FuncionarioRepositorySQLAlchemy


def test_acesso_log(session: Session):
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


def test_acesso_log_funcionario_id_nullable(session: Session):
    func_repo = FuncionarioRepositorySQLAlchemy(session)
    acesso_repo = AcessoLogRepositorySQLAlchemy(session)
    func = Funcionario(id="f9", nome="Zé Porteira")
    func_repo.salvar(func)
    session.commit()

    now = datetime.now()
    t = TentativaAcesso(
        aluno_id=None,
        funcionario_id="f9",
        direcao=DirecaoAcesso.ENTRADA,
        timestamp=now,
        resultado=ResultadoAcesso.LIBERADO,
        detalhes="Funcionário — Zé Porteira",
        catraca_id="catraca-1",
    )
    acesso_repo.registrar(t)
    session.commit()
    logs = acesso_repo.listar()
    assert len(logs) == 1
    assert logs[0].funcionario_id == "f9"
    assert logs[0].aluno_id is None
    assert logs[0].resultado == ResultadoAcesso.LIBERADO
