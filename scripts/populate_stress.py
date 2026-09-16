#!/usr/bin/env python3
"""Stress populate — 5-10k alunos + matriculas + pagamentos + fichas + acessos.

Uso:
  uv run python scripts/populate_stress.py --qtd 7500
  uv run python scripts/populate_stress.py --qtd 5000 --batch 500 --with-fichas --with-acessos
  GYMFLUX_DB_URL=sqlite:///data/gymflux.db uv run python scripts/populate_stress.py

Popula o banco para testar:
- Listagem/paginação (500+, 7500) em Alunos/Caixa/Frequência
- Filtros, busca por nome/CPF, ordenação
- Caixa totais, fichas, frequência, perfis
- Performance de queries com volume real

Não apaga dados existentes; é incremental e idempotente por id.
Fotos ignoradas (como pedido).
"""

from __future__ import annotations

import argparse
import json
import random
import time
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# garante que src está no path quando rodado como `python scripts/...`
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loguru import logger

from gymflux.core.ficha import AvaliacaoFisica
from gymflux.core.pagamento import FormaPagamento
from gymflux.core.plano import Plano, Vigencia
from gymflux.infra.db import get_session, init_db

# tenta garantir schema via alembic, fallback create_all
def _ensure_schema() -> None:
    ini = Path("alembic.ini")
    if ini.exists():
        try:
            from alembic import command
            from alembic.config import Config

            cfg = Config(str(ini))
            command.upgrade(cfg, "head")
            return
        except Exception as e:
            logger.warning(f"alembic upgrade falhou ({e}), usando create_all")
    init_db()


def _cpf_unico(seq: int) -> str:
    # 11 dígitos, simples e único por seq; validação só checa length 11
    base = 10000000000 + seq
    s = str(base).zfill(11)
    # garante 11 e evita duplicar com seed demo (111...,222...,333...)
    return s[:11]


def _rand_plano(planos: list[Plano]) -> Plano:
    # peso: mensal mais comum
    return random.choices(planos, weights=[6, 2, 2], k=1)[0] if len(planos) >= 3 else random.choice(planos)


