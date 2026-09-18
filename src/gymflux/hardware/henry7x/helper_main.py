"""Helper 32-bit Henry 7x — processo filho sem UI (Fase 5.1).

A ``kernel7x.dll`` é COM in-proc 32-bit: o processo principal 64-bit
(``GymFlux.exe`` com PySide6, que só tem wheels ``win_amd64``) NÃO consegue
carregá-la. Este helper roda em Python 32-bit e expõe o ``RealHenry7x`` via
JSON lines (stdio) ou TCP ``127.0.0.1:9477`` para o ``Henry7xHelperClient``.

Protocolo (uma linha JSON por mensagem; logs vão para stderr, stdout é SÓ
protocolo):

  -> {"id": 1, "cmd": "conectar", "porta": "COM3", "timeout_ms": 5000}
  <- {"id": 1, "ok": true, "result": true}
  -> {"id": 2, "cmd": "liberar", "direcao": "ENTRADA"}
  <- {"id": 2, "ok": true, "result": "LIBERADO"}
  -> {"id": 3, "cmd": "status"}
  <- {"id": 3, "ok": true, "result": {...}}
  -> {"id": 4, "cmd": "quit"}
  <- {"id": 4, "ok": true, "result": true}
  <- {"event": "giro", "direcao": "ENTRADA", "ts": 1234.5}  (espontâneo)

Uso (só Windows 32-bit com DLL registrada; ``--mock`` roda em qualquer lugar):

  python -m gymflux.hardware.henry7x.helper_main [--mock] [--transport stdio|tcp]
  GYMFLUX_HELPER_MOCK=1 python -m gymflux.hardware.henry7x.helper_main

Sem DLL / fora de Windows 32-bit o helper SOBE normalmente e responde
``{"ok": false, "error": ...}`` (falha graciosa — nunca crasha o protocolo).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import socket
import sys
import threading
from collections.abc import Callable
from typing import Any

from loguru import logger

from gymflux.hardware.henry7x.interface import Direcao

TRANSPORT_STDIO = "stdio"
TRANSPORT_TCP = "tcp"
DEFAULT_TCP_HOST = "127.0.0.1"
DEFAULT_TCP_PORT = 9477
DEFAULT_DLL_PATH = "vendor/Henry/Henry7x/Kernel7x.dll"


def _json_safe(obj: Any) -> Any:
    """Converte payload p/ tipos JSON (ex.: datetime COM vira str)."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return str(obj)


def _parse_direcao(valor: Any) -> Direcao:
    try:
        return Direcao[str(valor).strip().upper()]
    except (KeyError, AttributeError, TypeError) as e:
        raise RuntimeError(f"direcao inválida: {valor!r} (use ENTRADA|SAIDA)") from e


