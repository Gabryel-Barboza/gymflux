"""Funcionário — domínio puro, sem I/O.

Entrada indefinida na catraca (sem matrícula/plano/pagamento); autentica
por senha numérica como aluno (mesmo hash PBKDF2+salt, nunca texto puro).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from gymflux.core.aluno import conferir_senha, gerar_senha_hash

DIAS_ABREV = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
DIAS_VALIDOS = set(DIAS_ABREV)
DIAS_ORDEM = {d: i for i, d in enumerate(DIAS_ABREV)}
PRESET_DIAS = {
    "Seg-Sex": "Seg-Sex",
    "Sáb": "Sáb",
    "Dom": "Dom",
    "Seg-Sáb": "Seg-Sáb",
    "Todos": "Seg-Dom",
    "Seg-Dom": "Seg-Dom",
}


def _norm_dias_token(tok: str) -> str:
    tok = tok.strip().replace("Sab", "Sáb")
    return tok


def _validar_dias(dias: str) -> str:
    if not dias or not dias.strip():
        raise ValueError("Dias não pode ser vazio")
    norm = dias.strip().replace("–", "-").replace("—", "-").replace("Sab", "Sáb")
    # Todos alias
    if norm.lower() in ("todos", "todos os dias"):
        return "Seg-Dom"
    # valida tokens
    tokens = re.findall(r"Seg|Ter|Qua|Qui|Sex|Sáb|Dom", norm)
    if not tokens:
        raise ValueError(
            f"Dias inválido: '{dias}' — use Seg Ter Qua Qui Sex Sáb Dom com '-' para faixa"
        )
    cleaned = re.sub(r"Seg|Ter|Qua|Qui|Sex|Sáb|Dom", "", norm)
    cleaned = re.sub(r"[-\s,]+", "", cleaned)
    if cleaned.strip():
        raise ValueError(f"Dias inválido: '{dias}' contém '{cleaned}'")
    if "-" in norm:
        parts = [p.strip() for p in norm.split("-")]
        if len(parts) != 2:
            raise ValueError(f"Faixa de dias inválida: '{dias}' — use 'Seg-Sex'")
        for p in parts:
            if p not in DIAS_VALIDOS:
                raise ValueError(f"Faixa de dias inválida: '{dias}'")
        if DIAS_ORDEM[parts[0]] > DIAS_ORDEM[parts[1]]:
            raise ValueError(f"Faixa de dias inválida: '{dias}' — ordem crescente")
    # normaliza espaços/hífens
    norm = re.sub(r"\s*-\s*", "-", norm)
    norm = re.sub(r"\s*,\s*", ", ", norm)
    norm = re.sub(r"\s+", " ", norm).strip()
    # capitaliza? já correto
    return norm


def _validar_hhmm(s: str) -> str:
    s = s.strip()
    if not re.match(r"^\d{2}:\d{2}$", s):
        raise ValueError(f"Horário inválido: '{s}' — use HH:MM")
    h, m = s.split(":")
    hi, mi = int(h), int(m)
    if not (0 <= hi <= 23 and 0 <= mi <= 59):
        raise ValueError(f"Horário inválido: '{s}' — hora 00-23 e minuto 00-59")
    return f"{hi:02d}:{mi:02d}"


@dataclass(frozen=True, slots=True)
class Turno:
    dias: str
    inicio: str  # HH:MM
    fim: str  # HH:MM


def parse_turnos(text: str | None) -> list[Turno]:
    """Parseia turnos normalizados 'Seg-Sex 08:00-12:00; Sáb 08:00-12:00'.

    Valida HH:MM, dias abreviados Seg Ter Qua Qui Sex Sáb Dom, faixas com '-'
    e ';' como separador. Levanta ValueError amigável se inválido.
    """
    if not text or not text.strip():
        return []
    # tolerant: aceita separador ','? não, só ';' conforme spec, mas tolera ','
    partes = [p.strip() for p in text.strip().split(";") if p.strip()]
    turnos: list[Turno] = []
    for p in partes:
        # espera "<dias> HH:MM-HH:MM" ou "HH:MM-HH:MM" (legado) -> assume Seg-Sex
        # split última ocorrência de espaço antes do horário
        # encontra padrão HH:MM
        m = re.search(r"\d{2}:\d{2}\s*[-–—]\s*\d{2}:\d{2}", p)
        if not m:
            raise ValueError(f"Turno inválido: '{p}' — esperado 'DIAS HH:MM-HH:MM'")
        dias_part = p[: m.start()].strip()
        horario_part = p[m.start() :].strip()
        # normaliza separador de horário
        horario_part = horario_part.replace("–", "-").replace("—", "-")
        # valida horarios
        try:
            ini_str, fim_str = [x.strip() for x in horario_part.split("-", 1)]
        except ValueError as e:
            raise ValueError(f"Turno inválido: '{p}' — use HH:MM-HH:MM") from e
        ini = _validar_hhmm(ini_str)
        fim = _validar_hhmm(fim_str)
        if ini >= fim:
            raise ValueError(f"Turno inválido: '{p}' — início deve ser antes do fim")
        dias = "Seg-Sex" if not dias_part else _validar_dias(dias_part)
        turnos.append(Turno(dias=dias, inicio=ini, fim=fim))
    return turnos


def parse_turnos_tolerante(text: str | None, dias_legado: str | None = None) -> list[Turno]:
    """Parse tolerante para migração: aceita texto antigo '08:00-18:00' ou dias separado."""
    if not text or not text.strip():
        # tenta usar dias_legado se houver?
        if dias_legado and dias_legado.strip():
            # sem horários, não gera turno
            return []
        return []
    try:
        return parse_turnos(text)
    except ValueError:
        # tenta legado: texto é só horário sem dias
        txt = text.strip()
        # se txt puro horário, tenta parse como horário puro
        if re.match(r"^\s*\d{2}:\d{2}\s*[-–—]\s*\d{2}:\d{2}\s*$", txt):
            # sem dias, usa dias_legado ou default
            dias_use = dias_legado.strip() if dias_legado and dias_legado.strip() else "Seg-Sex"
            try:
                dias_norm = _validar_dias(dias_use)
            except ValueError:
                dias_norm = "Seg-Sex"
            # reutiliza parse com dias
            return parse_turnos(f"{dias_norm} {txt}")
        # tenta último recurso: retorna vazio e deixa view tratar como texto cru
        return []


def format_turnos(turnos: list[Turno]) -> str | None:
    if not turnos:
        return None
    return "; ".join(f"{t.dias} {t.inicio}-{t.fim}" for t in turnos)


def format_turnos_compacto(text: str | None, dias_legado: str | None = None) -> str:
    """Compacto multilinha para tabela: 'Seg–Sex\\n08–12h · 14–18h'.

    Agrupa por dias e usa en-dash + '·' entre horários do mesmo dia.
    """
    turnos = parse_turnos_tolerante(text, dias_legado)
    if not turnos:
        # fallback: mostra texto cru ou —
        raw = (text or "").strip() or (dias_legado or "").strip()
        return raw or "—"
    # agrupa por dias preservando ordem de aparição
    ordem_dias: list[str] = []
    por_dias: dict[str, list[Turno]] = {}
    for t in turnos:
        if t.dias not in por_dias:
            ordem_dias.append(t.dias)
            por_dias[t.dias] = []
        por_dias[t.dias].append(t)
    linhas: list[str] = []
    for dias in ordem_dias:
        lst = por_dias[dias]

        # compact horário 08–12h (remove :00 se minuto zero? mantém HHh)
        def _compact(h: str) -> str:
            hh, mm = h.split(":")
            if mm == "00":
                return f"{hh}h"
            return f"{hh}:{mm}"

        # dias com en-dash
        dias_compact = dias.replace("-", "–")
        horarios = " · ".join(f"{_compact(t.inicio)}–{_compact(t.fim)}" for t in lst)
        # múltiplos horários no mesmo dias => 2 linhas (dias + horários)
        if len(lst) > 1:
            linhas.append(f"{dias_compact}")
            linhas.append(horarios)
        else:
            linhas.append(f"{dias_compact} {horarios}")
    return "\n".join(linhas)


@dataclass(slots=True)
class Funcionario:
    """Colaborador com acesso livre; `ativo=False` bloqueia (manual)."""

    id: str
    nome: str
    senha_hash: str | None = None
    ativo: bool = True
    horarios: str | None = None
    dias: str | None = None
    foto: str | None = None
    # senha em texto para exibição no perfil
    senha: str | None = None

    def __post_init__(self) -> None:
        if not self.nome or not self.nome.strip():
            raise ValueError("Nome não pode ser vazio.")

    def definir_senha(self, senha: str) -> None:
        """Define senha numérica (4-8 dígitos); armazena hash e texto para exibição."""
        from gymflux.core.aluno import validar_senha_numerica

        self.senha = validar_senha_numerica(senha)
        self.senha_hash = gerar_senha_hash(senha)

    def verificar_senha(self, senha: str) -> bool:
        return conferir_senha(senha, self.senha_hash)

    def ativar(self) -> None:
        self.ativo = True

    def inativar(self) -> None:
        self.ativo = False
