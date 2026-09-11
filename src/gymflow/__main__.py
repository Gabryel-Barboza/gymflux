"""Entry point CLI `gymflow` — Fase 0-2 (mock demo, info, db)."""

from __future__ import annotations

import argparse
import sys


def cmd_mock_demo(_args: argparse.Namespace) -> int:
    from gymflow.hardware.henry7x.factory import get_henry_driver
    from gymflow.hardware.henry7x.interface import Direcao

    driver = get_henry_driver()
    print(f"[GymFlow] Driver: {driver.__class__.__name__} (mock={driver.is_mock})")
    print("[GymFlow] Conectando...")
    ok = driver.conectar(porta="MOCK:1")
    print(f"[GymFlow] conectar() -> {ok} | status={driver.status()}")

    print("[GymFlow] Liberando catraca (ENTRADA)...")
    res = driver.liberar(Direcao.ENTRADA)
    print(f"[GymFlow] liberar() -> {res}")

    def on_giro(direcao, ts):
        print(f"[EVENTO] giro detectado direcao={direcao} ts={ts}")

    driver.on_giro(on_giro)
    print("[GymFlow] Aguardando giro simulado (2s)...")
    import time

    time.sleep(2.5)
    print(f"[GymFlow] status final: {driver.status()}")
    driver.desconectar()
    print("[GymFlow] desconectado.")
    return 0


def cmd_info(_args: argparse.Namespace) -> int:
    import platform
    import struct

    print("GymFlow — Sistema de gerenciamento para academias (Henry 7x)")
    print(f"  Python: {platform.python_version()} ({struct.calcsize('P') * 8}-bit)")
    print(f"  Platform: {sys.platform} / {platform.machine()}")
    print(f"  Executable: {sys.executable}")
    from gymflow.config.settings import get_settings

    s = get_settings()
    print(f"  Settings: mock={s.henry_mock} dll={s.henry_dll_path} db={s.db_url}")
    # DB status
    try:
        from sqlalchemy import text

        from gymflow.infra.db import get_engine

        eng = get_engine()
        with eng.connect() as conn:
            # tenta contar tabelas
            res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [r[0] for r in res.fetchall()]
            print(f"  DB tables: {tables if tables else '(nenhuma — rode gymflow db upgrade)'}")
            if "alunos" in tables:
                cnt = conn.execute(text("SELECT count(*) FROM alunos")).scalar()
                print(f"  DB alunos: {cnt}")
    except Exception as e:
        print(f"  DB status: erro ({e})")
    return 0


def cmd_db_upgrade(_args: argparse.Namespace) -> int:
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    ini = Path("alembic.ini")
    if not ini.exists():
        print("[erro] alembic.ini não encontrado (rode na raiz do projeto)")
        return 1
    cfg = Config(str(ini))
    # garante script_location correto se relativo
    print(f"[GymFlow] alembic upgrade head (db={cfg.get_main_option('sqlalchemy.url')})")
    try:
        command.upgrade(cfg, "head")
        print("[GymFlow] upgrade concluído.")
        return 0
    except Exception as e:
        print(f"[erro] upgrade falhou: {e}")
        import traceback

        traceback.print_exc()
        return 1


def cmd_db_downgrade(_args: argparse.Namespace) -> int:
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    ini = Path("alembic.ini")
    if not ini.exists():
        print("[erro] alembic.ini não encontrado")
        return 1
    target = _args.revision or "-1"
    cfg = Config(str(ini))
    print(f"[GymFlow] alembic downgrade {target}")
    try:
        command.downgrade(cfg, target)
        print("[GymFlow] downgrade concluído.")
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

    from gymflow.core.aluno import Aluno, StatusAluno
    from gymflow.core.pagamento import Pagamento
    from gymflow.core.plano import Matricula, Plano, Vigencia
    from gymflow.infra.db import get_session
    from gymflow.infra.repositories.aluno import AlunoRepositorySQLAlchemy
    from gymflow.infra.repositories.matricula import MatriculaRepositorySQLAlchemy
    from gymflow.infra.repositories.pagamento import PagamentoRepositorySQLAlchemy
    from gymflow.infra.repositories.plano import PlanoRepositorySQLAlchemy

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
                email="ana@gymflow.local",
                status=StatusAluno.ATIVO,
            ),
            Aluno(
                id="aluno-2",
                nome="Bruno Souza",
                cpf="22255588846",
                telefone="11988888888",
                email="bruno@gymflow.local",
                status=StatusAluno.ATIVO,
            ),
            Aluno(
                id="aluno-3",
                nome="Carla Dias",
                cpf="33366699957",
                telefone="11977777777",
                email="carla@gymflow.local",
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gymflow", description="GymFlow — Sistema de gerenciamento para academias"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("mock-demo", help="demonstra hardware mockado (Linux)")
    sp.set_defaults(func=cmd_mock_demo)

    sp2 = sub.add_parser("info", help="mostra info do ambiente")
    sp2.set_defaults(func=cmd_info)

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

    # alias `gymflow seed` direto
    sp_seed2 = sub.add_parser("seed", help="alias para db seed")
    sp_seed2.set_defaults(func=cmd_db_seed)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
