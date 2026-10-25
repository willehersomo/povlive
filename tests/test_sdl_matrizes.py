"""Leitura do código (blocos, expressões) e matrizes das transformações."""
import math, subprocess

import pytest

from conftest import precisa_povray
from povlive_app import sdl, matrizes as M, pov


def test_blocos_e_objeto_sob_o_cursor():
    t = "union {\n  sphere { <0,1,0>, 1 }  // comentário com { chave\n  box { 0, 1 }\n}\n"
    b = sdl.objeto_em(t, t.index("<0,1,0>"))
    assert b.kw == "sphere" and b.pai.kw == "union"
    assert sdl.objeto_em(t, t.index("box") + 5).kw == "box"
    assert len(sdl.blocos(t)) == 3   # a chave dentro do comentário não conta


@pytest.mark.parametrize("expr,esperado", [
    ("2*3+1", 7.0), ("-<1,2,3>", (-1.0, -2.0, -3.0)), ("45*y", (0.0, 45.0, 0.0)),
    ("<1, 2, 3>*2", (2.0, 4.0, 6.0)), ("sin(pi/2)", 1.0), ("(1+2)*x", (3.0, 0.0, 0.0)),
    ("radians(180)", math.pi), ("<1,2>", (1.0, 2.0, 0.0)),
])
def test_expressoes(expr, esperado):
    v, _ = sdl.avaliar(expr)
    if isinstance(esperado, tuple):
        assert all(abs(a - b) < 1e-9 for a, b in zip(v, esperado))
    else:
        assert abs(v - esperado) < 1e-9


def test_expressao_para_no_proximo_comando():
    t = "rotate 45*y translate x"
    v, fim = sdl.avaliar(t, len("rotate"))
    assert v == (0.0, 45.0, 0.0) and t[fim:].strip().startswith("translate")


def test_variavel_do_for_e_desconhecida():
    with pytest.raises(sdl.Desconhecido):
        sdl.avaliar("i*30")


def test_variaveis_declaradas():
    vs = sdl.variaveis("#declare R = 2;\n#declare P = <R, 0, 1>*2;\n#declare Obj = sphere { 0, 1 }\n")
    assert vs["R"] == 2.0 and vs["P"] == (4.0, 0.0, 2.0) and "Obj" not in vs


def test_rotacao_segue_o_povray():
    """rotate <0,0,90> leva x até y (regra da mão esquerda) — conferido no POV-Ray."""
    p = M.aplicar(M.R("z", 90), (1, 0, 0))
    assert all(abs(a - b) < 1e-9 for a, b in zip(p, (0, 1, 0)))
    p = M.aplicar(M.R("y", 90), (1, 0, 0))
    assert all(abs(a - b) < 1e-9 for a, b in zip(p, (0, 0, -1)))


def test_nomes_da_aula():
    passos = M.passos_de("rotate", (0.0, 0.0, 30.0), "rotate <0,0,30>")
    assert "M_rah(30°) = M_r(-30°)" in passos[0][2]
    passos = M.passos_de("scale", (-1.0, 1.0, 1.0), "scale <-1,1,1>")
    assert "M_fx" in passos[0][2]


def test_ordem_das_matrizes_na_convencao_da_aula():
    t = "sphere { 0, 1 translate <2,0,0> rotate <0,0,90> }"
    d = M.analisar(t, 5)
    assert [p["nome"].split("(")[0] for p in d["passos"]] == ["T", "R<sub>z</sub>"]
    html_aula = M.html(d, "aula")
    assert "M2·M1" in html_aula and "M1·M2" in M.html(d, "pov")
    o = M.aplicar(d["total"], (0, 0, 0))
    assert all(abs(a - b) < 1e-9 for a, b in zip(o, (0, 2, 0)))


def test_object_inclui_transformacoes_do_declare():
    t = "#declare B = box { 0, 1 translate <1,0,0> }\nobject { B rotate <0,90,0> }\n"
    d = M.analisar(t, t.index("object") + 8)
    assert [p["grupo"].split()[0] for p in d["passos"]] == ["dentro", "object"]


def test_passo_com_variavel_do_for_nao_calcula_total():
    t = "#for (i, 0, 3)\n sphere { 0, 1 rotate <0, i*30, 0> }\n#end\n"
    d = M.analisar(t, t.index("sphere") + 8)
    assert d["total"] is None and d["passos"][0]["matriz"] is None


@precisa_povray
@pytest.mark.parametrize("cadeia", [
    "translate <1,2,3> rotate <0,0,90>",
    "rotate <30,45,60> translate <1,-2,0.5> scale <2,-1,0.5>",
    "scale 2 rotate 45*y translate x*3",
    "matrix <1,0,0, 0.5,1,0, 0,0,1, 1,2,3> rotate <10,20,30>",
])
def test_matriz_final_igual_ao_povray(cadeia, tmp_path):
    """A matriz calculada pelo app transforma um ponto igual ao vtransform do próprio POV-Ray."""
    P = (0.3, -1.2, 2.5)
    cena = f"""#version 3.7;
#include "transforms.inc"
global_settings {{ assumed_gamma 1 }}
#declare V = vtransform(<{P[0]},{P[1]},{P[2]}>, transform {{ {cadeia} }});
#debug concat("RES ", vstr(3, V, " ", 0, 6), "\\n")
camera {{ location -5 look_at 0 }} light_source {{ <0,5,-5> rgb 1 }} sphere {{ 0, 0.1 pigment {{ rgb 1 }} }}
"""
    (tmp_path / "v.pov").write_text(cena)
    r = subprocess.run(pov.comando(["+Iv.pov", "+Oo.png", "+W8", "+H8", "-D"]), cwd=tmp_path,
                       capture_output=True, text=True)
    linha = [l for l in r.stderr.splitlines() if l.startswith("RES ")][0]
    esperado = tuple(map(float, linha.split()[1:4]))
    d = M.analisar("sphere { <0,0,0>, 1 " + cadeia + " }", 10)
    obtido = M.aplicar(d["total"], P)
    assert all(abs(a - b) < 1e-4 for a, b in zip(obtido, esperado)), (obtido, esperado)
