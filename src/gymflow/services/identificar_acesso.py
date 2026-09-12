"""IdentificarAcessoService — autenticação estilo SCA (senha numérica/cartão).

Fluxo: teclado/cartão da catraca → ``Identificacao`` → lookup do aluno →
``LiberarAcessoService`` (RB01-RB05 intactas, sem duplicar regra) →
``(DecisaoAcesso, Aluno | None)``.

TODO (commissioning Windows/VM — NÃO implementar aqui): o ``RealHenry7x``
alimentará ``Identificacao`` a partir do ``SRegistro`` coletado via
``ColetaEventos``/``QuantRegsColetados``, com resposta online via
``RespostaOn(SResposta)`` — ver ``docs/DLL_CONTRACT.md`` §3.4 (eventos) e
tabela §3 (``RespostaOn``). Parse real do ``SRegistro`` pendente de VM.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Protocol

from loguru import logger

from gymflow.core.acesso import DecisaoAcesso, DirecaoAcesso
from gymflow.core.aluno import Aluno, validar_senha_numerica
from gymflow.services.liberar_acesso import LiberarAcessoService


class OrigemIdentificacao(StrEnum):
    TECLADO = "TECLADO"
    CARTAO = "CARTAO"


@dataclass(frozen=True, slots=True)
class Identificacao:
    """Código capturado na catraca + origem. Senha validada (4-8 dígitos)."""

    codigo: str
    origem: OrigemIdentificacao

    @classmethod
    def por_teclado(cls, senha: str) -> Identificacao:
        return cls(codigo=validar_senha_numerica(senha), origem=OrigemIdentificacao.TECLADO)

    @classmethod
    def por_cartao(cls, cartao_id: str) -> Identificacao:
        cid = cartao_id.strip()
        if not cid:
            raise ValueError("cartao_id não pode ser vazio")
        return cls(codigo=cid, origem=OrigemIdentificacao.CARTAO)


class _AlunoLookupProto(Protocol):
    def buscar_por_id(self, aluno_id: str) -> Aluno | None: ...
    def buscar_por_cartao(self, cartao_id: str) -> Aluno | None: ...
    def listar(self) -> list[Aluno]: ...


@dataclass(slots=True)
class IdentificarAcessoService:
    """Localiza aluno por credencial e delega decisão a ``LiberarAcessoService``.

    Sem commit próprio (padrão Fase 4.1): quem chama commita (ex: ViewModel).
    Desconhecido => delega com ``aluno=None`` (regra responde ALUNO_NAO_ENCONTRADO).
    """

    acesso: LiberarAcessoService
    aluno_repo: _AlunoLookupProto

    def identificar(
        self,
        identificacao: Identificacao,
        direcao: DirecaoAcesso = DirecaoAcesso.ENTRADA,
        agora: date | None = None,
        timestamp: datetime | None = None,
    ) -> tuple[DecisaoAcesso, Aluno | None]:
        aluno = self._localizar(identificacao)
        if aluno is None:
            decisao = self.acesso.tentar_acesso(
                aluno=None,
                matricula=None,
                pagamentos=[],
                direcao=direcao,
                agora=agora,
                timestamp=timestamp,
            )
        else:
            decisao = self.acesso.tentar_acesso_por_id(
                aluno.id, direcao, agora=agora, timestamp=timestamp
            )
        logger.info(
            f"[Identificar] origem={identificacao.origem.value} "
            f"aluno={aluno.id if aluno else '?'} liberado={decisao.liberado}"
        )
        return decisao, aluno

    def _localizar(self, identificacao: Identificacao) -> Aluno | None:
        if identificacao.origem == OrigemIdentificacao.CARTAO:
            try:
                return self.aluno_repo.buscar_por_cartao(identificacao.codigo)
            except Exception as e:
                logger.warning(f"[Identificar] buscar_por_cartao falhou: {e}")
                return None
        # TECLADO: hashes com salt exigem verificação por candidato (ok p/ <5k alunos).
        try:
            candidatos = self.aluno_repo.listar()
        except Exception as e:
            logger.warning(f"[Identificar] listar falhou: {e}")
            return None
        for aluno in candidatos:
            try:
                if aluno.verificar_senha(identificacao.codigo):
                    return aluno
            except Exception:
                continue
        return None
