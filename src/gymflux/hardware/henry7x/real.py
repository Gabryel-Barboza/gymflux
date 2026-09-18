"""Driver real Henry 7x — COM 32-bit `Kernel7x.Kernel` via pywin32.

Validado em Windows 10 64-bit (WOW64) com DLL 7.2.0.52: o ProgID registrado
é ``Kernel7x.Kernel`` (``Henry.Kernel7x`` NÃO existe no registro — ver
``docs/DLL_CONTRACT.md §3``). ``Kernel7x.Hamster``/``Kernel7x.Alternativo``
apontam para a mesma DLL e servem de fallback.

Só funciona em Windows + Python 32-bit + ``kernel7x.dll`` registrada
(``regsvr32``). Em qualquer outro ambiente o construtor levanta
``RuntimeError`` (falha graciosa); use ``get_henry_driver()`` que cai para o
mock automaticamente.

Contrato COM documentado em ``docs/DLL_CONTRACT.md §3`` (Fase 3, serial):

- conectar: ``AdicionaCard(SComConfig, card)`` (principal) com fallback
  ``AdicionaCardSerial(porta, catraca, modo)``; portas via ``ListaPortasSeriais``.
- desconectar: ``PararColetaEventos(card)`` + ``RemoveCard(card)``.
- liberar: ``EnviaTipoCatraca(csgLibEntrada/csgLibSaida)`` + pulso
  ``EnviaAcionaCtrl`` (relé 1=entrada, 2=saída — convenção configurável).
- bloquear: ``EnviaTipoCatraca(csgBloqueada)``.
- on_giro: polling ``ColetaEventos`` + ``QuantRegsColetados`` em thread daemon.
- status: ``ListaPortasSeriais`` / ``Versao`` / ``ThreadLastError`` / online.

Limitações honestas da Fase 3 (ver DLL_CONTRACT §3.4): a direção entregue aos
callbacks é a última comandada (igual ao mock); a direção lida do ``SRegistro``
e o fluxo online ``OnRegistro``/``RespostaOn`` ficam para a Fase 5.
"""

from __future__ import annotations

import contextlib
import struct
import sys
import threading
import time
from pathlib import Path
from typing import Any

from loguru import logger

from gymflux.hardware.henry7x.interface import (
    Direcao,
    GiroCallback,
    Henry7xDriver,
    ResultadoCatraca,
)

PROG_ID = "Kernel7x.Kernel"
# Ordem de tentativa: instalações antigas/docs legados podem ter outros ProgIDs.
PROG_IDS_CANDIDATOS = (
    "Kernel7x.Kernel",
    "Kernel7x.Hamster",
    "Kernel7x.Alternativo",
    "Henry.Kernel7x",
)
CARD_PADRAO = 1
PLACA_PADRAO = 1
POLL_INTERVAL_S = 0.5
TEMPO_RELE_S = 3.0

# Estrutura real 7.2.0.52 (via comtypes, TypeLib {25DC738C-...}):
# SComConfig = {Tcp(SComTcpip), Serial(SComSerial), ModoComunicacao(enum),
#               Modem(SComModem), TipoComunicacao(enum), GPRS(SComGPRS),
#               IsCatraca(VARIANT_BOOL)}
# SComSerial = {NumeroRelogio(c_ubyte), Porta(BSTR), Velocidade(enum c_int)}
# SAcionaCtrl = {TempoRele1/2/3(c_ubyte)} — sem AcionaRele booleano (legado).
# Campos candidatos (nomes exatos variam no TYPELIB Delphi; tenta em ordem;
# ver docs/DLL_CONTRACT.md §3.2 + scripts/dump_henry_typelib.py).
_SCOM_TIPO_FIELDS = ("TipoComunicacao", "Tipo", "pTipoComunicacao")
_SCOM_PORTA_FIELDS = ("Porta", "ComPort", "PortaSerial", "Port", "pPorta")
_SCOM_VEL_FIELDS = ("Velocidade", "BaudRate", "pVelocidade")
_SAC_RELE_FIELDS = ("AcionaRele1", "pAcionaRele1", "Rele1")  # legado, ausente em 7.2
_SAC_RELE2_FIELDS = ("AcionaRele2", "pAcionaRele2", "Rele2")  # legado, ausente em 7.2
_SAC_TEMPO_FIELDS = ("TempoRele1", "pTempoRele1", "Tempo1")
_SAC_TEMPO2_FIELDS = ("TempoRele2", "pTempoRele2", "Tempo2")

_MODO_POR_DIRECAO = {Direcao.ENTRADA: "csgLibEntrada", Direcao.SAIDA: "csgLibSaida"}


