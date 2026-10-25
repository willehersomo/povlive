"""Formatador, seleção por cor, avisos, cache de órbita, câmera, exercícios e exemplos do guia."""
import os

import pytest

from conftest import precisa_povray, renderizar, CENAS
from povlive_app import formatador, selecao, avisos, pov, sdl, exercicios as X, guia, cache_orbita as CO, i18n


# ---------------------------------------------------------------- formatador

def test_formatar_reindenta_e_e_idempotente():
    t = "sphere{\n<0,1,0>,1\n  pigment{\ncolor Red}\n}\n#for(i,0,2)\nbox{0,1}\n#end\n"
    f = formatador.formatar(t)
    assert f == "sphere{\n    <0,1,0>,1\n    pigment{\n        color Red}\n}\n#for(i,0,2)\n    box{0,1}\n#end\n"
    assert formatador.formatar(f) == f


def test_formatar_nao_mexe_em_comentario_de_bloco_nem_string():
    t = '/* {\n   texto { livre\n*/\ntext { ttf "a.ttf" "{ }" 1, 0 }\n'
    assert formatador.formatar(t) == t


@precisa_povray
def test_formatar_nao_muda_a_imagem(tmp_path):
    texto = open(os.path.join(CENAS, "boneco.pov")).read()
    import shutil
    shutil.copy(os.path.join(CENAS, "cor.inc"), tmp_path)
    a, _ = renderizar(texto, tmp_path)
    b, _ = renderizar(formatador.formatar(texto), tmp_path)
    assert (a == b).all()


# ---------------------------------------------------------------- seleção

def test_cor_e_id_ida_e_volta():
    for i in (1, 15, 16, 255, 256, 4095):
        r, g, b = (round(c * 255) for c in selecao.cor_do_id(i))
        assert selecao.id_da_cor(r, g, b) == i


@precisa_povray
def test_selecao_identifica_cada_objeto(tmp_path):
    import shutil
    shutil.copy(os.path.join(CENAS, "cor.inc"), tmp_path)
    texto = open(os.path.join(CENAS, "boneco.pov")).read()
    marcado, mapa = selecao.marcar(texto)
    img, _ = renderizar(marcado, tmp_path, 320, 240, ["+Q4"] + selecao.ARGS_EXTRA)
    ids = {selecao.id_da_cor(*map(int, img[y, x])) for y in range(0, 240, 2) for x in range(0, 320, 2)}
    assert ids - {0} <= set(mapa), "toda cor da imagem tem que corresponder a um objeto"
    tipos = {mapa[i].kw for i in ids if i}
    assert {"plane", "object", "sphere", "cone", "box"} <= tipos
    # as esferas dentro do #declare não são marcadas: cada cópia (object) tem a própria cor
    assert all(not (b.declarado or (b.pai and b.pai.declarado)) for b in mapa.values())


def test_translate_inserido_e_reaproveitado():
    t = "box {\n    <0,0,0>, <1,1,1>\n    pigment { Red }\n}\n"
    b = sdl.blocos(t)[0]
    assert selecao.translate_final(t, b) is None
    novo, (i, f) = selecao.inserir_translate(t, b)
    assert novo[i:f] == "<0, 0, 0>" and "    translate <0, 0, 0>\n}" in novo
    b2 = sdl.blocos(novo)[0]
    ini, fim, v = selecao.translate_final(novo, b2)
    assert v == (0.0, 0.0, 0.0) and novo[ini:fim] == "<0, 0, 0>"


def test_topo_e_o_objeto_de_primeiro_nivel():
    t = "union { sphere { 0, 1 } box { 0, 1 } }"
    esfera = [b for b in sdl.blocos(t) if b.kw == "sphere"][0]
    assert selecao.topo(esfera).kw == "union"


# ---------------------------------------------------------------- avisos

SAIDA = """File 'legado.pov' line 4: Parse Warning: Illegal Value: Scale Z by 0.0. Changed to
 1.0.
Possible Parse Error: assumed_gamma not specified in this POV-Ray 3.7 or later
 scene. Future versions of POV-Ray may consider this a fatal error.
Parse Warning: This scene had other declarations preceding the first #version
 directive.
File 'x.pov' line 9: Parse Warning: More than one camera in scene. Ignoring
 previous camera(s).
"""


