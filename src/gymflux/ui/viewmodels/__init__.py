"""ViewModels Qt-free — só ``services`` + ``core`` (tipos).

NUNCA importam ``hardware/*``, ``infra/*`` ou ``PySide6``. Repositórios
concretos (SQLAlchemy ou memória) são injetados pelo composition root
(``gymflux.ui.app``) via Protocols locais + callback de ``commit``.
"""

from gymflux.ui.viewmodels.alunos import AlunosViewModel
from gymflux.ui.viewmodels.caixa import CaixaViewModel
from gymflux.ui.viewmodels.dashboard import DashboardViewModel
from gymflux.ui.viewmodels.frequencia import FrequenciaViewModel
from gymflux.ui.viewmodels.funcionarios import FuncionariosViewModel
from gymflux.ui.viewmodels.planos import PlanosViewModel

__all__ = [
    "AlunosViewModel",
    "CaixaViewModel",
    "DashboardViewModel",
    "FrequenciaViewModel",
    "FuncionariosViewModel",
    "PlanosViewModel",
]
