"""Identidade visual GymFlow — paleta aprovada + QSS dark (Qt-free, só strings)."""

from __future__ import annotations

AZUL = "#5AC8FA"  # primária / botões
FUNDO = "#0F1113"  # fundo
LIMA = "#A3D65C"  # liberado / ok
VERMELHO = "#E57373"  # negado / erro
TEXTO = "#F2F5F7"  # texto

FUNDO_PAINEL = "#1A1E22"  # groupbox / inputs / headers
BORDA = "#2A3138"  # bordas e separadores
TEXTO_SUAVE = "#9AA7B2"  # placeholders e mensagens neutras
AZUL_ESCURO = "#3A9BC4"  # hover/pressed dos botões


def estilo_resultado(liberado: bool | None) -> str:
    """Estilo inline p/ rótulos de resultado: LIBERADO verde, NEGADO vermelho."""
    if liberado is True:
        return f"color: {LIMA}; font-weight: bold;"
    if liberado is False:
        return f"color: {VERMELHO}; font-weight: bold;"
    return f"color: {TEXTO_SUAVE};"


def stylesheet() -> str:
    """QSS dark da academia aplicado na QApplication (as 4 abas)."""
    return f"""
QMainWindow, QWidget {{
    background-color: {FUNDO};
    color: {TEXTO};
    font-size: 13px;
}}
QGroupBox {{
    background-color: {FUNDO_PAINEL};
    border: 1px solid {BORDA};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: {AZUL};
}}
QTabWidget::pane {{
    border: 1px solid {BORDA};
    border-radius: 6px;
    background-color: {FUNDO};
}}
QTabBar::tab {{
    background-color: {FUNDO_PAINEL};
    color: {TEXTO_SUAVE};
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{
    background-color: {FUNDO};
    color: {AZUL};
    font-weight: bold;
}}
QPushButton {{
    background-color: {AZUL};
    color: {FUNDO};
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
    background-color: {BORDA};
    color: {TEXTO_SUAVE};
}}
QLineEdit, QDateEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {FUNDO_PAINEL};
    color: {TEXTO};
    border: 1px solid {BORDA};
    border-radius: 6px;
    padding: 6px;
    selection-background-color: {AZUL};
}}
QLineEdit:focus, QComboBox:focus {{
    border: 1px solid {AZUL};
}}
QComboBox QAbstractItemView {{
    background-color: {FUNDO_PAINEL};
    color: {TEXTO};
    selection-background-color: {AZUL};
}}
QTableWidget {{
    background-color: {FUNDO_PAINEL};
    alternate-background-color: {FUNDO};
    gridline-color: {BORDA};
    border: 1px solid {BORDA};
    border-radius: 6px;
}}
QTableWidget::item:selected {{
    background-color: {AZUL};
    color: {FUNDO};
}}
QHeaderView::section {{
    background-color: {FUNDO_PAINEL};
    color: {AZUL};
    border: none;
    padding: 6px;
    font-weight: bold;
}}
QListWidget {{
    background-color: {FUNDO_PAINEL};
    border: 1px solid {BORDA};
    border-radius: 6px;
}}
QListWidget::item:selected {{
    background-color: {LIMA};
    color: {FUNDO};
}}
QCheckBox {{
    color: {TEXTO};
    spacing: 6px;
}}
QDialog {{
    background-color: {FUNDO};
}}
QFrame#PlanoCard {{
    background-color: {FUNDO_PAINEL};
    border: 1px solid {BORDA};
    border-radius: 8px;
}}
QFrame#PlanoCard QLabel#PlanoNome {{
    color: {AZUL};
    font-size: 15px;
    font-weight: bold;
}}
QFrame#PlanoCard QLabel#PlanoValor {{
    color: {LIMA};
    font-size: 14px;
    font-weight: bold;
}}
"""
