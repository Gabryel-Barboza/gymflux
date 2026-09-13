"""Aba Caixa — sidebar + tabela, combo pesquisável, pagamento sem vencimento."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import ClassVar

from loguru import logger
from PySide6.QtCore import QStringListModel, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gymflux.core.pagamento import FormaPagamento
from gymflux.ui.theme import AZUL, LIMA, VERMELHO, estilo_selo
from gymflux.ui.viewmodels.caixa import CaixaViewModel


class NovoPagamentoDialog(QDialog):
    """Modal sem vencimento (vencimento edita-se no perfil)."""

    FORMAS: ClassVar[list[str]] = ["—", *[f.value for f in FormaPagamento]]

    def __init__(self, aluno_nome: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Novo pagamento — {aluno_nome}")
        self.setMaximumWidth(420)
        form = QFormLayout(self)
        self.spn_valor = QDoubleSpinBox()
        self.spn_valor.setRange(0.01, 100000.0)
        self.spn_valor.setDecimals(2)
        self.spn_valor.setValue(99.90)
        self.cmb_forma = QComboBox()
        self.cmb_forma.addItems(self.FORMAS)
        self.chk_pago = QCheckBox("Pago hoje")
        self.chk_pago.setChecked(True)
        self.edt_comp = QLineEdit()
        self.edt_comp.setPlaceholderText("AAAA-MM (opcional)")
        form.addRow("Valor (R$)*:", self.spn_valor)
        form.addRow("Forma:", self.cmb_forma)
        form.addRow(self.chk_pago)
        form.addRow("Competência:", self.edt_comp)
        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        form.addRow(botoes)
        # compat: mantém dat_venc para código legado que chama .vencimento()
        # mas não exibe; vencimento será hoje ou derivado da competência
        self._vencimento_default = date.today()

    def forma(self) -> str | None:
        v = self.cmb_forma.currentText()
        return None if v == "—" else v

    def vencimento(self) -> date:
        # sem campo: usa hoje; se competência informada, usa 1º dia do mês
        comp = self.edt_comp.text().strip()
        if comp:
            try:
                y, m = comp.split("-")
                return date(int(y), int(m), 10)
            except Exception:
                pass
        return self._vencimento_default


class CaixaView(QWidget):
    COLUNAS = ("Aluno", "Valor (R$)", "Vencimento", "Situação", "Forma", "Competência")

    def __init__(self, vm: CaixaViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.vm = vm
        layout = QHBoxLayout(self)

        # -- sidebar esquerda --------------------------------------------------
        sidebar = QVBoxLayout()
        sidebar.setContentsMargins(0, 0, 0, 0)
        self.cmb_mes = QComboBox()
        self.lbl_fechado = QLabel("FECHADO")
        self.lbl_fechado.setStyleSheet(estilo_selo(self.vm.ui_config.tema))
        self.lbl_fechado.setVisible(False)
        sidebar.addWidget(QLabel("Mês:"))
        sidebar.addWidget(self.cmb_mes)
        sidebar.addWidget(self.lbl_fechado)
        # stats coloridas sem data
        self.lbl_recebido = QLabel("Recebido: R$ 0.00")
        self.lbl_recebido.setStyleSheet(f"color: {LIMA}; font-weight: bold;")
        self.lbl_pendente = QLabel("Pendente: R$ 0.00")
        self.lbl_pendente.setStyleSheet(f"color: {VERMELHO}; font-weight: bold;")
        self.lbl_total = QLabel("Total: R$ 0.00")
        self.lbl_total.setStyleSheet(f"color: {AZUL}; font-weight: bold;")
        # compat: lbl_totais agregado (testes leem lbl_totais)
        self.lbl_totais = QLabel("")
        self.lbl_totais.setVisible(False)
        sidebar.addWidget(self.lbl_recebido)
        sidebar.addWidget(self.lbl_pendente)
        sidebar.addWidget(self.lbl_total)
        sidebar.addWidget(self.lbl_totais)
        self.btn_fechar = QPushButton("Fechar caixa do mês")
        sidebar.addWidget(self.btn_fechar)
        sidebar.addStretch(1)
        side_widget = QWidget()
        side_widget.setLayout(sidebar)
        side_widget.setMaximumWidth(220)
        layout.addWidget(side_widget)

        # -- área principal ----------------------------------------------------
        principal = QVBoxLayout()
        self.tbl = QTableWidget(0, len(self.COLUNAS))
        self.tbl.setHorizontalHeaderLabels(list(self.COLUNAS))
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        principal.addWidget(self.tbl, 1)

        hbtn = QHBoxLayout()
        hbtn.addWidget(QLabel("Aluno:"))
        self.cmb_aluno = QComboBox()
        self.cmb_aluno.setEditable(True)
        self.cmb_aluno.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_aluno.setMaxVisibleItems(12)
        # filtro para 500+ alunos via QCompleter
        self._completer = QCompleter(self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer_model = QStringListModel(self)
        self._completer.setModel(self._completer_model)
        self.cmb_aluno.setCompleter(self._completer)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.btn_novo = QPushButton("Novo pagamento")
        hbtn.addWidget(self.cmb_aluno, 2)
        hbtn.addWidget(self.btn_novo)
        hbtn.addStretch(1)
        principal.addLayout(hbtn)

        layout.addLayout(principal, 1)

        # compat: mantém table de combo recarga etc
        self.cmb_mes.currentIndexChanged.connect(lambda _i: self.recarregar())
        self.cmb_aluno.editTextChanged.connect(self._filtrar_alunos)
        self.btn_novo.clicked.connect(self._novo)
        self.btn_fechar.clicked.connect(self._fechar)
        self.recarregar()

    def _filtrar_alunos(self, texto: str) -> None:
        # o completer já filtra; apenas garante scroll
        pass

    # -- helpers ---------------------------------------------------------------
    def _mes_atual(self) -> str | None:
        mes = self.cmb_mes.currentData()
        return str(mes) if mes is not None else None

    def _recarregar_combos(self) -> None:
        mes_atual = self._mes_atual()
        meses = self.vm.meses_disponiveis()
        if not meses:
            meses = [date.today().strftime("%Y-%m")]
        self.cmb_mes.blockSignals(True)
        try:
            self.cmb_mes.clear()
            self.cmb_mes.addItem("Todos", None)
            for m in meses:
                self.cmb_mes.addItem(m, m)
            if mes_atual is not None:
                idx = self.cmb_mes.findData(mes_atual)
                if idx >= 0:
                    self.cmb_mes.setCurrentIndex(idx)
        finally:
            self.cmb_mes.blockSignals(False)

        aluno_atual = self.cmb_aluno.currentData()
        texto_atual = self.cmb_aluno.currentText()
        self.cmb_aluno.blockSignals(True)
        try:
            self.cmb_aluno.clear()
            nomes = []
            for a in self.vm.listar_alunos():
                self.cmb_aluno.addItem(a.nome, a.id)
                nomes.append(a.nome)
            self._completer_model.setStringList(nomes)
            if aluno_atual is not None:
                idx = self.cmb_aluno.findData(aluno_atual)
                if idx >= 0:
                    self.cmb_aluno.setCurrentIndex(idx)
            elif texto_atual:
                self.cmb_aluno.setEditText(texto_atual)
        finally:
            self.cmb_aluno.blockSignals(False)

    def recarregar(self) -> None:
        self._recarregar_combos()
        mes = self._mes_atual()
        hoje = date.today()
        recebido, pendente, total = self.vm.totais_mes(mes)
        # sem data no texto (stats coloridas)
        self.lbl_recebido.setText(f"Recebido: R$ {recebido:.2f}")
        self.lbl_pendente.setText(f"Pendente: R$ {pendente:.2f}")
        self.lbl_total.setText(f"Total: R$ {total:.2f}")
        # compat lbl_totais
        rotulo = mes or "geral"
        self.lbl_totais.setText(
            f"{rotulo} — Recebido R$ {recebido:.2f} · "
            f"Pendente R$ {pendente:.2f} · Total R$ {total:.2f}"
        )
        fechado = mes is not None and self.vm.mes_fechado(mes)
        self.lbl_fechado.setStyleSheet(estilo_selo(self.vm.ui_config.tema))
        self.lbl_fechado.setVisible(fechado)

        linhas = self.vm.por_mes(mes)
        self.tbl.setRowCount(len(linhas))
        for row, (p, nome) in enumerate(linhas):
            if p.pago:
                sit = "PAGO"
            elif p.dias_atraso(hoje) > 0:
                sit = f"ATRASADO {p.dias_atraso(hoje)}d"
            else:
                sit = "PENDENTE"
            vals = (
                nome,
                f"{Decimal(str(p.valor)):.2f}",
                p.data_vencimento.isoformat(),
                sit,
                str(p.forma) if p.forma else "—",
                p.competencia or "—",
            )
            for col, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if not p.pago and p.dias_atraso(hoje) > 0:
                    item.setBackground(QColor("#ffe0e0"))
                self.tbl.setItem(row, col, item)

    # -- ações -------------------------------------------------------------------
    def _novo(self) -> None:
        aluno_id = self.cmb_aluno.currentData()
        # se editável e texto não casou, tenta resolver por nome
        if aluno_id is None:
            texto = self.cmb_aluno.currentText().strip()
            for a in self.vm.listar_alunos():
                if a.nome.lower() == texto.lower():
                    aluno_id = a.id
                    break
        if aluno_id is None:
            QMessageBox.information(self, "Caixa", "Cadastre um aluno primeiro.")
            return
        nome = self.cmb_aluno.currentText() or str(aluno_id)
        dlg = NovoPagamentoDialog(nome, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            pag = self.vm.registrar(
                aluno_id=str(aluno_id),
                valor=Decimal(str(dlg.spn_valor.value())),
                data_vencimento=dlg.vencimento(),
                forma=dlg.forma(),
                pago=dlg.chk_pago.isChecked(),
                competencia=dlg.edt_comp.text(),
            )
        except ValueError as e:
            QMessageBox.warning(self, "Caixa", str(e))
            return
        logger.info(f"[UI] pagamento registrado id={pag.id}")
        self.recarregar()

    def _fechar(self) -> None:
        mes = self._mes_atual()
        if mes is None:
            QMessageBox.information(self, "Caixa", "Selecione um mês para fechar.")
            return
        if self.vm.mes_fechado(mes):
            QMessageBox.information(self, "Caixa", f"Caixa de {mes} já está fechado.")
            return
        confirma = QMessageBox.question(
            self,
            "Caixa",
            f"Fechar o caixa de {mes}? Novos registros no mês serão bloqueados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirma != QMessageBox.StandardButton.Yes:
            return
        fechamento = self.vm.fechar_mes(mes)
        logger.info(f"[UI] caixa {mes} fechado total={fechamento.total}")
        QMessageBox.information(
            self, "Caixa", f"Caixa de {mes} fechado (R$ {fechamento.total:.2f})."
        )
        self.recarregar()
