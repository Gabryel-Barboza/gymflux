"""Regras de negócio de liberação de catraca — RB01..RB05."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from gymflux.core.acesso import DecisaoAcesso, DirecaoAcesso, MotivoNegado
from gymflux.core.aluno import Aluno, StatusAluno
from gymflux.core.pagamento import Pagamento, esta_adimplente
from gymflux.core.plano import Matricula


@dataclass(frozen=True, slots=True)
class RegraAcessoConfig:
    """Parâmetros configuráveis das regras (via Settings)."""

    tolerancia_dias: int = 3
    timeout_giro_s: int = 7
    anti_passback: bool = False


class RegraAcesso:
    """Avalia se aluno pode passar pela catraca.

    Ordem de precedência (RB03 > RB02 > RB01 > RB05):
    1. RB03 bloqueio manual (sobrepõe tudo)
    2. RB02 vigência / matrícula
    3. RB01 adimplência (tolerância)
    4. RB05 anti-passback (opcional)
    5. RB04 timeout é tratado em `acesso_expirou`
    """

    def __init__(self, config: RegraAcessoConfig | None = None) -> None:
        self.config = config or RegraAcessoConfig()

    # -- RB04 timeout (puro, sem I/O) ---------------------------------

    def acesso_expirou(self, liberado_em: datetime, agora: datetime) -> bool:
        """RB04: acesso liberado expira se não houver giro dentro do timeout."""
        if agora < liberado_em:
            return False
        delta = (agora - liberado_em).total_seconds()
        return delta > self.config.timeout_giro_s

    def tempo_restante_giro(self, liberado_em: datetime, agora: datetime) -> float:
        delta = (agora - liberado_em).total_seconds()
        return max(0.0, self.config.timeout_giro_s - delta)

    # -- Avaliação principal ------------------------------------------

    def avaliar(
        self,
        *,
        aluno: Aluno | None,
        matricula: Matricula | None,
        pagamentos: list[Pagamento],
        agora: date,
        direcao: DirecaoAcesso = DirecaoAcesso.ENTRADA,
        ultimo_acesso_direcao: DirecaoAcesso | None = None,
        tolerancia_dias: int | None = None,
    ) -> DecisaoAcesso:
        _ = direcao  # reservado para RB05 futuro (direção distinta)

        tol = tolerancia_dias if tolerancia_dias is not None else self.config.tolerancia_dias

        # aluno existe?
        if aluno is None:
            return DecisaoAcesso.negado(MotivoNegado.ALUNO_NAO_ENCONTRADO, "Aluno não encontrado")

        # RB03 — bloqueio manual sobrepõe tudo
        if aluno.esta_bloqueado:
            return DecisaoAcesso.negado(MotivoNegado.BLOQUEIO_MANUAL, "Aluno bloqueado manualmente")

        # status inativo também nega (não é bloqueio manual, mas inatividade)
        if aluno.status == StatusAluno.INATIVO:
            return DecisaoAcesso.negado(MotivoNegado.INATIVO, "Aluno inativo")

        # RB02 — matrícula / vigência
        if matricula is None:
            return DecisaoAcesso.negado(MotivoNegado.SEM_MATRICULA, "Sem matrícula vinculada")
        if not matricula.ativa:
            return DecisaoAcesso.negado(
                MotivoNegado.MATRICULA_INATIVA, "Matrícula inativa/cancelada"
            )
        if matricula.expirada_em(agora):
            return DecisaoAcesso.negado(
                MotivoNegado.MATRICULA_EXPIRADA,
                f"Matrícula expirada em {matricula.vigencia.fim.isoformat()}",
            )
        if not matricula.vigente_em(agora):
            # antes do inicio ou outro caso de não vigência
            return DecisaoAcesso.negado(
                MotivoNegado.MATRICULA_EXPIRADA,
                f"Fora da vigência {matricula.vigencia.inicio}..{matricula.vigencia.fim}",
            )

        # RB01 — adimplência / tolerância
        # tolerância do plano pode sobrescrever config; respeita param
        # explicito > config; compara vencimento mais recente
        if not esta_adimplente(pagamentos, hoje=agora, tolerancia_dias=tol):
            # calcula dias atraso para mensagem mais útil
            from gymflux.core.pagamento import dias_em_atraso

            dias = dias_em_atraso(pagamentos, hoje=agora)
            return DecisaoAcesso.negado(
                MotivoNegado.INADIMPLENTE,
                f"Inadimplente há {dias}d (tolerância {tol}d)",
            )

        # RB05 — anti-passback: não permitir ENTRADA duas vezes sem SAIDA
        if (
            self.config.anti_passback
            and ultimo_acesso_direcao is not None
            and ultimo_acesso_direcao == direcao
        ):
            return DecisaoAcesso.negado(
                MotivoNegado.ANTI_PASSBACK,
                f"Anti-passback: último acesso também foi {direcao.value}",
            )

        return DecisaoAcesso.liberado_ok("Acesso liberado")

    # sobrecarga compat: pode_acessar -> bool (usado em docs/ARCHITECTURE)
    def pode_acessar(
        self,
        aluno: Aluno | None,
        matricula: Matricula | None,
        pagamentos: list[Pagamento],
        agora: date,
    ) -> tuple[bool, str | None]:
        decisao = self.avaliar(aluno=aluno, matricula=matricula, pagamentos=pagamentos, agora=agora)
        motivo = (
            decisao.motivo.value if isinstance(decisao.motivo, MotivoNegado) else decisao.motivo
        )
        return decisao.liberado, motivo

    # timeout helper para registrar TIMEOUT após liberação sem giro
    def decisao_timeout_se_expirado(
        self,
        liberado_em: datetime,
        agora: datetime,
    ) -> DecisaoAcesso | None:
        if self.acesso_expirou(liberado_em, agora):
            delta = (agora - liberado_em).total_seconds()
            return DecisaoAcesso.timeout(
                f"Timeout giro após {delta:.1f}s (limite {self.config.timeout_giro_s}s)"
            )
        return None
