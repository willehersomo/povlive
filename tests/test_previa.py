"""Prévia instantânea: interpretador da cena, geometria, desenho em OpenGL e setas."""
import math

import numpy as np
import pytest

from conftest import precisa_povray, renderizar, esperar, cena
from povlive_app import previa3d as P, selecao, sdl


def caixa_limites(cena3d, topo_kw=None):
    pts = np.concatenate([p.tris.reshape(-1, 3) for p in cena3d.pecas
                          if topo_kw is None or p.topo.kw == topo_kw])
    return pts.min(0), pts.max(0)


def test_esfera_com_transformacoes():
    c = P.interpretar("sphere { <0, 1, 0>, 1 scale 2 translate <3, 0, 0> }")
    lo, hi = caixa_limites(c)
    assert np.allclose(lo, [1, 0, -2], atol=0.05) and np.allclose(hi, [5, 4, 2], atol=0.05)


def test_for_if_macro_e_declare():
    t = """#declare N = 4;
#declare Bola = sphere { 0, 0.2 }
#macro Torre(H) box { <0,0,0>, <1, H, 1> } #end
#for (i, 0, N - 1)
  #if (mod(i, 2) = 0)
    object { Bola translate <i, 0, 0> }
  #else
    cylinder { <i,0,0>, <i,1,0>, 0.1 }
  #end
#end
Torre(3)
object { Torre(2) translate <5, 0, 0> }
"""
    c = P.interpretar(t)
    kws = sorted(p.topo.kw for p in c.pecas)
    assert kws.count("object") == 3 and kws.count("cylinder") == 2   # 2 esferas + Torre(2); 2 cilindros
    assert kws.count("box") == 1                                     # Torre(3) chamada direto
    lo, hi = caixa_limites(c, "box")
    assert np.isclose(hi[1], 3)


def test_cores_dos_formatos_do_povray():
    c = P.interpretar('#include "colors.inc"\nsphere { 0, 1 pigment { color SkyBlue } }\n'
                      'box { 0, 1 pigment { color red 1 green 0.5 blue 0 } }\n'
                      'sphere { 0, 1 pigment { White } }\nsphere { 0, 1 pigment { rgbf <1, 1, 1, 0.9> } }')
    cores = [p.cor for p in c.pecas]
    assert np.allclose(cores[0], (0.196078, 0.6, 0.8), atol=1e-4)    # sintaxe antiga do colors.inc
    assert np.allclose(cores[1], (1, 0.5, 0)) and np.allclose(cores[2], (1, 1, 1))
    assert len(cores[3]) == 4 and cores[3][3] == 0.9                 # transparência (filter)


def test_camera_com_rotate_e_ortografica():
    c = P.interpretar("camera { location <0, 0, -5> look_at 0 rotate <0, 90, 0> }")
    assert np.allclose(c.camera["location"], [-5, 0, 0], atol=1e-9)
    c = P.interpretar("camera { orthographic location <0,0,-10> look_at 0 right x*8 up y*6 }")
    assert c.camera["orto"] == 3


def test_difference_e_intersection_recortam():
    from povlive_app import csg
    # caixa menos esfera grande: sobram só os cantos (nenhum ponto perto do centro das faces)
    c = P.interpretar("difference { box { -1, 1 } sphere { 0, 1.3 } }")
    pts = np.concatenate([p.tris.reshape(-1, 3) for p in c.pecas])
    assert np.all(np.linalg.norm(pts, axis=1) >= 1.27)     # a esfera de triângulos fica um pouco para dentro
    assert {round(float(v), 3) for v in pts.max(0)} == {1.0}
    # meia esfera: nada acima do plano, e a tampa plana aparece
    c = P.interpretar("intersection { sphere { 0, 1 } plane { y, 0.25 } }")
    pts = np.concatenate([p.tris.reshape(-1, 3) for p in c.pecas])
    assert pts[:, 1].max() <= 0.25 + 1e-6 and np.isclose(pts[:, 1].min(), -1, atol=0.01)
    tampa = [p for p in c.pecas if np.allclose(p.tris[:, :, 1], 0.25)]
    assert tampa and tampa[0].xadrez is None
    # sólido do resultado (para CSG dentro de CSG) com as transformações
    c = P.interpretar("difference { box { -1, 1 } cylinder { -2*x, 2*x, 0.5 } translate <5, 0, 0> }")
    s = c.pecas[0].solido
    assert list(s.dentro(np.array([[5.0, 0, 0], [5.0, 0.9, 0.9], [0.0, 0, 0]]))) == [False, True, False]
    assert csg.prisma(0, 1, [(0, 0), (1, 0), (0, 1)]).dentro(np.array([[0.2, 0.5, 0.2], [0.8, 0.5, 0.8]])).tolist() \
        == [True, False]


