"""FichaViewModel — salvar/listar ordenado por data desc."""

from __future__ import annotations

from datetime import date

from gymflux.infra.repositories.avaliacao_fisica import AvaliacaoFisicaRepositoryMemoria
from gymflux.ui.viewmodels.ficha import FichaViewModel


def test_ficha_salvar_e_listar_desc():
    repo = AvaliacaoFisicaRepositoryMemoria()
    vm = FichaViewModel(repo=repo)
    ava1 = vm.salvar(aluno_id="al-1", data=date(2026, 9, 10), peso_kg=70, medidas={"braco": 30})
    ava2 = vm.salvar(aluno_id="al-1", data=date(2026, 9, 15), peso_kg=75)
    lst = vm.listar_por_aluno("al-1")
    assert lst[0].id == ava2.id  # mais recente primeiro
    assert lst[1].id == ava1.id
    assert lst[0].peso_kg == 75


def test_ficha_filtra_por_aluno():
    repo = AvaliacaoFisicaRepositoryMemoria()
    vm = FichaViewModel(repo=repo)
    vm.salvar(aluno_id="al-1", data=date.today(), peso_kg=70)
    vm.salvar(aluno_id="al-2", data=date.today(), peso_kg=80)
    assert len(vm.listar_por_aluno("al-1")) == 1
    assert len(vm.listar()) == 2


def test_ficha_validacao_core():
    import pytest

    repo = AvaliacaoFisicaRepositoryMemoria()
    vm = FichaViewModel(repo=repo)
    with pytest.raises(ValueError, match="Peso"):
        vm.salvar(aluno_id="al-1", peso_kg=-5)
    with pytest.raises(ValueError, match="Gordura"):
        vm.salvar(aluno_id="al-1", gordura_pct=150)
