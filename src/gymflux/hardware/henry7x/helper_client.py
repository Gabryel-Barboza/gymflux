"""Cliente IPC do helper 32-bit Henry 7x (Fase 5.1).

Implementa ``Henry7xDriver`` sobre um subprocesso do helper
(``helper_main.py`` / ``GymFlux.HardwareHelper.exe``) via JSON lines em
stdin/stdout. Este módulo NUNCA importa ``win32com`` — é seguro no processo
principal 64-bit (UI PySide6).

Ciclo de vida: o processo helper é criado sob demanda no primeiro comando e
encerrado no ``desconectar()`` (sem órfãos). ``conectar()`` propaga
``RuntimeError`` do helper (ex.: sem DLL); ``liberar()`` espelha o real e
retorna ``ERRO`` em falha; ``status()`` nunca levanta.
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from loguru import logger

from gymflux.hardware.henry7x.interface import (
    Direcao,
    GiroCallback,
    Henry7xDriver,
    ResultadoCatraca,
)

HELPER_EXE_NAME = "GymFlux.HardwareHelper.exe"
HELPER_MODULE = "gymflux.hardware.henry7x.helper_main"
CONNECT_TIMEOUT_S = 60.0
REQUEST_TIMEOUT_S = 30.0


def resolve_helper_cmd(explicit_cmd: list[str] | None = None) -> list[str]:
    """Resolve como invocar o helper.

    Ordem: ``explicit_cmd`` (testes/dev) > ``GYMFLUX_HELPER_EXE`` > exe ao lado
    de ``sys.executable`` (instalado) > ``sys._MEIPASS`` (frozen). Sem candidato,
    levanta ``FileNotFoundError`` (a factory cai para o mock).
    """
    if explicit_cmd:
        return list(explicit_cmd)
    env_exe = os.getenv("GYMFLUX_HELPER_EXE")
    if env_exe:
        cand = Path(env_exe)
        if cand.exists():
            return [str(cand)]
        raise FileNotFoundError(f"GYMFLUX_HELPER_EXE não encontrado: {env_exe}")
    cands: list[Path] = [Path(sys.executable).parent / HELPER_EXE_NAME]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cands.append(Path(meipass) / HELPER_EXE_NAME)
    env_dir = os.getenv("GYMFLUX_HELPER_DIR")
    if env_dir:
        cands.append(Path(env_dir) / HELPER_EXE_NAME)
    for cand in cands:
        if cand.is_file():
            return [str(cand)]
    raise FileNotFoundError(
        f"helper não encontrado ({HELPER_EXE_NAME} ao lado de {sys.executable})"
    )


class Henry7xHelperClient(Henry7xDriver):
    """Proxy do ``RealHenry7x`` 32-bit via subprocesso helper (não é mock)."""

    is_mock = False

    def __init__(
        self,
        cmd: list[str] | None = None,
        dll_path: str | None = None,
        request_timeout_s: float = REQUEST_TIMEOUT_S,
        connect_timeout_s: float = CONNECT_TIMEOUT_S,
        stderr: Any = None,
    ) -> None:
        self._cmd = resolve_helper_cmd(cmd)
        self._dll_path = dll_path or os.getenv("GYMFLUX_HENRY_DLL_PATH")
        self._request_timeout_s = request_timeout_s
        self._connect_timeout_s = connect_timeout_s
        self._stderr = stderr
        self._proc: subprocess.Popen[str] | None = None
        self._write_lock = threading.Lock()
        self._seq = 0
        self._pending: dict[int, tuple[threading.Event, dict[str, Any]]] = {}
        self._callbacks: list[GiroCallback] = []
        self._cb_lock = threading.Lock()
        self._reader: threading.Thread | None = None

    # -- processo --
    def _proc_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def _ensure_proc(self) -> None:
        if self._proc_alive():
            return
        self._cleanup_proc()
        flags = 0
        if sys.platform == "win32":
            flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
        logger.info(f"[helper-client] spawn: {self._cmd}")
        try:
            self._proc = subprocess.Popen(
                self._cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self._stderr,
                text=True,
                bufsize=1,
                creationflags=flags,
            )
        except (OSError, ValueError) as e:
            raise RuntimeError(f"falha ao iniciar helper ({e})") from e
        self._reader = threading.Thread(
            target=self._reader_loop, name="henry-helper-reader", daemon=True
        )
        self._reader.start()

    def _cleanup_proc(self) -> None:
        self._proc = None
        self._reader = None

    def _terminate(self) -> None:
        proc, reader = self._proc, self._reader
        self._cleanup_proc()
        with self._write_lock:
            pendentes = dict(self._pending)
            self._pending.clear()
        for ev, slot in pendentes.values():
            slot["error"] = "helper encerrado"
            ev.set()
        if proc is not None and proc.poll() is None:
            with contextlib.suppress(OSError, ValueError):
                proc.terminate()
            try:
                proc.wait(timeout=5.0)
            except (subprocess.TimeoutExpired, OSError, ValueError):
                with contextlib.suppress(OSError, ValueError):
                    proc.kill()
        if reader is not None and reader.is_alive() and reader is not threading.current_thread():
            reader.join(timeout=5.0)

    def close(self) -> None:
        """Encerra o helper (idempotente; também roda no ``__del__``)."""
        try:
            self._terminate()
        except Exception as e:
            logger.debug(f"[helper-client] close: {e}")

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self.close()

    # -- protocolo --
    def _reader_loop(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            self._fail_all("helper sem stdout")
            return
        try:
            for raw in proc.stdout:
                line = raw.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.debug(f"[helper-client] linha inválida ignorada: {e}")
                    continue
                if not isinstance(msg, dict):
                    continue
                if msg.get("event") == "giro":
                    self._dispatch_giro(msg)
                    continue
                req_id = msg.get("id")
                if isinstance(req_id, int):
                    with self._write_lock:
                        pendente = self._pending.pop(req_id, None)
                    if pendente is not None:
                        ev, slot = pendente
                        slot["response"] = msg
                        ev.set()
        except (ValueError, OSError) as e:
            logger.debug(f"[helper-client] reader: {e}")
        finally:
            self._fail_all("helper encerrou (EOF)")

    def _fail_all(self, erro: str) -> None:
        with self._write_lock:
            pendentes = dict(self._pending)
            self._pending.clear()
        for ev, slot in pendentes.values():
            slot["error"] = erro
            ev.set()

    def _dispatch_giro(self, msg: dict[str, Any]) -> None:
        try:
            direcao = Direcao[str(msg.get("direcao", "ENTRADA")).strip().upper()]
        except (KeyError, AttributeError, TypeError):
            logger.debug(f"[helper-client] giro com direção inválida: {msg}")
            return
        try:
            ts = float(msg.get("ts", 0.0))
        except (TypeError, ValueError):
            ts = 0.0
        with self._cb_lock:
            cbs = list(self._callbacks)
        import time as _time

        ts = ts or _time.time()
        for cb in cbs:
            try:
                cb(direcao, ts)
            except Exception as e:
                logger.exception(f"callback giro falhou: {e}")

    def _request(self, cmd: str, timeout: float | None = None, **params: Any) -> Any:
        self._ensure_proc()
        assert self._proc is not None and self._proc.stdin is not None
        with self._write_lock:
            self._seq += 1
            req_id = self._seq
            ev = threading.Event()
            slot: dict[str, Any] = {}
            self._pending[req_id] = (ev, slot)
            payload = {"id": req_id, "cmd": cmd, **params}
            try:
                self._proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
                self._proc.stdin.flush()
            except (BrokenPipeError, ValueError, OSError) as e:
                self._pending.pop(req_id, None)
                raise RuntimeError(f"helper inacessível ({e})") from e
        ok = ev.wait(timeout if timeout is not None else self._request_timeout_s)
        if not ok:
            with self._write_lock:
                self._pending.pop(req_id, None)
            raise TimeoutError(f"helper sem resposta ({cmd}, timeout)")
        if "error" in slot and "response" not in slot:
            raise RuntimeError(str(slot["error"]))
        resp = slot.get("response", {})
        if not isinstance(resp, dict):
            raise RuntimeError(f"resposta inválida do helper: {resp!r}")
        if not resp.get("ok", False):
            raise RuntimeError(str(resp.get("error", f"helper falhou ({cmd})")))
        return resp.get("result")

    # -- Henry7xDriver --
    def conectar(self, porta: str | int, timeout_ms: int = 5000) -> bool:
        params: dict[str, Any] = {"porta": porta, "timeout_ms": timeout_ms}
        if self._dll_path:
            params["dll_path"] = self._dll_path
        return bool(self._request("conectar", timeout=self._connect_timeout_s, **params))

    def desconectar(self) -> None:
        try:
            if self._proc_alive():
                try:
                    self._request("desconectar", timeout=10.0)
                finally:
                    with self._write_lock:
                        proc = self._proc
                        stdin = proc.stdin if proc is not None else None
                        if proc is not None and proc.poll() is None and stdin is not None:
                            try:
                                self._seq += 1
                                stdin.write(json.dumps({"id": self._seq, "cmd": "quit"}) + "\n")
                                stdin.flush()
                            except (BrokenPipeError, ValueError, OSError):
                                pass
        except Exception as e:
            logger.debug(f"[helper-client] desconectar: {e}")
        finally:
            self._terminate()

    def liberar(self, direcao: Direcao) -> ResultadoCatraca:
        try:
            result = self._request("liberar", direcao=direcao.name)
            return ResultadoCatraca(str(result).strip().upper())
        except ValueError:
            return ResultadoCatraca.ERRO
        except Exception as e:
            logger.warning(f"[helper-client] liberar({direcao.name}) falhou: {e}")
            return ResultadoCatraca.ERRO

    def bloquear(self) -> None:
        try:
            self._request("bloquear")
        except Exception as e:
            logger.warning(f"[helper-client] bloquear() falhou: {e}")

    def on_giro(self, callback: GiroCallback) -> None:
        with self._cb_lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def off_giro(self, callback: GiroCallback) -> None:
        with self._cb_lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def status(self) -> dict[str, Any]:
        try:
            result = self._request("status", timeout=10.0)
            info = dict(result) if isinstance(result, dict) else {"online": False}
        except Exception as e:
            logger.debug(f"[helper-client] status: {e}")
            info = {"online": False, "erro": str(e)}
        info["via_helper"] = True
        return info
