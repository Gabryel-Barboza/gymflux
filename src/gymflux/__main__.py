"""Entry point CLI `gymflux` — Fase 0-2 (mock demo, info, db)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def cmd_mock_demo(_args: argparse.Namespace) -> int:
    from gymflux.hardware.henry7x.factory import get_henry_driver
    from gymflux.hardware.henry7x.interface import Direcao

    driver = get_henry_driver()
    print(f"[GymFlux] Driver: {driver.__class__.__name__} (mock={driver.is_mock})")
    print("[GymFlux] Conectando...")
    ok = driver.conectar(porta="MOCK:1")
    print(f"[GymFlux] conectar() -> {ok} | status={driver.status()}")

    print("[GymFlux] Liberando catraca (ENTRADA)...")
    res = driver.liberar(Direcao.ENTRADA)
    print(f"[GymFlux] liberar() -> {res}")

    def on_giro(direcao, ts):
        print(f"[EVENTO] giro detectado direcao={direcao} ts={ts}")

    driver.on_giro(on_giro)
    print("[GymFlux] Aguardando giro simulado (2s)...")
    import time

    time.sleep(2.5)
    print(f"[GymFlux] status final: {driver.status()}")
    driver.desconectar()
    print("[GymFlux] desconectado.")
    return 0


def cmd_catraca_status(args: argparse.Namespace) -> int:
    """Mostra status do driver (mock ou real) — Fase 3, VM Windows 32-bit."""
    from gymflux.hardware.henry7x.factory import get_henry_driver

    try:
        driver = get_henry_driver()
    except Exception as e:
        print(f"[erro] factory falhou: {e}")
        return 1
    print(f"[GymFlux] Driver: {driver.__class__.__name__} (mock={driver.is_mock})")
    print(f"[GymFlux] status={driver.status()}")
    return 0


def cmd_catraca_liberar(args: argparse.Namespace) -> int:
    """Conecta, libera giro na direção e aguarda giro físico (Fase 3)."""
    import threading
    import time

    from gymflux.config.settings import get_settings
    from gymflux.hardware.henry7x.factory import get_henry_driver
    from gymflux.hardware.henry7x.interface import Direcao

    settings = get_settings()
    porta = args.porta or settings.henry_porta
    direcao = Direcao.ENTRADA if args.direcao == "entrada" else Direcao.SAIDA
    timeout_s = (args.timeout_ms or settings.henry_timeout_ms) / 1000.0
    try:
        driver = get_henry_driver()
    except Exception as e:
        print(f"[erro] factory falhou: {e}")
        return 1
    print(f"[GymFlux] Driver: {driver.__class__.__name__} (mock={driver.is_mock})")
    try:
        ok = driver.conectar(porta=porta)
    except Exception as e:
        print(f"[erro] conectar({porta}) falhou: {e}")
        return 1
    print(f"[GymFlux] conectar({porta}) -> {ok}")
    if not ok:
        return 1
    giro = threading.Event()

    def on_giro(d, ts):
        print(f"[EVENTO] giro detectado direcao={d} ts={ts}")
        giro.set()

    driver.on_giro(on_giro)
    try:
        res = driver.liberar(direcao)
    except Exception as e:
        print(f"[erro] liberar({direcao.name}) falhou: {e}")
        driver.desconectar()
        return 1
    print(f"[GymFlux] liberar({direcao.name}) -> {res}")
    if "LIBERADO" not in res.name:
        driver.desconectar()
        return 1
    print(f"[GymFlux] Gire a catraca (aguardando até {timeout_s:.0f}s)...")
    deadline = time.time() + timeout_s
    while time.time() < deadline and not giro.is_set():
        time.sleep(0.2)
    print(f"[GymFlux] giro={'detectado' if giro.is_set() else 'TIMEOUT'} status={driver.status()}")
    driver.desconectar()
    print("[GymFlux] desconectado.")
    return 0 if giro.is_set() else 2


def cmd_catraca_bloquear(args: argparse.Namespace) -> int:
    """Conecta e bloqueia a catraca (Fase 3)."""
    from gymflux.config.settings import get_settings
    from gymflux.hardware.henry7x.factory import get_henry_driver

    settings = get_settings()
    porta = args.porta or settings.henry_porta
    try:
        driver = get_henry_driver()
    except Exception as e:
        print(f"[erro] factory falhou: {e}")
        return 1
    try:
        driver.conectar(porta=porta)
    except Exception as e:
        print(f"[erro] conectar({porta}) falhou: {e}")
        return 1
    try:
        driver.bloquear()
    except Exception as e:
        print(f"[erro] bloquear() falhou: {e}")
        driver.desconectar()
        return 1
    print(f"[GymFlux] bloqueada. status={driver.status()}")
    driver.desconectar()
    return 0


def cmd_info(_args: argparse.Namespace) -> int:
    import platform
    import struct

    print("GymFlux — Sistema de gerenciamento para academias (Henry 7x)")
    print(f"  Python: {platform.python_version()} ({struct.calcsize('P') * 8}-bit)")
    print(f"  Platform: {sys.platform} / {platform.machine()}")
    print(f"  Executable: {sys.executable}")
    from gymflux.config.settings import get_settings

    s = get_settings()
    print(f"  Settings: mock={s.henry_mock} dll={s.henry_dll_path} db={s.db_url}")
    # DB status
    try:
        from sqlalchemy import text

        from gymflux.infra.db import get_engine

        eng = get_engine()
        with eng.connect() as conn:
            # tenta contar tabelas
            res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [r[0] for r in res.fetchall()]
            print(f"  DB tables: {tables if tables else '(nenhuma — rode gymflux db upgrade)'}")
            if "alunos" in tables:
                cnt = conn.execute(text("SELECT count(*) FROM alunos")).scalar()
                print(f"  DB alunos: {cnt}")
    except Exception as e:
        print(f"  DB status: erro ({e})")
    return 0


def _resolve_alembic_ini() -> Path:
    try:
        from gymflux.infra.db import get_alembic_ini_path

        return get_alembic_ini_path()
    except Exception:
        import sys as _sys
        from pathlib import Path

        if bool(getattr(_sys, "frozen", False)):
            meipass = getattr(_sys, "_MEIPASS", None)
            if meipass:
                cand = Path(meipass) / "alembic.ini"
                if cand.exists():
                    return cand
        return Path("alembic.ini")


def cmd_db_upgrade(_args: argparse.Namespace) -> int:
    from alembic import command
    from alembic.config import Config

    ini = _resolve_alembic_ini()
    if not ini.exists():
        print(f"[erro] alembic.ini não encontrado em {ini} (rode na raiz ou verifique bundle)")
        return 1
    cfg = Config(str(ini))
    # frozen deve migrar %APPDATA%/GymFlux, não data/ junto ao exe (sem permissão)
    try:
        from gymflux.infra.db import _is_frozen, get_default_db_url

        if _is_frozen():
            cfg.set_main_option("sqlalchemy.url", get_default_db_url())
    except Exception:
        pass
    # garante script_location correto se relativo
    print(f"[GymFlux] alembic upgrade head (db={cfg.get_main_option('sqlalchemy.url')})")
    try:
        command.upgrade(cfg, "head")
        print("[GymFlux] upgrade concluído.")
        return 0
    except Exception as e:
        print(f"[erro] upgrade falhou: {e}")
        import traceback

        traceback.print_exc()
        return 1


def cmd_db_downgrade(_args: argparse.Namespace) -> int:
    from alembic import command
    from alembic.config import Config

    ini = _resolve_alembic_ini()
    if not ini.exists():
        print(f"[erro] alembic.ini não encontrado em {ini}")
        return 1
    target = _args.revision or "-1"
    cfg = Config(str(ini))
    try:
        from gymflux.infra.db import _is_frozen, get_default_db_url

        if _is_frozen():
            cfg.set_main_option("sqlalchemy.url", get_default_db_url())
    except Exception:
        pass
    print(f"[GymFlux] alembic downgrade {target}")
    try:
        command.downgrade(cfg, target)
        print("[GymFlux] downgrade concluído.")
        return 0
    except Exception as e:
        print(f"[erro] downgrade falhou: {e}")
        import traceback

        traceback.print_exc()
        return 1


def cmd_db_seed(_args: argparse.Namespace) -> int:
    """Seed demo — 3 alunos + planos Mensal/Trimestral (idempotente)."""
    from datetime import date, timedelta
    from decimal import Decimal

    from loguru import logger

    from gymflux.core.aluno import Aluno, StatusAluno
    from gymflux.core.pagamento import Pagamento
    from gymflux.core.plano import Matricula, Plano, Vigencia
    from gymflux.infra.db import get_session
    from gymflux.infra.repositories.aluno import AlunoRepositorySQLAlchemy
    from gymflux.infra.repositories.matricula import MatriculaRepositorySQLAlchemy
    from gymflux.infra.repositories.pagamento import PagamentoRepositorySQLAlchemy
    from gymflux.infra.repositories.plano import PlanoRepositorySQLAlchemy

    # garante DB migrated (log explícito em vez de suppress silencioso)
    try:
        cmd_db_upgrade(argparse.Namespace())
    except Exception as e:
        logger.warning(f"[seed] upgrade automático falhou ({e}), tentando seed mesmo assim")
        print(f"[seed] aviso: upgrade automático falhou ({e}), tentando seed mesmo assim")

    session = get_session()
    try:
        plano_repo = PlanoRepositorySQLAlchemy(session)
        aluno_repo = AlunoRepositorySQLAlchemy(session)
        mat_repo = MatriculaRepositorySQLAlchemy(session)
        pag_repo = PagamentoRepositorySQLAlchemy(session)

        # Planos
        mensal = Plano.criar_mensal(id="mensal", nome="Mensal", valor=Decimal("99.90"))
        trimestral = Plano.criar_trimestral(
            id="trimestral", nome="Trimestral", valor=Decimal("259.90")
        )
        for p in (mensal, trimestral):
            if plano_repo.buscar_por_id(p.id) is None:
                plano_repo.salvar(p)
                print(f"[seed] plano {p.id} criado")
            else:
                print(f"[seed] plano {p.id} já existe")

        hoje = date.today()
        vigencia_mensal = Vigencia.a_partir_de(hoje, duracao_dias=30)
        vigencia_trim = Vigencia.a_partir_de(hoje, duracao_dias=90)

        alunos_demo = [
            Aluno(
                id="aluno-1",
                nome="Ana Silva",
                cpf="11144477735",
                telefone="11999999999",
                email="ana@gymflux.local",
                status=StatusAluno.ATIVO,
            ),
            Aluno(
                id="aluno-2",
                nome="Bruno Souza",
                cpf="22255588846",
                telefone="11988888888",
                email="bruno@gymflux.local",
                status=StatusAluno.ATIVO,
            ),
            Aluno(
                id="aluno-3",
                nome="Carla Dias",
                cpf="33366699957",
                telefone="11977777777",
                email="carla@gymflux.local",
                status=StatusAluno.ATIVO,
            ),
        ]
        matriculas_demo = [
            (alunos_demo[0], mensal, vigencia_mensal),
            (alunos_demo[1], trimestral, vigencia_trim),
            (alunos_demo[2], mensal, vigencia_mensal),
        ]
        for aluno in alunos_demo:
            if aluno_repo.buscar_por_id(aluno.id) is None:
                aluno_repo.salvar(aluno)
                print(f"[seed] aluno {aluno.id} {aluno.nome} criado")
            else:
                print(f"[seed] aluno {aluno.id} já existe")

        for aluno, plano, vig in matriculas_demo:
            mid = f"mat-{aluno.id}"
            if mat_repo.buscar_por_id(mid) is None:
                mat = Matricula(aluno_id=aluno.id, plano=plano, vigencia=vig, ativa=True)
                mat_repo.salvar(mat, matricula_id=mid)
                print(f"[seed] matricula {mid} -> plano {plano.id} vig {vig.inicio}..{vig.fim}")
            else:
                print(f"[seed] matricula {mid} já existe")

        # Pagamentos adimplentes: vencimento futuro (ou pago hoje)
        for aluno in alunos_demo:
            pid = f"pag-{aluno.id}-001"
            if pag_repo.buscar_por_id(pid) is None:
                venc = hoje + timedelta(days=5)
                pag = Pagamento(
                    id=pid,
                    aluno_id=aluno.id,
                    valor=Decimal("99.90") if aluno.id != "aluno-2" else Decimal("259.90"),
                    data_vencimento=venc,
                    data_pagamento=venc,  # pago antecipado
                    forma="PIX",
                    competencia=hoje.strftime("%Y-%m"),
                )
                pag_repo.salvar(pag)
                print(f"[seed] pagamento {pid} venc {venc} criado")
            else:
                print(f"[seed] pagamento {pid} já existe")

        session.commit()
        print(
            f"[seed] concluído — alunos={aluno_repo.total()} "
            f"planos={plano_repo.total()} matriculas={mat_repo.total()} "
            f"pagamentos={pag_repo.total()}"
        )
        return 0
    except Exception as e:
        session.rollback()
        print(f"[erro] seed falhou: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        session.close()


def cmd_ui(_args: argparse.Namespace) -> int:
    """Abre a interface desktop PySide6 (Fase 4)."""
    try:
        import PySide6  # noqa: F401
    except ImportError:
        print("[erro] PySide6 não instalado. Rode: uv sync --extra ui")
        return 1
    from gymflux.ui.app import run

    return run()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gymflux", description="GymFlux — Sistema de gerenciamento para academias"
    )
    # sem cmd => abre UI (duplo-clique no GymFlux.exe)
    sub = p.add_subparsers(dest="cmd", required=False)

    sp = sub.add_parser("mock-demo", help="demonstra hardware mockado (Linux)")
    sp.set_defaults(func=cmd_mock_demo)

    sp2 = sub.add_parser("info", help="mostra info do ambiente")
    sp2.set_defaults(func=cmd_info)

    # catraca group (Fase 3: mock em Linux, COM real em VM Windows 32-bit)
    sp_cat = sub.add_parser("catraca", help="operações da catraca Henry 7x")
    cat_sub = sp_cat.add_subparsers(dest="catraca_cmd", required=True)

    sp_st = cat_sub.add_parser("status", help="mostra status do driver")
    sp_st.set_defaults(func=cmd_catraca_status)

    sp_lib = cat_sub.add_parser("liberar", help="libera giro e aguarda giro físico")
    sp_lib.add_argument("--porta", default=None, help="ex.: COM3 (default: GYMFLUX_HENRY_PORTA)")
    sp_lib.add_argument(
        "--direcao", choices=["entrada", "saida"], default="entrada", help="direção do giro"
    )
    sp_lib.add_argument("--timeout-ms", type=int, default=None, help="espera do giro (ms)")
    sp_lib.set_defaults(func=cmd_catraca_liberar)

    sp_blo = cat_sub.add_parser("bloquear", help="bloqueia a catraca")
    sp_blo.add_argument("--porta", default=None, help="ex.: COM3 (default: GYMFLUX_HENRY_PORTA)")
    sp_blo.set_defaults(func=cmd_catraca_bloquear)

    # db group
    sp_db = sub.add_parser("db", help="operações de banco (alembic/seed)")
    db_sub = sp_db.add_subparsers(dest="db_cmd", required=True)

    sp_up = db_sub.add_parser("upgrade", help="alembic upgrade head")
    sp_up.set_defaults(func=cmd_db_upgrade)

    sp_down = db_sub.add_parser("downgrade", help="alembic downgrade")
    sp_down.add_argument("revision", nargs="?", default="-1", help="revisão alvo (default -1)")
    sp_down.set_defaults(func=cmd_db_downgrade)

    sp_seed = db_sub.add_parser("seed", help="popula demo (3 alunos + planos)")
    sp_seed.set_defaults(func=cmd_db_seed)

    # alias `gymflux seed` direto
    sp_seed2 = sub.add_parser("seed", help="alias para db seed")
    sp_seed2.set_defaults(func=cmd_db_seed)

    # ui desktop (Fase 4)
    sp_ui = sub.add_parser("ui", help="abre interface desktop (PySide6)")
    sp_ui.set_defaults(func=cmd_ui)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    # duplo-clique/atallho sem args => UI (não mostra "the following arguments are required: cmd")
    if getattr(args, "cmd", None) is None:
        raise SystemExit(cmd_ui(args))
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