def test_recorte_do_csg_fica_guardado():
    t = "difference { box { -1, 1 } sphere { 0, R } translate <X, 0, 0> }"
    P._cache_csg.clear()
    P.interpretar("#declare R = 1.2; #declare X = 0;" + t)
    assert len(P._cache_csg) == 1
    P.interpretar("#declare R = 1.2; #declare X = 3;" + t)      # só moveu: reaproveita
    assert len(P._cache_csg) == 1
    P.interpretar("#declare R = 1.3; #declare X = 3;" + t)      # mudou o furo: recorta de novo
    assert len(P._cache_csg) == 2


def test_projetar_centro_da_tela():
    (x, y), = P.projetar([(0, 1, 0)], (0, 1, -5), (0, 1, 0), math.radians(60), 4 / 3)
    assert abs(x - 0.5) < 1e-9 and abs(y - 0.5) < 1e-9


def test_garantir_rotate_antes_do_translate():
    t = "box {\n    0, 1\n}\n"
    b = sdl.blocos(t)[0]
    novo, (ini, fim, v) = selecao.garantir_rotate(t, b)
    assert novo[ini:fim] == "<0, 0, 0>" and "rotate <0, 0, 0> translate <0, 0, 0>" in novo
    b2 = selecao.bloco_em(novo, b.kw_ini)
    novo2, (ini2, fim2, _) = selecao.garantir_rotate(novo, b2)
    assert novo2 == novo and (ini2, fim2) == (ini, fim)   # reaproveita o rotate existente


@pytest.fixture(scope="module")
def renderizador(qapp):
    r = P.Renderizador()
    if not r.disponivel:
        pytest.skip("OpenGL indisponível")
    return r


@precisa_povray
def test_silhueta_da_previa_bate_com_o_povray(renderizador, tmp_path):
    """Objetos chapados num fundo preto: a área ocupada na prévia e no POV-Ray tem que coincidir."""
    texto = """#version 3.7;
global_settings { assumed_gamma 1.0 }
camera { location <1, 2.5, -6> look_at <0, 0.8, 0> angle 55 }
light_source { <3, 5, -4> rgb 1 }
sphere { <-1, 1, 0>, 0.8 pigment { rgb <1, 0, 0> } finish { ambient 1 diffuse 0 } }
box { <0.5, 0, -0.5>, <1.5, 1.6, 0.5> pigment { rgb <0, 0, 1> } finish { ambient 1 diffuse 0 } rotate <0, 30, 0> }
cone { <0, 0, 2>, 0.6, <0, 2, 2>, 0 pigment { rgb <0, 1, 0> } finish { ambient 1 diffuse 0 } }
"""
    assert _iou(renderizador, texto, tmp_path) > 0.93


