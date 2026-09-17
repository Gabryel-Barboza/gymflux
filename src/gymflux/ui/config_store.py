"""Preferências operacionais da recepção — JSON local, Qt-free.

Não é schema de domínio (nada de models/migrations): são ajustes de
operação (bloqueios, tolerância, timeout, porta) persistidos em
``data/gymflux_config.json``. Arquivo ausente/corrompido => padrões.
"""

from __future__ import annotations

import json
import sys as _sys
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from loguru import logger

from gymflux.core.regras import RegraAcessoConfig
from gymflux.ui.theme import ModoTema

_DEFAULT_CONFIG_REL = Path("data/gymflux_config.json")


def _is_frozen() -> bool:
    return bool(getattr(_sys, "frozen", False))


def _frozen_data_dir() -> Path:
    try:
        from platformdirs import user_data_dir

        return Path(user_data_dir("GymFlux"))
    except Exception:
        if _sys.platform == "win32":
            return Path.home() / "AppData" / "Roaming" / "GymFlux"
        return Path.home() / ".local" / "share" / "GymFlux"


def _assets_base() -> Path:
    """Base de assets: _MEIPASS quando frozen, senão cwd."""
    if _is_frozen():
        meipass = getattr(_sys, "_MEIPASS", None)
        if meipass:
            cand = Path(meipass) / "src" / "gymflux" / "ui" / "assets"
            if cand.exists():
                return cand
            # alternativo: assets na raiz do bundle
            cand2 = Path(meipass) / "gymflux" / "ui" / "assets"
            if cand2.exists():
                return cand2
            cand3 = Path(meipass) / "assets"
            if cand3.exists():
                return cand3
    return Path("src/gymflux/ui/assets")


def get_default_config_path() -> Path:
    """JSON de config: data/ em dev, %APPDATA%/GymFlux em frozen."""
    if _is_frozen():
        d = _frozen_data_dir()
        d.mkdir(parents=True, exist_ok=True)
        return d / "gymflux_config.json"
    return _DEFAULT_CONFIG_REL


# compat: código legado compara com DEFAULT_CONFIG_PATH
DEFAULT_CONFIG_PATH = get_default_config_path() if _is_frozen() else _DEFAULT_CONFIG_REL

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


class ModoAcesso(StrEnum):
    LIVRE = "LIVRE"
    SENHA = "SENHA"


def _as_modo_acesso(valor: Any, default: ModoAcesso) -> ModoAcesso:
    if isinstance(valor, ModoAcesso):
        return valor
    try:
        return ModoAcesso(str(valor).strip().upper())
    except ValueError:
        return default


class ModoFundo(StrEnum):
    SOLIDO = "SOLIDO"
    WALLPAPER = "WALLPAPER"


def _as_modo_fundo(valor: Any, default: ModoFundo = ModoFundo.WALLPAPER) -> ModoFundo:
    if isinstance(valor, ModoFundo):
        return valor
    try:
        return ModoFundo(str(valor).strip().upper())
    except ValueError:
        return default


CADASTRO_CAMPOS: tuple[str, ...] = ("cpf", "telefone", "email", "data_nasc", "endereco")


def _as_cadastro_obrigatorios(valor: Any) -> dict[str, bool]:
    """Normaliza dict de obrigatórios: só chaves essenciais, bool, default False."""
    base = dict.fromkeys(CADASTRO_CAMPOS, False)  # type: ignore[arg-type]
    if not isinstance(valor, dict):
        return base  # type: ignore[return-value]
    for k in CADASTRO_CAMPOS:
        if k in valor:
            base[k] = _as_bool(valor[k], False)
    return base


