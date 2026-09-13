"""Tela de planos — cards em grade + dialog em grade."""

from __future__ import annotations

from decimal import Decimal

from loguru import logger
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gymflux.core.plano import Plano, TipoPlano
from gymflux.ui.viewmodels.planos import DURACAO_POR_TIPO, PlanosViewModel


class NovoPlanoDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, titulo: str = "Novo plano") -> None:
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMaximumWidth(520)
        layout = QVBoxLayout(self)
        grid = QGridLayout()
        self.edt_nome = QLineEdit()
        self.cmb_tipo = QComboBox()
        for t in TipoPlano:
            self.cmb_tipo.addItem(t.value, t)
        self.spn_valor = QDoubleSpinBox()
        self.spn_valor.setRange(0.0, 100000.0)
        self.spn_valor.setDecimals(2)
        self.spn_valor.setValue(99.90)
        self.spn_tol = QSpinBox()
        self.spn_tol.setRange(0, 90)
        self.spn_tol.setValue(3)
        self.spn_dur = QSpinBox()
        self.spn_dur.setRange(1, 3650)
        self.spn_dur.setValue(30)
        # grade 2x2
        grid.addWidget(QLabel("Nome*:"), 0, 0)
        grid.addWidget(self.edt_nome, 0, 1)
        grid.addWidget(QLabel("Tipo:"), 0, 2)
        grid.addWidget(self.cmb_tipo, 0, 3)
        grid.addWidget(QLabel("Valor (R$):"), 1, 0)
        grid.addWidget(self.spn_valor, 1, 1)
        grid.addWidget(QLabel("Tolerância (dias):"), 1, 2)
        grid.addWidget(self.spn_tol, 1, 3)
        self.lbl_dur = QLabel("Duração (dias):")
        grid.addWidget(self.lbl_dur, 2, 0)
        grid.addWidget(self.spn_dur, 2, 1)
        layout.addLayout(grid)
        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)
        self.cmb_tipo.currentIndexChanged.connect(self._tipo_mudou)
        self._tipo_mudou(0)

    def _tipo_mudou(self, _i: int) -> None:
        tipo = self.cmb_tipo.currentData()
        is_personalizado = tipo == TipoPlano.PERSONALIZADO
        self.lbl_dur.setVisible(is_personalizado)
        self.spn_dur.setVisible(is_personalizado)
        if not is_personalizado and isinstance(tipo, TipoPlano) and tipo in DURACAO_POR_TIPO:
            self.spn_dur.setValue(DURACAO_POR_TIPO[tipo])

    def preencher(self, plano: Plano) -> None:
        self.edt_nome.setText(plano.nome)
        idx = self.cmb_tipo.findData(plano.tipo)
        if idx >= 0:
            self.cmb_tipo.setCurrentIndex(idx)
        self.spn_valor.setValue(float(plano.valor))
        self.spn_tol.setValue(plano.tolerancia_dias)
        self.spn_dur.setValue(plano.duracao_dias)


class PlanosView(QWidget):
    """Cards em grade (2 colunas) + Editar/Excluir."""

    def __init__(self, vm: PlanosViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.vm = vm
        layout = QVBoxLayout(self)

        hbtn = QHBoxLayout()
        self.btn_novo = QPushButton("Novo plano")
        hbtn.addWidget(self.btn_novo)
        hbtn.addStretch(1)
        layout.addLayout(hbtn)

        self.area = QScrollArea()
        self.area.setWidgetResizable(True)
        self.cards_host = QWidget()
        self.cards_layout = QGridLayout(self.cards_host)
        self.cards_layout.setSpacing(8)
        # sem stretch aqui; grid ocupa espaço
        self.area.setWidget(self.cards_host)
        layout.addWidget(self.area, 1)

        self.btn_novo.clicked.connect(self._novo)
        self.recarregar()

    def _limpar_cards(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.deleteLater()

    def recarregar(self) -> None:
        self._limpar_cards()
        planos = self.vm.listar()
        self.cards: list[tuple[str, QFrame]] = []
        for idx, plano in enumerate(planos):
            card = self._montar_card(plano)
            card.setMinimumHeight(90)
            card.setMaximumWidth(340)
            # 2 colunas compactas
            row, col = divmod(idx, 2)
            self.cards_layout.addWidget(card, row, col)
            self.cards.append((plano.id, card))
        if not planos:
            vazio = QLabel("Nenhum plano cadastrado.")
            self.cards_layout.addWidget(vazio, 0, 0, 1, 2)

    def _montar_card(self, plano: Plano) -> QFrame:
        card = QFrame()
        card.setObjectName("PlanoCard")
        card.setMaximumWidth(320)
        lay = QVBoxLayout(card)
        nome = QLabel(plano.nome)
        nome.setObjectName("PlanoNome")
        lay.addWidget(nome)
        valor = QLabel(f"R$ {Decimal(str(plano.valor)):.2f}")
        valor.setObjectName("PlanoValor")
        lay.addWidget(valor)
        lay.addWidget(QLabel(f"Tipo: {plano.tipo}"))
        lay.addWidget(QLabel(f"Duração: {plano.duracao_dias} dias"))
        lay.addWidget(QLabel(f"Tolerância: {plano.tolerancia_dias} dias"))
        hb = QHBoxLayout()
        btn_editar = QPushButton("Editar")
        btn_excluir = QPushButton("Excluir")
        btn_editar.clicked.connect(lambda _c=False, pid=plano.id: self._editar(pid))
        btn_excluir.clicked.connect(
            lambda _c=False, pid=plano.id, n=plano.nome: self._excluir(pid, n)
        )
        hb.addWidget(btn_editar)
        hb.addWidget(btn_excluir)
        hb.addStretch(1)
        lay.addLayout(hb)
        return card

    def _coletar(self, dlg: NovoPlanoDialog, plano_id: str | None = None) -> Plano | None:
        if not dlg.edt_nome.text().strip():
            QMessageBox.warning(self, "Planos", "Nome é obrigatório.")
            return None
        try:
            return self.vm.salvar(
                nome=dlg.edt_nome.text(),
                tipo=dlg.cmb_tipo.currentData(),
                valor=Decimal(str(dlg.spn_valor.value())),
                tolerancia_dias=dlg.spn_tol.value(),
                duracao_dias=dlg.spn_dur.value(),
                plano_id=plano_id,
            )
        except ValueError as e:
            QMessageBox.warning(self, "Planos", str(e))
            return None

    def _novo(self) -> None:
        dlg = NovoPlanoDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        plano = self._coletar(dlg)
        if plano is None:
            return
        logger.info(f"[UI] plano salvo id={plano.id}")
        self.recarregar()

    def _editar(self, plano_id: str) -> None:
        plano = self.vm.repo.buscar_por_id(plano_id)
        if plano is None:
            QMessageBox.warning(self, "Planos", "Plano não encontrado.")
            return
        dlg = NovoPlanoDialog(self, titulo=f"Editar plano — {plano.nome}")
        dlg.preencher(plano)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if self._coletar(dlg, plano_id=plano_id) is None:
            return
        logger.info(f"[UI] plano editado id={plano_id}")
        self.recarregar()

    def _excluir(self, plano_id: str, nome: str) -> None:
        confirma = QMessageBox.question(
            self, "Planos", f"Remover o plano '{nome}'?", QMessageBox.StandardButton.Yes
        )
        if confirma != QMessageBox.StandardButton.Yes:
            return
        self.vm.remover(plano_id)
        self.recarregar()
