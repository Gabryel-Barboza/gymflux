"""FrequenciaViewModel — filtros dia/mês/aluno + resumo por dia (Qt-free)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from gymflow.core.acesso import DirecaoAcesso, ResultadoAcesso, TentativaAcesso
from gymflow.core.aluno import Aluno
from gymflow.core.funcionario import Funcionario
from gymflow.infra.repositories.acesso_log import AcessoLogRepositoryMemoria
from gymflow.infra.repositories.aluno import AlunoRepositoryMemoria
from gymflow.infra.repositories.funcionario import FuncionarioRepositoryMemoria
from gymflow.ui.viewmodels.frequencia import FrequenciaViewModel

HOJE = date(2026, 9, 12)
ONTEM = HOJE - timedelta(days=1)


def _t(
    aluno_id=None,
    dia=HOJE,
    hora=9,
    resultado=ResultadoAcesso.LIBERADO,
    direcao=DirecaoAcesso.ENTRADA,
    funcionario_id=None,
):
    return TentativaAcesso(
        aluno_id=aluno_id,
        funcionario_id=funcionario_id,
        direcao=direcao,
        timestamp=datetime(dia.year, dia.month, dia.day, hora, 0),
        resultado=resultado,
    )


def _vm():
    log = AcessoLogRepositoryMemoria()
    alunos = AlunoRepositoryMemoria()
    funcs = FuncionarioRepositoryMemoria()
    alunos.salvar(Aluno(id="a1", nome="Ana Silva"))
    alunos.salvar(Aluno(id="a2", nome="Bruno Souza"))
    f = Funcionario(id="f1", nome="Zé Porteira")
    funcs.salvar(f)
    log.registrar(_t("a1", HOJE, hora=8))
    log.registrar(_t("a1", HOJE, hora=18, direcao=DirecaoAcesso.SAIDA))
    log.registrar(_t("a2", ONTEM, hora=9))
    log.registrar(_t("a1", ONTEM, hora=9, resultado=ResultadoAcesso.NEGADO))
    log.registrar(_t(None, HOJE, hora=12, funcionario_id="f1"))
    return FrequenciaViewModel(log_repo=log, aluno_repo=alunos, funcionario_repo=funcs)


def test_filtrar_dia_mes_aluno():
    vm = _vm()
    assert len(vm.filtrar(dia=HOJE)) == 3
    assert len(vm.filtrar(dia=ONTEM)) == 2
    assert len(vm.filtrar(mes="2026-09")) == 5
    assert len(vm.filtrar(aluno_id="a1")) == 3
    assert len(vm.filtrar(dia=HOJE, aluno_id="a1")) == 2
    assert vm.filtrar() == vm.tentativas()
    assert len(vm.filtrar(aluno_id="inexistente")) == 0


def test_meses_e_nomes():
    vm = _vm()
    assert vm.meses_disponiveis() == ["2026-09"]
    assert [a.nome for a in vm.listar_alunos()] == ["Ana Silva", "Bruno Souza"]
    tentativas = vm.tentativas()
    nomes = {vm.nome_tentativa(t) for t in tentativas}
    assert {"Ana Silva", "Bruno Souza", "Zé Porteira"} <= nomes


def test_resumo_por_dia_exclui_hoje_e_negados():
    vm = _vm()
    # ontem a1 só tem 1 NEGADO => sem dia com presença
    assert vm.resumo_por_dia("a1", hoje=HOJE) == []
    vm2_tudo = vm.resumo_por_dia("a1", excluir_hoje=False, hoje=HOJE)
    assert vm2_tudo == [(HOJE, 1, 1)]


def test_sem_repos_nao_quebra():
    vm = FrequenciaViewModel()
    assert vm.tentativas() == []
    assert vm.filtrar(dia=HOJE) == []
    assert vm.meses_disponiveis() == []
    assert vm.listar_alunos() == []
    assert vm.resumo_por_dia("a1") == []
