"""Treino 3D: transformações (M_r horária da aula), câmera/projeção e Phong, conferidos com o POV-Ray."""
import subprocess

import numpy as np
import pytest

from conftest import precisa_povray, renderizar
from povlive_app import treino3d as T, treino2d, matrizes, i18n, pov

CASOS = [(n, nivel) for nivel in ("facil", "medio", "dificil") for n in (1, 7, 42, 300)]


def test_convencao_da_aula():
    # M_rz é o M_r do 2D (horária) no plano xy; as anti-horárias são o rotate do POV-Ray
    assert np.allclose(T.M_r("z", 30)[np.ix_([0, 1, 3], [0, 1, 3])], treino2d.M_r(30))
    for e in "xyz":
        assert np.allclose(T.M_rah(e, 37), matrizes.R(e, 37))
        assert np.allclose(T.M_r(e, 37), T.M_rah(e, 37).T)
    assert np.allclose(T.M_r("z", 90) @ [1, 0, 0, 1], [0, -1, 0, 1])
    assert np.allclose(T.M_f("z") @ [1, 2, 3, 1], [1, 2, -3, 1])
    # rotação em torno de uma reta paralela ao eixo: os pontos da reta não saem do lugar
    q = T.QuestaoTransformacao(1)
    q.ops = [("Rp", "y", 90, 1, 0, 2)]
    assert np.allclose(q.matriz() @ [1, 5, 2, 1], [1, 5, 2, 1])


def test_mesma_questao_pelo_numero_e_niveis():
    for modo in T.MODOS:
        a, b = T.questao(modo, 42, "dificil"), T.questao(modo, 42, "dificil")
        assert a.enunciado() == b.enunciado()
    for nivel, (lo, hi) in T.NIVEIS.items():
        for n in range(1, 60):
            q = T.QuestaoTransformacao(n, nivel)
            assert lo <= len(q.ops) <= hi
            M = q.matriz()
            assert np.allclose(M[3], [0, 0, 0, 1]) and np.isfinite(M).all()


@pytest.mark.parametrize("n,nivel", CASOS)
def test_camera_base_e_pontos_validos(n, nivel):
    q = T.QuestaoCamera(n, nivel)
    u, v, w = T.base_da_camera(q.olho, q.alvo)
    B = np.array([u, v, w])
    assert np.allclose(B @ B.T, np.eye(3))               # ortonormal
    assert np.allclose(np.cross(u, v), w)                # mão esquerda do POV-Ray vista como det = +1
    V = q.visao()
    assert np.allclose(V @ [*q.olho, 1], [0, 0, 0, 1])   # a câmera vai para a origem
    c = V @ [*q.alvo, 1]
    assert np.allclose(c[:2], 0) and c[2] > 0            # o alvo fica no eixo +z da câmera
    assert len(q.pontos_mundo) >= 2
    assert all(c[2] >= 1 for _, c in q.na_camera())


@pytest.mark.parametrize("n,nivel", CASOS)
def test_phong_valores(n, nivel):
    q = T.QuestaoPhong(n, nivel)
    v = q.vetores()
    assert np.linalg.norm(v["L"]) == pytest.approx(1) and np.linalg.norm(v["V"]) == pytest.approx(1)
    assert v["NL"] > 0 and np.linalg.norm(v["R"]) == pytest.approx(1)
    assert 0 < v["I"] <= 1


@pytest.mark.parametrize("idioma", ["pt", "en"])
def test_textos_dos_tres_modos(idioma):
    i18n.definir(idioma)
    for modo in T.MODOS:
        for nivel in T.NIVEIS:
            q = T.questao(modo, 5, nivel)
            html = q.enunciado() + q.solucao_html() + T.formulas_html(modo)
            assert ("Solução" if idioma == "pt" else "Solution") in html
            assert q.respostas() and "#version 3.7" in q.pov_cena()


def _executar(cena, pasta):
    (pasta / "v.pov").write_text(cena)
    r = subprocess.run(pov.comando(["+Iv.pov", "+Oo.png", "+W8", "+H8", "-D"]), cwd=pasta,
                       capture_output=True, text=True)
    return [linha for linha in r.stderr.splitlines() if linha.startswith("RES ")]