@dataclass
class UiConfig:
    """Ajustes da aba Configurações (valores sempre normalizados)."""

    bloquear_entrada: bool = False  # legado 4.8- (mantido p/ compat JSON antigo)
    bloquear_saida: bool = False
    senha_min_digitos: int = 4
    tolerancia_dias: int = 3
    timeout_giro_s: int = 7
    anti_passback: bool = False
    porta_catraca: str = "1"
    tema: ModoTema = ModoTema.ESCURO
    # Fase 4.9: por direção, LIVRE (passa sem senha) vs SENHA (exige identificação)
    entrada_modo: ModoAcesso = ModoAcesso.SENHA
    saida_modo: ModoAcesso = ModoAcesso.LIVRE
    # Fase 4.14: wallpaper
    wallpaper: str | None = None
    fundo_modo: ModoFundo = ModoFundo.WALLPAPER
    # Fase 4.14: obrigatoriedade configurável do cadastro
    cadastro_obrigatorios: dict[str, bool] = field(
        default_factory=lambda: dict.fromkeys(CADASTRO_CAMPOS, False)  # type: ignore[arg-type]
    )

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
        self.entrada_modo = _as_modo_acesso(self.entrada_modo, ModoAcesso.SENHA)
        self.saida_modo = _as_modo_acesso(self.saida_modo, ModoAcesso.LIVRE)
        # normaliza wallpaper: string vazia => None
        if isinstance(self.wallpaper, str):
            w = self.wallpaper.strip()
            self.wallpaper = w or None
        elif self.wallpaper is not None:
            self.wallpaper = str(self.wallpaper).strip() or None
        self.fundo_modo = _as_modo_fundo(self.fundo_modo, ModoFundo.WALLPAPER)
        # se wallpaper ativo mas sem imagem, cai para solido
        if self.fundo_modo == ModoFundo.WALLPAPER and not self.wallpaper:
            # mantém wallpaper default se possível, senão solido
            pass
        self.cadastro_obrigatorios = _as_cadastro_obrigatorios(self.cadastro_obrigatorios)

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

    path: Path | str = field(default_factory=lambda: get_default_config_path())
    fallback_porta: str = "1"

    @property
    def caminho(self) -> Path:
        return Path(self.path)

    def exists(self) -> bool:
        return self.caminho.exists()

    def _default_wallpaper(self, tema: ModoTema | None = None) -> str | None:
        base = _assets_base()
        # novo: wallpaper-preto.png / wallpaper-branco.png por tema
        if tema is not None:
            nome = "wallpaper-branco.png" if tema == ModoTema.CLARO else "wallpaper-preto.png"
            p = base / nome
            if p.exists():
                return str(p)
            # fallback legacy path dev
            p2 = Path(f"src/gymflux/ui/assets/{nome}")
            if p2.exists():
                return str(p2)
        # fallback: tenta ambos, depois legado
        for p in (
            base / "wallpaper-preto.png",
            base / "wallpaper-branco.png",
            base / "wallpaper.png",
            Path("src/gymflux/ui/assets/wallpaper-preto.png"),
            Path("src/gymflux/ui/assets/wallpaper-branco.png"),
            Path("src/gymflux/ui/assets/wallpaper.png"),
            Path("vendor/gymflux-logomarca.png"),
        ):
            if p.exists():
                return str(p)
        return None

    def wallpaper_efetivo(self, cfg: UiConfig) -> str | None:
        """Wallpaper real a usar: se cfg.wallpaper vazio e modo WALLPAPER, auto por tema."""
        if cfg.fundo_modo != ModoFundo.WALLPAPER:
            return None
        if cfg.wallpaper:
            return cfg.wallpaper
        # vazio => auto por tema
        return self._default_wallpaper(cfg.tema)

    def load(self) -> UiConfig:
        """Lê o arquivo; ausente/corrompido => padrões (+ porta de fallback)."""
        caminho = self.caminho
        if not caminho.exists():
            cfg = UiConfig(porta_catraca=self.fallback_porta)
            # deixa wallpaper None para auto por tema (não preenche)
            return cfg
        try:
            bruto = caminho.read_text(encoding="utf-8")
            data = json.loads(bruto)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"[ConfigStore] {caminho} ilegível ({e}) — usando padrões")
            cfg = UiConfig(porta_catraca=self.fallback_porta)
            return cfg
        if not isinstance(data, dict):
            logger.warning(f"[ConfigStore] {caminho} sem objeto JSON — usando padrões")
            cfg = UiConfig(porta_catraca=self.fallback_porta)
            return cfg
        cfg = UiConfig.from_dict(data)
        if "porta_catraca" not in data and self.fallback_porta:
            cfg.porta_catraca = self.fallback_porta.strip() or "1"
        # wallpaper vazio => auto, não preenche
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
