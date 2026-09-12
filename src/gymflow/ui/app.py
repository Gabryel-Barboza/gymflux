"""Composition root da UI — ÚNICO lugar da UI que importa ``infra``/``hardware``.

Monta ``Session`` + repos + services + bridge + ViewModels + janela.
ViewModels/Views recebem dependências prontas (nunca importam infra/hardware).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from loguru import logger
from PySide6.QtWidgets import QApplication, QMainWindow, QStyle, QTabWidget
from sqlalchemy.orm import Session

from gymflow.core.regras import RegraAcesso, RegraAcessoConfig
from gymflow.services.cadastrar_aluno import CadastrarAlunoService
from gymflow.services.identificar_acesso import IdentificarAcessoService
from gymflow.services.liberar_acesso import LiberarAcessoService
from gymflow.services.registrar_pagamento import RegistrarPagamentoService
from gymflow.ui.catraca_bridge import CatracaBridge
from gymflow.ui.config_store import ConfigStore, UiConfig
from gymflow.ui.theme import stylesheet
from gymflow.ui.viewmodels.alunos import AlunosViewModel
from gymflow.ui.viewmodels.caixa import CaixaViewModel
from gymflow.ui.viewmodels.config import ConfigViewModel
from gymflow.ui.viewmodels.dashboard import DashboardViewModel
from gymflow.ui.viewmodels.pagamentos import PagamentosViewModel
from gymflow.ui.viewmodels.planos import PlanosViewModel
from gymflow.ui.views.alunos import AlunosView
from gymflow.ui.views.caixa import CaixaView
from gymflow.ui.views.config import ConfigView
from gymflow.ui.views.dashboard import DashboardView
from gymflow.ui.views.planos import PlanosView


@dataclass
class AppContext:
    """Tudo que a janela precisa — criado por ``create_context``."""

    bridge: CatracaBridge
    dashboard_vm: DashboardViewModel
    alunos_vm: AlunosViewModel
    planos_vm: PlanosViewModel
    pagamentos_vm: PagamentosViewModel
    caixa_vm: CaixaViewModel
    config_vm: ConfigViewModel
    config_store: ConfigStore
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
    config_store = ConfigStore(fallback_porta=settings.henry_porta)
    ui_config = config_store.load()
    bridge = CatracaBridge(porta=ui_config.porta_catraca)

    if use_db:
        try:
            _ensure_schema()
            from gymflow.infra.db import get_session
            from gymflow.infra.repositories.acesso_log import AcessoLogRepositorySQLAlchemy
            from gymflow.infra.repositories.aluno import AlunoRepositorySQLAlchemy
            from gymflow.infra.repositories.fechamento_caixa import (
                FechamentoCaixaRepositorySQLAlchemy,
            )
            from gymflow.infra.repositories.matricula import MatriculaRepositorySQLAlchemy
            from gymflow.infra.repositories.pagamento import PagamentoRepositorySQLAlchemy
            from gymflow.infra.repositories.plano import PlanoRepositorySQLAlchemy

            session = get_session()
            aluno_repo: Any = AlunoRepositorySQLAlchemy(session)
            plano_repo: Any = PlanoRepositorySQLAlchemy(session)
            mat_repo: Any = MatriculaRepositorySQLAlchemy(session)
            pag_repo: Any = PagamentoRepositorySQLAlchemy(session)
            acesso_repo: Any = AcessoLogRepositorySQLAlchemy(session)
            fech_repo: Any = FechamentoCaixaRepositorySQLAlchemy(session)
            commit = _safe_commit(session)
            logger.info("[UI] contexto com SQLite")
            return _wire(
                bridge,
                aluno_repo,
                plano_repo,
                mat_repo,
                pag_repo,
                acesso_repo,
                fech_repo,
                ui_config=ui_config,
                config_store=config_store,
                session=session,
                commit=commit,
            )
        except Exception as e:
            logger.warning(f"[UI] DB indisponível ({e}) — fallback memória")

    from gymflow.infra.repositories.acesso_log import AcessoLogRepositoryMemoria
    from gymflow.infra.repositories.fechamento_caixa import FechamentoCaixaRepositoryMemoria
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
        FechamentoCaixaRepositoryMemoria(),
        ui_config=ui_config,
        config_store=config_store,
    )


def _wire(
    bridge: CatracaBridge,
    aluno_repo: Any,
    plano_repo: Any,
    mat_repo: Any,
    pag_repo: Any,
    acesso_repo: Any,
    fech_repo: Any,
    ui_config: UiConfig | None = None,
    config_store: ConfigStore | None = None,
    session: Session | None = None,
    commit: Callable[[], None] | None = None,
) -> AppContext:
    cfg = ui_config or UiConfig()
    store = config_store or ConfigStore()
    regra = RegraAcesso(
        RegraAcessoConfig(
            tolerancia_dias=cfg.tolerancia_dias,
            timeout_giro_s=cfg.timeout_giro_s,
            anti_passback=cfg.anti_passback,
        )
    )
    cadastrar_svc = CadastrarAlunoService(repo=aluno_repo)
    pagamento_svc = RegistrarPagamentoService(repo=pag_repo)
    pagamentos_vm = PagamentosViewModel(
        pagamentos=pagamento_svc, alunos=cadastrar_svc, commit=commit
    )
    caixa_vm = CaixaViewModel(pagamentos=pagamentos_vm, fechamentos=fech_repo, commit=commit)
    liberar_svc = LiberarAcessoService(
        driver=bridge.driver,
        regra=regra,
        aluno_repo=aluno_repo,
        matricula_repo=mat_repo,
        pagamento_repo=pag_repo,
        acesso_repo=acesso_repo,
    )
    identificar_svc = IdentificarAcessoService(acesso=liberar_svc, aluno_repo=aluno_repo)
    dashboard_vm = DashboardViewModel(
        acesso=liberar_svc,
        log_repo=acesso_repo,
        commit=commit,
        identificar=identificar_svc,
        ui_config=cfg,
    )

    def _aplicar(nova: UiConfig) -> None:
        liberar_svc.regra.config = nova.to_regra_config()
        dashboard_vm.ui_config = nova
        if nova.porta_catraca != bridge.porta:
            bridge.trocar_porta(nova.porta_catraca)
        logger.info("[UI] configurações aplicadas na sessão")

    config_vm = ConfigViewModel(store=store, on_aplicar=_aplicar)
    return AppContext(
        bridge=bridge,
        dashboard_vm=dashboard_vm,
        alunos_vm=AlunosViewModel(
            alunos=cadastrar_svc,
            commit=commit,
            matricula_repo=mat_repo,
            plano_repo=plano_repo,
        ),
        planos_vm=PlanosViewModel(repo=plano_repo, commit=commit),
        pagamentos_vm=pagamentos_vm,
        caixa_vm=caixa_vm,
        config_vm=config_vm,
        config_store=store,
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
        estilo = self.style()
        tabs.addTab(
            DashboardView(ctx.dashboard_vm, ctx.bridge),
            estilo.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon),
            "Catraca",
        )
        tabs.addTab(
            AlunosView(ctx.alunos_vm, ctx.caixa_vm),
            estilo.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView),
            "Alunos",
        )
        tabs.addTab(
            PlanosView(ctx.planos_vm),
            estilo.standardIcon(QStyle.StandardPixmap.SP_FileIcon),
            "Planos",
        )
        tabs.addTab(
            CaixaView(ctx.caixa_vm),
            estilo.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton),
            "Caixa",
        )
        tabs.addTab(
            ConfigView(ctx.config_vm),
            estilo.standardIcon(QStyle.StandardPixmap.SP_DialogResetButton),
            "Configurações",
        )
        self.setCentralWidget(tabs)
        self.tabs = tabs


def build_window(ctx: AppContext) -> GymFlowMainWindow:
    return GymFlowMainWindow(ctx)


def run(argv: list[str] | None = None) -> int:
    """Abre o app desktop (bloqueia até fechar)."""
    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication(argv or [])
    app.setStyleSheet(stylesheet())
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
