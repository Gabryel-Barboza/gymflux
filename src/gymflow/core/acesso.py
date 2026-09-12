"""Acesso — Tentativa, Resultado e Decisão."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class DirecaoAcesso(StrEnum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"


class ResultadoAcesso(StrEnum):
    LIBERADO = "LIBERADO"
    NEGADO = "NEGADO"
    TIMEOUT = "TIMEOUT"
    ERRO = "ERRO"


class MotivoNegado(StrEnum):
    BLOQUEIO_MANUAL = "BLOQUEIO_MANUAL"
    INATIVO = "INATIVO"
    MATRICULA_EXPIRADA = "MATRICULA_EXPIRADA"
    MATRICULA_INATIVA = "MATRICULA_INATIVA"
    INADIMPLENTE = "INADIMPLENTE"
    SEM_MATRICULA = "SEM_MATRICULA"
    ANTI_PASSBACK = "ANTI_PASSBACK"
    TIMEOUT_GIRO = "TIMEOUT_GIRO"
    ALUNO_NAO_ENCONTRADO = "ALUNO_NAO_ENCONTRADO"
    ERRO_HARDWARE = "ERRO_HARDWARE"


@dataclass(frozen=True, slots=True)
class DecisaoAcesso:
    liberado: bool
    resultado: ResultadoAcesso
    motivo: MotivoNegado | str | None = None
    detalhes: str | None = None

    @classmethod
    def liberado_ok(cls, detalhes: str | None = None) -> DecisaoAcesso:
        return cls(
            liberado=True, resultado=ResultadoAcesso.LIBERADO, motivo=None, detalhes=detalhes
        )

    @classmethod
    def negado(cls, motivo: MotivoNegado | str, detalhes: str | None = None) -> DecisaoAcesso:
        return cls(
            liberado=False, resultado=ResultadoAcesso.NEGADO, motivo=motivo, detalhes=detalhes
        )

    @classmethod
    def timeout(cls, detalhes: str | None = None) -> DecisaoAcesso:
        return cls(
            liberado=False,
            resultado=ResultadoAcesso.TIMEOUT,
            motivo=MotivoNegado.TIMEOUT_GIRO,
            detalhes=detalhes,
        )


@dataclass(frozen=True, slots=True)
class TentativaAcesso:
    aluno_id: str | None
    direcao: DirecaoAcesso
    timestamp: datetime
    resultado: ResultadoAcesso
    motivo: MotivoNegado | str | None = None
    detalhes: str | None = None
    catraca_id: str | None = None
    timeout_giro_s: int | None = None
    funcionario_id: str | None = None


@dataclass(slots=True)
class RegistroAcesso:
    """Log em memória de tentativas (fase 1). Futuro: persistido em SQLite."""

    tentativas: list[TentativaAcesso] = field(default_factory=list)

    def registrar(self, tentativa: TentativaAcesso) -> None:
        self.tentativas.append(tentativa)

    def por_aluno(self, aluno_id: str) -> list[TentativaAcesso]:
        return [t for t in self.tentativas if t.aluno_id == aluno_id]

    def total(self) -> int:
        return len(self.tentativas)

    def limpar(self) -> None:
        self.tentativas.clear()


# Compat helpers para converter com hardware/henry7x.interface.Direcao


def direcao_para_hardware(direcao: DirecaoAcesso) -> int:
    """Mapeia DirecaoAcesso -> valor int compatível com Direcao hardware (1/2)."""
    return 1 if direcao == DirecaoAcesso.ENTRADA else 2
