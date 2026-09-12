"""ViewModels Qt-free — só ``services`` + ``core`` (tipos).

NUNCA importam ``hardware/*``, ``infra/*`` ou ``PySide6``. Repositórios
concretos (SQLAlchemy ou memória) são injetados pelo composition root
(``gymflow.ui.app``) via Protocols locais + callback de ``commit``.
"""

from gymflow.ui.viewmodels.alunos import AlunosViewModel
from gymflow.ui.viewmodels.caixa import CaixaViewModel
from gymflow.ui.viewmodels.dashboard import DashboardViewModel
from gymflow.ui.viewmodels.funcionarios import FuncionariosViewModel
from gymflow.ui.viewmodels.pagamentos import PagamentosViewModel
from gymflow.ui.viewmodels.planos import PlanosViewModel

__all__ = [
    "AlunosViewModel",
    "CaixaViewModel",
    "DashboardViewModel",
    "FuncionariosViewModel",
    "PagamentosViewModel",
    "PlanosViewModel",
]
