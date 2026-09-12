"""RB04 — timeout de giro (puro, sem hardware)."""

from __future__ import annotations

from datetime import datetime, timedelta

from gymflux.core.acesso import MotivoNegado, ResultadoAcesso
from gymflux.core.regras import RegraAcesso, RegraAcessoConfig


def test_rb04_timeout_nao_expirou():
    regra = RegraAcesso(RegraAcessoConfig(timeout_giro_s=7))
    liberado_em = datetime(2026, 9, 11, 10, 0, 0)
    agora = liberado_em + timedelta(seconds=5)
    assert regra.acesso_expirou(liberado_em, agora) is False
    assert regra.decisao_timeout_se_expirado(liberado_em, agora) is None


def test_rb04_timeout_expirou():
    regra = RegraAcesso(RegraAcessoConfig(timeout_giro_s=7))
    liberado_em = datetime(2026, 9, 11, 10, 0, 0)
    agora = liberado_em + timedelta(seconds=8)
    assert regra.acesso_expirou(liberado_em, agora) is True
    decisao = regra.decisao_timeout_se_expirado(liberado_em, agora)
    assert decisao is not None
    assert decisao.resultado == ResultadoAcesso.TIMEOUT
    assert decisao.motivo == MotivoNegado.TIMEOUT_GIRO


def test_rb04_timeout_exato_limite():
    regra = RegraAcesso(RegraAcessoConfig(timeout_giro_s=7))
    liberado_em = datetime(2026, 9, 11, 10, 0, 0)
    agora = liberado_em + timedelta(seconds=7)
    # exatamente 7s não expirou (>7)
    assert regra.acesso_expirou(liberado_em, agora) is False
    agora2 = liberado_em + timedelta(seconds=7, milliseconds=1)
    assert regra.acesso_expirou(liberado_em, agora2) is True


def test_rb04_tempo_restante():
    regra = RegraAcesso(RegraAcessoConfig(timeout_giro_s=7))
    liberado_em = datetime(2026, 9, 11, 10, 0, 0)
    agora = liberado_em + timedelta(seconds=2)
    assert regra.tempo_restante_giro(liberado_em, agora) == 5.0
    agora3 = liberado_em + timedelta(seconds=10)
    assert regra.tempo_restante_giro(liberado_em, agora3) == 0.0
