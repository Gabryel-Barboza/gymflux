"""Models package — re-exporta 8 models Typed."""

from __future__ import annotations

# import para registrar no Base (evita F401)
import gymflux.infra.models.avaliacao_fisica as _avaliacao_fisica  # noqa: F401
from gymflux.infra.models.acesso_log import AcessoLogModel
from gymflux.infra.models.aluno import AlunoModel
from gymflux.infra.models.avaliacao_fisica import AvaliacaoFisicaModel
from gymflux.infra.models.fechamento_caixa import FechamentoCaixaModel
from gymflux.infra.models.funcionario import FuncionarioModel
from gymflux.infra.models.matricula import MatriculaModel
from gymflux.infra.models.pagamento import PagamentoModel
from gymflux.infra.models.plano import PlanoModel

__all__ = [
    "AcessoLogModel",
    "AlunoModel",
    "AvaliacaoFisicaModel",
    "FechamentoCaixaModel",
    "FuncionarioModel",
    "MatriculaModel",
    "PagamentoModel",
    "PlanoModel",
]