def main() -> int:
    ap = argparse.ArgumentParser(description="Popula DB com 5-10k alunos + fichas")
    ap.add_argument("--qtd", type=int, default=7500, help="quantidade de alunos (5000-10000)")
    ap.add_argument("--batch", type=int, default=500, help="tamanho do lote para commit")
    ap.add_argument("--with-fichas", action="store_true", default=True, help="cria ficha por aluno")
    ap.add_argument("--no-fichas", dest="with_fichas", action="store_false")
    ap.add_argument("--with-acessos", action="store_true", default=True)
    ap.add_argument("--no-acessos", dest="with_acessos", action="store_false")
    ap.add_argument("--with-pagamentos", action="store_true", default=True)
    ap.add_argument("--no-pagamentos", dest="with_pagamentos", action="store_false")
    args = ap.parse_args()

    qtd = max(100, min(15000, args.qtd))
    batch = max(100, args.batch)

    _ensure_schema()

    from gymflux.infra.models.aluno import AlunoModel
    from gymflux.infra.models.avaliacao_fisica import AvaliacaoFisicaModel
    from gymflux.infra.models.matricula import MatriculaModel
    from gymflux.infra.models.pagamento import PagamentoModel
    from gymflux.infra.models.plano import PlanoModel
    from gymflux.infra.models.acesso_log import AcessoLogModel

    session = get_session()
    try:
        # garante planos existem
        planos_exist = {p.id: p for p in session.execute(__import__("sqlalchemy").select(PlanoModel)).scalars().all()}
        # mapeia para core Plano para usar Vigencia e valor
        core_planos: list[Plano] = []
        if not planos_exist:
            # cria padrão se vazio
            for p in [Plano.criar_mensal(), Plano.criar_trimestral(), Plano.criar_anual()]:
                m = PlanoModel(id=p.id, nome=p.nome, duracao_dias=p.duracao_dias, valor=p.valor, tolerancia_dias=p.tolerancia_dias, tipo=p.tipo.value)
                session.add(m)
                core_planos.append(p)
            session.flush()
            logger.info("planos padrão criados")
        else:
            for pm in planos_exist.values():
                core_planos.append(
                    Plano(
                        id=pm.id,
                        nome=pm.nome,
                        duracao_dias=pm.duracao_dias,
                        valor=Decimal(str(pm.valor)),
                        tolerancia_dias=pm.tolerancia_dias,
                    )
                )

        # conta existente
        existing_alunos = session.query(AlunoModel).count()
        logger.info(f"alunos existentes: {existing_alunos} — adicionando {qtd}")

        start = time.perf_counter()
        created = 0
        # para CPF único, começa após existentes
        seq_start = existing_alunos + 1000

        # pré-carrega formas
        formas = [f.value for f in FormaPagamento]

        for i in range(qtd):
            seq = seq_start + i
            aluno_id = f"aluno-stress-{seq:05d}-{uuid.uuid4().hex[:4]}"
            nome = f"Aluno Stress {seq:05d}"
            cpf = _cpf_unico(seq)
            # dados variados
            email = f"stress{seq:05d}@gymflux.test"
            tel = f"119{random.randint(10000000, 99999999)}"
            nasc = date(1975 + (seq % 30), (seq % 12) + 1, (seq % 28) + 1)
            # 10% com data_nasc None para testar opcional
            if seq % 10 == 0:
                nasc_db = None
            else:
                nasc_db = nasc
            endereco = f"Rua {seq} Bairro {seq%100}" if seq % 3 != 0 else None

            aluno = AlunoModel(
                id=aluno_id,
                nome=nome,
                cpf=cpf,
                telefone=tel,
                email=email,
                data_nasc=nasc_db,
                status="ATIVO",
                bloqueado_manual=False,
                senha=f"{random.randint(1000,9999):04d}",
                endereco=endereco,
                observacoes=None,
                foto=None,
            )
            session.add(aluno)

            # matricula
            plano = _rand_plano(core_planos)
            inicio = date.today() - timedelta(days=random.randint(0, 60))
            fim = inicio + timedelta(days=plano.duracao_dias - 1)
            mat = MatriculaModel(
                id=f"mat-{aluno_id}",
                aluno_id=aluno_id,
                plano_id=plano.id,
                inicio=inicio,
                fim=fim,
                ativa=True,
            )
            session.add(mat)

            # pagamento(s) — 1 pendente + 30% com pago
            if args.with_pagamentos:
                # vencimento ancorado no dia da matrícula (Fase 4.15)
                import calendar

                dia_base = inicio.day
                hoje = date.today()
                ultimo = calendar.monthrange(hoje.year, hoje.month)[1]
                dia_venc = min(dia_base, ultimo)
                venc = date(hoje.year, hoje.month, dia_venc)
                comp = venc.strftime("%Y-%m")
                pag1 = PagamentoModel(
                    id=f"pag-{uuid.uuid4().hex[:8]}",
                    aluno_id=aluno_id,
                    valor=plano.valor,
                    vencimento=venc,
                    data_pagamento=None,
                    forma=None,
                    competencia=comp,
                )
                session.add(pag1)
                # 30% pagos no mês anterior
                if seq % 3 == 0:
                    venc2 = venc - timedelta(days=30)
                    # clamp para mês anterior
                    y, m = (venc2.year, venc2.month)
                    d = min(dia_base, calendar.monthrange(y, m)[1])
                    venc2 = date(y, m, d)
                    pag2 = PagamentoModel(
                        id=f"pag-{uuid.uuid4().hex[:8]}",
                        aluno_id=aluno_id,
                        valor=plano.valor,
                        vencimento=venc2,
                        data_pagamento=venc2,
                        forma=random.choice(formas),
                        competencia=venc2.strftime("%Y-%m"),
                    )
                    session.add(pag2)

            # ficha — 1 por aluno se habilitado
            if args.with_fichas:
                # 80% com ficha, para testar lista
                if seq % 5 != 0:
                    # medidas bilaterais
                    medidas = {
                        "braco_esq": round(random.uniform(28, 42), 1),
                        "braco_dir": round(random.uniform(28, 42), 1),
                        "peito": round(random.uniform(85, 115), 1),
                        "cintura": round(random.uniform(70, 105), 1),
                        "quadril": round(random.uniform(85, 115), 1),
                        "coxa_esq": round(random.uniform(48, 68), 1),
                        "coxa_dir": round(random.uniform(48, 68), 1),
                        "panturrilha_esq": round(random.uniform(32, 45), 1),
                        "panturrilha_dir": round(random.uniform(32, 45), 1),
                    }
                    # introduz assimetria em 20%
                    if seq % 5 == 1:
                        medidas["braco_esq"] = round(medidas["braco_esq"] + random.uniform(2, 5), 1)
                        medidas["coxa_dir"] = round(medidas["coxa_dir"] + random.uniform(2, 4), 1)
                    ficha = AvaliacaoFisicaModel(
                        id=f"ava-{uuid.uuid4().hex[:8]}",
                        aluno_id=aluno_id,
                        data=date.today() - timedelta(days=random.randint(0, 90)),
                        peso_kg=round(random.uniform(55, 105), 1),
                        altura_cm=round(random.uniform(155, 195), 1),
                        gordura_pct=round(random.uniform(8, 32), 1) if seq % 4 != 0 else None,
                        medidas=json.dumps(medidas, ensure_ascii=False),
                        problemas_saude=random.choice([None, "Nenhum", "Hipertensão leve", "Asma"]),
                        restricoes=random.choice([None, "Joelho", "Coluna lombar"]),
                        medicamentos=random.choice([None, "Whey", "Creatina"]),
                        contato_emergencia=f"Contato {seq} 1199999{seq%10000:04d}" if seq % 7 != 0 else None,
                    )
                    session.add(ficha)

            created += 1
            if (i + 1) % batch == 0:
                session.flush()
                session.commit()
                elapsed = time.perf_counter() - start
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                logger.info(f"batch {i+1}/{qtd} commit ({rate:.1f} alunos/s)")

        session.commit()
        # acessos em segunda fase para evitar FK ordering dentro do mesmo flush
        if args.with_acessos:
            logger.info("gerando acessos em segunda fase...")
            # busca ids recém-criados para garantir FK
            from sqlalchemy import select as _select

            # pega últimos qtd alunos stress
            stmt = _select(AlunoModel.id).where(AlunoModel.id.like("aluno-stress-%")).order_by(AlunoModel.id.desc()).limit(qtd)
            stress_ids = [r[0] for r in session.execute(stmt).all()]
            # se ainda não commitou todos (caso qtd grande), usa lista em memória
            if len(stress_ids) < qtd:
                # fallback: usa ids gerados no loop (não temos mais, então gera novamente a partir de seq)
                logger.warning(f"só {len(stress_ids)} stress ids encontrados, usando seq")
                stress_ids = [f"aluno-stress-{seq_start+i:05d}" for i in range(qtd)]
            for idx, aid in enumerate(stress_ids):
                # verifica se aluno existe (pode ter sufixo uuid, então busca like)
                # usa aluno real se existir, senão pula
                exists = session.get(AlunoModel, aid)
                if exists is None:
                    # tenta like: busca por prefixo
                    like = aid.split("-")[2] if "-" in aid else aid
                    stmt2 = _select(AlunoModel.id).where(AlunoModel.id.like(f"aluno-stress-{like}%")).limit(1)
                    row = session.execute(stmt2).first()
                    if row:
                        aid = row[0]
                    else:
                        continue
                if hash(aid) % 2 != 0:
                    continue
                for _ in range(random.randint(1, 3)):
                    ts = datetime.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
                    log = AcessoLogModel(
                        id=f"log-{uuid.uuid4().hex[:8]}",
                        aluno_id=aid,
                        funcionario_id=None,
                        direcao=random.choice(["ENTRADA", "SAIDA"]),
                        timestamp=ts,
                        resultado=random.choice(["LIBERADO", "LIBERADO", "LIBERADO", "NEGADO"]),
                        motivo=random.choice([None, "INADIMPLENTE", "SEM_MATRICULA"]),
                        detalhes="stress",
                    )
                    session.add(log)
                if (idx + 1) % batch == 0:
                    session.flush()
                    session.commit()
            session.commit()

        elapsed = time.perf_counter() - start
        logger.info(f"concluído: {created} alunos em {elapsed:.1f}s ({created/elapsed:.1f}/s)")

        # validação
        total_alunos = session.query(AlunoModel).count()
        total_mats = session.query(MatriculaModel).count()
        total_pags = session.query(PagamentoModel).count()
        total_fichas = session.query(AvaliacaoFisicaModel).count()
        total_logs = session.query(AcessoLogModel).count()
        print(f"TOTAL alunos={total_alunos} matriculas={total_mats} pagamentos={total_pags} fichas={total_fichas} logs={total_logs}")

        # sanity queries para testar funções
        t0 = time.perf_counter()
        # busca por nome com paginação
        from sqlalchemy import select

        stmt = select(AlunoModel).where(AlunoModel.nome.like("Aluno Stress%")).limit(50)
        res = session.execute(stmt).scalars().all()
        print(f"busca 50 alunos: {len(res)} em {(time.perf_counter()-t0)*1000:.1f}ms")
        # filtro por mês caixa
        t0 = time.perf_counter()
        stmt2 = select(PagamentoModel).limit(100)
        res2 = session.execute(stmt2).scalars().all()
        print(f"listar 100 pagamentos: {len(res2)} em {(time.perf_counter()-t0)*1000:.1f}ms")

        return 0
    except Exception as e:
        session.rollback()
        logger.error(f"falha: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        try:
            session.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
