"""FrequenciaView global — filtros (construção direta)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from gymflow.core.acesso import DirecaoAcesso, ResultadoAcesso, TentativaAcesso
from gymflow.ui.app import AppContext
from gymflow.ui.views.frequencia import FrequenciaView


def test_frequencia_global_filtra(qtbot, ctx: AppContext):
    aluno = ctx.alunos_vm.cadastrar(nome="Ana Silva", cpf="11144477735")
    repo = ctx.dashboard_vm.acesso.acesso_repo
    assert repo is not None
    hoje = date.today()
    repo.registrar(
        TentativaAcesso(
            aluno_id=aluno.id,
            direcao=DirecaoAcesso.ENTRADA,
            timestamp=datetime(hoje.year, hoje.month, hoje.day, 8, 0),
            resultado=ResultadoAcesso.LIBERADO,
        )
    )
    repo.registrar(
        TentativaAcesso(
            aluno_id="aluno-fantasma",
            direcao=DirecaoAcesso.ENTRADA,
            timestamp=datetime(hoje.year, hoje.month, hoje.day, 9, 0) - timedelta(days=1),
            resultado=ResultadoAcesso.NEGADO,
        )
    )
    view = FrequenciaView(ctx.frequencia_vm)
    qtbot.addWidget(view)
    assert view.tbl.rowCount() == 1  # dia de hoje por padrão
    assert "Ana Silva" in view.tbl.item(0, 1).text()  # type: ignore[union-attr]
    # filtra por aluno => só Ana; sem filtro de dia => todos dela; Todos => tudo
    view.cmb_aluno.setCurrentIndex(view.cmb_aluno.findText("Ana Silva"))
    assert view.tbl.rowCount() == 1
    view.chk_dia.setChecked(False)
    assert view.tbl.rowCount() == 1  # ainda filtrado por Ana
    view.cmb_aluno.setCurrentIndex(0)  # Todos
    assert view.tbl.rowCount() == 2
    assert "registro(s)" in view.lbl_total.text()