@precisa_povray
def test_silhueta_do_csg_bate_com_o_povray(renderizador, tmp_path):
    texto = """#version 3.7;
global_settings { assumed_gamma 1.0 }
camera { location <1, 3, -6> look_at <0, 0.5, 0> angle 60 }
light_source { <3, 5, -4> rgb 1 }
#declare F = finish { ambient 1 diffuse 0 };
difference {
  intersection { box { -1, 1 } sphere { 0, 1.4 } }
  sphere { <0, 0, -1.15>, 0.3 }
  cylinder { <0.4, -2, 0>, <0.4, 2, 0>, 0.2 }
  pigment { rgb <0.9, 0.9, 0.9> } finish { F }
  rotate <0, 25, 0> translate <-2, 1, 0>
}
intersection { sphere { 0, 1 } plane { y, 0.2 } pigment { rgb <0.2, 0.5, 1> } finish { F } translate <1.2, 1, 0> }
difference { cylinder { 0, 1.5*y, 0.6 } cylinder { -0.1*y, 1.6*y, 0.45 } pigment { rgb <0.2, 0.8, 0.3> }
             finish { F } translate <2.8, 0, 1> }
difference { torus { 0.8, 0.25 } box { <0, -1, -2>, <2, 1, 2> } pigment { rgb <1, 0.6, 0> } finish { F }
             rotate <-60, 0, 0> translate <0, 1.6, 2> }
"""
    assert _iou(renderizador, texto, tmp_path) > 0.97


def _iou(renderizador, texto, tmp_path):
    w, h = 320, 240
    real, _ = renderizar(texto, tmp_path, w, h)
    c = P.interpretar(texto)
    cam = c.camera
    img = renderizador.desenhar(c, cam["location"], cam["look_at"], math.radians(cam["angle"]), w, h)
    img = img.convertToFormat(img.Format_RGB888)
    ptr = img.constBits()
    ptr.setsize(img.byteCount())
    prev = np.frombuffer(ptr, np.uint8).reshape(h, img.bytesPerLine())[:, :w * 3].reshape(h, w, 3)
    a, b = real.max(axis=2) > 30, prev.max(axis=2) > 30
    return (a & b).sum() / (a | b).sum()


@pytest.fixture
def janela(qapp, monkeypatch, tmp_path):
    from PyQt5.QtCore import QSettings
    QSettings.setPath(QSettings.NativeFormat, QSettings.UserScope, str(tmp_path / "config"))
    from povlive_app.janela import Janela
    criadas = []

    def abrir(*arquivos):
        j = Janela(list(arquivos))
        j.show()
        j.resize(1300, 850)
        criadas.append(j)
        return j
    yield abrir
    for j in criadas:
        for e in j._editores():
            e.document().setModified(False)
        j.close()


@precisa_povray
def test_seta_x_move_o_objeto(janela, qapp, tmp_path):
    from PyQt5.QtGui import QColor
    j = janela(cena("boneco.pov", tmp_path))
    ok = lambda: j.status.currentMessage().startswith("OK")
    assert esperar(qapp, lambda: ok() and j.sel is not None and j.sel["chave"] == j._sel_chave())
    img, mapa = j.sel["img"], j.sel["mapa"]
    i_caixa = [i for i, b in mapa.items() if b.kw == "box"][0]
    alvo = next(((x + .5) / img.width(), (y + .5) / img.height())
                for y in range(0, img.height(), 2) for x in range(0, img.width(), 2)
                if selecao.id_da_cor(*QColor(img.pixel(x, y)).getRgb()[:3]) == i_caixa)
    j.visor.clicou.emit(*alvo)
    assert j.visor.gizmo and j.visor.gizmo["x"] is not None
    v = j.visor
    v.gizmo_sinal.emit("inicio", "x", 0, 0, 0)
    v.gizmo_sinal.emit("mover", "x", 80, 0, 0)
    v.gizmo_sinal.emit("fim", "x", 80, 0, 0)
    texto = j.cena.toPlainText()
    tf = selecao.translate_final(texto, [b for b in sdl.blocos(texto) if b.kw == "box"][0])
    assert tf[2][0] > 2.5 and tf[2][1] == 0 and tf[2][2] == 0   # câmera de frente: arrastar para a direita aumenta x
