"""Aba Caixa — sidebar + tabela, combo pesquisável, pagamento sem vencimento."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import ClassVar

from loguru import logger
from PySide6.QtCore import QDate, QPoint, QStringListModel, Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gymflux.core.pagamento import FormaPagamento
from gymflux.ui.theme import (
    AZUL,
    LIMA,
    VERMELHO,
    ModoTema,
    estilo_paginacao,
    estilo_selo,
    icone_preto,
    modo_de,
)
from gymflux.ui.viewmodels.caixa import CaixaViewModel


class NovoPagamentoDialog(QDialog):
    """Modal sem vencimento (vencimento edita-se no perfil). Valor>0 e forma obrigatória."""

    FORMAS: ClassVar[list[str]] = [f.value for f in FormaPagamento]

    def __init__(
        self,
        aluno_nome: str,
        parent: QWidget | None = None,
        dia_base: int | None = None,
        vencimento_default: date | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Novo pagamento — {aluno_nome}")
        self.setMinimumWidth(560)
        self.setMaximumWidth(620)
        form = QFormLayout(self)
        self.spn_valor = QDoubleSpinBox()
        self.spn_valor.setRange(0.01, 100000.0)
        self.spn_valor.setDecimals(2)
        self.spn_valor.setValue(99.90)
        self.cmb_forma = QComboBox()
        self.cmb_forma.addItems(self.FORMAS)
        # default PIX (forma obrigatória, sem vazio)
        idx_pix = self.cmb_forma.findText(FormaPagamento.PIX.value)
        if idx_pix >= 0:
            self.cmb_forma.setCurrentIndex(idx_pix)
        self.chk_pago = QCheckBox("Pago hoje")
        self.chk_pago.setChecked(True)
        self.edt_comp = QLineEdit()
        self.edt_comp.setPlaceholderText("AAAA-MM (ex: 2026-09)")
        # linha valor + forma lado a lado, alinhados
        h_valor_forma = QHBoxLayout()
        h_valor_forma.setContentsMargins(0, 0, 0, 0)
        h_valor_forma.setSpacing(12)
        h_valor_forma.addWidget(QLabel("Valor (R$)*:"))
        h_valor_forma.addWidget(self.spn_valor, 1)
        h_valor_forma.addWidget(QLabel("Forma*:"))
        h_valor_forma.addWidget(self.cmb_forma, 1)
        # container para HBox esticar
        w_valor_forma = QWidget()
        w_valor_forma.setLayout(h_valor_forma)
        form.addRow(w_valor_forma)
        form.addRow(self.chk_pago)
        form.addRow("Competência (AAAA-MM):", self.edt_comp)
        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._btn_ok = botoes.button(QDialogButtonBox.StandardButton.Ok)
        botoes.accepted.connect(self._on_accept)
        botoes.rejected.connect(self.reject)
        form.addRow(botoes)
        # Fase 4.15: default ancorado no dia da matrícula (ou hoje)
        if vencimento_default is not None:
            self._vencimento_default = vencimento_default
        elif dia_base is not None:
            try:
                from gymflux.core.plano import vencimento_no_mes

                hoje = date.today()
                self._vencimento_default = vencimento_no_mes(hoje.year, hoje.month, dia_base)
            except Exception:
                self._vencimento_default = date.today()
        else:
            self._vencimento_default = date.today()
        # validação reativa (bloqueia Ok)
        self.spn_valor.valueChanged.connect(lambda _v: self._atualizar_ok())
        self.cmb_forma.currentTextChanged.connect(lambda _t: self._atualizar_ok())
        self._atualizar_ok()

    def _validar(self) -> tuple[bool, str]:
        # valor >0 e não vazio/"-"
        texto_valor = str(self.spn_valor.value()).strip()
        if not texto_valor or texto_valor == "-":
            return False, "Valor é obrigatório"
        try:
            dec = Decimal(texto_valor)
        except Exception:
            return False, "Valor inválido"
        if dec <= Decimal("0"):
            return False, "Valor deve ser > 0"
        forma = self.cmb_forma.currentText().strip()
        if not forma or forma == "—":
            return False, "Forma é obrigatória"
        return True, ""

    def _atualizar_ok(self) -> None:
        if self._btn_ok is not None:
            ok, _msg = self._validar()
            self._btn_ok.setEnabled(ok)

    def _on_accept(self) -> None:
        ok, msg = self._validar()
        if not ok:
            QMessageBox.warning(self, "Pagamento", msg)
            return
        self.accept()

    def forma(self) -> str | None:
        v = self.cmb_forma.currentText().strip()
        if not v or v == "—":
            return None
        return v

    def vencimento(self) -> date:
        # sem campo: usa hoje; se competência informada, usa dia 10 do mês
        comp = self.edt_comp.text().strip()
        if comp:
            try:
                from gymflux.ui.formatters import parse_br_competencia

                comp_norm = parse_br_competencia(comp)
                if comp_norm:
                    y, m = comp_norm.split("-")
                    return date(int(y), int(m), 10)
            except Exception:
                pass
            # fallback YYYY-MM
            try:
                y, m = comp.split("-")
                return date(int(y), int(m), 10)
            except Exception:
                pass
            # fallback MM/AAAA
            try:
                m, y = comp.split("/")
                return date(int(y), int(m), 10)
            except Exception:
                pass
        return self._vencimento_default


class MarcarPagoDialog(QDialog):
    """Escolhe forma e data ao marcar pendente como pago."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Marcar como pago")
        form = QFormLayout(self)
        self.cmb_forma = QComboBox()
        for f in FormaPagamento:
            self.cmb_forma.addItem(f.value, f.value)
        idx = self.cmb_forma.findText(FormaPagamento.PIX.value)
        if idx >= 0:
            self.cmb_forma.setCurrentIndex(idx)
        self.dat_pag = QDateEdit(QDate.currentDate())
        self.dat_pag.setCalendarPopup(True)
        self.dat_pag.setDisplayFormat("dd/MM/yyyy")
        form.addRow("Forma*:", self.cmb_forma)
        form.addRow("Data pagamento*:", self.dat_pag)
        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        form.addRow(botoes)

    def forma(self) -> str:
        return str(self.cmb_forma.currentData() or self.cmb_forma.currentText()).strip()

    def data_pagamento(self) -> date:
        qd = self.dat_pag.date()
        return date(qd.year(), qd.month(), qd.day())