@precisa_povray
def test_transformacoes_iguais_ao_povray(tmp_path):
    """O código SDL da solução, rodado pelo POV-Ray (vtransform), leva cada ponto ao mesmo lugar."""
    linhas, esperado = [], []
    for n, nivel in CASOS:
        q = T.QuestaoTransformacao(n, nivel)
        cadeia = " ".join(T.pov_da_op(op) for op in q.ops)
        for (_, p), (_, alvo) in zip(q.figura, q.pontos()):
            linhas.append(f'#debug concat("RES ", vstr(3, vtransform({T._pov(p)}, transform {{ {cadeia} }}), '
                          f'" ", 0, 6), "\\n")')
            esperado.append(alvo)
    cena = ("#version 3.7;\n#include \"transforms.inc\"\n" + "\n".join(linhas) +
            "\ncamera { location -5 look_at 0 } light_source { <0,5,-5> rgb 1 } sphere { 0, 0.1 pigment { rgb 1 } }\n")
    res = _executar(cena, tmp_path)
    assert len(res) == len(esperado)
    for linha, alvo in zip(res, esperado):
        assert np.allclose(list(map(float, linha.split()[1:4])), alvo, atol=1e-4), (linha, alvo)


@precisa_povray
@pytest.mark.parametrize("n,nivel", [(1, "facil"), (2, "facil"), (2, "medio"), (4, "dificil"), (3, "dificil")])
def test_pixel_igual_ao_povray(n, nivel, tmp_path):
    """Uma esfera pequena e brilhante em cada ponto aparece no pixel calculado (±1,5 px)."""
    q = T.QuestaoCamera(n, nivel)
    for (_, p), (_, (px, py)) in zip(q.pontos_mundo, q.pixels()):
        cena = (f"#version 3.7;\nglobal_settings {{ assumed_gamma 1 }}\n{q.codigo_camera()}\nbackground {{ rgb 0 }}\n"
                f"sphere {{ {T._pov(p)}, 0.04 pigment {{ rgb 1 }} finish {{ emission 1 diffuse 0 ambient 0 }} }}\n")
        img, _ = renderizar(cena, tmp_path, T.W, T.H)
        m = img.astype(float).sum(2)
        ys, xs = np.nonzero(m > 30)
        pesos = m[ys, xs]
        cx = (xs * pesos).sum() / pesos.sum() + 0.5
        cy = (ys * pesos).sum() / pesos.sum() + 0.5
        assert abs(cx - px) < 1.5 and abs(cy - py) < 1.5, ((cx, cy), (px, py))


@precisa_povray
@pytest.mark.parametrize("n,nivel", [(1, "facil"), (5, "facil"), (1, "medio"), (5, "medio"), (1, "dificil"),
                                     (5, "dificil")])
def test_phong_igual_ao_povray(n, nivel, tmp_path):
    """Com File_Gamma=1, a cor do pixel do meio (o ponto P) é a intensidade I calculada."""
    q = T.QuestaoPhong(n, nivel)
    img, _ = renderizar(q.pov_cena(), tmp_path, 81, 81, ["File_Gamma=1.0"])
    assert img[40, 40, 0] / 255 == pytest.approx(q.vetores()["I"], abs=0.01)


class _Pai:
    def __init__(self):
        from PyQt5.QtWidgets import QWidget
        self.w = QWidget()
        self.aberto = None

    def abrir_exemplo(self, nome, texto):
        self.aberto = (nome, texto)


def test_janela_confere_os_tres_modos(qapp):
    from povlive_app.treino3d_ui import Treino3D
    d = Treino3D()
    d.show()
    try:
        for i, modo in enumerate(T.MODOS):
            d.cb_modo.setCurrentIndex(i)
            for nivel in range(3):
                d.cb_nivel.setCurrentIndex(nivel)
                d.sp_num.setValue(100 + nivel)
                assert d.q.modo == modo
                total = 0
                for s, linhas in zip(d.secoes, d.campos):
                    for valores, campos in zip(s["valores"], linhas):
                        for v, c in zip(valores, campos):
                            c.setText(T.fmt(v).replace(".", ","))
                            total += 1
                assert d.conferir() == (total, total), (modo, nivel)
                d.campos[0][0][0].setText("999")
                assert d.conferir() == (total - 1, total)
                d.mostrar_solucao()
                assert d.solucao.toPlainText()
                d.vista.grab()
                d.tela.grab()
        assert not d.bt_pov.isEnabled()
    finally:
        d.close()


def test_ver_no_povray_abre_a_cena(qapp):
    from povlive_app.treino3d_ui import Treino3D
    pai = _Pai()
    d = Treino3D(pai.w)
    d.parent = lambda: pai          # o botão só usa o abrir_exemplo do pai
    d.ver_no_povray()
    assert pai.aberto and "#version 3.7" in pai.aberto[1]
    d.close()
