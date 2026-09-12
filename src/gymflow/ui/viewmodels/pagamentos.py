"""PagamentosViewModel — registro + situação de adimplência (RB01)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from gymflow.core.aluno import Aluno
from gymflow.core.pagamento import (
    FormaPagamento,
    Pagamento,
    dias_em_atraso,
    esta_adimplente,
)
from gymflow.services.cadastrar_aluno import CadastrarAlunoService
from gymflow.services.registrar_pagamento import RegistrarPagamentoService


@dataclass
class PagamentosViewModel:
    pagamentos: RegistrarPagamentoService
    alunos: CadastrarAlunoService
    commit: Callable[[], None] | None = None
    tolerancia_padrao_dias: int = 3

    def _commit(self) -> None:
        if self.commit is not None:
            self.commit()

    def listar_alunos(self) -> list[Aluno]:
        return sorted(self.alunos.listar(), key=lambda a: a.nome.lower())

    def do_aluno(self, aluno_id: str) -> list[Pagamento]:
        pags = self.pagamentos.pagamentos_do_aluno(aluno_id)
        return sorted(pags, key=lambda p: p.data_vencimento, reverse=True)

    def registrar(
        self,
        *,
        aluno_id: str,
        valor: Decimal | float | str,
        data_vencimento: date,
        forma: FormaPagamento | str | None = None,
        pago: bool = False,
        data_pagamento: date | None = None,
        competencia: str | None = None,
    ) -> Pagamento:
        if self.alunos.buscar(aluno_id) is None:
            raise ValueError(f"Aluno id={aluno_id} não encontrado")
        result = self.pagamentos.registrar_rapido(
            id=f"pag-{uuid.uuid4().hex[:8]}",
            aluno_id=aluno_id,
            valor=Decimal(str(valor)),
            data_vencimento=data_vencimento,
            data_pagamento=date.today() if pago else data_pagamento,
            forma=forma,
            competencia=(competencia.strip() or None) if competencia else None,
        )
        self._commit()
        return result

    def situacao(self, aluno_id: str, hoje: date | None = None) -> tuple[str, int]:
        """Retorna (rotulo, dias_em_atraso) p/ destaque de inadimplente (RB01)."""
        ref = hoje or date.today()
        pags = self.pagamentos.pagamentos_do_aluno(aluno_id)
        if not pags:
            return ("SEM PAGAMENTOS", 0)
        atraso = dias_em_atraso(pags, ref)
        if esta_adimplente(pags, ref, self.tolerancia_padrao_dias):
            return ("ADIMPLENTE", atraso)
        return ("INADIMPLENTE", atraso)
