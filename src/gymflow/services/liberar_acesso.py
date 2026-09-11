"""LiberarAcessoService — orquestra RegraAcesso + Henry7xDriver + log.

NUNCA importa ctypes/pywin32/PySide6/sqlalchemy direto.
Fase 2: suporta injeção opcional de repos para consulta por aluno_id.
Se repos None, mantém compatibilidade Fase 1 (caller fornece domínio).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Protocol

from loguru import logger

from gymflow.core.acesso import DecisaoAcesso, DirecaoAcesso, MotivoNegado, TentativaAcesso
from gymflow.core.acesso import ResultadoAcesso as ResultadoDominio
from gymflow.core.aluno import Aluno
from gymflow.core.pagamento import Pagamento
from gymflow.core.plano import Matricula
from gymflow.core.regras import RegraAcesso, RegraAcessoConfig
from gymflow.hardware.henry7x.interface import Direcao, Henry7xDriver, ResultadoCatraca

if TYPE_CHECKING:
    pass


def _direcao_core_para_hw(d: DirecaoAcesso) -> Direcao:
    return Direcao.ENTRADA if d == DirecaoAcesso.ENTRADA else Direcao.SAIDA


@dataclass(slots=True)
class RegistroMemoria:
    tentativas: list[TentativaAcesso] = field(default_factory=list)

    def registrar(self, t: TentativaAcesso) -> None:
        self.tentativas.append(t)

    def por_aluno(self, aluno_id: str) -> list[TentativaAcesso]:
        return [x for x in self.tentativas if x.aluno_id == aluno_id]

    def total(self) -> int:
        return len(self.tentativas)

    def limpar(self) -> None:
        self.tentativas.clear()


class _AlunoRepoProto(Protocol):
    def buscar_por_id(self, aluno_id: str) -> Aluno | None: ...
    def buscar_por_cpf(self, cpf: str) -> Aluno | None: ...


class _MatriculaRepoProto(Protocol):
    def buscar_vigente(self, aluno_id: str, data: date) -> Matricula | None: ...
    def listar_por_aluno(self, aluno_id: str) -> list[Matricula]: ...


class _PagamentoRepoProto(Protocol):
    def listar_por_aluno(self, aluno_id: str) -> list[Pagamento]: ...


class _AcessoRepoProto(Protocol):
    def registrar(self, tentativa: TentativaAcesso) -> Any: ...
    def listar_por_aluno(self, aluno_id: str) -> list[TentativaAcesso]: ...


@dataclass(slots=True)
class LiberarAcessoService:
    """Caso de uso principal — decide e aciona catraca.

    - `tentar_acesso` avalia regra; se liberado, chama `driver.liberar`.
    - `tentar_acesso_por_id` busca dados via repos injetados (opcional Fase 2).
    - `verificar_timeout` deve ser chamado após liberação se giro não ocorrer (RB04).
    """

    driver: Henry7xDriver
    regra: RegraAcesso = field(default_factory=RegraAcesso)
    registro: RegistroMemoria = field(default_factory=RegistroMemoria)
    catraca_id: str = "catraca-1"
    # Fase 2 — repos opcionais (injeção). Se None, mantém modo memória Fase 1.
    aluno_repo: _AlunoRepoProto | None = None
    matricula_repo: _MatriculaRepoProto | None = None
    pagamento_repo: _PagamentoRepoProto | None = None
    acesso_repo: _AcessoRepoProto | None = None

    def _persistir_tentativa(self, tentativa: TentativaAcesso) -> None:
        self.registro.registrar(tentativa)
        if self.acesso_repo is not None:
            try:
                self.acesso_repo.registrar(tentativa)
            except Exception as e:
                logger.warning(f"[LiberarAcesso] acesso_repo.registrar falhou: {e}")

    def _ultimo_acesso_direcao(self, aluno_id: str) -> DirecaoAcesso | None:
        # tenta via acesso_repo primeiro (persistido), fallback registro memória
        if self.acesso_repo is not None:
            try:
                # tenta método buscar_ultimo se existir
                if hasattr(self.acesso_repo, "buscar_ultimo_por_aluno"):
                    ultimo = self.acesso_repo.buscar_ultimo_por_aluno(aluno_id)  # type: ignore[attr-defined]
                    if ultimo:
                        return ultimo.direcao  # type: ignore[no-any-return]
                logs = self.acesso_repo.listar_por_aluno(aluno_id)
                if logs:
                    return logs[-1].direcao
            except Exception as e:
                logger.warning(f"[LiberarAcesso] falha ao buscar ultimo acesso: {e}")
        logs_mem = self.registro.por_aluno(aluno_id)
        if logs_mem:
            return logs_mem[-1].direcao
        return None

    def tentar_acesso(
        self,
        *,
        aluno: Aluno | None,
        matricula: Matricula | None,
        pagamentos: list[Pagamento],
        direcao: DirecaoAcesso = DirecaoAcesso.ENTRADA,
        agora: date | None = None,
        timestamp: datetime | None = None,
        ultimo_acesso_direcao: DirecaoAcesso | None = None,
    ) -> DecisaoAcesso:
        hoje: date = agora or date.today()
        ts: datetime = timestamp or datetime.now()

        tolerancia = matricula.plano.tolerancia_dias if matricula is not None else None

        # anti-passback: se não fornecido explicitamente e config habilitada, busca último
        if ultimo_acesso_direcao is None and self.regra.config.anti_passback and aluno is not None:
            ultimo_acesso_direcao = self._ultimo_acesso_direcao(aluno.id)

        decisao = self.regra.avaliar(
            aluno=aluno,
            matricula=matricula,
            pagamentos=pagamentos,
            agora=hoje,
            direcao=direcao,
            ultimo_acesso_direcao=ultimo_acesso_direcao,
            tolerancia_dias=tolerancia,
        )

        aluno_id = aluno.id if aluno else "desconhecido"

        if not decisao.liberado:
            tentativa = TentativaAcesso(
                aluno_id=aluno_id,
                direcao=direcao,
                timestamp=ts,
                resultado=ResultadoDominio.NEGADO,
                motivo=decisao.motivo,
                detalhes=decisao.detalhes,
                catraca_id=self.catraca_id,
                timeout_giro_s=self.regra.config.timeout_giro_s,
            )
            self._persistir_tentativa(tentativa)
            logger.info(f"[LiberarAcesso] NEGADO aluno={aluno_id} motivo={decisao.motivo}")
            return decisao

        hw_dir = _direcao_core_para_hw(direcao)
        try:
            resultado_hw = self.driver.liberar(hw_dir)
        except Exception as e:
            logger.exception(f"[LiberarAcesso] erro hardware liberar: {e}")
            tentativa = TentativaAcesso(
                aluno_id=aluno_id,
                direcao=direcao,
                timestamp=ts,
                resultado=ResultadoDominio.ERRO,
                motivo=MotivoNegado.ERRO_HARDWARE,
                detalhes=str(e),
                catraca_id=self.catraca_id,
            )
            self._persistir_tentativa(tentativa)
            return DecisaoAcesso(
                liberado=False,
                resultado=ResultadoDominio.ERRO,
                motivo=MotivoNegado.ERRO_HARDWARE,
                detalhes=str(e),
            )

        if resultado_hw == ResultadoCatraca.LIBERADO:
            tentativa = TentativaAcesso(
                aluno_id=aluno_id,
                direcao=direcao,
                timestamp=ts,
                resultado=ResultadoDominio.LIBERADO,
                motivo=None,
                detalhes="Catraca liberada",
                catraca_id=self.catraca_id,
                timeout_giro_s=self.regra.config.timeout_giro_s,
            )
            self._persistir_tentativa(tentativa)
            logger.info(
                f"[LiberarAcesso] LIBERADO aluno={aluno_id} dir={direcao.value} hw={resultado_hw}"
            )
            return DecisaoAcesso.liberado_ok("Catraca liberada")

        motivo_hw = MotivoNegado.ERRO_HARDWARE
        if resultado_hw == ResultadoCatraca.BLOQUEADO:
            motivo_hw = MotivoNegado.BLOQUEIO_MANUAL
        elif resultado_hw == ResultadoCatraca.TIMEOUT:
            motivo_hw = MotivoNegado.TIMEOUT_GIRO
        tentativa = TentativaAcesso(
            aluno_id=aluno_id,
            direcao=direcao,
            timestamp=ts,
            resultado=ResultadoDominio.NEGADO
            if resultado_hw == ResultadoCatraca.BLOQUEADO
            else ResultadoDominio.ERRO,
            motivo=motivo_hw,
            detalhes=f"Hardware retornou {resultado_hw.value}",
            catraca_id=self.catraca_id,
        )
        self._persistir_tentativa(tentativa)
        return DecisaoAcesso(
            liberado=False,
            resultado=tentativa.resultado,
            motivo=motivo_hw,
            detalhes=tentativa.detalhes,
        )

    def tentar_acesso_por_id(
        self,
        aluno_id: str,
        direcao: DirecaoAcesso = DirecaoAcesso.ENTRADA,
        agora: date | None = None,
        timestamp: datetime | None = None,
    ) -> DecisaoAcesso:
        """Fase 2: busca aluno/matricula/pagamentos via repos injetados."""
        if self.aluno_repo is None:
            raise RuntimeError("aluno_repo não injetado — use tentar_acesso com objetos de domínio")
        hoje: date = agora or date.today()
        aluno = self.aluno_repo.buscar_por_id(aluno_id)
        matricula: Matricula | None = None
        if self.matricula_repo is not None:
            try:
                matricula = self.matricula_repo.buscar_vigente(aluno_id, hoje)
            except Exception:
                # fallback para listar e filtrar
                lst = self.matricula_repo.listar_por_aluno(aluno_id)
                for m in lst:
                    if m.vigente_em(hoje):
                        matricula = m
                        break
        pagamentos: list[Pagamento] = []
        if self.pagamento_repo is not None:
            pagamentos = self.pagamento_repo.listar_por_aluno(aluno_id)
        # delega ao método principal
        return self.tentar_acesso(
            aluno=aluno,
            matricula=matricula,
            pagamentos=pagamentos,
            direcao=direcao,
            agora=hoje,
            timestamp=timestamp,
        )

    def verificar_timeout(
        self,
        liberado_em: datetime,
        agora: datetime,
        aluno_id: str,
        direcao: DirecaoAcesso = DirecaoAcesso.ENTRADA,
    ) -> DecisaoAcesso | None:
        """RB04: se expirou timeout sem giro, bloqueia catraca e loga TIMEOUT."""
        decisao = self.regra.decisao_timeout_se_expirado(liberado_em, agora)
        if decisao is None:
            return None
        try:
            self.driver.bloquear()
        except Exception as e:
            logger.warning(f"[LiberarAcesso] bloquear() falhou no timeout: {e}")

        tentativa = TentativaAcesso(
            aluno_id=aluno_id,
            direcao=direcao,
            timestamp=agora,
            resultado=ResultadoDominio.TIMEOUT,
            motivo=MotivoNegado.TIMEOUT_GIRO,
            detalhes=decisao.detalhes,
            catraca_id=self.catraca_id,
            timeout_giro_s=self.regra.config.timeout_giro_s,
        )
        self._persistir_tentativa(tentativa)
        logger.info(f"[LiberarAcesso] TIMEOUT aluno={aluno_id} {decisao.detalhes}")
        return decisao

    @classmethod
    def com_mock(
        cls,
        config: RegraAcessoConfig | None = None,
        auto_giro: bool = True,
        giro_delay_s: float = 1.0,
    ) -> LiberarAcessoService:
        from gymflow.hardware.henry7x.mock import MockHenry7x

        driver = MockHenry7x(auto_giro=auto_giro, giro_delay_s=giro_delay_s)
        driver.conectar("MOCK:1")
        regra = RegraAcesso(config or RegraAcessoConfig())
        return cls(driver=driver, regra=regra)
