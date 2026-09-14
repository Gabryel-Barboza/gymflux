"""aplicar_inatividade — desativa aluno sem entrada há N dias (Fase 4.8).

Regra operacional (NÃO é RB01-RB05): aluno ATIVO sem ``TentativaAcesso``
LIBERADO nos últimos ``dias`` (default 90, nunca entrou conta como
inativo) → ``status=INATIVO`` + ``senha=None`` (PIN expira junto).

Só toca ATIVO (BLOQUEADO manual e INATIVO ficam intactos). Sem commit
próprio (padrão Fase 4.1): quem chama commita. Falha ao ler o log de um
aluno pula só ele (nunca aborta a varredura).
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

from loguru import logger

from gymflux.core.acesso import ResultadoAcesso, TentativaAcesso
from gymflux.core.aluno import Aluno


class _AlunoRepoProto(Protocol):
    def listar(self) -> list[Aluno]: ...
    def salvar(self, aluno: Aluno) -> Aluno | None: ...


class _AcessoRepoProto(Protocol):
    def listar_por_aluno(self, aluno_id: str) -> list[TentativaAcesso]: ...


def aplicar_inatividade(
    aluno_repo: _AlunoRepoProto,
    acesso_repo: _AcessoRepoProto,
    dias: int = 90,
    ref: date | None = None,
) -> int:
    """Varre alunos e inativa os sem entrada há ``dias``. Retorna qtd."""
    hoje = ref or date.today()
    inativados = 0
    for aluno in aluno_repo.listar():
        # só ATIVO não-bloqueado: bloqueio manual e INATIVO ficam intactos
        if not aluno.esta_ativo:
            continue
        try:
            logs = acesso_repo.listar_por_aluno(aluno.id)
        except Exception as e:
            logger.warning(f"[Inatividade] log de {aluno.id} falhou ({e}) — pulado")
            continue
        ultima = max(
            (t.timestamp.date() for t in logs if t.resultado == ResultadoAcesso.LIBERADO),
            default=None,
        )
        if ultima is not None:
            if (hoje - ultima).days < dias:
                continue
        else:
            # nunca entrou: usa created_at como carência (90 dias)
            created = getattr(aluno, "created_at", None)
            if created is not None:
                try:
                    c_date = created.date() if hasattr(created, "date") else created
                    if (hoje - c_date).days < dias:  # type: ignore[operator]
                        continue
                except Exception:
                    pass
            else:
                # sem created_at e sem logs: mantém regra antiga (inativa) para compat com testes
                # mas em produção com DB, created_at sempre existe (server_default), então
                # novos alunos ficam protegidos por 90 dias
                pass
        aluno.inativar()
        aluno.limpar_senha()
        aluno_repo.salvar(aluno)
        inativados += 1
        logger.info(f"[Inatividade] {aluno.id} inativo (última entrada: {ultima})")
    return inativados
