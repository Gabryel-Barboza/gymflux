"""aplicar_inatividade — sem entrada há 90d => INATIVO + sem senha (Fase 4.8)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from gymflux.core.acesso import DirecaoAcesso, ResultadoAcesso, TentativaAcesso
from gymflux.core.aluno import Aluno, StatusAluno
from gymflux.infra.repositories.acesso_log import AcessoLogRepositoryMemoria
from gymflux.infra.repositories.aluno import AlunoRepositoryMemoria
from gymflux.services.inatividade import aplicar_inatividade

HOJE = date(2026, 9, 12)


def _aluno(repo: AlunoRepositoryMemoria, aluno_id: str, senha: str = "1234") -> Aluno:
    a = Aluno(id=aluno_id, nome=f"Aluno {aluno_id}")
    a.definir_senha(senha)
    return repo.salvar(a)


def _entrada(
    repo: AcessoLogRepositoryMemoria,
    aluno_id: str,
    ha_dias: int,
    resultado: ResultadoAcesso = ResultadoAcesso.LIBERADO,
) -> None:
    ts = datetime.combine(HOJE - timedelta(days=ha_dias), datetime.min.time())
    repo.registrar(
        TentativaAcesso(
            aluno_id=aluno_id,
            direcao=DirecaoAcesso.ENTRADA,
            timestamp=ts,
            resultado=resultado,
        )
    )


def _repos() -> tuple[AlunoRepositoryMemoria, AcessoLogRepositoryMemoria]:
    return AlunoRepositoryMemoria(), AcessoLogRepositoryMemoria()


def test_entrada_recente_mantem_ativo_e_senha():
    alunos, logs = _repos()
    _aluno(alunos, "a1")
    _entrada(logs, "a1", ha_dias=10)
    assert aplicar_inatividade(alunos, logs, ref=HOJE) == 0
    mantido = alunos.buscar_por_id("a1")
    assert mantido is not None
    assert mantido.status == StatusAluno.ATIVO
    assert mantido.senha == "1234"


def test_entrada_antiga_inativa_e_limpa_senha():
    alunos, logs = _repos()
    _aluno(alunos, "a1")
    _entrada(logs, "a1", ha_dias=91)
    assert aplicar_inatividade(alunos, logs, ref=HOJE) == 1
    velho = alunos.buscar_por_id("a1")
    assert velho is not None
    assert velho.status == StatusAluno.INATIVO
    assert velho.senha is None


def test_limite_90_dias_inativa():
    alunos, logs = _repos()
    _aluno(alunos, "a1")
    _entrada(logs, "a1", ha_dias=90)
    assert aplicar_inatividade(alunos, logs, ref=HOJE) == 1
    assert alunos.buscar_por_id("a1").status == StatusAluno.INATIVO  # type: ignore[union-attr]


def test_nunca_entrou_inativa():
    alunos, logs = _repos()
    _aluno(alunos, "a1")
    assert aplicar_inatividade(alunos, logs, ref=HOJE) == 1
    velho = alunos.buscar_por_id("a1")
    assert velho is not None and velho.status == StatusAluno.INATIVO
    assert velho.senha is None


def test_so_negado_nao_segura():
    alunos, logs = _repos()
    _aluno(alunos, "a1")
    _entrada(logs, "a1", ha_dias=5, resultado=ResultadoAcesso.NEGADO)
    assert aplicar_inatividade(alunos, logs, ref=HOJE) == 1


def test_inativo_e_bloqueado_intactos():
    alunos, logs = _repos()
    a = _aluno(alunos, "a1")
    a.inativar()
    alunos.salvar(a)
    b = _aluno(alunos, "a2")
    b.bloquear_manual()
    alunos.salvar(b)
    assert aplicar_inatividade(alunos, logs, ref=HOJE) == 0
    assert alunos.buscar_por_id("a1").senha == "1234"  # type: ignore[union-attr]
    assert alunos.buscar_por_id("a2").senha == "1234"  # type: ignore[union-attr]


def test_dias_customizado():
    alunos, logs = _repos()
    _aluno(alunos, "a1")
    _entrada(logs, "a1", ha_dias=40)
    assert aplicar_inatividade(alunos, logs, dias=30, ref=HOJE) == 1
