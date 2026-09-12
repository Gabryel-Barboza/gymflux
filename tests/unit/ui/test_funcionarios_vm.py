"""FuncionariosViewModel — CRUD + ativar/inativar + senha."""

from __future__ import annotations

import pytest

from gymflow.infra.repositories.funcionario import FuncionarioRepositoryMemoria
from gymflow.ui.viewmodels.funcionarios import FuncionariosViewModel


def test_funcionarios_crud_e_ativar():
    vm = FuncionariosViewModel(repo=FuncionarioRepositoryMemoria())
    func = vm.cadastrar(nome="Zé Porteira", senha="1234")
    assert func.senha_hash is not None and "1234" not in func.senha_hash
    assert func.ativo is True
    assert [f.nome for f in vm.listar()] == ["Zé Porteira"]
    vm.definir_ativo(func.id, False)
    assert vm.buscar(func.id) is not None
    assert vm.buscar(func.id).ativo is False  # type: ignore[union-attr]
    vm.atualizar(func.id, nome="José", senha="")
    atual = vm.buscar(func.id)
    assert atual is not None and atual.nome == "José"
    assert atual.verificar_senha("1234") is True  # vazia mantém
    with pytest.raises(ValueError, match="não encontrado"):
        vm.definir_ativo("inexistente", True)
    with pytest.raises(ValueError, match="dígitos"):
        vm.cadastrar(nome="X", senha="12")
