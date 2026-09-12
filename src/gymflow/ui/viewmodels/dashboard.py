"""DashboardViewModel — decisões de acesso + log, sem Qt e sem hardware."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from gymflow.core.acesso import DecisaoAcesso, DirecaoAcesso, TentativaAcesso
from gymflow.core.aluno import Aluno
from gymflow.services.identificar_acesso import (
    Identificacao,
    IdentificarAcessoService,
    OrigemIdentificacao,
)
from gymflow.services.liberar_acesso import LiberarAcessoService


class LogRepoProto(Protocol):
    """Protocolo mínimo p/ log de tentativas (SQLAlchemy ou memória)."""

    def listar(self) -> list[TentativaAcesso]: ...


@dataclass
class DashboardViewModel:
    """Orquestra liberação via ``LiberarAcessoService`` (que aciona o driver)."""

    acesso: LiberarAcessoService
    log_repo: LogRepoProto | None = None
    commit: Callable[[], None] | None = None
    giros: list[tuple[str, float]] = field(default_factory=list)
    identificar: IdentificarAcessoService | None = None

    def _commit(self) -> None:
        if self.commit is not None:
            self.commit()

    # -- liberação (passa pela RB01-RB05 + hardware via service) --------------
    def liberar_entrada(self, aluno_id: str) -> DecisaoAcesso:
        decisao = self.acesso.tentar_acesso_por_id(aluno_id, DirecaoAcesso.ENTRADA)
        self._commit()
        return decisao

    def liberar_saida(self, aluno_id: str) -> DecisaoAcesso:
        decisao = self.acesso.tentar_acesso_por_id(aluno_id, DirecaoAcesso.SAIDA)
        self._commit()
        return decisao

    # -- resolução de aluno p/ recepção (id exato ou CPF) ----------------------
    def resolver_aluno(self, texto: str) -> Aluno | None:
        repo = self.acesso.aluno_repo
        if repo is None:
            return None
        chave = texto.strip()
        if not chave:
            return None
        aluno = repo.buscar_por_id(chave)
        if aluno is not None:
            return aluno
        try:
            return repo.buscar_por_cpf(chave)
        except Exception:
            return None

    # -- identificação estilo SCA (teclado/cartão) -> decisão + aluno ---------
    def identificar_acesso(
        self,
        codigo: str,
        origem: OrigemIdentificacao | str,
        direcao: DirecaoAcesso = DirecaoAcesso.ENTRADA,
    ) -> tuple[DecisaoAcesso, Aluno | None]:
        if self.identificar is None:
            raise RuntimeError("IdentificarAcessoService não injetado")
        ori = OrigemIdentificacao(origem) if isinstance(origem, str) else origem
        ident = (
            Identificacao.por_cartao(codigo)
            if ori == OrigemIdentificacao.CARTAO
            else Identificacao.por_teclado(codigo)
        )
        decisao, aluno = self.identificar.identificar(ident, direcao=direcao)
        self._commit()
        return decisao, aluno

    # -- giro vindo do bridge (Signal -> view chama este método) --------------
    def registrar_giro(self, direcao_nome: str, ts: float) -> None:
        self.giros.append((direcao_nome, ts))
        del self.giros[:-50]

    # -- log ------------------------------------------------------------------
    def ultimas_tentativas(self, n: int = 50) -> list[TentativaAcesso]:
        if self.log_repo is not None:
            return self.log_repo.listar()[-n:]
        return self.acesso.registro.tentativas[-n:]

    def nome_aluno(self, aluno_id: str) -> str:
        """Nome p/ exibir no log; fallback p/ ID se aluno sumiu do cadastro."""
        repo = self.acesso.aluno_repo
        if repo is None:
            return aluno_id
        try:
            aluno = repo.buscar_por_id(aluno_id)
        except Exception:
            return aluno_id
        return aluno.nome if aluno is not None else aluno_id

    @staticmethod
    def resume_decisao(d: DecisaoAcesso) -> str:
        if d.liberado:
            return f"LIBERADO — {d.detalhes or 'catraca liberada'}"
        motivo = str(d.motivo) if d.motivo else "negado"
        extra = f" ({d.detalhes})" if d.detalhes else ""
        return f"NEGADO — {motivo}{extra}"
