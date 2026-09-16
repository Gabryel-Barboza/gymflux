"""Turnos — parse/format/compato + VM roundtrip."""

from __future__ import annotations

import pytest

from gymflux.core.funcionario import (
    Turno,
    format_turnos,
    format_turnos_compacto,
    parse_turnos,
    parse_turnos_tolerante,
)
from gymflux.infra.repositories.funcionario import FuncionarioRepositoryMemoria
from gymflux.ui.viewmodels.funcionarios import FuncionariosViewModel


def test_parse_format_basico():
    txt = "Seg-Sex 08:00-12:00; Seg-Sex 14:00-18:00; Sáb 08:00-12:00"
    turnos = parse_turnos(txt)
    assert len(turnos) == 3
    assert turnos[0] == Turno(dias="Seg-Sex", inicio="08:00", fim="12:00")
    assert format_turnos(turnos) == txt


def test_parse_todos_e_sab_normaliza():
    # Todos -> Seg-Dom
    t = parse_turnos("Todos 08:00-12:00")
    assert t[0].dias == "Seg-Dom"
    assert format_turnos(t) == "Seg-Dom 08:00-12:00"
    # Sab sem acento
    t2 = parse_turnos("Sab 08:00-12:00")
    assert t2[0].dias == "Sáb"


def test_parse_valida_hhmm_e_dias():
    with pytest.raises(ValueError, match="Horário inválido"):
        parse_turnos("Seg-Sex 25:00-12:00")
    with pytest.raises(ValueError, match="início deve ser antes"):
        parse_turnos("Seg-Sex 14:00-12:00")
    with pytest.raises(ValueError, match="Dias inválido"):
        parse_turnos("Foo 08:00-12:00")
    with pytest.raises(ValueError, match="Faixa de dias inválida"):
        parse_turnos("Sex-Seg 08:00-12:00")


def test_parse_tolerante_legado():
    # antigo só horário + dias separado
    turnos = parse_turnos_tolerante("08:00-18:00", dias_legado="Seg-Sex")
    assert turnos[0].dias == "Seg-Sex"
    # texto já novo passa direto
    turnos2 = parse_turnos_tolerante("Sáb 08:00-12:00", dias_legado=None)
    assert turnos2[0].dias == "Sáb"
    # vazio
    assert parse_turnos_tolerante(None) == []
    assert parse_turnos_tolerante("  ") == []


def test_compacto_agrupa_por_dias():
    txt = "Seg-Sex 08:00-12:00; Seg-Sex 14:00-18:00; Sáb 08:00-12:00"
    compact = format_turnos_compacto(txt)
    # deve agrupar Seg-Sex com dois horários no mesmo grupo
    assert "Seg–Sex" in compact  # en-dash
    assert "08h–12h" in compact or "08:00–12:00" in compact
    assert "14h–18h" in compact or "14:00–18:00" in compact
    assert "Sáb" in compact
    # tooltip usa full via format_turnos, compact usa en-dash
    # linhas: Seg–Sex /08–12h · 14–18h / Sáb 08–12h  => 3 linhas
    assert compact.count("\n") >= 1


def test_vm_roundtrip_normaliza():
    vm = FuncionariosViewModel(repo=FuncionarioRepositoryMemoria())
    func = vm.cadastrar(nome="Ana", senha="1234", horarios="Seg-Sex 08:00-12:00; Sáb 08:00-12:00")
    assert func.horarios == "Seg-Sex 08:00-12:00; Sáb 08:00-12:00"
    # atualizar com Todos normaliza
    func2 = vm.atualizar(func.id, nome="Ana", horarios="Todos 08:00-12:00")
    assert func2.horarios == "Seg-Dom 08:00-12:00"
    # horário inválido rejeita
    with pytest.raises(ValueError, match="Horário inválido"):
        vm.cadastrar(nome="Bob", senha="2345", horarios="Seg-Sex 99:00-12:00")
    with pytest.raises(ValueError, match="Dias inválido"):
        vm.cadastrar(nome="Carol", senha="3456", horarios="Foo 08:00-12:00")
    # texto legado tolerante via parse_turnos_tolerante não usado direto no VM,
    # mas VM deve validar; horário puro sem dias vira Seg-Sex
    # Na VM, parse_turnos puro espera dias, então "08:00-12:00"
    # será parseado como dias padrão Seg-Sex
    func3 = vm.cadastrar(nome="Dave", senha="4567", horarios="08:00-12:00")
    assert func3.horarios == "Seg-Sex 08:00-12:00"
