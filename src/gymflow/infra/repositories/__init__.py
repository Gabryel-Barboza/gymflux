"""Repositories package — re-exporta protocolos e impls."""

from __future__ import annotations

from gymflow.infra.repositories.acesso_log import (
    AcessoLogRepository,
    AcessoLogRepositoryMemoria,
    AcessoLogRepositorySQLAlchemy,
)
from gymflow.infra.repositories.aluno import (
    AlunoRepository,
    AlunoRepositoryMemoria,
    AlunoRepositorySQLAlchemy,
)
from gymflow.infra.repositories.matricula import (
    MatriculaRepository,
    MatriculaRepositoryMemoria,
    MatriculaRepositorySQLAlchemy,
)
from gymflow.infra.repositories.pagamento import (
    PagamentoRepository,
    PagamentoRepositoryMemoria,
    PagamentoRepositorySQLAlchemy,
)
from gymflow.infra.repositories.plano import (
    PlanoRepository,
    PlanoRepositoryMemoria,
    PlanoRepositorySQLAlchemy,
)

__all__ = [
    "AcessoLogRepository",
    "AcessoLogRepositoryMemoria",
    "AcessoLogRepositorySQLAlchemy",
    "AlunoRepository",
    "AlunoRepositoryMemoria",
    "AlunoRepositorySQLAlchemy",
    "MatriculaRepository",
    "MatriculaRepositoryMemoria",
    "MatriculaRepositorySQLAlchemy",
    "PagamentoRepository",
    "PagamentoRepositoryMemoria",
    "PagamentoRepositorySQLAlchemy",
    "PlanoRepository",
    "PlanoRepositoryMemoria",
    "PlanoRepositorySQLAlchemy",
]
