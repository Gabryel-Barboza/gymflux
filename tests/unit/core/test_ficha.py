"""Ficha de avaliação física + saúde — validações."""

from __future__ import annotations

from datetime import date

import pytest

from gymflux.core.ficha import AvaliacaoFisica


def test_ficha_campos_validos_e_resumo():
    ava = AvaliacaoFisica(
        id="ava-1",
        aluno_id="al-1",
        data=date(2026, 9, 15),
        peso_kg=75.5,
        altura_cm=178,
        gordura_pct=12.3,
        medidas={"braco_esq": 30, "braco_dir": 31, "peito": 95, "cintura": 80},
        problemas_saude="Hipertensão leve",
        restricoes="Joelho direito",
        medicamentos="Losartana",
        contato_emergencia="Maria 11999999999",
    )
    assert ava.peso_kg == 75.5
    assert "Braço Esq 30cm" in ava.resumo_fisico()
    assert "Braço Dir 31cm" in ava.resumo_fisico()
    assert "15/09/2026" in ava.resumo_fisico()
    assert "Problemas de saúde: Hipertensão leve" in ava.saude_resumo()
    assert "Contato de emergência: Maria" in ava.saude_resumo()


def test_ficha_medidas_normaliza_e_ignora_invalidas():
    ava = AvaliacaoFisica(
        id="ava-1",
        aluno_id="al-1",
        data=date.today(),
        medidas={"braco_esq": "30", "invalido": 999, "peito": 0, "cintura": "abc"},
    )
    assert ava.medidas == {"braco_esq": 30.0}
    assert "Braço Esq" in ava.resumo_fisico()
    assert "Peito" not in ava.resumo_fisico()


def test_ficha_valores_positivos():
    with pytest.raises(ValueError, match="Peso"):
        AvaliacaoFisica(id="a", aluno_id="al", data=date.today(), peso_kg=-5)
    with pytest.raises(ValueError, match="Altura"):
        AvaliacaoFisica(id="a", aluno_id="al", data=date.today(), altura_cm=0)
    with pytest.raises(ValueError, match="Gordura"):
        AvaliacaoFisica(id="a", aluno_id="al", data=date.today(), gordura_pct=150)
    with pytest.raises(ValueError, match="Gordura"):
        AvaliacaoFisica(id="a", aluno_id="al", data=date.today(), gordura_pct="abc")


def test_ficha_textos_normaliza_vazio_para_none():
    ava = AvaliacaoFisica(
        id="a",
        aluno_id="al",
        data=date.today(),
        problemas_saude="  ",
        restricoes="",
        contato_emergencia="  Maria  ",
    )
    assert ava.problemas_saude is None
    assert ava.restricoes is None
    assert ava.contato_emergencia == "Maria"
    assert ava.saude_resumo() == "Contato de emergência: Maria"


def test_ficha_medidas_json():
    ava = AvaliacaoFisica(id="a", aluno_id="al", data=date.today(), medidas={"braco_esq": 30})
    js = ava.medidas_json()
    assert "braco_esq" in js
    assert AvaliacaoFisica.from_json_medidas(js) == {"braco_esq": 30.0}
    # legado sem lado mapeia para ambos
    assert AvaliacaoFisica.from_json_medidas('{"braco": 30}') == {
        "braco_esq": 30.0,
        "braco_dir": 30.0,
    }
    assert AvaliacaoFisica.from_json_medidas(None) == {}
    assert AvaliacaoFisica.from_json_medidas("") == {}


def test_ficha_bilateral_assimetria():
    ava = AvaliacaoFisica(
        id="a",
        aluno_id="al",
        data=date.today(),
        medidas={"braco_esq": 30, "braco_dir": 32, "coxa_esq": 50, "coxa_dir": 51},
    )
    txt = ava.resumo_fisico()
    assert "Braço Esq 30cm" in txt
    assert "Braço Dir 32cm" in txt
    assert "Coxa Esq 50cm" in txt
    assert txt.count("Braço") == 2