class HelperServer:
    """Dono do driver (Real ou Mock) + despacho do protocolo JSON lines."""

    def __init__(self, *, mock: bool, dll_path: str, giro_delay_s: float = 1.0) -> None:
        self._mock = mock
        self._dll_path = dll_path
        self._giro_delay_s = giro_delay_s
        self._driver: Any = None
        self._send: Callable[[str], None] = lambda _line: None
        self._send_lock = threading.Lock()
        self._shutdown = threading.Event()

    # -- driver (criação preguiçosa: sem DLL o helper sobe e falha por comando) --
    def _create_driver(self) -> Any:
        if self._mock:
            from gymflux.hardware.henry7x.mock import MockHenry7x

            return MockHenry7x(giro_delay_s=self._giro_delay_s)
        from gymflux.hardware.henry7x.real import RealHenry7x

        return RealHenry7x(dll_path=self._dll_path)

    def _require_driver(self) -> Any:
        if self._driver is None:
            raise RuntimeError("helper não conectado — envie conectar primeiro")
        return self._driver

    def _on_giro_driver(self, direcao: Direcao, ts: float) -> None:
        self._emit({"event": "giro", "direcao": direcao.name, "ts": ts})

    # -- emissão (thread-safe; stdout é só protocolo) --
    def _emit(self, msg: dict[str, Any]) -> None:
        line = json.dumps(_json_safe(msg), ensure_ascii=False)
        try:
            with self._send_lock:
                self._send(line)
        except (BrokenPipeError, ValueError, OSError) as e:
            logger.debug(f"[helper] emissão descartada ({e})")

    # -- despacho --
    def dispatch(self, req: dict[str, Any]) -> dict[str, Any]:
        """Executa um comando; sempre retorna dict (nunca levanta)."""
        cmd = str(req.get("cmd", "")).strip().lower()
        try:
            if cmd == "conectar":
                return {"ok": True, "result": self._cmd_conectar(req)}
            if cmd == "liberar":
                return {"ok": True, "result": self._cmd_liberar(req)}
            if cmd == "bloquear":
                self._require_driver().bloquear()
                return {"ok": True, "result": True}
            if cmd == "desconectar":
                if self._driver is not None:
                    self._driver.desconectar()
                return {"ok": True, "result": True}
            if cmd == "status":
                return {"ok": True, "result": self._cmd_status()}
            if cmd == "ping":
                return {"ok": True, "result": "pong"}
            if cmd == "quit":
                self._shutdown.set()
                return {"ok": True, "result": True}
            raise RuntimeError(f"comando desconhecido: {req.get('cmd')!r}")
        except Exception as e:
            logger.warning(f"[helper] {cmd or '?'} falhou: {e}")
            return {"ok": False, "error": str(e)}

    def _cmd_conectar(self, req: dict[str, Any]) -> bool:
        porta = req.get("porta", "1")
        try:
            timeout_ms = int(req.get("timeout_ms", 5000))
        except (TypeError, ValueError):
            timeout_ms = 5000
        dll_path = str(req.get("dll_path") or self._dll_path)
        if self._driver is None:
            self._dll_path = dll_path
            self._driver = self._create_driver()
            self._driver.on_giro(self._on_giro_driver)
        return bool(self._driver.conectar(porta, timeout_ms=timeout_ms))

    def _cmd_liberar(self, req: dict[str, Any]) -> str:
        driver = self._require_driver()
        direcao = _parse_direcao(req.get("direcao"))
        return str(driver.liberar(direcao).name)

    def _cmd_status(self) -> dict[str, Any]:
        if self._driver is None:
            return {
                "online": False,
                "helper": True,
                "mock": self._mock,
                "porta": None,
                "versao": None,
            }
        info = dict(self._driver.status())
        info["helper"] = True
        return info

    # -- transportes --
    def run_stdio(self) -> None:
        def _send_stdout(line: str) -> None:
            sys.stdout.write(line + "\n")
            sys.stdout.flush()

        self._send = _send_stdout
        logger.info("[helper] transporte stdio (JSON lines)")
        for raw in sys.stdin:
            if self._shutdown.is_set():
                break
            line = raw.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning(f"[helper] linha inválida ignorada: {e}")
                continue
            if not isinstance(req, dict):
                logger.warning("[helper] mensagem não-objeto ignorada")
                continue
            resp: dict[str, Any] = {"id": req.get("id")}
            resp.update(self.dispatch(req))
            self._emit(resp)
            if self._shutdown.is_set():
                break
        logger.info("[helper] stdio EOF/shutdown")

    def run_tcp(self, host: str = DEFAULT_TCP_HOST, port: int = DEFAULT_TCP_PORT) -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((host, port))
            srv.listen(1)
            srv.settimeout(0.5)
            logger.info(f"[helper] transporte TCP {host}:{port}")
            while not self._shutdown.is_set():
                try:
                    conn, addr = srv.accept()
                except TimeoutError:
                    continue
                logger.info(f"[helper] cliente {addr}")
                try:
                    self._serve_tcp_conn(conn)
                except Exception as e:
                    logger.warning(f"[helper] conexão falhou: {e}")
                finally:
                    with self._send_lock, contextlib.suppress(OSError):
                        conn.close()
        finally:
            srv.close()
        logger.info("[helper] TCP shutdown")

    def _serve_tcp_conn(self, conn: socket.socket) -> None:
        fh = conn.makefile("r", encoding="utf-8")

        def _send_conn(line: str) -> None:
            conn.sendall((line + "\n").encode("utf-8"))

        with self._send_lock:
            self._send = _send_conn
        try:
            for raw in fh:
                if self._shutdown.is_set():
                    break
                line = raw.strip()
                if not line:
                    continue
                try:
                    req = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.warning(f"[helper] linha inválida ignorada: {e}")
                    continue
                if not isinstance(req, dict):
                    continue
                resp: dict[str, Any] = {"id": req.get("id")}
                resp.update(self.dispatch(req))
                self._emit(resp)
                if self._shutdown.is_set():
                    break
        finally:
            fh.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gymflux-helper",
        description="Helper 32-bit Henry 7x (JSON lines stdio/TCP, sem UI)",
    )
    p.add_argument("--mock", action="store_true", help="usa MockHenry7x (sem DLL)")
    p.add_argument(
        "--transport",
        choices=[TRANSPORT_STDIO, TRANSPORT_TCP],
        default=TRANSPORT_STDIO,
        help="canal IPC (default: stdio)",
    )
    p.add_argument("--host", default=DEFAULT_TCP_HOST, help="host TCP (default 127.0.0.1)")
    p.add_argument("--port", type=int, default=DEFAULT_TCP_PORT, help="porta TCP (default 9477)")
    p.add_argument("--dll-path", default=None, help="caminho kernel7x.dll (default: env/vendor)")
    p.add_argument(
        "--giro-delay-s",
        type=float,
        default=1.0,
        help="delay do giro no modo mock (default 1.0s)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logger.remove()
    logger.add(sys.stderr, level=os.getenv("GYMFLUX_LOG_LEVEL", "INFO"))

    mock = bool(args.mock or os.getenv("GYMFLUX_HELPER_MOCK") == "1")
    dll_path = args.dll_path or os.getenv("GYMFLUX_HENRY_DLL_PATH") or DEFAULT_DLL_PATH
    server = HelperServer(mock=mock, dll_path=dll_path, giro_delay_s=args.giro_delay_s)
    logger.info(
        f"[helper] GymFlux.HardwareHelper mock={mock} transport={args.transport} "
        f"dll={dll_path} (PID {os.getpid()})"
    )
    try:
        if args.transport == TRANSPORT_TCP:
            server.run_tcp(host=args.host, port=args.port)
        else:
            server.run_stdio()
    except KeyboardInterrupt:
        logger.info("[helper] interrompido")
    finally:
        try:
            if server._driver is not None:
                server._driver.desconectar()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
