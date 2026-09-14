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
        # nunca inativa recém-criado sem histórico: dá 30 dias de carência
        # (evita que aluno novo sem LIBERADO seja inativado antes da primeira cobrança)
        try:
            # tenta pegar data de criação via atributo opcional (se existir)
            criacao = getattr(aluno, "created_at", None)
            if criacao is not None:
                try:
                    criacao_date = criacao.date() if hasattr(criacao, "date") else criacao
                    if (hoje - criacao_date).days < 30:
                        continue
                except Exception:
                    pass
        except Exception:
            pass
        try:
            logs = acesso_repo.listar_por_aluno(aluno.id)
        except Exception as e:
            logger.warning(f"[Inatividade] log de {aluno.id} falhou ({e}) — pulado")
            continue
        ultima = max(
            (t.timestamp.date() for t in logs if t.resultado == ResultadoAcesso.LIBERADO),
            default=None,
        )
        if ultima is None:
            # sem histórico: só inativa se já passou da carência (acima)
            # se não tem created_at, mantém regra antiga (inativa)
            # mas se tem carência, já pulou acima
            pass
        elif (hoje - ultima).days < dias:
            continue
        aluno.inativar()
        aluno.limpar_senha()
        aluno_repo.salvar(aluno)
        inativados += 1
        logger.info(f"[Inatividade] {aluno.id} inativo (última entrada: {ultima})")
    return inativados
