"""Preferências operacionais da recepção — JSON local, Qt-free.

Não é schema de domínio (nada de models/migrations): são ajustes de
operação (bloqueios, tolerância, timeout, porta) persistidos em
``data/gymflow_config.json``. Arquivo ausente/corrompido => padrões.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from gymflow.core.regras import RegraAcessoConfig
from gymflow.ui.theme import ModoTema

DEFAULT_CONFIG_PATH = Path("data/gymflow_config.json")

SENHA_MIN_MIN = 4
SENHA_MIN_MAX = 8


def _clamp_int(valor: Any, default: int, minimo: int, maximo: int) -> int:
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return default
    return max(minimo, min(maximo, numero))


def _as_bool(valor: Any, default: bool = False) -> bool:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, str):
        return valor.strip().lower() in ("1", "true", "sim", "yes", "on")
    return default


def _as_modo_tema(valor: Any) -> ModoTema:
    """Normaliza o tema; valor inválido/ausente => ESCURO (padrão legado)."""
    if isinstance(valor, ModoTema):
        return valor
    try:
        return ModoTema(str(valor).strip().upper())
    except ValueError:
        return ModoTema.ESCURO


@dataclass
class UiConfig:
    """Ajustes da aba Configurações (valores sempre normalizados)."""

    bloquear_entrada: bool = False
    bloquear_saida: bool = False
    senha_min_digitos: int = 4
    tolerancia_dias: int = 3
    timeout_giro_s: int = 7
    anti_passback: bool = False
    porta_catraca: str = "1"
    tema: ModoTema = ModoTema.ESCURO

    def __post_init__(self) -> None:
        self.bloquear_entrada = _as_bool(self.bloquear_entrada)
        self.bloquear_saida = _as_bool(self.bloquear_saida)
        self.senha_min_digitos = _clamp_int(self.senha_min_digitos, 4, SENHA_MIN_MIN, SENHA_MIN_MAX)
        self.tolerancia_dias = _clamp_int(self.tolerancia_dias, 3, 0, 30)
        self.timeout_giro_s = _clamp_int(self.timeout_giro_s, 7, 1, 60)
        self.anti_passback = _as_bool(self.anti_passback)
        porta = str(self.porta_catraca or "").strip()
        self.porta_catraca = porta or "1"
        self.tema = _as_modo_tema(self.tema)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UiConfig:
        """Tolerante: ignora chaves desconhecidas, normaliza o resto."""
        conhecidos = {f.name for f in cls.__dataclass_fields__.values()}
        filtrado = {k: v for k, v in data.items() if k in conhecidos}
        return cls(**filtrado)  # type: ignore[arg-type]

    def to_regra_config(self) -> RegraAcessoConfig:
        """Espelha tolerância/timeout/anti-passback p/ o domínio (RB01/RB04/RB05)."""
        return RegraAcessoConfig(
            tolerancia_dias=self.tolerancia_dias,
            timeout_giro_s=self.timeout_giro_s,
            anti_passback=self.anti_passback,
        )


@dataclass
class ConfigStore:
    """Carrega/salva ``UiConfig`` em JSON (escrita atômica via tmp+replace)."""

    path: Path | str = field(default=DEFAULT_CONFIG_PATH)
    fallback_porta: str = "1"

    @property
    def caminho(self) -> Path:
        return Path(self.path)

    def exists(self) -> bool:
        return self.caminho.exists()

    def load(self) -> UiConfig:
        """Lê o arquivo; ausente/corrompido => padrões (+ porta de fallback)."""
        caminho = self.caminho
        if not caminho.exists():
            return UiConfig(porta_catraca=self.fallback_porta)
        try:
            bruto = caminho.read_text(encoding="utf-8")
            data = json.loads(bruto)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"[ConfigStore] {caminho} ilegível ({e}) — usando padrões")
            return UiConfig(porta_catraca=self.fallback_porta)
        if not isinstance(data, dict):
            logger.warning(f"[ConfigStore] {caminho} sem objeto JSON — usando padrões")
            return UiConfig(porta_catraca=self.fallback_porta)
        cfg = UiConfig.from_dict(data)
        if "porta_catraca" not in data and self.fallback_porta:
            cfg.porta_catraca = self.fallback_porta.strip() or "1"
        return cfg

    def save(self, cfg: UiConfig) -> Path:
        """Persiste; cria diretórios pais. Retorna o caminho final."""
        caminho = self.caminho
        caminho.parent.mkdir(parents=True, exist_ok=True)
        tmp = caminho.with_name(caminho.name + ".tmp")
        tmp.write_text(
            json.dumps(cfg.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp.replace(caminho)
        logger.info(f"[ConfigStore] salvo em {caminho}")
        return caminho
