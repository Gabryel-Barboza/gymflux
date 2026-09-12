"""Repositories package — re-exporta protocolos e impls."""

from __future__ import annotations

from gymflux.infra.repositories.acesso_log import (
    AcessoLogRepository,
    AcessoLogRepositoryMemoria,
    AcessoLogRepositorySQLAlchemy,
)
from gymflux.infra.repositories.aluno import (
    AlunoRepository,
    AlunoRepositoryMemoria,
    AlunoRepositorySQLAlchemy,
)
from gymflux.infra.repositories.fechamento_caixa import (
    FechamentoCaixaRepository,
    FechamentoCaixaRepositoryMemoria,
    FechamentoCaixaRepositorySQLAlchemy,
)
from gymflux.infra.repositories.funcionario import (
    FuncionarioRepository,
    FuncionarioRepositoryMemoria,
    FuncionarioRepositorySQLAlchemy,
)
from gymflux.infra.repositories.matricula import (
    MatriculaRepository,
    MatriculaRepositoryMemoria,
    MatriculaRepositorySQLAlchemy,
)
from gymflux.infra.repositories.pagamento import (
    PagamentoRepository,
    PagamentoRepositoryMemoria,
    PagamentoRepositorySQLAlchemy,
)
from gymflux.infra.repositories.plano import (
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
    "FechamentoCaixaRepository",
    "FechamentoCaixaRepositoryMemoria",
    "FechamentoCaixaRepositorySQLAlchemy",
    "FuncionarioRepository",
    "FuncionarioRepositoryMemoria",
    "FuncionarioRepositorySQLAlchemy",
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