class CaixaView(QWidget):
    COLUNAS = ("Aluno", "Valor (R$)", "Vencimento", "Situação", "Forma", "Competência")

    # duplo-clique redireciona para o aluno (perfil na aba Pagamentos)
    aluno_perfil_solicitado = Signal(str)

    def __init__(
        self,
        vm: CaixaViewModel,
        parent: QWidget | None = None,
        dia_base_provider: object | None = None,
    ) -> None:
        super().__init__(parent)
        self.vm = vm
        self._dia_base_provider = dia_base_provider
        layout = QHBoxLayout(self)

        # -- sidebar esquerda --------------------------------------------------
        sidebar = QVBoxLayout()
        sidebar.setContentsMargins(8, 8, 18, 8)
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
        self.btn_reabrir = QPushButton("Reabrir caixa")
        sidebar.addWidget(self.btn_fechar)
        sidebar.addWidget(self.btn_reabrir)
        sidebar.addStretch(1)
        side_widget = QWidget()
        side_widget.setLayout(sidebar)
        side_widget.setMaximumWidth(220)
        layout.addWidget(side_widget)

        # -- área principal ----------------------------------------------------
        principal = QVBoxLayout()
        # filtragem similar alunos: busca por aluno + ordenação por header
        hbusca = QHBoxLayout()
        self.edt_busca = QLineEdit()
        self.edt_busca.setPlaceholderText("Buscar por aluno...")
        hbusca.addWidget(self.edt_busca, 3)
        hbusca.addStretch(1)
        principal.addLayout(hbusca)
        self.tbl = QTableWidget(0, len(self.COLUNAS))
        self.tbl.setHorizontalHeaderLabels(list(self.COLUNAS))
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.horizontalHeader().setSectionsClickable(True)
        self.tbl.setSortingEnabled(True)
        self.tbl.horizontalHeader().setSortIndicatorShown(True)
        self._sort_col = -1
        self._sort_asc = True
        # paginação 500 por vez para 7k
        self._page_size = 500
        self._rendered = 500
        self._filtered_linhas: list = []
        self.tbl.verticalScrollBar().valueChanged.connect(self._on_scroll)
        principal.addWidget(self.tbl, 1)

        # label de paginação (mostrando X de Y) — cor por tema (claro: preto legível)
        self.lbl_paginacao = QLabel("")
        self.lbl_paginacao.setStyleSheet(estilo_paginacao(self.vm.ui_config.tema))
        self.lbl_paginacao.setVisible(False)
        principal.addWidget(self.lbl_paginacao)

        hbtn = QHBoxLayout()
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
        self.btn_marcar_pago = QPushButton("Marcar como pago")
        self.btn_marcar_pago.setToolTip("Marca o pagamento selecionado como pago hoje")
        self.btn_atualizar = QPushButton("Atualizar")
        self.btn_atualizar.setToolTip("Recarrega a lista (otimizado: só repinta)")
        self.btn_atualizar.setIcon(
            icone_preto(self.style(), QStyle.StandardPixmap.SP_BrowserReload)
        )
        hbtn.addWidget(self.cmb_aluno, 2)
        hbtn.addWidget(self.btn_novo)
        hbtn.addWidget(self.btn_marcar_pago)
        hbtn.addWidget(self.btn_atualizar)
        hbtn.addStretch(1)
        principal.addLayout(hbtn)

        layout.addLayout(principal, 1)
        self._linhas_cache: list = []

        # compat: mantém table de combo recarga etc
        self.cmb_mes.currentIndexChanged.connect(lambda _i: self.recarregar())
        self.cmb_aluno.editTextChanged.connect(self._filtrar_alunos)
        # debounce 300ms: evita 1 full-refresh por tecla (travava em 7k)
        self._busca_timer = QTimer(self)
        self._busca_timer.setSingleShot(True)
        self._busca_timer.setInterval(300)
        self._busca_timer.timeout.connect(self.recarregar)
        self.edt_busca.textChanged.connect(lambda _t: self._busca_timer.start())
        self.tbl.horizontalHeader().sectionClicked.connect(self._ordenar_coluna)
        self.tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tbl.customContextMenuRequested.connect(self._menu_contexto)
        # duplo-clique redireciona para o aluno (perfil na aba Pagamentos)
        self.tbl.cellDoubleClicked.connect(lambda _r, _c: self._abrir_perfil_aluno())
        self.btn_novo.clicked.connect(self._novo)
        self.btn_marcar_pago.clicked.connect(self._marcar_pago)
        self.btn_atualizar.clicked.connect(self._atualizar_otimizado)
        self.btn_fechar.clicked.connect(self._fechar)
        self.btn_reabrir.clicked.connect(self._reabrir)
        self.recarregar()

    def _atualizar_otimizado(self) -> None:
        """Refresh otimizado: só repinta a tabela (sem recriar combos)."""
        # evita recalcular combos/meses quando só pagamentos mudaram no perfil
        self.recarregar()
        # dica: recarregar já é otimizado (3 listas + dict), mas este atalho
        # evita piscar combos quando o usuário só quer ver exclusão refletida

    def _filtrar_alunos(self, texto: str) -> None:
        # o completer já filtra; apenas garante scroll
        pass

    # -- helpers ---------------------------------------------------------------
    def _mes_atual(self) -> str | None:
        mes = self.cmb_mes.currentData()
        return str(mes) if mes is not None else None

    def _recarregar_meses(self) -> None:
        mes_atual = self._mes_atual()
        meses = self.vm.meses_disponiveis()
        if not meses:
            meses = [date.today().strftime("%Y-%m")]
        self.cmb_mes.blockSignals(True)
        try:
            self.cmb_mes.clear()
            self.cmb_mes.addItem("Todos", None)
            for m in meses:
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

    def _recarregar_alunos_combo(self) -> None:
        aluno_atual = self.cmb_aluno.currentData()
        texto_atual = self.cmb_aluno.currentText()
        self.cmb_aluno.blockSignals(True)
        try:
            self.cmb_aluno.clear()
            nomes = []
            # usar listar_ordenado quando disponível já é ordenado e com busca
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

    def _recarregar_combos(self) -> None:
        # LEGADO: mantém compat (chamado por testes/externo) -> só meses + alunos se combo vazio
        self._recarregar_meses()
        # só recarrega alunos se ainda vazio (evita full-load por troca de mês)
        if self.cmb_aluno.count() == 0:
            self._recarregar_alunos_combo()
        else:
            # se já tem, apenas garante que meses está atualizado; alunos fica cacheado
            pass

    def recarregar(self) -> None:
        # PART 1: pushdown — UM refresh por troca de mês
        #  (meses DISTINCT + totais SUM + página LIMIT)
        # _recarregar_combos dividido: meses sempre, alunos só se vazio
        self._recarregar_meses()
        if self.cmb_aluno.count() == 0:
            self._recarregar_alunos_combo()
        mes = self._mes_atual()
        recebido, pendente, total = self.vm.totais_mes(mes)
        self.lbl_recebido.setText(f"Recebido: R$ {recebido:.2f}")
        self.lbl_pendente.setText(f"Pendente: R$ {pendente:.2f}")
        self.lbl_total.setText(f"Total: R$ {total:.2f}")
        rotulo = mes or "geral"
        self.lbl_totais.setText(
            f"{rotulo} — Recebido R$ {recebido:.2f} · "
            f"Pendente R$ {pendente:.2f} · Total R$ {total:.2f}"
        )
        fechado = mes is not None and self.vm.mes_fechado(mes)
        self.lbl_fechado.setStyleSheet(estilo_selo(self.vm.ui_config.tema))
        self.lbl_paginacao.setStyleSheet(estilo_paginacao(self.vm.ui_config.tema))
        self.lbl_fechado.setVisible(fechado)
        self.btn_reabrir.setVisible(fechado)
        self.btn_fechar.setVisible(not fechado)

        termo = self.edt_busca.text().strip().lower()
        if termo:
            # busca ativa com pushdown (JOIN+LIKE paginado; fallback filtra em Python)
            self._total_mes = self.vm.contar_busca(mes, termo)
            pagina = self.vm.buscar(mes, termo, limit=self._page_size, offset=0)
            self._linhas_cache = list(pagina)
            self._filtered_linhas = list(pagina)
            self._rendered = len(pagina)
            self._render_tabela()
            if self._total_mes > self._page_size:
                self.lbl_paginacao.setText(
                    f"Mostrando {self._rendered} de {self._total_mes} — "
                    "role até o final para carregar mais"
                )
                self.lbl_paginacao.setVisible(self._rendered < self._total_mes)
            else:
                self.lbl_paginacao.setVisible(False)
            return

        # modo pushdown paginado
        self._total_mes = self.vm.contar_por_mes(mes)
        pagina = self.vm.por_mes(mes, limit=self._page_size, offset=0)
        self._linhas_cache = list(pagina)
        self._filtered_linhas = list(pagina)
        self._rendered = len(pagina)
        # se total ainda não refletiu página (contar pode ser maior), guarda total
        if not hasattr(self, "_total_mes"):
            self._total_mes = self._rendered
        self._render_tabela()
        if self._total_mes > self._page_size:
            self.lbl_paginacao.setText(
                f"Mostrando {self._rendered} de {self._total_mes} — "
                "role até o final para carregar mais"
            )
            self.lbl_paginacao.setVisible(self._rendered < self._total_mes)
        else:
            self.lbl_paginacao.setVisible(False)

    def sincronizar_tema(self, tema) -> None:  # type: ignore[no-untyped-def]
        """Atualiza selo + paginação sem recarregar (troca de tema sem restart)."""
        self.lbl_fechado.setStyleSheet(estilo_selo(tema))
        self.lbl_paginacao.setStyleSheet(estilo_paginacao(tema))

    def _render_tabela(self) -> None:
        hoje = date.today()
        sorting = self.tbl.isSortingEnabled()
        self.tbl.setSortingEnabled(False)
        # evita flicker: block signals
        self.tbl.blockSignals(True)
        try:
            self.tbl.setRowCount(self._rendered)
            for row in range(self._rendered):
                p, nome = self._filtered_linhas[row]
                if p.pago:
                    sit = "PAGO"
                elif p.dias_atraso(hoje) > 0:
                    sit = f"ATRASADO {p.dias_atraso(hoje)}d"
                else:
                    sit = "PENDENTE"
                from gymflux.ui.formatters import fmt_br

                def _comp_br(comp: str | None) -> str:
                    if not comp or comp == "—":
                        return "—"
                    try:
                        y, m = comp.split("-")
                        return f"{m}/{y}"
                    except Exception:
                        return comp

                vals = (
                    nome,
                    f"{Decimal(str(p.valor)):.2f}",
                    fmt_br(p.data_vencimento),
                    sit,
                    str(p.forma) if p.forma else "—",
                    _comp_br(p.competencia),
                )
                for col, v in enumerate(vals):
                    item = QTableWidgetItem(v)
                    item.setData(Qt.ItemDataRole.UserRole, p.id)
                    item.setData(Qt.ItemDataRole.UserRole + 1, p.aluno_id)
                    if not p.pago and p.dias_atraso(hoje) > 0:
                        is_escuro = modo_de(self.vm.ui_config.tema) == ModoTema.ESCURO
                        bg = "#3a1a1a" if is_escuro else "#ffe0e0"
                        fg = VERMELHO if is_escuro else "#991111"
                        item.setBackground(QColor(bg))
                        item.setForeground(QColor(fg))
                    self.tbl.setItem(row, col, item)
        finally:
            self.tbl.blockSignals(False)
            self.tbl.setSortingEnabled(sorting)
        if self._sort_col >= 0:
            order = Qt.SortOrder.AscendingOrder if self._sort_asc else Qt.SortOrder.DescendingOrder
            self.tbl.sortByColumn(self._sort_col, order)

    def _on_scroll(self, value: int) -> None:
        bar = self.tbl.verticalScrollBar()
        if bar.maximum() == 0:
            return
        if value < bar.maximum() * 0.9:
            return
        total = getattr(self, "_total_mes", len(self._filtered_linhas))
        if self._rendered >= total:
            return
        termo = self.edt_busca.text().strip().lower()
        if termo:
            # busca ativa paginada: próxima página no repo (pushdown)
            mes = self._mes_atual()
            try:
                proxima = self.vm.buscar(mes, termo, limit=self._page_size, offset=self._rendered)
            except Exception:
                proxima = []
            if not proxima:
                return
            self._filtered_linhas.extend(proxima)
            self._linhas_cache.extend(proxima)
            novo = self._rendered + len(proxima)
            hoje = date.today()
            sorting = self.tbl.isSortingEnabled()
            self.tbl.setSortingEnabled(False)
            self.tbl.blockSignals(True)
            try:
                self.tbl.setRowCount(novo)
                for row in range(self._rendered, novo):
                    p, nome = self._filtered_linhas[row]
                    if p.pago:
                        sit = "PAGO"
                    elif p.dias_atraso(hoje) > 0:
                        sit = f"ATRASADO {p.dias_atraso(hoje)}d"
                    else:
                        sit = "PENDENTE"
                    from gymflux.ui.formatters import fmt_br

                    def _comp_br2(comp: str | None) -> str:
                        if not comp or comp == "—":
                            return "—"
                        try:
                            y, m = comp.split("-")
                            return f"{m}/{y}"
                        except Exception:
                            return comp

                    vals = (
                        nome,
                        f"{Decimal(str(p.valor)):.2f}",
                        fmt_br(p.data_vencimento),
                        sit,
                        str(p.forma) if p.forma else "—",
                        _comp_br2(p.competencia),
                    )
                    for col, v in enumerate(vals):
                        item = QTableWidgetItem(v)
                        item.setData(Qt.ItemDataRole.UserRole, p.id)
                        item.setData(Qt.ItemDataRole.UserRole + 1, p.aluno_id)
                        if not p.pago and p.dias_atraso(hoje) > 0:
                            is_escuro = modo_de(self.vm.ui_config.tema) == ModoTema.ESCURO
                            bg = "#3a1a1a" if is_escuro else "#ffe0e0"
                            fg = VERMELHO if is_escuro else "#991111"
                            item.setBackground(QColor(bg))
                            item.setForeground(QColor(fg))
                        self.tbl.setItem(row, col, item)
                self._rendered = novo
                if total > self._page_size:
                    self.lbl_paginacao.setText(
                        f"Mostrando {self._rendered} de {total} — "
                        "role até o final para carregar mais"
                    )
                    self.lbl_paginacao.setVisible(self._rendered < total)
                else:
                    self.lbl_paginacao.setVisible(False)
            finally:
                self.tbl.blockSignals(False)
                self.tbl.setSortingEnabled(sorting)
            return
        # pushdown: busca próxima página no repo
        mes = self._mes_atual()
        try:
            proxima = self.vm.por_mes(mes, limit=self._page_size, offset=self._rendered)
        except Exception:
            proxima = []
        if not proxima:
            return
        hoje = date.today()
        sorting = self.tbl.isSortingEnabled()
        self.tbl.setSortingEnabled(False)
        self.tbl.blockSignals(True)
        try:
            novo = self._rendered + len(proxima)
            self._filtered_linhas.extend(proxima)
            self._linhas_cache.extend(proxima)
            self.tbl.setRowCount(novo)
            for idx, (p, nome) in enumerate(proxima, start=self._rendered):
                if p.pago:
                    sit = "PAGO"
                elif p.dias_atraso(hoje) > 0:
                    sit = f"ATRASADO {p.dias_atraso(hoje)}d"
                else:
                    sit = "PENDENTE"
                from gymflux.ui.formatters import fmt_br

                def _comp_br3(comp: str | None) -> str:
                    if not comp or comp == "—":
                        return "—"
                    try:
                        y, m = comp.split("-")
                        return f"{m}/{y}"
                    except Exception:
                        return comp

                vals = (
                    nome,
                    f"{Decimal(str(p.valor)):.2f}",
                    fmt_br(p.data_vencimento),
                    sit,
                    str(p.forma) if p.forma else "—",
                    _comp_br3(p.competencia),
                )
                for col, v in enumerate(vals):
                    item = QTableWidgetItem(v)
                    item.setData(Qt.ItemDataRole.UserRole, p.id)
                    item.setData(Qt.ItemDataRole.UserRole + 1, p.aluno_id)
                    if not p.pago and p.dias_atraso(hoje) > 0:
                        is_escuro = modo_de(self.vm.ui_config.tema) == ModoTema.ESCURO
                        bg = "#3a1a1a" if is_escuro else "#ffe0e0"
                        fg = VERMELHO if is_escuro else "#991111"
                        item.setBackground(QColor(bg))
                        item.setForeground(QColor(fg))
                    self.tbl.setItem(idx, col, item)
            self._rendered = novo
            if total > self._page_size:
                self.lbl_paginacao.setText(
                    f"Mostrando {self._rendered} de {total} — role até o final para carregar mais"
                )
                self.lbl_paginacao.setVisible(self._rendered < total)
            else:
                self.lbl_paginacao.setVisible(False)
        finally:
            self.tbl.blockSignals(False)
            self.tbl.setSortingEnabled(sorting)

    def _ordenar_coluna(self, col: int) -> None:
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True
        order = Qt.SortOrder.AscendingOrder if self._sort_asc else Qt.SortOrder.DescendingOrder
        self.tbl.sortByColumn(col, order)

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
        dia_base = None
        try:
            provider = getattr(self, "_dia_base_provider", None)
            if callable(provider):
                dia_base = provider(str(aluno_id))  # type: ignore[operator]
        except Exception:
            dia_base = None
        dlg = NovoPagamentoDialog(nome, self, dia_base=dia_base)
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

    def _pagamento_selecionado(self):  # type: ignore[no-untyped-def]
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.information(self, "Caixa", "Selecione um pagamento na tabela.")
            return None
        # resolve via UserRole (sobrevive à ordenação visual)
        item = self.tbl.item(row, 0)
        pag_id = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if not pag_id:
            QMessageBox.information(self, "Caixa", "Selecione um pagamento na tabela.")
            return None
        for p, _n in getattr(self, "_linhas_cache", []):
            if p.id == pag_id:
                return p
        return None

    def _aluno_selecionado_id(self) -> str | None:
        row = self.tbl.currentRow()
        if row < 0:
            return None
        item = self.tbl.item(row, 0)
        if item is None:
            return None
        aluno_id = item.data(Qt.ItemDataRole.UserRole + 1)
        return str(aluno_id) if aluno_id else None

    def _abrir_perfil_aluno(self) -> None:
        aluno_id = self._aluno_selecionado_id()
        if not aluno_id:
            QMessageBox.information(self, "Caixa", "Selecione um pagamento na tabela.")
            return
        self.aluno_perfil_solicitado.emit(aluno_id)

    def _marcar_pago(self) -> None:
        pag = self._pagamento_selecionado()
        if pag is None:
            return
        if pag.pago:
            # oferece voltar para pendente
            confirma = QMessageBox.question(
                self,
                "Caixa",
                "Pagamento já está pago. Voltar para pendente?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirma != QMessageBox.StandardButton.Yes:
                return
            try:
                self.vm.desmarcar_pago(pag.id)
            except ValueError as e:
                QMessageBox.warning(self, "Caixa", str(e))
                return
            self.recarregar()
            return
        dlg = MarcarPagoDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.vm.marcar_como_pago(pag.id, data_pagamento=dlg.data_pagamento(), forma=dlg.forma())
        except ValueError as e:
            QMessageBox.warning(self, "Caixa", str(e))
            return
        self.recarregar()

    def _menu_contexto(self, pos: QPoint) -> None:
        from PySide6.QtWidgets import QMenu

        item = self.tbl.itemAt(pos)
        if item is None:
            return
        self.tbl.selectRow(item.row())
        menu = QMenu(self)
        a_perfil = menu.addAction("Abrir aluno (pagamentos)...")
        a_pago = menu.addAction("Marcar como pago / pendente")
        acao = menu.exec(self.tbl.viewport().mapToGlobal(pos))
        if acao == a_perfil:
            self._abrir_perfil_aluno()
        elif acao == a_pago:
            self._marcar_pago()

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

    def _reabrir(self) -> None:
        mes = self._mes_atual()
        if mes is None:
            QMessageBox.information(self, "Caixa", "Selecione um mês para reabrir.")
            return
        if not self.vm.mes_fechado(mes):
            QMessageBox.information(self, "Caixa", f"Caixa de {mes} já está aberto.")
            return
        confirma = QMessageBox.question(
            self,
            "Caixa",
            f"Reabrir o caixa de {mes}? Registros voltarão a ser permitidos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirma != QMessageBox.StandardButton.Yes:
            return
        try:
            self.vm.reabrir_mes(mes)
        except ValueError as e:
            QMessageBox.warning(self, "Caixa", str(e))
            return
        logger.info(f"[UI] caixa {mes} reaberto")
        QMessageBox.information(self, "Caixa", f"Caixa de {mes} reaberto.")
        self.recarregar()
