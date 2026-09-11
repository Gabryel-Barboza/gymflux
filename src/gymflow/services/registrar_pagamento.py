"""RegistrarPagamentoService — memória (Fase 1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from loguru import logger

from gymflow.core.pagamento import FormaPagamento as Forma
from gymflow.core.pagamento import Pagamento


@dataclass(slots=True)
class RepositorioPagamentosMemoria:
    _pagamentos: dict[str, Pagamento] = field(default_factory=dict)

    def salvar(self, pagamento: Pagamento) -> None:
        self._pagamentos[pagamento.id] = pagamento

    def listar_por_aluno(self, aluno_id: str) -> list[Pagamento]:
        return [p for p in self._pagamentos.values() if p.aluno_id == aluno_id]

    def total(self) -> int:
        return len(self._pagamentos)

    def limpar(self) -> None:
        self._pagamentos.clear()


@dataclass(slots=True)
class RegistrarPagamentoService:
    repo: RepositorioPagamentosMemoria = field(default_factory=RepositorioPagamentosMemoria)

    def registrar(self, pagamento: Pagamento) -> Pagamento:
        if pagamento.id in self.repo._pagamentos:
            raise ValueError(f"Pagamento id={pagamento.id} já existe")
        self.repo.salvar(pagamento)
        logger.info(f"[RegistrarPagamento] id={pagamento.id} aluno={pagamento.aluno_id}")
        return pagamento

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
