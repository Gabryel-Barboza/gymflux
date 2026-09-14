"""Tela de alunos — tabela + busca, cadastro, perfil editável e matrícula."""

from __future__ import annotations

import contextlib
from dataclasses import replace as _replace_pag
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from loguru import logger
from PySide6.QtCore import QDate, QPoint, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gymflux.core.aluno import Aluno, StatusAluno
from gymflux.core.pagamento import FormaPagamento, Pagamento
from gymflux.ui.viewmodels.alunos import AlunosViewModel
from gymflux.ui.viewmodels.frequencia import FrequenciaViewModel
from gymflux.ui.views.caixa import NovoPagamentoDialog


class PagamentosProto(Protocol):
    """Subconjunto usado pelo perfil: lista + registra + remover (Pagamentos ou Caixa VM)."""

    def do_aluno(self, aluno_id: str) -> list[Pagamento]: ...
    def registrar(
        self,
        *,
        aluno_id: str,
        valor: Decimal | float | str,
        data_vencimento: date,
        forma: FormaPagamento | str | None = None,
        pago: bool = False,
        data_pagamento: date | None = None,
        competencia: str | None = None,
    ) -> Pagamento: ...
    def remover_pagamento(self, pagamento_id: str) -> None: ...  # opcional em testes


class _AlunoForm(QWidget):
    """Campos do aluno em grade + foto quadrada clicável à direita."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMaximumWidth(680)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        self.edt_nome = QLineEdit()
        self.edt_cpf = QLineEdit()
        self.edt_cpf.setPlaceholderText("somente números (opcional)")
        self.edt_nasc = QLineEdit()
        self.edt_nasc.setPlaceholderText("AAAA-MM-DD (opcional)")
        self.edt_tel = QLineEdit()
        self.edt_email = QLineEdit()
        self.edt_endereco = QLineEdit()
        self.edt_endereco.setPlaceholderText("Rua, número, bairro (opcional)")
        self.edt_obs = QTextEdit()
        self.edt_obs.setPlaceholderText("Observações (opcional)")
        self.edt_obs.setMinimumHeight(80)
        # borda destacada só no tema escuro (azul #5AC8FA, foco #3A9BC4)
        self.edt_obs.setStyleSheet(
            "QTextEdit { border: 1px solid #5AC8FA; border-radius: 6px; padding: 6px; }"
            " QTextEdit:focus { border: 1px solid #3A9BC4; }"
        )
        self.edt_senha = QLineEdit()
        self.edt_senha.setEchoMode(QLineEdit.EchoMode.Normal)
        self.edt_senha.setPlaceholderText("")
        self.cmb_status = QComboBox()
        for st in StatusAluno:
            self.cmb_status.addItem(st.value, st)
        # linha 0: Nome* | CPF
        grid.addWidget(QLabel("Nome*:"), 0, 0)
        grid.addWidget(self.edt_nome, 0, 1)
        grid.addWidget(QLabel("CPF:"), 0, 2)
        grid.addWidget(self.edt_cpf, 0, 3)
        # linha 1: Nascimento | Telefone
        grid.addWidget(QLabel("Nascimento:"), 1, 0)
        grid.addWidget(self.edt_nasc, 1, 1)
        grid.addWidget(QLabel("Telefone:"), 1, 2)
        grid.addWidget(self.edt_tel, 1, 3)
        # linha 2: E-mail | Endereço
        grid.addWidget(QLabel("E-mail:"), 2, 0)
        grid.addWidget(self.edt_email, 2, 1)
        grid.addWidget(QLabel("Endereço:"), 2, 2)
        grid.addWidget(self.edt_endereco, 2, 3)
        # linha 3: Senha | Status
        grid.addWidget(QLabel("Senha numérica:"), 3, 0)
        grid.addWidget(self.edt_senha, 3, 1)
        grid.addWidget(QLabel("Status:"), 3, 2)
        grid.addWidget(self.cmb_status, 3, 3)
        # linha 4: Observações (separado, span)
        grid.addWidget(QLabel("Observações:"), 4, 0)
        grid.addWidget(self.edt_obs, 4, 1, 1, 3)
        root.addLayout(grid, 1)
        # foto quadrada à direita clicável
        foto_wrap = QVBoxLayout()
        foto_wrap.setContentsMargins(0, 0, 0, 0)
        foto_wrap.setSpacing(4)
        self.lbl_foto = QLabel()
        self.lbl_foto.setFixedSize(120, 120)
        self.lbl_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_foto.setText("Foto\n(clique)")
        self.lbl_foto.setScaledContents(False)
        self.lbl_foto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_foto.mousePressEvent = lambda e: self._escolher_foto()  # type: ignore[method-assign]
        self._foto_path: str | None = None
        foto_wrap.addWidget(self.lbl_foto, 0, Qt.AlignmentFlag.AlignTop)
        self.btn_remover_foto = QPushButton("Remover foto")
        self.btn_remover_foto.setMaximumWidth(120)
        self.btn_remover_foto.clicked.connect(self._remover_foto)
        foto_wrap.addWidget(self.btn_remover_foto)
        foto_wrap.addStretch(1)
        root.addLayout(foto_wrap)
        self._aplicar_tema_foto(False)

    def _escolher_foto(self) -> None:
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Escolher foto", "", "Imagens (*.png *.jpg *.jpeg *.bmp);;Todos (*)"
        )
        if caminho:
            self._foto_path = caminho
            self._atualizar_foto()

    def _remover_foto(self) -> None:
        self._foto_path = None
        self.lbl_foto.clear()
        self.lbl_foto.setText("Foto\n(clique)")
        self._aplicar_tema_foto(False)

    def _atualizar_foto(self) -> None:
        if not self._foto_path or not Path(self._foto_path).exists():
            self.lbl_foto.clear()
            self.lbl_foto.setText("Foto\n(clique)")
            self._aplicar_tema_foto(False)
            return
        pix = QPixmap(self._foto_path)
        if pix.isNull():
            self.lbl_foto.setText("Inválida")
            return
        # enquadra bem: KeepAspectRatioByExpanding + crop central
        scaled = pix.scaled(
            QSize(120, 120),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        # crop central para quadrado
        x = max(0, (scaled.width() - 120) // 2)
        y = max(0, (scaled.height() - 120) // 2)
        cropped = scaled.copy(x, y, 120, 120)
        self.lbl_foto.setPixmap(cropped)
        self._aplicar_tema_foto(True)

    def _detectar_tema(self):  # type: ignore[no-untyped-def]
        from gymflux.ui.theme import ModoTema

        tema = ModoTema.ESCURO
        try:
            parent = self.parent()
            while parent is not None:
                has_vm = hasattr(parent, "vm")  # type: ignore[attr-defined]
                dash = getattr(parent, "dashboard_vm", None)  # type: ignore[attr-defined]
                if has_vm and dash is not None:
                    cfg = getattr(dash, "ui_config", None)
                    tema = getattr(cfg, "tema", tema)
                    break
                parent = parent.parent()
        except Exception:
            pass
        # fallback via stylesheet global (claro tem #E8EDF1)
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

    def _aplicar_tema_foto(self, tem_foto: bool) -> None:
        from gymflux.ui.theme import paleta_do_modo

        tema = self._detectar_tema()
        try:
            paleta = paleta_do_modo(tema)
        except Exception:
            from gymflux.ui.theme import PALETA_ESCURA

            paleta = PALETA_ESCURA
        is_claro = paleta.texto == "#1A1E22"
        bg = paleta.painel if is_claro else "#0F1113"
        border = "#C8D0D8" if is_claro else "#5AC8FA"
        if tem_foto:
            self.lbl_foto.setStyleSheet(
                "QLabel { border: 2px solid " + border + "; border-radius: 8px;"
                f" background-color: {bg}; }}"
            )
        else:
            dash = "dashed" if not tem_foto else "solid"
            self.lbl_foto.setStyleSheet(
                f"QLabel {{ border: 2px {dash} {border}; border-radius: 8px;"
                f" background-color: {bg}; color: {paleta.suave}; }}"
            )

    def preencher(self, aluno: Aluno) -> None:
        self.edt_nome.setText(aluno.nome)
        self.edt_cpf.setText(aluno.cpf or "")
        self.edt_nasc.setText(aluno.data_nasc.isoformat() if aluno.data_nasc else "")
        self.edt_tel.setText(aluno.telefone or "")
        self.edt_email.setText(aluno.email or "")
        self.edt_endereco.setText(aluno.endereco or "")
        self.edt_obs.setPlainText(aluno.observacoes or "")
        # senha visivel texto claro, echo Normal, preenchido
        self.edt_senha.setEchoMode(QLineEdit.EchoMode.Normal)
        self.edt_senha.setText(aluno.senha or "")
        self.edt_senha.setPlaceholderText("")
        idx = self.cmb_status.findData(aluno.status)
        if idx >= 0:
            self.cmb_status.setCurrentIndex(idx)
        self._foto_path = getattr(aluno, "foto", None)
        self._atualizar_foto()

    def dados(self) -> dict[str, str]:
        status = self.cmb_status.currentData()
        return {
            "nome": self.edt_nome.text(),
            "cpf": self.edt_cpf.text(),
            "data_nasc": self.edt_nasc.text().strip(),
            "telefone": self.edt_tel.text(),
            "email": self.edt_email.text(),
            "observacoes": self.edt_obs.toPlainText(),
            "endereco": self.edt_endereco.text(),
            "senha": self.edt_senha.text(),
            "status": str(status) if status is not None else StatusAluno.ATIVO.value,
            "foto": self._foto_path or "",
        }


class NovoAlunoDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Novo aluno")
        self.setMaximumWidth(620)
        layout = QVBoxLayout(self)
        self.form = _AlunoForm(self)
        self.edt_nome = self.form.edt_nome
        self.edt_cpf = self.form.edt_cpf
        self.edt_nasc = self.form.edt_nasc
        self.edt_tel = self.form.edt_tel
        self.edt_email = self.form.edt_email
        self.edt_obs = self.form.edt_obs
        self.edt_endereco = self.form.edt_endereco
        self.edt_senha = self.form.edt_senha
        layout.addWidget(self.form)
        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

    def dados(self) -> dict[str, str]:
        return self.form.dados()


class PerfilAlunoDialog(QDialog):
    """Modal de perfil em abas (Pessoais | Plano/Matrícula | Frequência | Pagamentos) + Liberar."""

    COLUNAS_PAG = ("Vencimento", "Valor (R$)", "Pagamento", "Forma")
    COLUNAS_FREQ = ("Data", "Entradas", "Saídas")

    def __init__(
        self,
        alunos_vm: AlunosViewModel,
        pagamentos_vm: PagamentosProto,
        aluno_id: str,
        parent: QWidget | None = None,
        frequencia_vm: FrequenciaViewModel | None = None,
        dashboard_vm: object | None = None,
        aba_inicial: int = 0,
    ) -> None:
        super().__init__(parent)
        aluno = alunos_vm.alunos.buscar(aluno_id)
        if aluno is None:
            raise ValueError(f"Aluno id={aluno_id} não encontrado")
        self._vm = alunos_vm
        self._pagamentos = pagamentos_vm
        self._aluno_id = aluno_id
        self._frequencia = frequencia_vm
        self._dashboard_vm = dashboard_vm
        self._pagamentos_cache: list[Pagamento] = []
        self._matriculas_cache: list[tuple[str, object]] = []  # (id, Matricula)
        self.setWindowTitle(f"Perfil — {aluno.nome}")
        self.resize(640, 520)
        self.setMaximumWidth(700)
        layout = QVBoxLayout(self)

        tabs = QTabWidget(self)
        # aba 1: Pessoais
        tab_pessoais = QWidget()
        lay_p = QVBoxLayout(tab_pessoais)
        self.form = _AlunoForm(tab_pessoais)
        self.form.preencher(aluno)
        lay_p.addWidget(self.form)
        lay_p.addStretch(1)
        tabs.addTab(tab_pessoais, "Pessoais")

        # aba 2: Plano/Matrícula
        tab_plano = QWidget()
        lay_plano = QVBoxLayout(tab_plano)
        lay_plano.addWidget(QLabel("Matrículas do aluno:"))
        self.tbl_mat = QTableWidget(0, 2)
        self.tbl_mat.setHorizontalHeaderLabels(["Plano", "Vigência"])
        self.tbl_mat.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_mat.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tbl_mat.horizontalHeader().setStretchLastSection(True)
        lay_plano.addWidget(self.tbl_mat, 1)
        hmat = QHBoxLayout()
        self.btn_matricular = QPushButton("Matricular...")
        self.btn_excluir_mat = QToolButton()
        self.btn_excluir_mat.setToolTip("Excluir matrícula selecionada")
        self.btn_excluir_mat.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.btn_excluir_mat.setStyleSheet(
            "QToolButton { color: #E57373; border: none; padding: 4px; }"
            " QToolButton:hover { color: #FF8A8A; }"
        )
        self.btn_excluir_mat.setMaximumWidth(32)
        hmat.addWidget(self.btn_matricular)
        hmat.addWidget(self.btn_excluir_mat)
        hmat.addStretch(1)
        lay_plano.addLayout(hmat)
        tabs.addTab(tab_plano, "Plano/Matrícula")

        # aba 3: Frequência
        tab_freq = QWidget()
        lay_f = QVBoxLayout(tab_freq)
        self.tbl_freq = QTableWidget(0, len(self.COLUNAS_FREQ))
        self.tbl_freq.setHorizontalHeaderLabels(list(self.COLUNAS_FREQ))
        self.tbl_freq.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_freq.horizontalHeader().setStretchLastSection(True)
        lay_f.addWidget(self.tbl_freq, 1)
        tabs.addTab(tab_freq, "Frequência")

        # aba 4: Pagamentos
        tab_pag = QWidget()
        lay_pag = QVBoxLayout(tab_pag)
        self.tbl_pag = QTableWidget(0, len(self.COLUNAS_PAG))
        self.tbl_pag.setHorizontalHeaderLabels(list(self.COLUNAS_PAG))
        # vencimento editável no perfil (col 0), demais não
        self.tbl_pag.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed
        )
        self.tbl_pag.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tbl_pag.horizontalHeader().setStretchLastSection(True)
        lay_pag.addWidget(self.tbl_pag, 1)
        hb = QHBoxLayout()
        self.btn_novo_pag = QPushButton("Novo pagamento")
        self.btn_pago_pag = QPushButton("Marcar como pago")
        self.btn_pago_pag.setToolTip("Marca o pagamento selecionado como pago hoje")
        self.btn_excluir_pag = QToolButton()
        self.btn_excluir_pag.setToolTip("Excluir pagamento selecionado")
        self.btn_excluir_pag.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.btn_excluir_pag.setStyleSheet(
            "QToolButton { color: #E57373; border: none; padding: 4px; }"
            " QToolButton:hover { color: #FF8A8A; }"
        )
        self.btn_excluir_pag.setMaximumWidth(32)
        hb.addWidget(self.btn_novo_pag)
        hb.addWidget(self.btn_pago_pag)
        hb.addWidget(self.btn_excluir_pag)
        hb.addStretch(1)
        lay_pag.addLayout(hb)
        tabs.addTab(tab_pag, "Pagamentos")

        layout.addWidget(tabs, 1)

        # botão Liberar (extra, fora das abas)
        hlib = QHBoxLayout()
        self.btn_liberar = QPushButton("Liberar")
        self.btn_liberar.setToolTip("Liberar catraca para este aluno")
        hlib.addWidget(self.btn_liberar)
        hlib.addStretch(1)
        layout.addLayout(hlib)

        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        # traduz Save -> Salvar e alinha à direita com tema correto
        btn_save = botoes.button(QDialogButtonBox.StandardButton.Save)
        if btn_save is not None:
            btn_save.setText("Salvar")
            btn_save.setStyleSheet(
                "QPushButton { background-color: #5AC8FA; color: #0F1113;"
                " border-radius: 6px; padding: 6px 14px; font-weight: bold; }"
            )
        btn_cancel = botoes.button(QDialogButtonBox.StandardButton.Cancel)
        if btn_cancel is not None:
            btn_cancel.setText("Cancelar")
            btn_cancel.setStyleSheet(
                "QPushButton { background-color: transparent;"
                " border: 1px solid #5AC8FA; color: #5AC8FA;"
                " border-radius: 6px; padding: 6px 14px; }"
            )
        botoes.accepted.connect(self._salvar)
        botoes.rejected.connect(self.reject)
        # alinha botões à direita com stretch
        h_botoes = QHBoxLayout()
        h_botoes.setContentsMargins(0, 8, 0, 0)
        h_botoes.addStretch(1)
        h_botoes.addWidget(botoes)
        layout.addLayout(h_botoes)

        self.btn_novo_pag.clicked.connect(self._novo_pagamento)
        self.btn_matricular.clicked.connect(self._matricular)
        self.btn_liberar.clicked.connect(self._liberar)
        self.btn_excluir_mat.clicked.connect(self._excluir_matricula)
        self.btn_excluir_pag.clicked.connect(self._excluir_pagamento)
        self.btn_pago_pag.clicked.connect(self._marcar_pago)
        self.tbl_mat.customContextMenuRequested.connect(self._menu_mat)
        self.tbl_pag.customContextMenuRequested.connect(self._menu_pag)
        self.tbl_pag.cellChanged.connect(self._vencimento_editado)
        self._recarregar_pagamentos()
        self._recarregar_frequencia()
        self._recarregar_matriculas()
        if 0 <= aba_inicial < tabs.count():
            tabs.setCurrentIndex(aba_inicial)

    def _recarregar_matriculas(self) -> None:
        # usa cache com ids para exclusão
        if hasattr(self._vm, "matriculas_com_id"):
            try:
                mats_com_id = self._vm.matriculas_com_id(self._aluno_id)  # type: ignore[attr-defined]
            except Exception:
                mats_com_id = [
                    (f"idx-{i}", m)
                    for i, m in enumerate(self._vm.matriculas_do_aluno(self._aluno_id))
                ]
        else:
            mats_com_id = [
                (f"idx-{i}", m) for i, m in enumerate(self._vm.matriculas_do_aluno(self._aluno_id))
            ]
        self._matriculas_cache = mats_com_id  # type: ignore[assignment]
        self.tbl_mat.blockSignals(True)
        try:
            self.tbl_mat.setRowCount(len(mats_com_id))
            for row, (_mid, m) in enumerate(mats_com_id):
                vig = f"{m.vigencia.inicio.isoformat()} → {m.vigencia.fim.isoformat()}"  # type: ignore[attr-defined]
                self.tbl_mat.setItem(row, 0, QTableWidgetItem(m.plano.nome))  # type: ignore[attr-defined]
                self.tbl_mat.setItem(row, 1, QTableWidgetItem(vig))
        finally:
            self.tbl_mat.blockSignals(False)

    def _matricular(self) -> None:
        planos = [(p.id, f"{p.nome} ({p.duracao_dias}d)") for p in self._vm.planos_disponiveis()]
        if not planos:
            QMessageBox.information(self, "Perfil", "Cadastre um plano primeiro (aba Planos).")
            return
        aluno = self._vm.alunos.buscar(self._aluno_id)
        if aluno is None:
            return
        dlg = MatricularDialog(aluno.nome, planos, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self._vm.matricular(self._aluno_id, dlg.plano_id(), dlg.inicio())
        except (ValueError, RuntimeError) as e:
            QMessageBox.warning(self, "Perfil", str(e))
            return
        self._recarregar_matriculas()

    def _excluir_matricula(self) -> None:
        row = self.tbl_mat.currentRow()
        if row < 0 or row >= len(self._matriculas_cache):
            QMessageBox.information(self, "Perfil", "Selecione uma matrícula para excluir.")
            return
        mat_id, mat = self._matriculas_cache[row]  # type: ignore[assignment]
        nome_plano = getattr(getattr(mat, "plano", None), "nome", str(mat))
        confirma = QMessageBox.question(
            self,
            "Excluir matrícula",
            f"Remover vínculo com o plano '{nome_plano}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirma != QMessageBox.StandardButton.Yes:
            return
        try:
            self._vm.remover_matricula(mat_id)  # type: ignore[attr-defined]
        except Exception as e:
            QMessageBox.warning(self, "Perfil", str(e))
            return
        logger.info(f"[UI] matrícula removida id={mat_id} aluno={self._aluno_id}")
        self._recarregar_matriculas()

    def _menu_mat(self, pos: QPoint) -> None:
        item = self.tbl_mat.itemAt(pos)
        if item is None:
            return
        self.tbl_mat.selectRow(item.row())
        menu = QMenu(self)
        a_exc = menu.addAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "Excluir"
        )
        acao = menu.exec(self.tbl_mat.viewport().mapToGlobal(pos))
        if acao == a_exc:
            self._excluir_matricula()

    def _liberar(self) -> None:
        # tenta via dashboard_vm se disponível, senão via alunos_vm + mensagem
        if self._dashboard_vm is not None:
            try:
                decisao = self._dashboard_vm.liberar_entrada(self._aluno_id)  # type: ignore[attr-defined]
                QMessageBox.information(
                    self,
                    "Liberar",
                    self._dashboard_vm.resume_decisao(decisao),  # type: ignore[attr-defined]
                )
                return
            except Exception as e:
                QMessageBox.warning(self, "Liberar", str(e))
                return
        # fallback: informa que catraca liberada depende do dashboard
        QMessageBox.information(self, "Liberar", "Use a aba Catraca para liberar com CPF/senha.")

    def _recarregar_frequencia(self) -> None:
        if self._frequencia is None:
            return
        linhas = self._frequencia.resumo_por_dia(self._aluno_id)
        self.tbl_freq.setRowCount(len(linhas))
        for row, (dia, entradas, saidas) in enumerate(linhas):
            for col, v in enumerate((dia.isoformat(), str(entradas), str(saidas))):
                self.tbl_freq.setItem(row, col, QTableWidgetItem(v))

    def _recarregar_pagamentos(self) -> None:
        pags = sorted(
            self._pagamentos.do_aluno(self._aluno_id),
            key=lambda p: p.data_vencimento,
            reverse=True,
        )
        self._pagamentos_cache = pags
        self.tbl_pag.blockSignals(True)
        try:
            self.tbl_pag.setRowCount(len(pags))
            for row, p in enumerate(pags):
                vals = (
                    p.data_vencimento.isoformat(),
                    f"{Decimal(str(p.valor)):.2f}",
                    p.data_pagamento.isoformat() if p.data_pagamento else "—",
                    str(p.forma) if p.forma else "—",
                )
                for col, v in enumerate(vals):
                    item = QTableWidgetItem(v)
                    # só vencimento editável no perfil
                    if col == 0:
                        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                    else:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.tbl_pag.setItem(row, col, item)
        finally:
            self.tbl_pag.blockSignals(False)

    def _vencimento_editado(self, row: int, col: int) -> None:
        if col != 0:
            return
        if row < 0 or row >= len(self._pagamentos_cache):
            return
        pag = self._pagamentos_cache[row]
        item = self.tbl_pag.item(row, col)
        if item is None:
            return
        texto = item.text().strip()
        try:
            novo = date.fromisoformat(texto)
        except ValueError:
            QMessageBox.warning(self, "Perfil", "Vencimento inválido (use AAAA-MM-DD).")
            self._recarregar_pagamentos()
            return
        # atualiza via repo diretamente (mantém id/valor/pago)
        try:
            # tenta via pagamentos_vm que pode ser CaixaViewModel ou service
            if hasattr(self._pagamentos, "pagamentos"):
                # CaixaViewModel -> pagamentos é RegistrarPagamentoService
                svc = self._pagamentos.pagamentos  # type: ignore[attr-defined]
                repo = getattr(svc, "repo", None)
                if repo is not None and hasattr(repo, "buscar_por_id"):
                    orig = repo.buscar_por_id(pag.id)  # type: ignore[attr-defined]
                    if orig is not None:
                        from dataclasses import replace

                        novo_pag = replace(orig, data_vencimento=novo)  # type: ignore[arg-type]
                        # Pagamento é frozen, usa replace
                        # mas repo espera salvar novo
                        if hasattr(repo, "salvar"):
                            repo.salvar(novo_pag)  # type: ignore[attr-defined]
                            # commit se houver
                            commit = getattr(self._pagamentos, "commit", None) or getattr(
                                self._vm, "commit", None
                            )
                            if callable(commit):
                                with contextlib.suppress(Exception):
                                    commit()  # type: ignore[misc]
            elif hasattr(self._pagamentos, "repo"):
                repo = self._pagamentos.repo  # type: ignore[attr-defined]
                if hasattr(repo, "buscar_por_id"):
                    orig = repo.buscar_por_id(pag.id)  # type: ignore[attr-defined]
                    if orig is not None:
                        from dataclasses import replace

                        novo_pag = replace(orig, data_vencimento=novo)
                        repo.salvar(novo_pag)  # type: ignore[attr-defined]
                        commit = getattr(self._vm, "commit", None)
                        if callable(commit):
                            with contextlib.suppress(Exception):
                                commit()  # type: ignore[misc]
            # fallback: se pagamentos é RepositorioPagamentosMemoria direto
            elif hasattr(self._pagamentos, "buscar_por_id"):
                orig = self._pagamentos.buscar_por_id(pag.id)  # type: ignore[attr-defined]
                if orig is not None:
                    from dataclasses import replace

                    novo_pag = replace(orig, data_vencimento=novo)
                    self._pagamentos.salvar(novo_pag)  # type: ignore[attr-defined]
        except Exception as e:
            QMessageBox.warning(self, "Perfil", f"Erro ao atualizar vencimento: {e}")
            self._recarregar_pagamentos()
            return
        logger.info(f"[UI] vencimento atualizado pag={pag.id} -> {novo}")
        self._recarregar_pagamentos()

    def _excluir_pagamento(self) -> None:
        row = self.tbl_pag.currentRow()
        if row < 0 or row >= len(self._pagamentos_cache):
            QMessageBox.information(self, "Perfil", "Selecione um pagamento para excluir.")
            return
        pag = self._pagamentos_cache[row]
        confirma = QMessageBox.question(
            self,
            "Excluir pagamento",
            f"Excluir pagamento de R$ {pag.valor:.2f} vencimento {pag.data_vencimento}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirma != QMessageBox.StandardButton.Yes:
            return
        try:
            if hasattr(self._pagamentos, "remover_pagamento"):
                self._pagamentos.remover_pagamento(pag.id)  # type: ignore[attr-defined]
            elif hasattr(self._pagamentos, "remover"):
                self._pagamentos.remover(pag.id)  # type: ignore[attr-defined]
            elif hasattr(self._pagamentos, "pagamentos") and hasattr(
                self._pagamentos.pagamentos, "remover"
            ):
                self._pagamentos.pagamentos.remover(pag.id)  # type: ignore[attr-defined]
                commit = getattr(self._pagamentos, "commit", None)
                if callable(commit):
                    commit()  # type: ignore[misc]
            else:
                raise RuntimeError("Repositório de pagamentos sem remover()")
        except Exception as e:
            QMessageBox.warning(self, "Perfil", str(e))
            return
        logger.info(f"[UI] pagamento removido id={pag.id}")
        self._recarregar_pagamentos()

    def _menu_pag(self, pos: QPoint) -> None:
        item = self.tbl_pag.itemAt(pos)
        if item is None:
            return
        self.tbl_pag.selectRow(item.row())
        menu = QMenu(self)
        a_pago = menu.addAction("Marcar como pago / pendente")
        a_exc = menu.addAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "Excluir"
        )
        acao = menu.exec(self.tbl_pag.viewport().mapToGlobal(pos))
        if acao == a_pago:
            self._marcar_pago()
        elif acao == a_exc:
            self._excluir_pagamento()

    def _marcar_pago(self) -> None:
        row = self.tbl_pag.currentRow()
        if row < 0 or row >= len(self._pagamentos_cache):
            QMessageBox.information(self, "Perfil", "Selecione um pagamento.")
            return
        pag = self._pagamentos_cache[row]
        try:
            if hasattr(self._pagamentos, "marcar_como_pago"):
                if pag.pago:
                    self._pagamentos.desmarcar_pago(pag.id)  # type: ignore[attr-defined]
                else:
                    self._pagamentos.marcar_como_pago(pag.id)  # type: ignore[attr-defined]
            else:
                # fallback genérico via repo direto (memória/SQL)
                repo = None
                if hasattr(self._pagamentos, "pagamentos"):
                    inner = self._pagamentos.pagamentos  # type: ignore[attr-defined]
                    repo = getattr(inner, "repo", None)
                elif hasattr(self._pagamentos, "repo"):
                    repo = self._pagamentos.repo  # type: ignore[attr-defined]
                elif hasattr(self._pagamentos, "buscar_por_id"):
                    repo = self._pagamentos  # type: ignore[assignment]
                if repo is None or not hasattr(repo, "salvar"):
                    raise RuntimeError("Repositório sem salvar()")
                orig = repo.buscar_por_id(pag.id)  # type: ignore[attr-defined]
                if orig is None:
                    raise ValueError("Pagamento não encontrado")
                novo = _replace_pag(
                    orig, data_pagamento=None if orig.pago else date.today()
                )
                repo.salvar(novo)  # type: ignore[attr-defined]
                commit = getattr(self._pagamentos, "commit", None) or getattr(
                    self._vm, "commit", None
                )
                if callable(commit):
                    with contextlib.suppress(Exception):
                        commit()  # type: ignore[misc]
        except (ValueError, RuntimeError) as e:
            QMessageBox.warning(self, "Perfil", str(e))
            return
        self._recarregar_pagamentos()

    def _novo_pagamento(self) -> None:
        aluno = self._vm.alunos.buscar(self._aluno_id)
        if aluno is None:
            return
        dlg = NovoPagamentoDialog(aluno.nome, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            # vencimento editável só no perfil; aqui usa hoje/competência
            venc = dlg.vencimento() if hasattr(dlg, "vencimento") else date.today()
            self._pagamentos.registrar(
                aluno_id=self._aluno_id,
                valor=Decimal(str(dlg.spn_valor.value())),
                data_vencimento=venc,
                forma=dlg.forma(),
                pago=dlg.chk_pago.isChecked(),
                competencia=dlg.edt_comp.text(),
            )
        except ValueError as e:
            QMessageBox.warning(self, "Perfil", str(e))
            return
        self._recarregar_pagamentos()

    def _salvar(self) -> None:
        d = self.form.dados()
        if not d["nome"].strip():
            QMessageBox.warning(self, "Perfil", "Nome é obrigatório.")
            return
        nasc: date | None = None
        if d["data_nasc"]:
            try:
                nasc = date.fromisoformat(d["data_nasc"])
            except ValueError:
                QMessageBox.warning(self, "Perfil", "Nascimento inválido (use AAAA-MM-DD).")
                return
        try:
            status = StatusAluno(d["status"])
        except ValueError:
            QMessageBox.warning(self, "Perfil", "Status inválido.")
            return
        foto_src = d.get("foto", "")
        foto_final = None
        # foto pode ser caminho original ou vazio (remover) ou já definitiva
        aluno_atual = self._vm.alunos.buscar(self._aluno_id)
        foto_atual = getattr(aluno_atual, "foto", None) if aluno_atual else None
        if foto_src and Path(foto_src).exists():  # type: ignore[arg-type]
            # se já é o caminho definitivo, mantém
            if foto_atual and Path(foto_src).resolve() == Path(foto_atual).resolve() if Path(foto_atual).exists() else False:  # type: ignore[arg-type]  # noqa: E501
                foto_final = foto_atual
            else:
                try:
                    dst_dir = Path("data/fotos/alunos")
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    ext = Path(foto_src).suffix or ".jpg"  # type: ignore[arg-type]
                    dst = dst_dir / f"{self._aluno_id}{ext}"
                    import shutil

                    shutil.copy2(foto_src, dst)
                    foto_final = str(dst)
                except Exception as e:
                    logger.warning(f"[UI] falha ao copiar foto {e}")
                    foto_final = foto_src
        elif not foto_src:
            # remover foto se campo vazio e antes tinha
            foto_final = None
        else:
            foto_final = foto_atual
        try:
            self._vm.atualizar(
                self._aluno_id,
                nome=d["nome"],
                cpf=d["cpf"],
                data_nasc=nasc,
                telefone=d["telefone"],
                email=d["email"],
                observacoes=d["observacoes"],
                endereco=d["endereco"],
                senha=d["senha"],
                status=status,
                foto=foto_final,
            )
        except ValueError as e:
            QMessageBox.warning(self, "Perfil", str(e))
            return
        logger.info(f"[UI] perfil atualizado id={self._aluno_id}")
        self.accept()


class MatricularDialog(QDialog):
    def __init__(
        self, aluno_nome: str, planos: list[tuple[str, str]], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Matricular — {aluno_nome}")
        self.setMaximumWidth(420)
        form = QFormLayout(self)
        self.cmb_plano = QComboBox()
        for plano_id, plano_nome in planos:
            self.cmb_plano.addItem(plano_nome, plano_id)
        self.dat_inicio = QDateEdit(QDate.currentDate())
        self.dat_inicio.setCalendarPopup(True)
        form.addRow("Plano:", self.cmb_plano)
        form.addRow("Início:", self.dat_inicio)
        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        form.addRow(botoes)

    def plano_id(self) -> str:
        return str(self.cmb_plano.currentData())

    def inicio(self) -> date:
        qd = self.dat_inicio.date()
        return date(qd.year(), qd.month(), qd.day())


class AlunosView(QWidget):
    COLUNAS = ("ID", "Nome", "CPF", "Telefone", "Status", "Bloqueio")

    def __init__(
        self,
        vm: AlunosViewModel,
        pagamentos_vm: PagamentosProto | None = None,
        parent: QWidget | None = None,
        frequencia_vm: FrequenciaViewModel | None = None,
        dashboard_vm: object | None = None,
    ) -> None:
        super().__init__(parent)
        self.vm = vm
        self.pagamentos_vm = pagamentos_vm
        self.frequencia_vm = frequencia_vm
        self.dashboard_vm = dashboard_vm
        layout = QVBoxLayout(self)

        hbusca = QHBoxLayout()
        self.edt_busca = QLineEdit()
        self.edt_busca.setPlaceholderText("Buscar por nome ou CPF...")
        self.cmb_status = QComboBox()
        self.cmb_status.addItem("Todos", None)
        for st in StatusAluno:
            self.cmb_status.addItem(st.value, st)
        hbusca.addWidget(self.edt_busca, 3)
        hbusca.addWidget(QLabel("Status:"))
        hbusca.addWidget(self.cmb_status, 1)
        layout.addLayout(hbusca)

        # central: tabela + painel detalhes à direita
        central = QHBoxLayout()
        central.setSpacing(12)
        self.tbl = QTableWidget(0, len(self.COLUNAS))
        self.tbl.setHorizontalHeaderLabels(list(self.COLUNAS))
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setColumnHidden(0, True)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tbl.horizontalHeader().setSectionsClickable(True)
        self.tbl.setSortingEnabled(True)
        self.tbl.horizontalHeader().setSortIndicatorShown(True)
        self._sort_col = -1
        self._sort_asc = True
        central.addWidget(self.tbl, 3)
        # painel detalhes à direita da tabela — tema correto
        self.detalhes_frame = QFrame()
        self.detalhes_frame.setObjectName("DetalhesAlunoFrame")
        self.detalhes_frame.setMinimumWidth(280)
        self.detalhes_frame.setMaximumWidth(340)
        det_lay = QVBoxLayout(self.detalhes_frame)
        det_lay.setContentsMargins(12, 12, 12, 12)
        det_lay.setSpacing(8)
        self.lbl_detalhes_foto = QLabel()
        self.lbl_detalhes_foto.setFixedSize(140, 140)
        self.lbl_detalhes_foto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_detalhes_foto.setText("Sem foto")
        det_lay.addWidget(self.lbl_detalhes_foto, 0, Qt.AlignmentFlag.AlignHCenter)
        self.lbl_detalhes_nome = QLabel("Selecione um aluno")
        self.lbl_detalhes_nome.setWordWrap(True)
        det_lay.addWidget(self.lbl_detalhes_nome)
        self.lbl_detalhes_info = QLabel("Detalhes aparecerão aqui")
        self.lbl_detalhes_info.setWordWrap(True)
        self.lbl_detalhes_info.setTextFormat(Qt.TextFormat.PlainText)
        det_lay.addWidget(self.lbl_detalhes_info)
        det_lay.addStretch(1)
        central.addWidget(self.detalhes_frame, 1)
        layout.addLayout(central, 1)
        self._aplicar_tema_detalhes()

        hbtn = QHBoxLayout()
        self.btn_novo = QPushButton("Novo aluno")
        # toggle Bloquear/Desbloquear (único visível)
        self.btn_bloq_toggle = QPushButton("Bloquear/Desbloquear")
        # legados ocultos mas mantidos p/ compat testes antigos
        self.btn_matricular = QPushButton("Matricular...")
        self.btn_bloquear = QPushButton("Bloquear")
        self.btn_desbloquear = QPushButton("Desbloquear")
        self.btn_inativar = QPushButton("Inativar/Reativar")
        self.btn_matricular.setVisible(False)
        self.btn_bloquear.setVisible(False)
        self.btn_desbloquear.setVisible(False)
        self.btn_inativar.setVisible(False)
        for b in (
            self.btn_novo,
            self.btn_bloq_toggle,
            self.btn_matricular,
            self.btn_bloquear,
            self.btn_desbloquear,
            self.btn_inativar,
        ):
            hbtn.addWidget(b)
        hbtn.addStretch(1)
        layout.addLayout(hbtn)

        self.edt_busca.textChanged.connect(lambda _t: self.recarregar())
        self.cmb_status.currentIndexChanged.connect(lambda _i: self.recarregar())
        self.tbl.cellDoubleClicked.connect(lambda _r, _c: self._abrir_perfil())
        self.tbl.itemSelectionChanged.connect(self._atualizar_detalhes)
        self.tbl.horizontalHeader().sectionClicked.connect(self._ordenar_coluna)
        self.tbl.customContextMenuRequested.connect(self._menu_contexto)
        self.btn_novo.clicked.connect(self._novo)
        self.btn_bloq_toggle.clicked.connect(self._toggle_bloqueio)
        # legados
        self.btn_matricular.clicked.connect(self._matricular)
        self.btn_bloquear.clicked.connect(lambda: self._acao("bloquear"))
        self.btn_desbloquear.clicked.connect(lambda: self._acao("desbloquear"))
        self.btn_inativar.clicked.connect(lambda: self._acao("inativar"))

        self.recarregar()

    # -- helpers ---------------------------------------------------------------
    def _selecionado(self) -> tuple[str, str] | None:
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.information(self, "Alunos", "Selecione um aluno na tabela.")
            return None
        item_id = self.tbl.item(row, 0)
        item_nome = self.tbl.item(row, 1)
        if item_id is None:
            return None
        return (item_id.text(), item_nome.text() if item_nome else "")

    def recarregar(self) -> None:
        status = self.cmb_status.currentData()
        alunos = self.vm.listar(busca=self.edt_busca.text(), status=status)
        # desativa ordenação durante preenchimento para não interferir
        sorting = self.tbl.isSortingEnabled()
        self.tbl.setSortingEnabled(False)
        self.tbl.setRowCount(len(alunos))
        for row, a in enumerate(alunos):
            vals = (
                a.id,
                a.nome,
                a.cpf or "—",
                a.telefone or "—",
                str(a.status),
                "SIM" if a.esta_bloqueado else "não",
            )
            for col, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if a.esta_bloqueado:
                    item.setForeground(QBrush(QColor("#E57373")))
                self.tbl.setItem(row, col, item)
        self.tbl.setSortingEnabled(sorting)
        # reaplica ordenação se já houver coluna selecionada
        if self._sort_col >= 0:
            order = Qt.SortOrder.AscendingOrder if self._sort_asc else Qt.SortOrder.DescendingOrder
            self.tbl.sortByColumn(self._sort_col, order)
        self._atualizar_detalhes()

    def _atualizar_detalhes(self) -> None:
        row = self.tbl.currentRow()
        if row < 0:
            self.lbl_detalhes_foto.clear()
            self.lbl_detalhes_foto.setText("Sem foto")
            self.lbl_detalhes_nome.setText("Selecione um aluno")
            self.lbl_detalhes_info.setText("Detalhes aparecerão aqui")
            self._aplicar_tema_detalhes()
            return
        item_id = self.tbl.item(row, 0)
        if item_id is None:
            return
        aluno = self.vm.alunos.buscar(item_id.text())
        if aluno is None:
            return
        # foto
        foto_path = getattr(aluno, "foto", None)
        if foto_path and Path(foto_path).exists():  # type: ignore[arg-type]
            pix = QPixmap(foto_path)
            if not pix.isNull():
                scaled = pix.scaled(
                    QSize(140, 140),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                x = max(0, (scaled.width() - 140) // 2)
                y = max(0, (scaled.height() - 140) // 2)
                cropped = scaled.copy(x, y, 140, 140)
                self.lbl_detalhes_foto.setPixmap(cropped)
            else:
                self.lbl_detalhes_foto.clear()
                self.lbl_detalhes_foto.setText("Sem foto")
        else:
            self.lbl_detalhes_foto.clear()
            self.lbl_detalhes_foto.setText("Sem foto")
        self.lbl_detalhes_nome.setText(aluno.nome)
        info = (
            f"nome: {aluno.nome}\n"
            f"CPF: {aluno.cpf or '—'}\n"
            f"Telefone: {aluno.telefone or '—'}\n"
            f"E-mail: {aluno.email or '—'}\n"
            f"Status: {aluno.status}\n"
            f"Bloqueio: {'SIM' if aluno.esta_bloqueado else 'não'}\n"
            f"Senha: {aluno.senha or '—'}\n"
            f"Endereço: {aluno.endereco or '—'}"
        )
        self.lbl_detalhes_info.setText(info)
        self._aplicar_tema_detalhes()

    def _aplicar_tema_detalhes(self, tema=None) -> None:  # type: ignore[no-untyped-def]
        from gymflux.ui.theme import ModoTema, paleta_do_modo

        # tenta inferir tema atual via dashboard_vm ou QApplication
        if tema is None:
            try:
                if hasattr(self, "dashboard_vm") and self.dashboard_vm is not None:  # type: ignore[attr-defined]
                    cfg = getattr(self.dashboard_vm, "ui_config", None)  # type: ignore[attr-defined]
                    tema = getattr(cfg, "tema", None) if cfg else None
            except Exception:
                tema = None
        if tema is None:
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
        try:
            paleta = paleta_do_modo(tema or ModoTema.ESCURO)
        except Exception:
            from gymflux.ui.theme import PALETA_ESCURA

            paleta = PALETA_ESCURA
        is_claro = paleta.texto == "#1A1E22"
        # detalhe frame
        self.detalhes_frame.setStyleSheet(
            "QFrame#DetalhesAlunoFrame { border: 1px solid " + paleta.borda + ";"
            f" border-radius: 8px; background-color: {paleta.painel}; }}"
        )
        # foto no detalhes
        foto_bg = paleta.painel if is_claro else "#0F1113"
        foto_border = "#C8D0D8" if is_claro else "#5AC8FA"
        pm = self.lbl_detalhes_foto.pixmap()
        if pm is None or pm.isNull():
            self.lbl_detalhes_foto.setStyleSheet(
                f"QLabel {{ border: 2px dashed {foto_border}; border-radius: 8px;"
                f" background-color: {foto_bg}; color: {paleta.suave}; }}"
            )
        else:
            self.lbl_detalhes_foto.setStyleSheet(
                f"QLabel {{ border: 2px solid {foto_border}; border-radius: 8px;"
                f" background-color: {foto_bg}; }}"
            )
        # textos
        self.lbl_detalhes_nome.setStyleSheet(
            f"font-weight: bold; font-size: 14px; color: {paleta.texto};"
            " background: transparent;"
        )
        self.lbl_detalhes_info.setStyleSheet(
            f"color: {paleta.suave}; background: transparent;"
        )
        # foto no form (se existir)
        with contextlib.suppress(Exception):
            if hasattr(self, "form") and hasattr(self.form, "lbl_foto"):
                # atualiza foto do form se existir (para perfil)
                pass

    def sincronizar_tema(self, tema) -> None:
        self._aplicar_tema_detalhes(tema)
        with contextlib.suppress(Exception):
            if hasattr(self, "form") and hasattr(self.form, "_atualizar_foto"):
                # força re-render foto com tema correto se já tem pixmap
                self.form._atualizar_foto()

    def _ordenar_coluna(self, col: int) -> None:
        """SORT no header: toggle asc/desc na mesma coluna."""
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True
        order = Qt.SortOrder.AscendingOrder if self._sort_asc else Qt.SortOrder.DescendingOrder
        self.tbl.sortByColumn(col, order)

    def _header_clicado(self, col: int) -> None:
        """Menu tipo Excel: lista valores únicos da coluna + busca, aplica filtro."""
        header = self.tbl.horizontalHeader()
        # coleta valores únicos da coluna
        valores: set[str] = set()
        for aluno in self.vm.alunos.listar():
            if col == 1:
                valores.add(aluno.nome)
            elif col == 2:
                valores.add(aluno.cpf or "—")
            elif col == 3:
                valores.add(aluno.telefone or "—")
            elif col == 4:
                valores.add(str(aluno.status))
            elif col == 5:
                valores.add("SIM" if aluno.esta_bloqueado else "não")
            elif col == 0:
                valores.add(aluno.id)
        if not valores:
            return
        menu = QMenu(self)
        # busca
        edt = QLineEdit(menu)
        edt.setPlaceholderText("Buscar...")
        # placeholder
        container = QWidget(menu)
        lay = QHBoxLayout(container)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.addWidget(edt)
        # cria QListWidget para valores filtráveis
        lst = QListWidget(menu)
        lst.setMaximumHeight(180)
        for v in sorted(valores):
            it = QListWidgetItem(v)
            lst.addItem(it)
        # layout menu custom: adiciona widgets via layout do menu é tricky; usa QWidgetAction
        from PySide6.QtWidgets import QWidgetAction

        wa_search = QWidgetAction(menu)
        wa_search.setDefaultWidget(container)
        menu.addAction(wa_search)
        wa_list = QWidgetAction(menu)
        wa_list.setDefaultWidget(lst)
        menu.addAction(wa_list)
        menu.addSeparator()
        act_limpar = menu.addAction("Limpar filtro")
        act_todos = menu.addAction("Todos")

        def _filtrar_lista(txt: str) -> None:
            txt_l = txt.lower()
            for i in range(lst.count()):
                it = lst.item(i)
                assert it is not None
                it.setHidden(txt_l not in it.text().lower())

        edt.textChanged.connect(_filtrar_lista)
        lst.itemClicked.connect(
            lambda it: self._aplicar_filtro_coluna(col, it.text())  # type: ignore[arg-type]
        )
        act_limpar.triggered.connect(lambda: self._aplicar_filtro_coluna(col, ""))
        act_todos.triggered.connect(lambda: self._aplicar_filtro_coluna(col, ""))

        # posiciona abaixo do header
        x = header.sectionViewportPosition(col)
        y = header.height()
        global_pos = header.mapToGlobal(QPoint(x, y))
        menu.exec(global_pos)

    def _aplicar_filtro_coluna(self, col: int, texto: str) -> None:
        if not texto or texto == "—":
            self.edt_busca.clear()
            self.cmb_status.setCurrentIndex(0)
            self.recarregar()
            return
        if col == 4:
            try:
                st = StatusAluno(texto)
                idx = self.cmb_status.findData(st)
                if idx >= 0:
                    self.cmb_status.setCurrentIndex(idx)
                    return
            except ValueError:
                pass
        self.edt_busca.setText(texto)

    def _toggle_bloqueio(self) -> None:
        sel = self._selecionado()
        if sel is None:
            return
        aluno_id, _nome = sel
        aluno = self.vm.alunos.buscar(aluno_id)
        if aluno is None:
            return
        try:
            if aluno.esta_bloqueado:
                self.vm.desbloquear(aluno_id)
            else:
                self.vm.bloquear(aluno_id)
        except ValueError as e:
            QMessageBox.warning(self, "Alunos", str(e))
            return
        self.recarregar()

    # -- ações -------------------------------------------------------------------
    def _menu_contexto(self, pos: QPoint) -> None:
        item = self.tbl.itemAt(pos)
        if item is None:
            return
        self.tbl.selectRow(item.row())
        menu = QMenu(self)
        a_perfil = menu.addAction("Abrir perfil...")
        a_mat = menu.addAction("Matricular...")
        a_bloq = menu.addAction("Bloquear/Desbloquear")
        a_inat = menu.addAction("Inativar/Reativar")
        acao = menu.exec(self.tbl.viewport().mapToGlobal(pos))
        if acao == a_perfil:
            self._abrir_perfil()
        elif acao == a_mat:
            self._matricular()
        elif acao == a_bloq:
            self._toggle_bloqueio()
        elif acao == a_inat:
            self._acao("inativar")

    def _abrir_perfil(self) -> None:
        sel = self._selecionado()
        if sel is None:
            return
        aluno_id, _nome = sel
        self.abrir_perfil_por_id(aluno_id)

    def abrir_perfil_por_id(self, aluno_id: str, aba_inicial: int = 0) -> None:
        """Abre o perfil direto pelo id (uso do click-through do dashboard/caixa)."""
        if self.pagamentos_vm is None:
            QMessageBox.warning(self, "Alunos", "Módulo de pagamentos indisponível.")
            return
        try:
            dlg = PerfilAlunoDialog(
                self.vm,
                self.pagamentos_vm,
                aluno_id,
                self,
                frequencia_vm=self.frequencia_vm,
                dashboard_vm=self.dashboard_vm,
                aba_inicial=aba_inicial,
            )
        except ValueError as e:
            QMessageBox.warning(self, "Alunos", str(e))
            return
        dlg.exec()
        self.recarregar()

    def _novo(self) -> None:
        dlg = NovoAlunoDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        d = dlg.dados()
        if not d["nome"].strip():
            QMessageBox.warning(self, "Alunos", "Nome é obrigatório.")
            return
        nasc: date | None = None
        if d["data_nasc"]:
            try:
                nasc = date.fromisoformat(d["data_nasc"])
            except ValueError:
                QMessageBox.warning(self, "Alunos", "Nascimento inválido (use AAAA-MM-DD).")
                return
        foto_src = d.get("foto", "")
        foto_dst = None
        if foto_src and Path(foto_src).exists():  # type: ignore[arg-type]
            try:
                dst_dir = Path("data/fotos/alunos")
                dst_dir.mkdir(parents=True, exist_ok=True)
                ext = Path(foto_src).suffix or ".jpg"  # type: ignore[arg-type]
                # id ainda não existe, usa temp; após cadastrar copia
                foto_dst = foto_src
            except Exception:
                foto_dst = foto_src
        try:
            aluno = self.vm.cadastrar(
                nome=d["nome"],
                cpf=d["cpf"],
                data_nasc=nasc,
                telefone=d["telefone"],
                email=d["email"],
                observacoes=d["observacoes"],
                endereco=d["endereco"],
                senha=d["senha"],
                foto=foto_dst,
            )
            # se foto selecionada, copia para pasta definitiva com id
            if foto_src and Path(foto_src).exists():  # type: ignore[arg-type]
                try:
                    dst_dir = Path("data/fotos/alunos")
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    ext = Path(foto_src).suffix or ".jpg"  # type: ignore[arg-type]
                    dst = dst_dir / f"{aluno.id}{ext}"
                    import shutil

                    shutil.copy2(foto_src, dst)
                    # atualiza com caminho definitivo
                    self.vm.atualizar(aluno.id, nome=aluno.nome, cpf=aluno.cpf, data_nasc=nasc, telefone=aluno.telefone, email=aluno.email, observacoes=aluno.observacoes, endereco=aluno.endereco, senha=d["senha"], status=aluno.status, foto=str(dst))  # noqa: E501
                except Exception as e:
                    logger.warning(f"[UI] falha ao copiar foto {e}")
        except ValueError as e:
            QMessageBox.warning(self, "Alunos", str(e))
            return
        logger.info(f"[UI] aluno cadastrado id={aluno.id}")
        self.recarregar()

    def _acao(self, qual: str) -> None:
        sel = self._selecionado()
        if sel is None:
            return
        aluno_id, _nome = sel
        try:
            if qual == "bloquear":
                self.vm.bloquear(aluno_id)
            elif qual == "desbloquear":
                self.vm.desbloquear(aluno_id)
            else:
                atual = self.vm.alunos.buscar(aluno_id)
                if atual is not None and atual.status == StatusAluno.INATIVO:
                    self.vm.reativar(aluno_id)
                else:
                    self.vm.inativar(aluno_id)
        except ValueError as e:
            QMessageBox.warning(self, "Alunos", str(e))
            return
        self.recarregar()

    def _matricular(self) -> None:
        sel = self._selecionado()
        if sel is None:
            return
        aluno_id, aluno_nome = sel
        planos = [(p.id, f"{p.nome} ({p.duracao_dias}d)") for p in self.vm.planos_disponiveis()]
        if not planos:
            QMessageBox.information(self, "Alunos", "Cadastre um plano primeiro (aba Planos).")
            return
        dlg = MatricularDialog(aluno_nome, planos, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.vm.matricular(aluno_id, dlg.plano_id(), dlg.inicio())
        except (ValueError, RuntimeError) as e:
            QMessageBox.warning(self, "Alunos", str(e))
            return
        QMessageBox.information(self, "Alunos", f"{aluno_nome} matriculado com sucesso.")
