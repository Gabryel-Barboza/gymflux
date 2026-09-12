"""Composition root da UI — ÚNICO lugar da UI que importa ``infra``/``hardware``.

Monta ``Session`` + repos + services + bridge + ViewModels + janela.
ViewModels/Views recebem dependências prontas (nunca importam infra/hardware).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from loguru import logger
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
from sqlalchemy.orm import Session

from gymflow.services.cadastrar_aluno import CadastrarAlunoService
from gymflow.services.liberar_acesso import LiberarAcessoService
from gymflow.services.registrar_pagamento import RegistrarPagamentoService
from gymflow.ui.catraca_bridge import CatracaBridge
from gymflow.ui.viewmodels.alunos import AlunosViewModel
from gymflow.ui.viewmodels.dashboard import DashboardViewModel
from gymflow.ui.viewmodels.pagamentos import PagamentosViewModel
from gymflow.ui.viewmodels.planos import PlanosViewModel
from gymflow.ui.views.alunos import AlunosView
from gymflow.ui.views.dashboard import DashboardView
from gymflow.ui.views.pagamentos import PagamentosView
from gymflow.ui.views.planos import PlanosView


@dataclass
class AppContext:
    """Tudo que a janela precisa — criado por ``create_context``."""

    bridge: CatracaBridge
    dashboard_vm: DashboardViewModel
    alunos_vm: AlunosViewModel
    planos_vm: PlanosViewModel
    pagamentos_vm: PagamentosViewModel
    session: Session | None = None
    commit: Callable[[], None] | None = None

    def close(self) -> None:
        if self.session is not None:
            try:
                self.session.close()
            except Exception as e:
                logger.warning(f"[UI] session.close falhou: {e}")
            self.session = None


def _ensure_schema() -> None:
    """Garante tabelas: alembic upgrade head (se alembic.ini) ou create_all."""
    from pathlib import Path

    ini = Path("alembic.ini")
    if ini.exists():
        from alembic import command
        from alembic.config import Config

        cfg = Config(str(ini))
        command.upgrade(cfg, "head")
    else:
        from gymflow.infra.db import init_db

        init_db()


def _safe_commit(session: Session) -> Callable[[], None]:
    def _do() -> None:
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise

    return _do


def create_context(use_db: bool = True) -> AppContext:
    """Monta repos + services + VMs. Sem DB (ou falha) => fallback memória."""
    from gymflow.config.settings import get_settings

    settings = get_settings()
    bridge = CatracaBridge(porta=settings.henry_porta)

    if use_db:
        try:
            _ensure_schema()
            from gymflow.infra.db import get_session
            from gymflow.infra.repositories.acesso_log import AcessoLogRepositorySQLAlchemy
            from gymflow.infra.repositories.aluno import AlunoRepositorySQLAlchemy
            from gymflow.infra.repositories.matricula import MatriculaRepositorySQLAlchemy
            from gymflow.infra.repositories.pagamento import PagamentoRepositorySQLAlchemy
            from gymflow.infra.repositories.plano import PlanoRepositorySQLAlchemy

            session = get_session()
            aluno_repo: Any = AlunoRepositorySQLAlchemy(session)
            plano_repo: Any = PlanoRepositorySQLAlchemy(session)
            mat_repo: Any = MatriculaRepositorySQLAlchemy(session)
            pag_repo: Any = PagamentoRepositorySQLAlchemy(session)
            acesso_repo: Any = AcessoLogRepositorySQLAlchemy(session)
            commit = _safe_commit(session)
            logger.info("[UI] contexto com SQLite")
            return _wire(
                bridge,
                aluno_repo,
                plano_repo,
                mat_repo,
                pag_repo,
                acesso_repo,
                session=session,
                commit=commit,
            )
        except Exception as e:
            logger.warning(f"[UI] DB indisponível ({e}) — fallback memória")

    from gymflow.infra.repositories.acesso_log import AcessoLogRepositoryMemoria
    from gymflow.infra.repositories.matricula import MatriculaRepositoryMemoria
    from gymflow.infra.repositories.plano import PlanoRepositoryMemoria
    from gymflow.services.cadastrar_aluno import RepositorioAlunosMemoria
    from gymflow.services.registrar_pagamento import RepositorioPagamentosMemoria

    logger.info("[UI] contexto em memória (sem persistência)")
    return _wire(
        bridge,
        RepositorioAlunosMemoria(),
        PlanoRepositoryMemoria(),
        MatriculaRepositoryMemoria(),
        RepositorioPagamentosMemoria(),
        AcessoLogRepositoryMemoria(),
    )


def _wire(
    bridge: CatracaBridge,
    aluno_repo: Any,
    plano_repo: Any,
    mat_repo: Any,
    pag_repo: Any,
    acesso_repo: Any,
    session: Session | None = None,
    commit: Callable[[], None] | None = None,
) -> AppContext:
    cadastrar_svc = CadastrarAlunoService(repo=aluno_repo)
    pagamento_svc = RegistrarPagamentoService(repo=pag_repo)
    liberar_svc = LiberarAcessoService(
        driver=bridge.driver,
        aluno_repo=aluno_repo,
        matricula_repo=mat_repo,
        pagamento_repo=pag_repo,
        acesso_repo=acesso_repo,
    )
    return AppContext(
        bridge=bridge,
        dashboard_vm=DashboardViewModel(acesso=liberar_svc, log_repo=acesso_repo),
        alunos_vm=AlunosViewModel(
            alunos=cadastrar_svc,
            commit=commit,
            matricula_repo=mat_repo,
            plano_repo=plano_repo,
        ),
        planos_vm=PlanosViewModel(repo=plano_repo, commit=commit),
        pagamentos_vm=PagamentosViewModel(
            pagamentos=pagamento_svc, alunos=cadastrar_svc, commit=commit
        ),
        session=session,
        commit=commit,
    )


class GymFlowMainWindow(QMainWindow):
    def __init__(self, ctx: AppContext, parent: Any = None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("GymFlow")
        self.resize(1024, 640)
        tabs = QTabWidget(self)
        tabs.addTab(DashboardView(ctx.dashboard_vm, ctx.bridge), "Catraca")
        tabs.addTab(AlunosView(ctx.alunos_vm), "Alunos")
        tabs.addTab(PlanosView(ctx.planos_vm), "Planos")
        tabs.addTab(PagamentosView(ctx.pagamentos_vm), "Pagamentos")
        self.setCentralWidget(tabs)
        self.tabs = tabs


def build_window(ctx: AppContext) -> GymFlowMainWindow:
    return GymFlowMainWindow(ctx)


def run(argv: list[str] | None = None) -> int:
    """Abre o app desktop (bloqueia até fechar)."""
    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication(argv or [])
    ctx = create_context()
    try:
        ok = ctx.bridge.conectar()
        logger.info(f"[UI] catraca conectar() -> {ok}")
    except Exception as e:
        logger.warning(f"[UI] falha ao conectar catraca: {e}")
    win = build_window(ctx)
    app.aboutToQuit.connect(ctx.close)
    win.show()
    return app.exec()
