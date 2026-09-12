"""DashboardViewModel — decisões de acesso + log, sem Qt e sem hardware."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from gymflux.core.acesso import DecisaoAcesso, DirecaoAcesso, MotivoNegado, TentativaAcesso
from gymflux.core.aluno import Aluno
from gymflux.core.funcionario import Funcionario
from gymflux.services.identificar_acesso import (
    Identificacao,
    IdentificarAcessoService,
    OrigemIdentificacao,
)
from gymflux.services.liberar_acesso import LiberarAcessoService
from gymflux.ui.config_store import UiConfig


class LogRepoProto(Protocol):
    """Protocolo mínimo p/ log de tentativas (SQLAlchemy ou memória)."""

    def listar(self) -> list[TentativaAcesso]: ...


class FuncionarioRepoProto(Protocol):
    """Protocolo mínimo p/ exibir nome de funcionário no log."""

    def buscar_por_id(self, funcionario_id: str) -> Funcionario | None: ...


@dataclass
class DashboardViewModel:
    """Orquestra liberação via ``LiberarAcessoService`` (que aciona o driver)."""

    acesso: LiberarAcessoService
    log_repo: LogRepoProto | None = None
    commit: Callable[[], None] | None = None
    giros: list[tuple[str, float]] = field(default_factory=list)
    identificar: IdentificarAcessoService | None = None
    ui_config: UiConfig = field(default_factory=UiConfig)
    funcionario_repo: FuncionarioRepoProto | None = None

    def _commit(self) -> None:
        if self.commit is not None:
            self.commit()

    def _direcao_bloqueada(self, direcao: DirecaoAcesso) -> DecisaoAcesso | None:
        """NEGADO direto se a direção está bloqueada nas Configurações."""
        bloqueada = (
            self.ui_config.bloquear_entrada
            if direcao == DirecaoAcesso.ENTRADA
            else self.ui_config.bloquear_saida
        )
        if not bloqueada:
            return None
        return DecisaoAcesso.negado(
            MotivoNegado.BLOQUEIO_MANUAL,
            f"{direcao.value.capitalize()} bloqueada (Configurações)",
        )

    # -- liberação (passa pela RB01-RB05 + hardware via service) --------------
    def liberar_entrada(self, aluno_id: str) -> DecisaoAcesso:
        negado = self._direcao_bloqueada(DirecaoAcesso.ENTRADA)
        if negado is not None:
            self._commit()
            return negado
        decisao = self.acesso.tentar_acesso_por_id(aluno_id, DirecaoAcesso.ENTRADA)
        self._commit()
        return decisao

    def liberar_saida(self, aluno_id: str) -> DecisaoAcesso:
        negado = self._direcao_bloqueada(DirecaoAcesso.SAIDA)
        if negado is not None:
            self._commit()
            return negado
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

    # -- identificação estilo SCA (teclado) -> decisão + aluno -----------------
    def identificar_acesso(
        self,
        codigo: str,
        origem: OrigemIdentificacao | str,
        direcao: DirecaoAcesso = DirecaoAcesso.ENTRADA,
    ) -> tuple[DecisaoAcesso, Aluno | None]:
        if self.identificar is None:
            raise RuntimeError("IdentificarAcessoService não injetado")
        negado = self._direcao_bloqueada(direcao)
        if negado is not None:
            self._commit()
            return negado, None
        ori = OrigemIdentificacao(origem) if isinstance(origem, str) else origem
        if ori != OrigemIdentificacao.TECLADO:
            raise ValueError(f"origem {ori} removida na Fase 4.8 (só TECLADO)")
        digitos = sum(1 for c in codigo if c.isdigit())
        if digitos < self.ui_config.senha_min_digitos:
            self._commit()
            return (
                DecisaoAcesso.negado(
                    "SENHA_CURTA",
                    f"Senha com {digitos} dígitos (mínimo {self.ui_config.senha_min_digitos})",
                ),
                None,
            )
        decisao, aluno = self.identificar.identificar(
            Identificacao.por_teclado(codigo), direcao=direcao
        )
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

    def tentativas_do_dia(self, dia: date | None = None, n: int = 50) -> list[TentativaAcesso]:
        """Só o dia (antifraude) — padrão hoje; imune a troca de data via param."""
        ref = dia or date.today()
        do_dia = [t for t in self._todas() if t.timestamp.date() == ref]
        return do_dia[-n:]

    def _todas(self) -> list[TentativaAcesso]:
        if self.log_repo is not None:
            return self.log_repo.listar()
        return list(self.acesso.registro.tentativas)

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

    def nome_tentativa(self, tentativa: TentativaAcesso) -> str:
        """Nome p/ exibir no log (aluno, funcionário ou fallback p/ ID)."""
        if tentativa.funcionario_id:
            repo = self.funcionario_repo
            if repo is None:
                return tentativa.funcionario_id
            try:
                func = repo.buscar_por_id(tentativa.funcionario_id)
            except Exception:
                return tentativa.funcionario_id
            return func.nome if func is not None else tentativa.funcionario_id
        if tentativa.aluno_id:
            return self.nome_aluno(tentativa.aluno_id)
        return "—"

    @staticmethod
    def resume_decisao(d: DecisaoAcesso) -> str:
        if d.liberado:
            return f"LIBERADO — {d.detalhes or 'catraca liberada'}"
        motivo = str(d.motivo) if d.motivo else "negado"
        extra = f" ({d.detalhes})" if d.detalhes else ""
        return f"NEGADO — {motivo}{extra}"
