"""IdentificarAcessoService — autenticação estilo SCA (senha numérica/cartão).

Fluxo: teclado/cartão da catraca → ``Identificacao`` → funcionário (bypass,
senha) → lookup do aluno → ``LiberarAcessoService`` (RB01-RB05 intactas,
sem duplicar regra) → ``(DecisaoAcesso, Aluno | None)``.

Funcionário ativo libera direto (sem RB01/RB02); inativo nega (bloqueio
manual). O pulso vai direto ao driver e a tentativa é persistida com
``funcionario_id`` (``aluno_id`` fica NULL).

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

from gymflow.core.acesso import DecisaoAcesso, DirecaoAcesso, MotivoNegado, TentativaAcesso
from gymflow.core.acesso import ResultadoAcesso as ResultadoDominio
from gymflow.core.aluno import Aluno, validar_senha_numerica
from gymflow.core.funcionario import Funcionario
from gymflow.hardware.henry7x.interface import Direcao as DirecaoHW
from gymflow.hardware.henry7x.interface import ResultadoCatraca
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


class _FuncionarioLookupProto(Protocol):
    def listar(self) -> list[Funcionario]: ...


@dataclass(slots=True)
class IdentificarAcessoService:
    """Localiza aluno por credencial e delega decisão a ``LiberarAcessoService``.

    Sem commit próprio (padrão Fase 4.1): quem chama commita (ex: ViewModel).
    Desconhecido => delega com ``aluno=None`` (regra responde ALUNO_NAO_ENCONTRADO).
    """

    acesso: LiberarAcessoService
    aluno_repo: _AlunoLookupProto
    funcionario_repo: _FuncionarioLookupProto | None = None

    def identificar(
        self,
        identificacao: Identificacao,
        direcao: DirecaoAcesso = DirecaoAcesso.ENTRADA,
        agora: date | None = None,
        timestamp: datetime | None = None,
    ) -> tuple[DecisaoAcesso, Aluno | None]:
        funcionario = self._localizar_funcionario(identificacao)
        if funcionario is not None:
            decisao = self._liberar_funcionario(funcionario, direcao, timestamp=timestamp)
            logger.info(f"[Identificar] funcionario={funcionario.id} liberado={decisao.liberado}")
            return decisao, None
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

    def _localizar_funcionario(self, identificacao: Identificacao) -> Funcionario | None:
        """Funcionário autentica só por senha (teclado), antes do aluno."""
        if self.funcionario_repo is None or identificacao.origem != OrigemIdentificacao.TECLADO:
            return None
        try:
            candidatos = self.funcionario_repo.listar()
        except Exception as e:
            logger.warning(f"[Identificar] listar funcionarios falhou: {e}")
            return None
        for func in candidatos:
            try:
                if func.verificar_senha(identificacao.codigo):
                    return func
            except Exception:
                continue
        return None

    def _liberar_funcionario(
        self,
        func: Funcionario,
        direcao: DirecaoAcesso,
        timestamp: datetime | None = None,
    ) -> DecisaoAcesso:
        """Bypass RB01/RB02 (entrada indefinida); inativo nega (bloqueio manual).

        Pulso direto no driver + tentativa persistida com ``funcionario_id``
        (``aluno_id`` NULL) p/ auditoria antifraude.
        """
        ts: datetime = timestamp or datetime.now()
        if not func.ativo:
            decisao = DecisaoAcesso.negado(
                MotivoNegado.BLOQUEIO_MANUAL, f"Funcionário {func.nome} inativo"
            )
            self._persistir_funcionario(func, direcao, ts, decisao)
            return decisao
        hw_dir = DirecaoHW.ENTRADA if direcao == DirecaoAcesso.ENTRADA else DirecaoHW.SAIDA
        try:
            resultado_hw = self.acesso.driver.liberar(hw_dir)
        except Exception as e:
            logger.exception(f"[Identificar] erro hardware liberar funcionario: {e}")
            decisao = DecisaoAcesso(
                liberado=False,
                resultado=ResultadoDominio.ERRO,
                motivo=MotivoNegado.ERRO_HARDWARE,
                detalhes=str(e),
            )
            self._persistir_funcionario(func, direcao, ts, decisao)
            return decisao
        if resultado_hw == ResultadoCatraca.LIBERADO:
            decisao = DecisaoAcesso.liberado_ok(f"Funcionário — {func.nome}")
            self._persistir_funcionario(func, direcao, ts, decisao)
            return decisao
        motivo_hw = MotivoNegado.ERRO_HARDWARE
        if resultado_hw == ResultadoCatraca.BLOQUEADO:
            motivo_hw = MotivoNegado.BLOQUEIO_MANUAL
        elif resultado_hw == ResultadoCatraca.TIMEOUT:
            motivo_hw = MotivoNegado.TIMEOUT_GIRO
        decisao = DecisaoAcesso(
            liberado=False,
            resultado=ResultadoDominio.NEGADO
            if resultado_hw == ResultadoCatraca.BLOQUEADO
            else ResultadoDominio.ERRO,
            motivo=motivo_hw,
            detalhes=f"Hardware retornou {resultado_hw.value}",
        )
        self._persistir_funcionario(func, direcao, ts, decisao)
        return decisao

    def _persistir_funcionario(
        self,
        func: Funcionario,
        direcao: DirecaoAcesso,
        ts: datetime,
        decisao: DecisaoAcesso,
    ) -> None:
        """Log antifraude do bypass (memória + repo, como LiberarAcessoService)."""
        tentativa = TentativaAcesso(
            aluno_id=None,
            direcao=direcao,
            timestamp=ts,
            resultado=decisao.resultado,
            motivo=decisao.motivo,
            detalhes=decisao.detalhes,
            catraca_id=self.acesso.catraca_id,
            funcionario_id=func.id,
        )
        self.acesso.registro.registrar(tentativa)
        if self.acesso.acesso_repo is not None:
            try:
                self.acesso.acesso_repo.registrar(tentativa)
            except Exception as e:
                logger.warning(f"[Identificar] acesso_repo.registrar falhou: {e}")

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
