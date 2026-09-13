"""CaixaViewModel — registro, consulta por mês, totais e fechamento (Qt-free)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from gymflux.core.aluno import Aluno
from gymflux.core.caixa import FechamentoCaixa, validar_mes
from gymflux.core.pagamento import FormaPagamento, Pagamento
from gymflux.services.cadastrar_aluno import CadastrarAlunoService
from gymflux.services.registrar_pagamento import RegistrarPagamentoService
from gymflux.ui.config_store import UiConfig


class FechamentoRepoProto(Protocol):
    def salvar(self, fechamento: FechamentoCaixa) -> FechamentoCaixa: ...
    def buscar_por_mes(self, mes: str) -> FechamentoCaixa | None: ...
    def listar(self) -> list[FechamentoCaixa]: ...
    def remover(self, fechamento_id: str) -> None: ...


@dataclass
class CaixaViewModel:
    pagamentos: RegistrarPagamentoService
    alunos: CadastrarAlunoService
    fechamentos: FechamentoRepoProto
    commit: Callable[[], None] | None = None
    ui_config: UiConfig = field(default_factory=UiConfig)

    def _commit(self) -> None:
        if self.commit is not None:
            self.commit()

    # -- consulta ---------------------------------------------------------------
    @staticmethod
    def mes_de(pagamento: Pagamento) -> str:
        return pagamento.competencia or pagamento.data_vencimento.strftime("%Y-%m")

    def listar_todos(self) -> list[Pagamento]:
        return self.pagamentos.listar()

    def meses_disponiveis(self) -> list[str]:
        meses = {self.mes_de(p) for p in self.listar_todos()}
        meses.update(f.mes for f in self.fechamentos.listar())
        return sorted(meses, reverse=True)

    def por_mes(self, mes: str | None) -> list[tuple[Pagamento, str]]:
        """(pagamento, nome_aluno) do mês ou todos; ordenado por vencimento desc."""
        nomes = {a.id: a.nome for a in self.listar_alunos()}
        pags = self.listar_todos()
        if mes is not None:
            pags = [p for p in pags if self.mes_de(p) == mes]
        pags.sort(key=lambda p: p.data_vencimento, reverse=True)
        return [(p, nomes.get(p.aluno_id, p.aluno_id)) for p in pags]

    def totais_mes(self, mes: str | None) -> tuple[Decimal, Decimal, Decimal]:
        """(recebido, pendente, total) do mês ou geral."""
        recebido = Decimal("0")
        pendente = Decimal("0")
        for p, _nome in self.por_mes(mes):
            if p.pago:
                recebido += p.valor
            else:
                pendente += p.valor
        return recebido, pendente, recebido + pendente

    def listar_alunos(self) -> list[Aluno]:
        return sorted(self.alunos.listar(), key=lambda a: a.nome.lower())

    def do_aluno(self, aluno_id: str) -> list[Pagamento]:
        pags = self.pagamentos.pagamentos_do_aluno(aluno_id)
        return sorted(pags, key=lambda p: p.data_vencimento, reverse=True)

    # -- fechamento ---------------------------------------------------------------
    def fechado_em(self, mes: str) -> datetime | None:
        fechado = self.fechamentos.buscar_por_mes(validar_mes(mes))
        return fechado.fechado_em if fechado else None

    def mes_fechado(self, mes: str) -> bool:
        return self.fechado_em(mes) is not None

    def fechar_mes(self, mes: str, agora: datetime | None = None) -> FechamentoCaixa:
        mes_ok = validar_mes(mes)
        if self.mes_fechado(mes_ok):
            raise ValueError(f"Caixa de {mes_ok} já está fechado")
        recebido, _pendente, _total = self.totais_mes(mes_ok)
        fechamento = FechamentoCaixa(
            id=f"fec-{uuid.uuid4().hex[:8]}",
            mes=mes_ok,
            total=recebido,
            fechado_em=agora or datetime.now(),
        )
        self.fechamentos.salvar(fechamento)
        self._commit()
        return fechamento

    def reabrir_mes(self, mes: str) -> None:
        """Remove fechamento do mês, liberando novos registros."""
        mes_ok = validar_mes(mes)
        fech = self.fechamentos.buscar_por_mes(mes_ok)
        if fech is None:
            raise ValueError(f"Caixa de {mes_ok} não está fechado")
        self.fechamentos.remover(fech.id)
        self._commit()

    # -- registro (bloqueia mês fechado) -------------------------------------------
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
        comp = (competencia.strip() or None) if competencia else None
        if comp is not None:
            validar_mes(comp)
        mes = comp or data_vencimento.strftime("%Y-%m")
        if self.mes_fechado(mes):
            raise ValueError(f"Caixa de {mes} está FECHADO — registro bloqueado")
        if self.alunos.buscar(aluno_id) is None:
            raise ValueError(f"Aluno id={aluno_id} não encontrado")
        # valida valor >0 e forma: None => PIX, só vazio/"-" é erro
        texto_valor = str(valor).strip()
        if not texto_valor or texto_valor == "-":
            raise ValueError("Valor é obrigatório e deve ser > 0")
        try:
            dec = Decimal(texto_valor)
        except Exception as exc:
            raise ValueError("Valor inválido") from exc
        if dec <= Decimal("0"):
            raise ValueError("Valor deve ser > 0")
        if forma is None:
            forma = FormaPagamento.PIX
        elif isinstance(forma, str) and (not forma.strip() or forma.strip() == "—"):
            raise ValueError("Forma de pagamento é obrigatória")
        result = self.pagamentos.registrar_rapido(
            id=f"pag-{uuid.uuid4().hex[:8]}",
            aluno_id=aluno_id,
            valor=dec,
            data_vencimento=data_vencimento,
            data_pagamento=date.today() if pago else data_pagamento,
            forma=forma,
            competencia=comp,
        )
        self._commit()
        return result

    def remover_pagamento(self, pagamento_id: str) -> None:
        """Remove pagamento (resolve débito) + commit."""
        # tenta via service.repo.remover (memória) ou via pagamento_repo SQL
        repo = getattr(self.pagamentos, "repo", None)
        if repo is not None and hasattr(repo, "remover"):
            repo.remover(pagamento_id)  # type: ignore[attr-defined]
        elif hasattr(self.pagamentos, "remover"):
            self.pagamentos.remover(pagamento_id)  # type: ignore[attr-defined]
        else:  # fallback: chama pagamento repo direto se existir
            raise RuntimeError("Repositório de pagamentos sem remover()")
        self._commit()
