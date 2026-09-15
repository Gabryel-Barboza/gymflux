"""Ficha de avaliação física + saúde — domínio puro."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any

MEDIDAS_CHAVES: tuple[str, ...] = (
    "braco",
    "peito",
    "cintura",
    "quadril",
    "coxa",
    "panturrilha",
)


def _validar_positivo(nome: str, valor: float | None) -> None:
    if valor is None:
        return
    if not isinstance(valor, (int, float)):
        raise ValueError(f"{nome} deve ser numérico")
    if float(valor) <= 0:
        raise ValueError(f"{nome} deve ser > 0")


def _normalizar_medidas(valor: Any) -> dict[str, float]:
    """Aceita dict, JSON str ou None → dict[str,float] com chaves normalizadas."""
    if valor is None or valor == "":
        return {}
    if isinstance(valor, str):
        v = valor.strip()
        if not v:
            return {}
        try:
            parsed = json.loads(v)
            if isinstance(parsed, dict):
                valor = parsed
            else:
                return {}
        except (json.JSONDecodeError, ValueError):
            return {}
    if isinstance(valor, dict):
        out: dict[str, float] = {}
        for k, v in valor.items():
            key = str(k).strip().lower()
            if key in MEDIDAS_CHAVES:
                try:
                    fv = float(v)
                    if fv > 0:
                        out[key] = fv
                except (TypeError, ValueError):
                    continue
        return out
    return {}


def _formatar_medidas(medidas: dict[str, float]) -> str:
    """Texto legível: 'Braço 30cm · Peito 95cm · Cintura 80cm'."""
    if not medidas:
        return "—"
    ordem = [k for k in MEDIDAS_CHAVES if k in medidas]
    # mantém ordem definida, depois extras
    extras = [k for k in medidas if k not in MEDIDAS_CHAVES]
    ordem.extend(extras)
    partes = []
    for k in ordem:
        label = k.capitalize()
        # braco → Braço
        if k == "braco":
            label = "Braço"
        partes.append(f"{label} {medidas[k]:g}cm")
    return " · ".join(partes)


@dataclass(slots=True)
class AvaliacaoFisica:
    """Avaliação física e anamnese de saúde.

    Texto legível na interface: labels em português com acentos,
    medidas formatadas como 'Braço 30cm · Peito 95cm', saúde em
    blocos com quebras de linha.
    """

    id: str
    aluno_id: str
    data: date
    peso_kg: float | None = None
    altura_cm: float | None = None
    gordura_pct: float | None = None
    medidas: dict[str, float] = field(default_factory=dict)
    problemas_saude: str | None = None
    restricoes: str | None = None
    medicamentos: str | None = None
    contato_emergencia: str | None = None

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("Id não pode ser vazio.")
        if not self.aluno_id or not self.aluno_id.strip():
            raise ValueError("Aluno não pode ser vazio.")
        if not isinstance(self.data, date):
            raise ValueError("Data deve ser uma data.")
        _validar_positivo("Peso", self.peso_kg)
        _validar_positivo("Altura", self.altura_cm)
        if self.gordura_pct is not None:
            try:
                g = float(self.gordura_pct)
            except (TypeError, ValueError) as e:
                raise ValueError("Gordura deve ser numérica.") from e
            if not 0 <= g <= 100:
                raise ValueError("Gordura deve estar entre 0 e 100.")
        # normaliza medidas
        norm = _normalizar_medidas(self.medidas)
        object.__setattr__(self, "medidas", norm)
        for k, v in norm.items():
            _validar_positivo(k.capitalize(), v)
        # normaliza textos: strip, None se vazio
        for campo in ("problemas_saude", "restricoes", "medicamentos", "contato_emergencia"):
            val_txt = getattr(self, campo)
            if isinstance(val_txt, str):
                v_txt = val_txt.strip()
                object.__setattr__(self, campo, v_txt or None)

    def resumo_fisico(self) -> str:
        """Linha resumida para lista: '15/09/2026 · 75kg · 178cm · 12% · Braço 30cm...'."""
        from gymflux.ui.formatters import fmt_br

        partes = [fmt_br(self.data)]
        if self.peso_kg is not None:
            partes.append(f"{self.peso_kg:g}kg")
        if self.altura_cm is not None:
            partes.append(f"{self.altura_cm:g}cm")
        if self.gordura_pct is not None:
            partes.append(f"{self.gordura_pct:g}%")
        med_txt = _formatar_medidas(self.medidas)
        if med_txt != "—":
            partes.append(med_txt)
        return " · ".join(partes)

    def saude_resumo(self) -> str:
        """Bloco de saúde legível."""
        linhas: list[str] = []
        if self.problemas_saude:
            linhas.append(f"Problemas de saúde: {self.problemas_saude}")
        if self.restricoes:
            linhas.append(f"Restrições: {self.restricoes}")
        if self.medicamentos:
            linhas.append(f"Medicamentos: {self.medicamentos}")
        if self.contato_emergencia:
            linhas.append(f"Contato de emergência: {self.contato_emergencia}")
        return "\n".join(linhas) if linhas else "—"

    def medidas_json(self) -> str:
        return json.dumps(self.medidas, ensure_ascii=False)

    @classmethod
    def from_json_medidas(cls, s: str | None) -> dict[str, float]:
        return _normalizar_medidas(s)
