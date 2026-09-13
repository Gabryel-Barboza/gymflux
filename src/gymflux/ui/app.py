"""Composition root da UI — ÚNICO lugar da UI que importa ``infra``/``hardware``.

Monta ``Session`` + repos + services + bridge + ViewModels + janela.
ViewModels/Views recebem dependências prontas (nunca importam infra/hardware).
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QStyle,
    QTabWidget,
)
from sqlalchemy.orm import Session

from gymflux.core.regras import RegraAcesso, RegraAcessoConfig
from gymflux.services.cadastrar_aluno import CadastrarAlunoService
from gymflux.services.identificar_acesso import IdentificarAcessoService
from gymflux.services.inatividade import aplicar_inatividade
from gymflux.services.liberar_acesso import LiberarAcessoService
from gymflux.services.registrar_pagamento import RegistrarPagamentoService
from gymflux.ui.catraca_bridge import CatracaBridge
from gymflux.ui.config_store import ConfigStore, UiConfig
from gymflux.ui.theme import AZUL, TEXTO, ModoTema, stylesheet
from gymflux.ui.viewmodels.alunos import AlunosViewModel
from gymflux.ui.viewmodels.caixa import CaixaViewModel
from gymflux.ui.viewmodels.config import ConfigViewModel
from gymflux.ui.viewmodels.dashboard import DashboardViewModel
from gymflux.ui.viewmodels.frequencia import FrequenciaViewModel
from gymflux.ui.viewmodels.funcionarios import FuncionariosViewModel
from gymflux.ui.viewmodels.planos import PlanosViewModel
from gymflux.ui.views.alunos import AlunosView
from gymflux.ui.views.caixa import CaixaView
from gymflux.ui.views.config import ConfigView
from gymflux.ui.views.dashboard import DashboardView
from gymflux.ui.views.frequencia import FrequenciaView
from gymflux.ui.views.funcionarios import FuncionariosView
from gymflux.ui.views.planos import PlanosView


@dataclass
class AppContext:
    """Tudo que a janela precisa — criado por ``create_context``."""

    bridge: CatracaBridge
    dashboard_vm: DashboardViewModel
    alunos_vm: AlunosViewModel
    planos_vm: PlanosViewModel
    caixa_vm: CaixaViewModel
    funcionarios_vm: FuncionariosViewModel
    frequencia_vm: FrequenciaViewModel
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
        from gymflux.infra.db import init_db

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
    from gymflux.config.settings import get_settings

    settings = get_settings()
    config_store = ConfigStore(fallback_porta=settings.henry_porta)
    ui_config = config_store.load()
    bridge = CatracaBridge(porta=ui_config.porta_catraca)

    if use_db:
        try:
            _ensure_schema()
            from gymflux.infra.db import get_session
            from gymflux.infra.repositories.acesso_log import AcessoLogRepositorySQLAlchemy
            from gymflux.infra.repositories.aluno import AlunoRepositorySQLAlchemy
            from gymflux.infra.repositories.fechamento_caixa import (
                FechamentoCaixaRepositorySQLAlchemy,
            )
            from gymflux.infra.repositories.funcionario import (
                FuncionarioRepositorySQLAlchemy,
            )
            from gymflux.infra.repositories.matricula import MatriculaRepositorySQLAlchemy
            from gymflux.infra.repositories.pagamento import PagamentoRepositorySQLAlchemy
            from gymflux.infra.repositories.plano import PlanoRepositorySQLAlchemy

            session = get_session()
            aluno_repo: Any = AlunoRepositorySQLAlchemy(session)
            plano_repo: Any = PlanoRepositorySQLAlchemy(session)
            mat_repo: Any = MatriculaRepositorySQLAlchemy(session)
            pag_repo: Any = PagamentoRepositorySQLAlchemy(session)
            acesso_repo: Any = AcessoLogRepositorySQLAlchemy(session)
            fech_repo: Any = FechamentoCaixaRepositorySQLAlchemy(session)
            func_repo: Any = FuncionarioRepositorySQLAlchemy(session)
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
                func_repo,
                ui_config=ui_config,
                config_store=config_store,
                session=session,
                commit=commit,
            )
        except Exception as e:
            logger.warning(f"[UI] DB indisponível ({e}) — fallback memória")

    from gymflux.infra.repositories.acesso_log import AcessoLogRepositoryMemoria
    from gymflux.infra.repositories.fechamento_caixa import FechamentoCaixaRepositoryMemoria
    from gymflux.infra.repositories.funcionario import FuncionarioRepositoryMemoria
    from gymflux.infra.repositories.matricula import MatriculaRepositoryMemoria
    from gymflux.infra.repositories.plano import PlanoRepositoryMemoria
    from gymflux.services.cadastrar_aluno import RepositorioAlunosMemoria
    from gymflux.services.registrar_pagamento import RepositorioPagamentosMemoria

    logger.info("[UI] contexto em memória (sem persistência)")
    return _wire(
        bridge,
        RepositorioAlunosMemoria(),
        PlanoRepositoryMemoria(),
        MatriculaRepositoryMemoria(),
        RepositorioPagamentosMemoria(),
        AcessoLogRepositoryMemoria(),
        FechamentoCaixaRepositoryMemoria(),
        FuncionarioRepositoryMemoria(),
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
    func_repo: Any,
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
    caixa_vm = CaixaViewModel(
        pagamentos=pagamento_svc,
        alunos=cadastrar_svc,
        fechamentos=fech_repo,
        commit=commit,
        ui_config=cfg,
    )
    frequencia_vm = FrequenciaViewModel(
        log_repo=acesso_repo, aluno_repo=aluno_repo, funcionario_repo=func_repo
    )
    liberar_svc = LiberarAcessoService(
        driver=bridge.driver,
        regra=regra,
        aluno_repo=aluno_repo,
        matricula_repo=mat_repo,
        pagamento_repo=pag_repo,
        acesso_repo=acesso_repo,
    )
    identificar_svc = IdentificarAcessoService(
        acesso=liberar_svc, aluno_repo=aluno_repo, funcionario_repo=func_repo
    )
    dashboard_vm = DashboardViewModel(
        acesso=liberar_svc,
        log_repo=acesso_repo,
        commit=commit,
        identificar=identificar_svc,
        ui_config=cfg,
        funcionario_repo=func_repo,
    )

    # Fase 4.8: expira quem está sem entrar há 90d (nunca aborta o startup).
    try:
        n_inativos = aplicar_inatividade(aluno_repo, acesso_repo)
        if n_inativos and commit is not None:
            commit()
    except Exception as e:
        n_inativos = 0
        logger.warning(f"[UI] aplicar_inatividade falhou: {e}")
    if n_inativos:
        logger.info(f"[UI] inatividade: {n_inativos} aluno(s) desativado(s)")

    def _aplicar(nova: UiConfig) -> None:
        liberar_svc.regra.config = nova.to_regra_config()
        dashboard_vm.ui_config = nova
        caixa_vm.ui_config = nova
        if nova.porta_catraca != bridge.porta:
            bridge.trocar_porta(nova.porta_catraca)
        app_inst = QApplication.instance()
        if isinstance(app_inst, QApplication):
            app_inst.setStyleSheet(stylesheet(nova.tema))
            # atualiza ícone da aba selecionada e wallpaper
            import contextlib

            for w in app_inst.topLevelWidgets():
                if hasattr(w, "_aplicar_tema_icones"):
                    with contextlib.suppress(Exception):
                        w._aplicar_tema_icones(nova.tema)  # type: ignore[attr-defined]
                if hasattr(w, "aplicar_wallpaper"):
                    with contextlib.suppress(Exception):
                        from gymflux.ui.config_store import ModoFundo

                        modo = getattr(nova, "fundo_modo", ModoFundo.WALLPAPER)
                        if modo == ModoFundo.WALLPAPER:
                            w.aplicar_wallpaper(nova.wallpaper)  # type: ignore[attr-defined]
                        else:
                            w.aplicar_wallpaper(None)  # type: ignore[attr-defined]
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
        caixa_vm=caixa_vm,
        funcionarios_vm=FuncionariosViewModel(repo=func_repo, commit=commit),
        frequencia_vm=frequencia_vm,
        config_vm=config_vm,
        config_store=store,
        session=session,
        commit=commit,
    )


def _tint_icon(icon, color_hex: str):  # type: ignore[no-untyped-def]
    """Tint QIcon para color_hex (usado no claro p/ aba selecionada)."""
    from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

    sizes = icon.availableSizes() or [icon.pixmap(32, 32).size()]
    tinted = QIcon()
    for sz in sizes:
        pix = icon.pixmap(sz)
        if pix.isNull():
            continue
        out = QPixmap(pix.size())
        out.fill(QColor("transparent"))
        p = QPainter(out)
        p.drawPixmap(0, 0, pix)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)  # type: ignore[attr-defined]
        p.fillRect(out.rect(), QColor(color_hex))
        p.end()
        tinted.addPixmap(out)
    return tinted if not tinted.isNull() else icon


class GymFluxMainWindow(QMainWindow):
    def __init__(self, ctx: AppContext, parent: Any = None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("GymFlux")
        self.resize(1024, 640)
        tabs = QTabWidget(self)
        estilo = self.style()
        # ícones base (guardados para tint)
        self._base_icons = [
            estilo.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon),
            estilo.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView),
            estilo.standardIcon(QStyle.StandardPixmap.SP_FileIcon),
            estilo.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton),
            estilo.standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon),
            estilo.standardIcon(QStyle.StandardPixmap.SP_FileDialogListView),
            estilo.standardIcon(QStyle.StandardPixmap.SP_DialogResetButton),
        ]
        dashboard_view = DashboardView(ctx.dashboard_vm, ctx.bridge)
        dashboard_view.perfil_solicitado.connect(self._abrir_perfil_aluno)
        tabs.addTab(dashboard_view, self._base_icons[0], "Catraca")
        self.dashboard_view = dashboard_view
        self.alunos_view = AlunosView(
            ctx.alunos_vm,
            ctx.caixa_vm,
            frequencia_vm=ctx.frequencia_vm,
            dashboard_vm=ctx.dashboard_vm,
        )
        tabs.addTab(self.alunos_view, self._base_icons[1], "Alunos")
        tabs.addTab(PlanosView(ctx.planos_vm), self._base_icons[2], "Planos")
        tabs.addTab(CaixaView(ctx.caixa_vm), self._base_icons[3], "Caixa")
        tabs.addTab(FuncionariosView(ctx.funcionarios_vm), self._base_icons[4], "Funcionários")
        tabs.addTab(FrequenciaView(ctx.frequencia_vm), self._base_icons[5], "Frequência")
        tabs.addTab(ConfigView(ctx.config_vm), self._base_icons[6], "Configurações")
        self.setCentralWidget(tabs)
        self.tabs = tabs
        tabs.currentChanged.connect(self._on_tab_changed)
        self._aplicar_tema_icones(ctx.config_vm.config.tema)
        # wallpaper: fundo global desabilitado — fica só atrás dos containers da catraca
        self._wallpaper_label = QLabel(self)
        self._wallpaper_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._wallpaper_label.hide()
        # mantém atributos p/ compat, mas não usa wallpaper global
        self._wallpaper_pixmap: QPixmap | None = None
        self._scaled_wallpaper: QPixmap | None = None
        self._cached_wallpaper_size: Any = None
        from gymflux.ui.config_store import ModoFundo

        cfg_wall = ctx.config_vm.config.wallpaper
        cfg_modo = getattr(ctx.config_vm.config, "fundo_modo", ModoFundo.WALLPAPER)
        if cfg_modo == ModoFundo.WALLPAPER:
            self.aplicar_wallpaper(cfg_wall)
        else:
            self.aplicar_wallpaper(None)
        self.tabs.raise_()

    def _aplicar_tema_icones(self, tema) -> None:  # type: ignore[no-untyped-def]
        is_claro = tema == ModoTema.CLARO or str(tema).upper() == "CLARO"
        for i, base in enumerate(self._base_icons):
            if i == self.tabs.currentIndex():
                color = AZUL if is_claro else TEXTO  # escuro: branco #F2F5F7, não apagado
                icon = _tint_icon(base, color)
            else:
                icon = base
            self.tabs.setTabIcon(i, icon)

    def _on_tab_changed(self, idx: int) -> None:  # type: ignore[no-untyped-def]
        self._aplicar_tema_icones(self.ctx.config_vm.config.tema)

    def aplicar_wallpaper(self, path: str | None) -> None:
        """Delega wallpaper aos containers da catraca; fundo global sempre sólido."""
        # garante fundo global sólido (sem wallpaper atrás de tudo)
        try:
            self._wallpaper_label.hide()
            self._wallpaper_pixmap = None
            self._scaled_wallpaper = None
            self._cached_wallpaper_size = None
        except Exception:
            pass
        # delega aos 4 containers da dashboard
        try:
            if hasattr(self, "dashboard_view") and hasattr(
                self.dashboard_view, "aplicar_wallpaper"
            ):
                self.dashboard_view.aplicar_wallpaper(path)
        except Exception as e:
            logger.warning(f"[UI] delegar wallpaper falhou {path}: {e}")

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        # sem wallpaper global — dashboard cuida via eventFilter/resize
        with contextlib.suppress(Exception):
            self.tabs.raise_()

    def _abrir_perfil_aluno(self, aluno_id: str) -> None:
        """Click-through do log: troca p/ aba Alunos e abre o modal de perfil."""
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "Alunos":
                self.tabs.setCurrentIndex(i)
                break
        self.alunos_view.abrir_perfil_por_id(aluno_id)


def build_window(ctx: AppContext) -> GymFluxMainWindow:
    return GymFluxMainWindow(ctx)


def run(argv: list[str] | None = None) -> int:
    """Abre o app desktop (bloqueia até fechar)."""
    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication(argv or [])
    ctx = create_context()
    app.setStyleSheet(stylesheet(ctx.config_vm.config.tema))
    try:
        ok = ctx.bridge.conectar()
        logger.info(f"[UI] catraca conectar() -> {ok}")
    except Exception as e:
        logger.warning(f"[UI] falha ao conectar catraca: {e}")
    win = build_window(ctx)
    app.aboutToQuit.connect(ctx.close)
    win.show()
    return app.exec()
