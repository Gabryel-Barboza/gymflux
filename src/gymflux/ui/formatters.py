"""Formatadores BR — datas no padrão brasileiro DD/MM/AAAA."""

from __future__ import annotations

from datetime import date, datetime


def fmt_br(d: date | datetime | None) -> str:
    """DD/MM/AAAA ou '—' se None."""
    if d is None:
        return "—"
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime("%d/%m/%Y")


def fmt_br_datetime(dt: datetime | None, with_seconds: bool = False) -> str:
    """DD/MM/AAAA HH:MM[:SS]"""
    if dt is None:
        return "—"
    fmt = "%d/%m/%Y %H:%M:%S" if with_seconds else "%d/%m/%Y %H:%M"
    return dt.strftime(fmt)


def parse_br(s: str) -> date:
    """Aceita DD/MM/AAAA ou AAAA-MM-DD (compat). Levanta ValueError se inválido."""
    txt = s.strip()
    if not txt:
        raise ValueError("data vazia")
    # tenta DD/MM/AAAA
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"data inválida: {s} (use DD/MM/AAAA)")


def parse_br_competencia(s: str) -> str | None:
    """Valida competência YYYY-MM ou MM/AAAA, retorna YYYY-MM ou None."""
    txt = s.strip()
    if not txt:
        return None
    # YYYY-MM
    try:
        dt = datetime.strptime(txt, "%Y-%m")
        return dt.strftime("%Y-%m")
    except ValueError:
        pass
    # MM/AAAA
    try:
        dt = datetime.strptime(txt, "%m/%Y")
        return dt.strftime("%Y-%m")
    except ValueError:
        pass
    # DD/MM/AAAA -> extrai MM/AAAA
    try:
        dt = datetime.strptime(txt, "%d/%m/%Y")
        return dt.strftime("%Y-%m")
    except ValueError:
        pass
    raise ValueError(f"competência inválida: {s} (use MM/AAAA ou AAAA-MM)")
