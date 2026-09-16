"""Aba Frequência — presença global com filtros dia/mês/aluno (antifraude)."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, QStringListModel, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QListView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gymflux.ui.theme import ModoTema, estilo_paginacao
from gymflux.ui.viewmodels.frequencia import FrequenciaViewModel


class FrequenciaView(QWidget):
    COLUNAS = ("Data/Hora", "Pessoa", "Direção", "Resultado", "Motivo")

    def __init__(self, vm: FrequenciaViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.vm = vm
        layout = QVBoxLayout(self)

        filtros = QHBoxLayout()
        filtros.addWidget(QLabel("Aluno:"))
        self.cmb_aluno = QComboBox()
        self.cmb_aluno.setEditable(True)
        self.cmb_aluno.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_aluno.setMaxVisibleItems(12)
        # QCompleter + QListView + paginação 50 para 500+
        self._completer = QCompleter(self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer_model = QStringListModel(self)
        self._completer.setModel(self._completer_model)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.cmb_aluno.setCompleter(self._completer)
        self.cmb_aluno.setView(QListView())
        filtros.addWidget(self.cmb_aluno, 2)
        filtros.addWidget(QLabel("Mês:"))
        self.cmb_mes = QComboBox()
        filtros.addWidget(self.cmb_mes, 1)
        self.chk_dia = QCheckBox("Dia:")
        self.chk_dia.setChecked(True)
        self.dat_dia = QDateEdit(QDate.currentDate())
        self.dat_dia.setCalendarPopup(True)
        self.dat_dia.setDisplayFormat("dd/MM/yyyy")
        filtros.addWidget(self.chk_dia)
        filtros.addWidget(self.dat_dia)
        filtros.addStretch(1)
        layout.addLayout(filtros)

        self.lbl_total = QLabel("")
        layout.addWidget(self.lbl_total)

        self.tbl = QTableWidget(0, len(self.COLUNAS))
        self.tbl.setHorizontalHeaderLabels(list(self.COLUNAS))
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tbl, 1)
        # paginação 500 por vez para testes com 7k
        self._page_size = 500
        self._filtered: list = []
        self._rendered = 500
        self.lbl_paginacao = QLabel("")
        self.lbl_paginacao.setStyleSheet(estilo_paginacao(self._tema_atual()))
        self.lbl_paginacao.setVisible(False)
        layout.addWidget(self.lbl_paginacao)
        self.tbl.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.cmb_aluno.currentIndexChanged.connect(lambda _i: self.recarregar())
        self.cmb_aluno.editTextChanged.connect(self._filtrar_alunos)
        self.cmb_mes.currentIndexChanged.connect(lambda _i: self.recarregar())
        self.chk_dia.toggled.connect(self._on_chk_dia)
        self.dat_dia.dateChanged.connect(lambda _d: self.recarregar())
        self.recarregar()

    @staticmethod
    def _tema_atual():  # type: ignore[no-untyped-def]
        """Detecta claro/escuro via stylesheet global (VM não carrega UiConfig)."""
        tema = ModoTema.ESCURO
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            ss = ""
            if isinstance(app, QApplication):
                ss = app.styleSheet()
            if "#E8EDF1" in ss:
                tema = ModoTema.CLARO
        except Exception:
            pass
        return tema

    def sincronizar_tema(self, tema=None) -> None:  # type: ignore[no-untyped-def]
        """Atualiza paginação sem recarregar (troca de tema sem restart)."""
        self.lbl_paginacao.setStyleSheet(estilo_paginacao(tema or self._tema_atual()))

    def _on_chk_dia(self, checked: bool) -> None:
        self.dat_dia.setEnabled(checked)
        self.recarregar()

    def _filtrar_alunos(self, texto: str) -> None:
        # paginação: mostra até 100 que contêm texto (7k total, evita travar QComboBox)
        if not hasattr(self, "_todos_alunos_cache"):
            return
        txt = texto.strip().lower()
        filtrados = (
            [a.nome for a in self._todos_alunos_cache if txt in a.nome.lower()]
            if txt
            else [a.nome for a in self._todos_alunos_cache]
        )
        exib = filtrados[:100]
        self._completer_model.setStringList(exib)
        # mantém popup se filtrado
        if txt and exib:
            self._completer.complete()

    # -- helpers ---------------------------------------------------------------
    @staticmethod
    def _qdate_para_date(qd: QDate) -> date:
        return date(qd.year(), qd.month(), qd.day())

    def _recarregar_combos(self) -> None:
        aluno_atual = self.cmb_aluno.currentData()
        texto_atual = self.cmb_aluno.currentText()
        self._todos_alunos_cache = self.vm.listar_alunos()
        self.cmb_aluno.blockSignals(True)
        try:
            self.cmb_aluno.clear()
            self.cmb_aluno.addItem("Todos", None)
            # paginação 100 visíveis (todos em cache 7k, evita travar dropdown)
            for a in self._todos_alunos_cache[:100]:
                self.cmb_aluno.addItem(a.nome, a.id)
            self._completer_model.setStringList([a.nome for a in self._todos_alunos_cache[:100]])
            if aluno_atual is not None:
                idx = self.cmb_aluno.findData(aluno_atual)
                if idx >= 0:
                    self.cmb_aluno.setCurrentIndex(idx)
                else:
                    # aluno não na primeira página, adiciona
                    for a in self._todos_alunos_cache:
                        if a.id == aluno_atual:
                            self.cmb_aluno.addItem(a.nome, a.id)
                            self.cmb_aluno.setCurrentIndex(self.cmb_aluno.findData(aluno_atual))
                            break
            elif texto_atual and texto_atual != "Todos":
                self.cmb_aluno.setEditText(texto_atual)
        finally:
            self.cmb_aluno.blockSignals(False)

        mes_atual = self.cmb_mes.currentData()
        self.cmb_mes.blockSignals(True)
        try:
            self.cmb_mes.clear()
            self.cmb_mes.addItem("Todos", None)
            for m in self.vm.meses_disponiveis():
                try:
                    y, mo = m.split("-")
                    label = f"{mo}/{y}"
                except Exception:
                    label = m
                self.cmb_mes.addItem(label, m)
            if mes_atual is not None:
                idx = self.cmb_mes.findData(mes_atual)
                if idx >= 0:
                    self.cmb_mes.setCurrentIndex(idx)
        finally:
            self.cmb_mes.blockSignals(False)

    def recarregar(self) -> None:
        self._recarregar_combos()
        aluno_id = self.cmb_aluno.currentData()
        mes = self.cmb_mes.currentData()
        dia = self._qdate_para_date(self.dat_dia.date()) if self.chk_dia.isChecked() else None
        linhas = self.vm.filtrar(
            dia=dia,
            mes=str(mes) if mes is not None else None,
            aluno_id=str(aluno_id) if aluno_id is not None else None,
        )
        self._filtered = list(reversed(linhas))
        self.lbl_total.setText(f"{len(self._filtered)} registro(s)")
        self.lbl_paginacao.setStyleSheet(estilo_paginacao(self._tema_atual()))
        self._rendered = min(self._page_size, len(self._filtered))
        self._render_tabela()
        if len(self._filtered) > self._page_size:
            self.lbl_paginacao.setText(
                f"Mostrando {self._rendered} de {len(self._filtered)} — role até o final para carregar mais"
            )
            self.lbl_paginacao.setVisible(True)
        else:
            self.lbl_paginacao.setVisible(False)

    def _render_tabela(self) -> None:
        self.tbl.setRowCount(self._rendered)
        for row in range(self._rendered):
            t = self._filtered[row]
            vals = (
                t.timestamp.strftime("%d/%m %H:%M:%S"),
                self.vm.nome_tentativa(t),
                str(t.direcao),
                str(t.resultado),
                str(t.motivo or "—"),
            )
            for col, v in enumerate(vals):
                self.tbl.setItem(row, col, QTableWidgetItem(v))

    def _on_scroll(self, value: int) -> None:
        bar = self.tbl.verticalScrollBar()
        if bar.maximum() == 0:
            return
        if value < bar.maximum() * 0.9:
            return
        if self._rendered >= len(self._filtered):
            return
        novo = min(self._rendered + self._page_size, len(self._filtered))
        # adiciona incrementalmente
        self.tbl.setRowCount(novo)
        for row in range(self._rendered, novo):
            t = self._filtered[row]
            vals = (
                t.timestamp.strftime("%d/%m %H:%M:%S"),
                self.vm.nome_tentativa(t),
                str(t.direcao),
                str(t.resultado),
                str(t.motivo or "—"),
            )
            for col, v in enumerate(vals):
                self.tbl.setItem(row, col, QTableWidgetItem(v))
        self._rendered = novo
        if len(self._filtered) > self._page_size:
            self.lbl_paginacao.setText(
                f"Mostrando {self._rendered} de {len(self._filtered)} — role até o final para carregar mais"
            )
            self.lbl_paginacao.setVisible(self._rendered < len(self._filtered))
        else:
            self.lbl_paginacao.setVisible(False)