def _normalizar_porta(porta: str | int) -> str:
    """Normaliza porta serial: 3 -> 'COM3', 'com3' -> 'COM3'."""
    if isinstance(porta, int):
        return f"COM{porta}"
    texto = str(porta).strip().upper()
    if texto.isdigit():
        return f"COM{texto}"
    if texto.startswith("COM") and texto[3:].isdigit():
        return texto
    raise ValueError(f"porta serial inválida: {porta!r} (use 'COM3' ou 3)")


class RealHenry7x(Henry7xDriver):
    is_mock = False

    def __init__(
        self,
        dll_path: str | Path = "vendor/Henry/Henry7x/Kernel7x.dll",
        card_id: int = CARD_PADRAO,
        placa: int = PLACA_PADRAO,
        poll_interval_s: float = POLL_INTERVAL_S,
        rele_entrada: int = 1,
        rele_saida: int = 2,
        tempo_rele_s: float = TEMPO_RELE_S,
    ) -> None:
        if sys.platform != "win32":
            raise RuntimeError("RealHenry7x disponível apenas em Windows 32-bit")
        if struct.calcsize("P") * 8 != 32:
            raise RuntimeError(
                "RealHenry7x requer Python 32-bit (WOW64) em Windows para COM Kernel7x.Kernel"
            )

        self.dll_path: Path = Path(dll_path)
        self._card_id: int = card_id
        self._placa: int = placa
        self._poll_interval_s: float = poll_interval_s
        self._rele_entrada: int = rele_entrada
        self._rele_saida: int = rele_saida
        self._tempo_rele_s: float = tempo_rele_s
        self._com: Any = None
        self._prog_id_usado: str = PROG_ID
        try:
            import win32com.client  # type: ignore[import-not-found]

            ultimo_erro: Exception | None = None
            for pid in PROG_IDS_CANDIDATOS:
                try:
                    try:
                        # Early-bound: registra a typelib, expõe SComConfig/SAcionaCtrl
                        # como classes + constantes (csg*/cv*/cmc*/ctc*) em constants.
                        self._com = win32com.client.gencache.EnsureDispatch(pid)
                    except Exception:
                        logger.warning(
                            f"[RealHenry7x] EnsureDispatch({pid}) falhou, usando Dispatch dinâmico"
                        )
                        self._com = win32com.client.Dispatch(pid)
                    self._prog_id_usado = pid
                    break
                except Exception as e:
                    ultimo_erro = e
                    continue
            if self._com is None:
                raise RuntimeError(
                    f"Falha ao criar COM ({'/'.join(PROG_IDS_CANDIDATOS)}) "
                    f"({ultimo_erro}) — rode regsvr32 {self.dll_path}"
                ) from ultimo_erro
        except ImportError as e:
            raise RuntimeError("pywin32 não instalado — uv sync --extra windows") from e
        except RuntimeError:
            raise
        except Exception as e:  # COM não registrado ou DLL faltando
            raise RuntimeError(
                f"Falha ao criar COM {PROG_ID} ({e}) — rode regsvr32 {self.dll_path}"
            ) from e

        self._lock: threading.Lock = threading.Lock()
        self._callbacks: list[GiroCallback] = []
        self._conectado: bool = False
        self._porta: str | None = None
        self._ultima_liberacao: Direcao | None = None
        self._ultima_qtd_regs: int = 0
        self._stop: threading.Event = threading.Event()
        self._poll_thread: threading.Thread | None = None
        logger.info(f"[RealHenry7x] COM {self._prog_id_usado} criado (dll={self.dll_path})")

    # --- helpers COM ---

    def _const(self, name: str) -> Any | None:
        """Constante da typelib (csg*/cv*/cmc*/ctc*); None se makepy ausente."""
        try:
            import win32com.client  # type: ignore[import-not-found]

            return getattr(win32com.client.constants, name, None)
        except Exception:
            return None

    def _record(self, name: str) -> Any | None:
        """Instancia record COM (SComConfig/SAcionaCtrl); None se indisponível."""
        try:
            import win32com.client  # type: ignore[import-not-found]

            return win32com.client.Record(name, self._com)
        except Exception as e:
            logger.debug(f"[RealHenry7x] Record({name}) indisponível: {e}")
            return None

    @staticmethod
    def _set_first(record: Any, candidatos: tuple[str, ...], valor: Any) -> bool:
        for campo in candidatos:
            try:
                setattr(record, campo, valor)
                return True
            except Exception:
                continue
        return False

    def _texto_erro(self, contexto: str) -> str:
        """Monta 'contexto (código: descrição)' via ThreadLastError/ErrorDescription."""
        try:
            codigo = int(self._com.ThreadLastError(self._card_id))
        except Exception:
            return contexto
        try:
            desc = str(self._com.ErrorDescription(codigo))
        except Exception:
            desc = "<sem descrição>"
        return f"{contexto} (erro {codigo}: {desc})"

    def _montar_scomconfig(self, porta: str) -> Any | None:
        """Monta SComConfig serial; None se o record/constantes não existirem.

        7.2.0.52: ``SComConfig`` aninhado = ``{Tcp, Serial(SComSerial),
        ModoComunicacao, Modem, TipoComunicacao, GPRS, IsCatraca}`` com
        ``SComSerial = {NumeroRelogio, Porta(BSTR), Velocidade(enum)}``.
        Enums Delphi chegam como ``VT_RECORD`` — setar int puro pode falhar
        (``Only com_record``); nesse caso mantém o default 0, que já é o
        correto para serial 9600 (``ctcSerial``/``cv9600``).
        """
        cfg = self._record("SComConfig")
        if cfg is None:
            return None
        try:
            serial = cfg.Serial  # SComSerial aninhado (7.2)
        except Exception:
            serial = None
        if serial is None:
            # DLL antiga (record plano) — tenta direto
            tipo = self._const("ctcSerial")
            if tipo is not None:
                self._set_first(cfg, _SCOM_TIPO_FIELDS, tipo)
            if not self._set_first(cfg, _SCOM_PORTA_FIELDS, porta):
                logger.warning("[RealHenry7x] SComConfig sem campo de porta conhecido")
                return None
            vel = self._const("cv9600")  # padrão conservador Henry 7x serial
            if vel is not None:
                self._set_first(cfg, _SCOM_VEL_FIELDS, vel)
            return cfg
        try:
            serial.Porta = porta
        except Exception as e:
            logger.debug(f"[RealHenry7x] Serial.Porta falhou: {e}")
            if not self._set_first(cfg, _SCOM_PORTA_FIELDS, porta):
                logger.warning("[RealHenry7x] SComConfig sem campo de porta conhecido")
                return None
        with contextlib.suppress(Exception):
            serial.NumeroRelogio = 1
        vel = self._const("cv9600")
        if vel is not None:
            try:
                serial.Velocidade = vel
            except Exception as e:
                logger.debug(f"[RealHenry7x] Serial.Velocidade falhou (enum VT_RECORD): {e}")
        tipo = self._const("ctcSerial")
        if tipo is not None:
            try:
                cfg.TipoComunicacao = tipo
            except Exception as e:
                logger.debug(f"[RealHenry7x] TipoComunicacao falhou: {e}")
        modo = self._const("cmcOnOff")
        if modo is not None:
            try:
                cfg.ModoComunicacao = modo
            except Exception as e:
                logger.debug(f"[RealHenry7x] ModoComunicacao falhou: {e}")
        with contextlib.suppress(Exception):
            cfg.IsCatraca = True
        return cfg

    # --- API ---

    def conectar(self, porta: str | int, timeout_ms: int = 5000) -> bool:
        porta_str = _normalizar_porta(porta)
        logger.info(f"[RealHenry7x] conectar porta={porta_str} timeout={timeout_ms}ms")
        with self._lock:
            if self._conectado:
                return True
        erros: list[str] = []

        # Caminho principal: AdicionaCard(SComConfig, card).
        cfg = self._montar_scomconfig(porta_str)
        if cfg is not None:
            try:
                if bool(self._com.AdicionaCard(cfg, self._card_id)):
                    logger.info("[RealHenry7x] conectado via AdicionaCard(SComConfig)")
                    self._pos_conectar(porta_str)
                    return True
                erros.append(self._texto_erro("AdicionaCard retornou False"))
            except Exception as e:
                erros.append(f"AdicionaCard: {e}")
        else:
            erros.append("SComConfig indisponível (makepy?)")

        # Fallbacks: variantes AdicionaCard* escalares (algumas DLLs expõem
        # AdicionaCardSerial etc. em outra interface — tenta via getattr).
        for nome, args in (
            ("AdicionaCardSerial", (porta_str, self._card_id, self._const("cmcOnOff"))),
            (
                "AdicionaCardSerial485",
                (1, porta_str, self._const("cv9600"), 1, self._const("cmcOnOff")),
            ),
            ("AdicionaCardTcpIp", (porta_str, "", 0, 1, self._const("cmcOnOff"))),
        ):
            try:
                func = getattr(self._com, nome, None)
                if func is None:
                    continue
                if any(a is None for a in args):
                    continue  # constante ausente — próxima variante
                if bool(func(*args)):
                    logger.info(f"[RealHenry7x] conectado via {nome} (fallback)")
                    self._pos_conectar(porta_str)
                    return True
                erros.append(self._texto_erro(f"{nome} retornou False"))
            except Exception as e:
                erros.append(f"{nome}: {e}")
        # Best-effort via comtypes (NÃO validado — catraca off na validação):
        # recria SComConfig com BSTRs inicializadas para evitar access violation.
        try:
            import comtypes.client as _ct
            import comtypes.gen._25DC738C_6571_47AD_8B19_362853B14E8D_0_1_0 as _gen  # type: ignore[import-not-found]
            from comtypes import BSTR as _BSTR

            ct_com = _ct.CreateObject(PROG_ID)
            cfg_ct = _gen.SComConfig()
            try:
                cfg_ct.Tcp.Ip = _BSTR("")
                cfg_ct.Tcp.MAC = _BSTR("")
                cfg_ct.Modem.Fone = _BSTR("")
                cfg_ct.Modem.Porta = _BSTR("")
            except Exception:
                pass
            cfg_ct.Serial.Porta = porta_str
            cfg_ct.Serial.NumeroRelogio = 1
            cfg_ct.Serial.Velocidade = 0  # cv9600
            cfg_ct.TipoComunicacao = 0  # ctcSerial
            cfg_ct.ModoComunicacao = 2  # cmcOnOff
            cfg_ct.IsCatraca = True
            try:
                ret = ct_com.AdicionaCard[cfg_ct]
                ok = bool(ret[1] if isinstance(ret, tuple) else ret)
            except Exception as ce:
                erros.append(f"comtypes AdicionaCard: {ce}")
                ok = False
            if ok:
                logger.info("[RealHenry7x] conectado via comtypes AdicionaCard")
                self._pos_conectar(porta_str)
                return True
            erros.append("comtypes AdicionaCard retornou False")
        except Exception as e:
            logger.debug(f"[RealHenry7x] comtypes indisponível: {e}")

        raise RuntimeError(f"[RealHenry7x] conectar({porta_str}) falhou: {'; '.join(erros)}")

    def _pos_conectar(self, porta: str) -> None:
        with self._lock:
            self._conectado = True
            self._porta = porta
            self._ultima_qtd_regs = self._quant_regs()
        self._stop.clear()
        thread = threading.Thread(target=self._poll_loop, name="henry7x-poll", daemon=True)
        self._poll_thread = thread
        thread.start()

    def desconectar(self) -> None:
        logger.info("[RealHenry7x] desconectar")
        self._stop.set()
        thread = self._poll_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        self._poll_thread = None
        try:
            self._com.PararColetaEventos(self._card_id)
        except Exception as e:
            logger.warning(f"[RealHenry7x] PararColetaEventos falhou: {e}")
        try:
            if not bool(self._com.RemoveCard(self._card_id)):
                logger.warning(self._texto_erro("[RealHenry7x] RemoveCard retornou False"))
        except Exception as e:
            logger.warning(f"[RealHenry7x] RemoveCard falhou: {e}")
        with self._lock:
            self._conectado = False
            self._porta = None

    def liberar(self, direcao: Direcao) -> ResultadoCatraca:
        with self._lock:
            if not self._conectado:
                logger.warning("[RealHenry7x] liberar() sem conexão -> ERRO")
                return ResultadoCatraca.ERRO
            self._ultima_liberacao = direcao
        logger.info(f"[RealHenry7x] liberar {direcao.name}")
        ok_modo = self._envia_modo(_MODO_POR_DIRECAO[direcao])
        rele = self._rele_entrada if direcao is Direcao.ENTRADA else self._rele_saida
        ok_pulso = self._envia_pulso(rele)
        if ok_modo or ok_pulso:
            return ResultadoCatraca.LIBERADO
        logger.error(self._texto_erro("[RealHenry7x] liberar falhou (modo e pulso)"))
        return ResultadoCatraca.ERRO

    def bloquear(self) -> None:
        logger.info("[RealHenry7x] bloquear")
        if not self._envia_modo("csgBloqueada"):
            logger.error(self._texto_erro("[RealHenry7x] bloquear falhou"))

    def _envia_modo(self, const_modo: str) -> bool:
        """EnviaTipoCatraca(csg*); False se constante ausente ou COM recusar."""
        modo = self._const(const_modo)
        if modo is None:
            logger.warning(
                f"[RealHenry7x] constante {const_modo} ausente — "
                "rode scripts/dump_henry_typelib.py na VM e refaça makepy"
            )
            return False
        try:
            return bool(self._com.EnviaTipoCatraca(self._card_id, modo))
        except Exception as e:
            logger.warning(f"[RealHenry7x] EnviaTipoCatraca({const_modo}) falhou: {e}")
            return False

    def _envia_pulso(self, rele: int) -> bool:
        """Pulso EnviaAcionaCtrl no relé (1=entrada, 2=saída por convenção).

        7.2.0.52: ``SAcionaCtrl = {TempoRele1/2/3}`` (c_ubyte) — tempo>0
        aciona o relé por N segundos. DLLs antigas usavam AcionaRele bool
        + Tempo (mantido como fallback).
        """
        rec = self._record("SAcionaCtrl")
        if rec is None:
            logger.warning("[RealHenry7x] record SAcionaCtrl indisponível — pulso ignorado")
            return False
        try:
            if rele == 1:
                rec.TempoRele1 = int(self._tempo_rele_s)
            elif rele == 2:
                rec.TempoRele2 = int(self._tempo_rele_s)
            else:
                rec.TempoRele3 = int(self._tempo_rele_s)
        except Exception:
            # fallback legado AcionaRele bool
            rele_fields = _SAC_RELE_FIELDS if rele == 1 else _SAC_RELE2_FIELDS
            tempo_fields = _SAC_TEMPO_FIELDS if rele == 1 else _SAC_TEMPO2_FIELDS
            self._set_first(rec, rele_fields, True)
            self._set_first(rec, tempo_fields, int(self._tempo_rele_s))
        try:
            return bool(self._com.EnviaAcionaCtrl(self._card_id, self._placa, rec))
        except Exception as e:
            logger.warning(f"[RealHenry7x] EnviaAcionaCtrl(rele={rele}) falhou: {e}")
            return False

    def on_giro(self, callback: GiroCallback) -> None:
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def off_giro(self, callback: GiroCallback) -> None:
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def _quant_regs(self) -> int:
        try:
            return int(self._com.QuantRegsColetados(self._card_id))
        except Exception:
            return 0

    def _poll_loop(self) -> None:
        logger.info("[RealHenry7x] polling ColetaEventos iniciado")
        while not self._stop.wait(self._poll_interval_s):
            try:
                self._com.ColetaEventos(self._card_id, "")
            except Exception as e:
                logger.debug(f"[RealHenry7x] ColetaEventos falhou: {e}")
                continue
            qtd = self._quant_regs()
            with self._lock:
                if qtd <= self._ultima_qtd_regs:
                    # sem novidade (ou contador zerado após consumo) — só sincroniza
                    self._ultima_qtd_regs = qtd
                    continue
                self._ultima_qtd_regs = qtd
                direcao = self._ultima_liberacao or Direcao.ENTRADA
                cbs = list(self._callbacks)
            ts = time.time()
            logger.info(f"[RealHenry7x] giro detectado direcao={direcao.name} regs={qtd}")
            for cb in cbs:
                try:
                    cb(direcao, ts)
                except Exception as e:
                    logger.exception(f"callback giro falhou: {e}")
        logger.info("[RealHenry7x] polling ColetaEventos parado")

    def status(self) -> dict[str, Any]:
        with self._lock:
            online = self._conectado
            porta = self._porta
        info: dict[str, Any] = {
            "online": online,
            "mock": False,
            "dll": str(self.dll_path),
            "card_id": self._card_id,
            "porta": porta,
            "versao": None,
            "portas": None,
            "ultimo_erro": None,
            "ultimo_erro_txt": None,
            "ultima_comunicacao": None,
        }
        try:
            info["versao"] = str(self._com.Versao)
        except Exception as e:
            logger.debug(f"[RealHenry7x] status Versao indisponível: {e}")
        try:
            raw = str(self._com.ListaPortasSeriais)
            info["portas"] = [p for p in raw.split("-") if p] or raw
        except Exception as e:
            logger.debug(f"[RealHenry7x] status ListaPortasSeriais indisponível: {e}")
        try:
            codigo = int(self._com.ThreadLastError(self._card_id))
            info["ultimo_erro"] = codigo
            try:
                info["ultimo_erro_txt"] = str(self._com.ErrorDescription(codigo))
            except Exception as e:
                logger.debug(f"[RealHenry7x] status ErrorDescription indisponível: {e}")
        except Exception as e:
            logger.debug(f"[RealHenry7x] status ThreadLastError indisponível: {e}")
        try:
            info["ultima_comunicacao"] = self._com.DataHoraUltimaComunicacao(self._card_id)
        except Exception as e:
            logger.debug(f"[RealHenry7x] status DataHoraUltimaComunicacao indisponível: {e}")
        return info
