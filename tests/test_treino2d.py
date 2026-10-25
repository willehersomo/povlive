"""Treino de transformações 2D (convenção da aula: M_r horária, ponto em coluna)."""
import math

import numpy as np
import pytest

from povlive_app import treino2d as T, i18n


def test_convencao_da_aula():
    # M_r é horária: (1, 0) girado 90° vai para (0, -1); M_rah é a anti-horária
    assert np.allclose(T.M_r(90) @ [1, 0, 1], [0, -1, 1])
    assert np.allclose(T.M_rah(90) @ [1, 0, 1], [0, 1, 1])
    assert np.allclose(T.M_fx @ [2, 3, 1], [-2, 3, 1])
    # rotação em torno de um ponto: o próprio ponto não sai do lugar
    q = T.Questao(1)
    q.ops = [("Rp", 90, 2, 1)]
    assert np.allclose(q.matriz() @ [2, 1, 1], [2, 1, 1])
    assert np.allclose(q.matriz() @ [3, 1, 1], [2, 0, 1])


def test_ordem_ultima_a_esquerda():
    q = T.Questao(1)
    q.ops = [("T", 1, 0), ("R", 90)]          # primeiro translada, depois gira
    q.figura = T.FIGURA_AULA
    assert np.allclose(q.matriz(), T.M_r(90) @ T.M_t(1, 0))
    assert q.pontos()[0][1] == pytest.approx((1, -2))   # A(1,1) -> (2,1) -> (1,-2)


def test_mesma_questao_pelo_numero_e_niveis():
    a, b = T.Questao(42, "dificil"), T.Questao(42, "dificil")
    assert a.ops == b.ops and a.figura == b.figura
    for nivel, (lo, hi) in T.NIVEIS.items():
        for n in range(1, 60):
            q = T.Questao(n, nivel)
            assert lo <= len(q.ops) <= hi
            M = q.matriz()
            assert np.allclose(M[2], [0, 0, 1]) and np.isfinite(M).all()


def test_ler_numero():
    for t, v in (("0,866", 0.866), ("-1/2", -0.5), ("√3/2", math.sqrt(3) / 2), ("sqrt(2)/2", math.sqrt(2) / 2),
                 ("cos(60)", 0.5), ("−2", -2), (" 3 ", 3), ("2^2", 4)):
        assert T.ler_numero(t) == pytest.approx(v)
    for ruim in ("", "abc", "import os", "1/0", "__import__('os')"):
        with pytest.raises(T.EntradaInvalida):
            T.ler_numero(ruim)


@pytest.mark.parametrize("idioma", ["pt", "en"])
def test_solucao_e_enunciado(idioma):
    i18n.definir(idioma)
    q = T.Questao(5, "dificil")
    html = q.enunciado() + q.solucao_html()
    assert "M1" in html and ("Solução" if idioma == "pt" else "Solution") in html


def test_janela_confere(qapp):
    from povlive_app.treino2d_ui import Treino2D
    d = Treino2D()
    d.show()
    try:
        d.sp_num.setValue(123)
        M = d.q.matriz()
        for i in range(3):
            for j in range(3):
                d.campos_m[i][j].setText(T.fmt(M[i, j]).replace(".", ","))
        for (cx, cy), (_, (x, y)) in zip(d.campos_p, d.q.pontos()):
            cx.setText(T.fmt(x))
            cy.setText(T.fmt(y))
        assert d.conferir() == (9, 2 * len(d.campos_p))
        d.campos_p[0][0].setText("999")
        assert d.conferir()[1] == 2 * len(d.campos_p) - 1
        d.mostrar_solucao()
        assert "M =" in d.solucao.toPlainText()
    finally:
        d.close()
