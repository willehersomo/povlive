"""Importar OBJ e STL como mesh2."""
import struct

import numpy as np

from conftest import precisa_povray, renderizar
from povlive_app import importar as I, previa3d as P

OBJ = """# quadrado e triângulo
v 0 0 0
v 1 0 0
v 1 1 0
v 0 1 0
v 0 0 1
f 1 2 3 4
f -5/1/1 -4/2/2 -1/3/3
"""


def test_obj_triangula_e_troca_a_mao():
    V, F = I.ler_obj(OBJ)
    assert F.shape == (3, 3) and np.allclose(V[4], [0, 0, -1])     # z troca de sinal
    assert F[0].tolist() == [2, 1, 0]                                # ordem invertida (normal para fora)
    assert F[2].tolist() == [4, 1, 0]                                # índices negativos


def _stl_binario(tris):
    dados = b"\0" * 80 + struct.pack("<I", len(tris))
    for t in tris:
        dados += struct.pack("<3f", 0, 0, 1) + struct.pack("<9f", *np.ravel(t)) + b"\0\0"
    return dados


def test_stl_binario_e_texto_unem_vertices_e_poem_y_para_cima():
    tris = [[(0, 0, 0), (1, 0, 0), (0, 1, 0)], [(1, 0, 0), (1, 1, 0), (0, 1, 0)], [(0, 0, 0), (0, 0, 2), (1, 0, 0)]]
    V, F = I.ler_stl(_stl_binario(tris))
    assert len(V) == 5 and F.shape == (3, 3)
    assert np.isclose(V[:, 1].max(), 2)              # o z do STL vira o y (altura)
    texto = "solid t\n" + "".join("facet normal 0 0 1\nouter loop\n" + "".join(
        f"vertex {a} {b} {c}\n" for a, b, c in t) + "endloop\nendfacet\n" for t in tris) + "endsolid t\n"
    V2, F2 = I.ler_stl(texto.encode())
    assert np.allclose(V2, V) and (F2 == F).all()


def test_ajustar_e_nome():
    W = I.ajustar(np.array([[10.0, 5, 3], [14, 9, 5]]), 2)
    assert np.allclose(W.min(0), [-1, 0, -0.5]) and np.allclose(W.max(0), [1, 2, 0.5])
    assert I.nome_pov("/x/meu bule (v2).obj") == "Meu_bule_v2" and I.nome_pov("3d.stl") == "M_3d"


@precisa_povray
def test_mesh2_renderiza_e_aparece_na_previa(tmp_path):
    (tmp_path / "bule.obj").write_text(OBJ)
    inc, nome, n = I.importar(str(tmp_path / "bule.obj"), str(tmp_path))
    assert nome == "Bule" and n == 3 and inc.endswith("bule.inc")
    cena = ('#version 3.7;\nglobal_settings { assumed_gamma 1.0 }\n#include "bule.inc"\n'
            "camera { location <2, 3, -4> look_at <0, 0.5, 0> }\nlight_source { <2, 4, -3> rgb 1 }\n"
            "object { Bule pigment { rgb 1 } translate <0, 0, 0> }\n")
    img, log = renderizar(cena, tmp_path, 80, 60)
    assert "Parse Warning" not in log and "Possible" not in log and img.max() > 50
    c = P.interpretar(cena, str(tmp_path))
    assert len(c.pecas) == 1 and len(c.pecas[0].tris) == 3
    lo, hi = c.pecas[0].tris.reshape(-1, 3).min(0), c.pecas[0].tris.reshape(-1, 3).max(0)
    assert np.isclose(lo[1], 0) and np.isclose(max(hi - lo), 2)


@precisa_povray
def test_importar_pelo_menu(qapp, tmp_path, monkeypatch):
    from PyQt5.QtCore import QSettings
    from PyQt5.QtWidgets import QFileDialog
    from conftest import cena, esperar
    QSettings.setPath(QSettings.NativeFormat, QSettings.UserScope, str(tmp_path / "config"))
    from povlive_app.janela import Janela
    (tmp_path / "cubo.obj").write_text(OBJ)
    j = Janela([cena("boneco.pov", tmp_path)])
    j.show()
    try:
        assert esperar(qapp, lambda: j.status.currentMessage().startswith("OK"), 30)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(tmp_path / "cubo.obj"), "")))
        j.importar_modelo()
        t = j.cena.toPlainText()
        assert '#include "cubo.inc"' in t and "object {\n    Cubo\n" in t and (tmp_path / "cubo.inc").exists()
        j.pedir_render()
        assert esperar(qapp, lambda: j.status.currentMessage().startswith("OK"), 30)
    finally:
        j.cena.document().setModified(False)
        j.close()