def test_avisos_lidos_e_traduzidos():
    lista = avisos.ler(SAIDA)
    assert [a["linha"] for a in lista] == [4, None, None, 9]
    assert "eixo Z" in lista[0]["texto"]
    assert [a["correcao"] for a in lista] == [None, "gamma", "versao", None]
    assert len(avisos.ler(SAIDA, ignorar_cameras=True)) == 3


def test_correcoes_rapidas():
    t = "#include \"colors.inc\"\nsphere { 0, 1 }\n"
    v = avisos.corrigir(t, "versao")
    assert v.startswith("#version 3.7;\n")
    g = avisos.corrigir(v, "gamma")
    assert g.split("\n")[1] == "global_settings { assumed_gamma 1.0 }"
    assert "assumed_gamma 1.0 ambient" in avisos.corrigir("global_settings { ambient_light 1 }", "gamma")


@precisa_povray
def test_avisos_de_verdade_do_povray(tmp_path):
    _, saida = renderizar(open(os.path.join(CENAS, "legado.pov")).read(), tmp_path)
    tipos = {a["correcao"] for a in avisos.ler(saida)}
    assert {"gamma", "versao"} <= tipos


# ---------------------------------------------------------------- câmera e cache de órbita

def test_ler_e_gravar_camera():
    t = "camera {\n  location <0, 2, -5>\n  look_at <0, 1, 0>\n  angle 50\n}\nsphere { 0, 1 }"
    c = pov.ler_camera(t)
    assert c["location"] == [0, 2, -5] and c["look_at"] == [0, 1, 0] and c["angle"] == 50
    novo = pov.gravar_camera(t, [1, 2, 3], [0, 0, 0])
    assert "location <1, 2, 3>" in novo and "look_at <0, 0, 0>" in novo and "angle 50" in novo


def test_orbita_preserva_a_posicao():
    o = pov.Orbita(pov.ler_camera("camera { location <1, 2, -5> look_at <0, 1, 0> }"))
    assert all(abs(a - b) < 1e-9 for a, b in zip(o.posicao(), (1, 2, -5)))


def test_cache_cobre_cada_angulo_uma_vez():
    posicoes = {CO.quadro_para_posicao(f) for f in range(1, CO.NPROC * CO.CHUNK + 1)}
    assert len(posicoes) == CO.NY * len(CO.LINHAS)
    # os primeiros quadros de cada processo são os mais prioritários (linha atual, ângulos próximos)
    primeiros = {CO.quadro_para_posicao(p * CO.CHUNK + 1) for p in range(CO.NPROC)}
    assert all(r == 0 and abs(o) <= CO.NPROC // 2 for r, o in primeiros)


# ---------------------------------------------------------------- exercícios e guia

@precisa_povray
@pytest.mark.parametrize("idioma", ["pt", "en"])
@pytest.mark.parametrize("ex", X.EXERCICIOS, ids=[e["id"] for e in X.EXERCICIOS])
def test_exercicio_gabarito_passa_e_inicio_nao(ex, idioma, tmp_path):
    i18n.definir(idioma)
    w, h = X.TAMANHO
    vazio, _ = renderizar(X.texto_vazio(ex), tmp_path, w, h, X.ARGS)
    gab, _ = renderizar(X.texto_gabarito(ex), tmp_path, w, h, X.ARGS)
    ini, _ = renderizar(X.texto_inicial(ex), tmp_path, w, h, X.ARGS)
    assert X.comparar(gab, gab, vazio)[0] == 1.0
    assert X.comparar(ini, gab, vazio)[0] < X.NOTA_MINIMA
    assert X.id_no_texto(X.texto_inicial(ex)) == ex["id"]


@precisa_povray
@pytest.mark.parametrize("idioma", ["pt", "en"])
@pytest.mark.parametrize("id_", sorted(guia.exemplos()))
def test_exemplo_do_guia_renderiza_sem_erro_nem_aviso(id_, idioma, tmp_path):
    i18n.definir(idioma)
    _, saida = renderizar(guia.exemplos()[id_], tmp_path, 80, 60, ["+K0.3"])
    assert not avisos.ler(saida), avisos.ler(saida)


def test_erros_explicados_em_portugues():
    assert "chave" in avisos.explicar_erro("Parse Error: No matching } in 'sphere', End of File\n found instead")
    assert "'Bola'" in avisos.explicar_erro("Parse Error: Undeclared identifier 'Bola'")
    assert avisos.explicar_erro("algo totalmente diferente") is None
