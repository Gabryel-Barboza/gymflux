"""Identidade visual GymFlux — paleta aprovada + QSS escuro/claro (Qt-free).

No modo claro troca SÓ a base (fundo/painel/texto/suave/borda); os acentos
AZUL/LIMA/VERMELHO seguem idênticos. Onde texto colorido sobre fundo claro
não atinge contraste mínimo, o modo claro usa tinta escura (sem cor nova):
- títulos/cabeçalhos e valor do card: texto base (AZUL/LIMA ~1.9:1 no branco);
- texto sobre preenchimento AZUL/LIMA: tinta escura fixa (9.7-10.8:1);
- resultado LIBERADO/NEGADO no claro: selo colorido + tinta escura (ver
  ``estilo_resultado``); no escuro segue texto colorido como na Fase 4.2.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

AZUL = "#5AC8FA"  # primária / botões / seleções (ambos os modos)
FUNDO = "#0F1113"  # fundo (modo escuro)
LIMA = "#A3D65C"  # liberado / ok (ambos os modos)
VERDE_FORTE = "#2ECC71"  # status online no claro — verde forte com texto preto
VERMELHO = "#E57373"  # negado / erro (ambos os modos)
TEXTO = "#F2F5F7"  # texto (modo escuro)

FUNDO_PAINEL = "#1A1E22"  # groupbox / inputs / headers (modo escuro)
BORDA = "#2A3138"  # bordas e separadores (modo escuro)
TEXTO_SUAVE = "#9AA7B2"  # placeholders e mensagens neutras (modo escuro)
AZUL_ESCURO = "#3A9BC4"  # hover/pressed dos botões (ambos os modos)

# Base clara (Fase 4.10-A): containers cinza claro + borda visível.
FUNDO_CLARO = "#E8EDF1"
PAINEL_CLARO = "#E8EDF1"
TEXTO_CLARO = "#1A1E22"
SUAVE_CLARO = "#5A6B78"
BORDA_CLARA = "#C8D0D8"

# Tinta escura sobre preenchimentos claros/azuis (botões, seleções, selos).
TINTA_SOBRE_ACENTO = "#0F1113"


class ModoTema(StrEnum):
    ESCURO = "ESCURO"
    CLARO = "CLARO"


@dataclass(frozen=True)
class Paleta:
    """Cores de superfície/texto por modo; acentos vêm das constantes."""

    fundo: str
    painel: str
    texto: str
    suave: str
    borda: str
    titulo: str  # cabeçalhos/títulos (contraste de texto)
    valor: str  # valor do card PlanoCard (contraste de texto)


PALETA_ESCURA = Paleta(
    fundo=FUNDO,
    painel=FUNDO_PAINEL,
    texto=TEXTO,
    suave=TEXTO_SUAVE,
    borda=BORDA,
    titulo=AZUL,
    valor=LIMA,
)

PALETA_CLARA = Paleta(
    fundo=FUNDO_CLARO,
    painel=PAINEL_CLARO,
    texto=TEXTO_CLARO,
    suave=SUAVE_CLARO,
    borda=BORDA_CLARA,
    titulo=TEXTO_CLARO,
    valor=TEXTO_CLARO,
)


def paleta_do_modo(modo: ModoTema | str = ModoTema.ESCURO) -> Paleta:
    """Resolve o modo (str tolerante, ex. vindo do JSON); inválido => escuro."""
    if isinstance(modo, ModoTema):
        return PALETA_ESCURA if modo == ModoTema.ESCURO else PALETA_CLARA
    try:
        normalizado = ModoTema(str(modo).strip().upper())
    except ValueError:
        return PALETA_ESCURA
    return PALETA_ESCURA if normalizado == ModoTema.ESCURO else PALETA_CLARA


def modo_de(modo: ModoTema | str = ModoTema.ESCURO) -> ModoTema:
    if isinstance(modo, ModoTema):
        return modo
    try:
        return ModoTema(str(modo).strip().upper())
    except ValueError:
        return ModoTema.ESCURO


def estilo_resultado(liberado: bool | None, modo: ModoTema | str = ModoTema.ESCURO) -> str:
    """Estilo inline p/ rótulos de resultado: LIBERADO verde, NEGADO vermelho.

    No escuro, texto colorido (Fase 4.2, inalterado). No claro, selo colorido
    com tinta escura (texto LIMA/VERMELHO sobre fundo claro não tem contraste).
    """
    if liberado is True:
        if modo_de(modo) == ModoTema.CLARO:
            return (
                f"background-color: {LIMA}; color: {TINTA_SOBRE_ACENTO}; "
                "font-weight: bold; padding: 2px 8px; border-radius: 4px;"
            )
        return f"color: {LIMA}; font-weight: bold;"
    if liberado is False:
        if modo_de(modo) == ModoTema.CLARO:
            return (
                f"background-color: {VERMELHO}; color: {TINTA_SOBRE_ACENTO}; "
                "font-weight: bold; padding: 2px 8px; border-radius: 4px;"
            )
        return f"color: {VERMELHO}; font-weight: bold;"
    paleta = paleta_do_modo(modo)
    return f"color: {paleta.suave};"


def cores_indicador(ok: bool, modo: ModoTema | str = ModoTema.ESCURO) -> tuple[str, str | None]:
    """(texto, fundo|None) p/ indicador Online com contraste nos dois modos."""
    if modo_de(modo) == ModoTema.CLARO:
        return (TINTA_SOBRE_ACENTO, VERDE_FORTE if ok else VERMELHO)
    return (LIMA if ok else VERMELHO, None)


def estilo_paginacao(modo: ModoTema | str = ModoTema.ESCURO) -> str:
    """Texto 'Mostrando X de Y' — suave no escuro, preto legível no claro.

    O cinza do escuro (#9AA7B2) sobre fundo claro tem contraste ~2:1;
    no claro usa a tinta base (#1A1E22, ~13:1 sobre #E8EDF1).
    """
    if modo_de(modo) == ModoTema.CLARO:
        return f"color: {TEXTO_CLARO}; font-size: 11px;"
    return f"color: {TEXTO_SUAVE}; font-size: 11px;"


def estilo_selo(modo: ModoTema | str = ModoTema.ESCURO) -> str:
    """Selo FECHADO: texto com borda no escuro, selo preenchido no claro."""
    if modo_de(modo) == ModoTema.CLARO:
        return (
            f"background-color: {VERMELHO}; color: {TINTA_SOBRE_ACENTO}; "
            "font-weight: bold; border-radius: 6px; padding: 2px 8px;"
        )
    return (
        f"color: {VERMELHO}; font-weight: bold; "
        f"border: 2px solid {VERMELHO}; border-radius: 6px; padding: 2px 8px;"
    )


def _luminancia(hex_cor: str) -> float:
    """Luminância relativa WCAG de cor #RRGGBB."""
    h = hex_cor.strip().lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    def linear(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)


def contraste(frente: str, fundo: str) -> float:
    """Razão de contraste WCAG entre duas cores #RRGGBB (1 a 21)."""
    l1 = _luminancia(frente)
    l2 = _luminancia(fundo)
    claro, escuro = (l1, l2) if l1 >= l2 else (l2, l1)
    return (claro + 0.05) / (escuro + 0.05)


_ICONE_CACHE: dict[int, object] = {}  # type: ignore[no-untyped-def]


def _tint_icon(icon, color_hex: str):  # type: ignore[no-untyped-def]
    """Tint QIcon para cor_hex (usado para ícones pretos destacados) — via QImage alpha."""
    try:
        from PySide6.QtGui import QColor, QIcon, QImage, QPixmap

        sizes = icon.availableSizes() or [icon.pixmap(32, 32).size()]
        tinted = QIcon()
        target = QColor(color_hex)
        for sz in sizes:
            pix = icon.pixmap(sz)
            if pix.isNull():
                continue
            img = pix.toImage().convertToFormat(QImage.Format.Format_ARGB32)
            for y in range(img.height()):
                for x in range(img.width()):
                    c = img.pixelColor(x, y)
                    if c.alpha() == 0:
                        continue
                    c.setRed(target.red())
                    c.setGreen(target.green())
                    c.setBlue(target.blue())
                    img.setPixelColor(x, y, c)
            out = QPixmap.fromImage(img)
            tinted.addPixmap(out)
        return tinted if not tinted.isNull() else icon
    except Exception:
        return icon


def icone_preto(style, standard_pixmap):  # type: ignore[no-untyped-def]
    """Retorna ícone padrão tintado de preto (#0F1113) para destaque (com cache)."""
    try:
        key = int(standard_pixmap) if hasattr(standard_pixmap, "__int__") else hash(str(standard_pixmap))  # noqa: E501
        if key in _ICONE_CACHE:
            return _ICONE_CACHE[key]  # type: ignore[no-any-return]
        base = style.standardIcon(standard_pixmap)
        tinted = _tint_icon(base, TINTA_SOBRE_ACENTO)
        _ICONE_CACHE[key] = tinted
        return tinted
    except Exception:
        try:
            return style.standardIcon(standard_pixmap)
        except Exception:
            from PySide6.QtGui import QIcon

            return QIcon()


def icone_vermelho(style, standard_pixmap):  # type: ignore[no-untyped-def]
    """Retorna ícone padrão tintado de vermelho (VERMELHO) para destaque."""
    try:
        base = style.standardIcon(standard_pixmap)
        return _tint_icon(base, VERMELHO)
    except Exception:
        try:
            return style.standardIcon(standard_pixmap)
        except Exception:
            from PySide6.QtGui import QIcon

            return QIcon()


def stylesheet(modo: ModoTema | str = ModoTema.ESCURO) -> str:
    """QSS da academia aplicado na QApplication (todas as abas)."""
    paleta = paleta_do_modo(modo)
    fundo = paleta.fundo
    painel = paleta.painel
    texto = paleta.texto
    suave = paleta.suave
    borda = paleta.borda
    titulo = paleta.titulo
    valor = paleta.valor
    is_claro = modo_de(modo) == ModoTema.CLARO
    # Fase 4.10-A: aba selecionada com ícone/texto em AZUL no claro
    cor_selecionada = AZUL if is_claro else titulo
    # sombra leve só no claro (QSS não tem box-shadow; simula com borda + fundo)
    sombra_clara = (
        "\nQGroupBox, QTableWidget, QListWidget, QFrame#PlanoCard {"
        "\n    border: 1px solid #C8D0D8;"
        "\n}"
        if is_claro
        else ""
    )
    # Header em modo claro: fundo preto + texto branco para destaque (antes apagado #E8EDF1/#5A6B78)
    header_claro = (
        "\nQTabWidget::pane { background-color: #0F1113; border: 1px solid #0F1113; }"
        "\nQTabBar { background-color: #0F1113; }"
        "\nQTabBar::tab { background-color: #0F1113; color: #F2F5F7; }"
        "\nQTabBar::tab:selected { background-color: #0F1113; color: #5AC8FA; border-bottom: 2px solid #5AC8FA; }"  # noqa: E501
        if is_claro
        else ""
    )
    return f"""
QMainWindow, QWidget {{
    background-color: {fundo};
    color: {texto};
    font-size: 13px;
}}
QGroupBox {{
    background-color: {painel};
    border: 1px solid {borda};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: {titulo};
}}
QLabel {{
    background-color: transparent;
}}
QGroupBox QLabel {{
    background-color: transparent;
}}
QCheckBox {{
    background-color: transparent;
}}
QGroupBox QCheckBox {{
    background-color: transparent;
}}
QTabWidget::pane {{
    border: 1px solid {borda};
    border-radius: 8px;
    background-color: {fundo};
}}
QTabBar::tab {{
    background-color: {painel};
    color: {suave};
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{
    background-color: {fundo};
    color: {cor_selecionada};
    font-weight: bold;
    border-bottom: 2px solid {AZUL};
}}{sombra_clara}{header_claro}
QPushButton {{
    background-color: {AZUL};
    color: {TINTA_SOBRE_ACENTO};
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {AZUL_ESCURO};
}}
QPushButton:pressed {{
    background-color: {AZUL_ESCURO};
    padding-top: 9px;
}}
QPushButton:disabled {{
    background-color: {borda};
    color: {suave};
}}
QLineEdit, QDateEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {painel};
    color: {texto};
    border: 1px solid {borda};
    border-radius: 6px;
    padding: 6px;
    selection-background-color: {AZUL};
    selection-color: {TINTA_SOBRE_ACENTO};
}}
QLineEdit:focus, QComboBox:focus {{
    border: 1px solid {AZUL};
}}
QComboBox QAbstractItemView {{
    background-color: {painel};
    color: {texto};
    selection-background-color: {AZUL};
    selection-color: {TINTA_SOBRE_ACENTO};
}}
QTableWidget {{
    background-color: {painel};
    alternate-background-color: {fundo};
    gridline-color: {borda};
    border: 1px solid {borda};
    border-radius: 6px;
    selection-background-color: {AZUL};
    selection-color: {TINTA_SOBRE_ACENTO};
}}
QTableWidget::item:selected {{
    background-color: {AZUL};
    color: {TINTA_SOBRE_ACENTO};
}}
QHeaderView::section {{
    background-color: {painel};
    color: {titulo};
    border: none;
    padding: 6px;
    font-weight: bold;
}}
QListWidget {{
    background-color: {painel};
    border: 1px solid {borda};
    border-radius: 6px;
    selection-background-color: {LIMA};
    selection-color: {TINTA_SOBRE_ACENTO};
}}
QListWidget::item:selected {{
    background-color: {LIMA};
    color: {TINTA_SOBRE_ACENTO};
}}
QCheckBox {{
    color: {texto};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {borda};
    border-radius: 4px;
    background-color: {painel};
}}
QCheckBox::indicator:checked {{
    background-color: {AZUL};
    border: 1px solid {AZUL};
}}
QCheckBox::indicator:unchecked:disabled {{
    background-color: {fundo};
    border: 1px solid {borda};
}}
QScrollBar:vertical {{
    border: none;
    background: {fundo};
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {suave};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {AZUL};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
}}
QScrollBar:horizontal {{
    border: none;
    background: {fundo};
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {suave};
    border-radius: 5px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {AZUL};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    background: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}
QDialog {{
    background-color: {fundo};
}}
QFrame#PlanoCard {{
    background-color: {painel};
    border: 1px solid {borda};
    border-left: 4px solid {LIMA};
    border-radius: 8px;
}}
QFrame#PlanoCard QLabel#PlanoNome {{
    color: {titulo};
    font-size: 15px;
    font-weight: bold;
}}
QFrame#PlanoCard QLabel#PlanoValor {{
    color: {valor};
    font-size: 14px;
    font-weight: bold;
}}
"""
