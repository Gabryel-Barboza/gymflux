"""RegistrarPagamentoService — Fase 2 com injeção de repositório."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol

from loguru import logger

from gymflow.core.pagamento import FormaPagamento as Forma
from gymflow.core.pagamento import Pagamento


class PagamentoRepoProtocol(Protocol):
    def salvar(self, pagamento: Pagamento) -> Pagamento | None: ...
    def listar_por_aluno(self, aluno_id: str) -> list[Pagamento]: ...
    def buscar_por_id(self, pagamento_id: str) -> Pagamento | None: ...


@dataclass(slots=True)
class RepositorioPagamentosMemoria:
    _pagamentos: dict[str, Pagamento] = field(default_factory=dict)

    def salvar(self, pagamento: Pagamento) -> Pagamento:
        self._pagamentos[pagamento.id] = pagamento
        return pagamento

    def buscar_por_id(self, pagamento_id: str) -> Pagamento | None:
        return self._pagamentos.get(pagamento_id)

    def listar_por_aluno(self, aluno_id: str) -> list[Pagamento]:
        return [p for p in self._pagamentos.values() if p.aluno_id == aluno_id]

    def listar(self) -> list[Pagamento]:
        return list(self._pagamentos.values())

    def total(self) -> int:
        return len(self._pagamentos)

    def limpar(self) -> None:
        self._pagamentos.clear()

    def remover(self, pagamento_id: str) -> None:
        self._pagamentos.pop(pagamento_id, None)


@dataclass(slots=True)
class RegistrarPagamentoService:
    repo: PagamentoRepoProtocol = field(default_factory=RepositorioPagamentosMemoria)

    def registrar(self, pagamento: Pagamento) -> Pagamento:
        if self.repo.buscar_por_id(pagamento.id) is not None:
            raise ValueError(f"Pagamento id={pagamento.id} já existe")
        result = self.repo.salvar(pagamento)
        logger.info(f"[RegistrarPagamento] id={pagamento.id} aluno={pagamento.aluno_id}")
        return result if result is not None else pagamento

    def registrar_rapido(
        self,
        *,
        id: str,
        aluno_id: str,
        valor: Decimal | float | str,
        data_vencimento: date,
        data_pagamento: date | None = None,
        forma: Forma | str | None = None,
        competencia: str | None = None,
    ) -> Pagamento:
        v = Decimal(str(valor))
        p = Pagamento(
            id=id,
            aluno_id=aluno_id,
            valor=v,
            data_vencimento=data_vencimento,
            data_pagamento=data_pagamento,
            forma=forma,
            competencia=competencia,
        )
        return self.registrar(p)

    def pagamentos_do_aluno(self, aluno_id: str) -> list[Pagamento]:
        return self.repo.listar_por_aluno(aluno_id)

    def listar(self) -> list[Pagamento]:
        if hasattr(self.repo, "listar"):
            return self.repo.listar()  # type: ignore[no-any-return]
        return self.pagamentos_do_aluno("")  # fallback
