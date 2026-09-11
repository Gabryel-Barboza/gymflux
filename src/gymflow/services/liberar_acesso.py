"""LiberarAcessoService — orquestra RegraAcesso + Henry7xDriver + log memória.

NUNCA importa ctypes/pywin32/PySide6/sqlalchemy. Todo I/O via interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from loguru import logger

from gymflow.core.acesso import DecisaoAcesso, DirecaoAcesso, MotivoNegado, TentativaAcesso
from gymflow.core.acesso import ResultadoAcesso as ResultadoDominio
from gymflow.core.aluno import Aluno
from gymflow.core.pagamento import Pagamento
from gymflow.core.plano import Matricula
from gymflow.core.regras import RegraAcesso, RegraAcessoConfig
from gymflow.hardware.henry7x.interface import Direcao, Henry7xDriver, ResultadoCatraca


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


@dataclass(slots=True)
class LiberarAcessoService:
    """Caso de uso principal — decide e aciona catraca.

    - `tentar_acesso` avalia regra; se liberado, chama `driver.liberar`.
    - `verificar_timeout` deve ser chamado após liberação se giro não ocorrer (RB04).
    """

    driver: Henry7xDriver
    regra: RegraAcesso = field(default_factory=RegraAcesso)
    registro: RegistroMemoria = field(default_factory=RegistroMemoria)
    catraca_id: str = "catraca-1"

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
            # log negado sem acionar hardware
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
            self.registro.registrar(tentativa)
            logger.info(f"[LiberarAcesso] NEGADO aluno={aluno_id} motivo={decisao.motivo}")
            return decisao

        # liberado pela regra -> tentar hardware
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
            self.registro.registrar(tentativa)
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
            self.registro.registrar(tentativa)
            logger.info(
                f"[LiberarAcesso] LIBERADO aluno={aluno_id} dir={direcao.value} hw={resultado_hw}"
            )
            return DecisaoAcesso.liberado_ok("Catraca liberada")

        # hardware bloqueou/timeout/erro
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
        self.registro.registrar(tentativa)
        return DecisaoAcesso(
            liberado=False,
            resultado=tentativa.resultado,
            motivo=motivo_hw,
            detalhes=tentativa.detalhes,
        )

    def verificar_timeout(
        self,
        liberado_em: datetime,
        agora: datetime,
        aluno_id: str,
        direcao: DirecaoAcesso = DirecaoAcesso.ENTRADA,
    ) -> DecisaoAcesso | None:
        """RB04: se expirou timeout sem giro, bloqueia catraca e loga TIMEOUT.

        Retorna DecisaoAcesso TIMEOUT se expirou, None caso contrário.
        """
        decisao = self.regra.decisao_timeout_se_expirado(liberado_em, agora)
        if decisao is None:
            return None
        # aciona bloqueio físico
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
        self.registro.registrar(tentativa)
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
