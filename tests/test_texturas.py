"""Biblioteca de texturas: catálogo, aplicar no código, miniaturas e arrastar até a imagem."""

import pytest
from PyQt5.QtGui import QImage

from conftest import precisa_povray, esperar, cena, renderizar
from povlive_app import texturas as T, sdl


def item(nome):
    return next(it for it in T.catalogo() if it.nome == nome)


def test_catalogo_tem_as_categorias_e_nada_repetido():
    c = T.catalogo()
    assert len(c) > 300
    assert len({(it.include, it.nome) for it in c}) == len(c)
    cats = {it.categoria for it in c}
    assert {"metais", "madeiras", "pedras", "vidros", "acabamentos", "cores"} <= cats
    assert item("T_Wood10").include == "woods.inc" and item("T_Stone8").include == "stones.inc"
    assert item("M_Ruby_Glass").tipo == "material" and item("Jade").tipo == "pigment"
    assert item("Mirror").tipo == "finish" and item("Red").tipo == "color"
    nomes = {it.nome for it in c}
    assert not nomes & {"T_Grnt0a", "T_Crack1", "Glass", "Ruby_Glass", "P_WoodGrain1A"}


def test_textura_troca_toda_a_aparencia():
    t = ('#version 3.7;\n#include "colors.inc"\nsphere {\n    0, 1\n    pigment { Red }\n'
         '    finish { phong 1 }\n    translate x\n}\n')
    novo, pos = T.aplicar(t, t.index("sphere") + 2, item("T_Wood10"))
    assert novo == ('#version 3.7;\n#include "colors.inc"\n#include "woods.inc"\nsphere {\n    0, 1\n'
                    '    texture { T_Wood10 }\n    translate x\n}\n')
    assert novo[pos:].startswith("texture { T_Wood10 }")


def test_objeto_de_uma_linha_e_sem_aparencia():
    t = "sphere { 0, 1 translate <1, 0, 0> }\n"
    novo, pos = T.aplicar(t, 3, item("M_Ruby_Glass"))
    assert novo == ('#include "colors.inc"\n#include "textures.inc"\n'
                    "sphere { 0, 1 material { M_Ruby_Glass } translate <1, 0, 0> }\n")
    assert novo[pos:].startswith("material {")
    # objeto de várias linhas sem transformação: entra antes do '}'
    t = "box {\n    0, 1\n}\n"
    novo, _ = T.aplicar(t, 2, item("Polished_Chrome"))
    assert novo.endswith("box {\n    0, 1\n    texture { Polished_Chrome }\n}\n")


def test_pigmento_e_acabamento_mexem_so_na_sua_parte():
    t = "sphere { 0, 1 texture { pigment { rgb 1 } finish { phong 1 } } }"
    novo, _ = T.aplicar(t, 3, item("Jade"))
    assert "texture { pigment { Jade } finish { phong 1 } }" in novo
    novo, _ = T.aplicar(novo, novo.index("sphere"), item("Mirror"))
    assert "texture { pigment { Jade } finish { Mirror } }" in novo and '#include "finish.inc"' in novo
    t = "box { 0, 1 texture { T_Stone8 } }"
    novo, _ = T.aplicar(t, 3, item("Shiny"))
    assert "texture { T_Stone8 finish { Shiny } }" in novo   # o nome da textura tem que vir primeiro
    t = "box { 0, 1 texture { pigment { Red } } }"
    novo, _ = T.aplicar(t, 3, item("Shiny"))
    assert "texture { pigment { Red } finish { Shiny } }" in novo
    novo, _ = T.aplicar("cone { 0, 1, y, 0 pigment { Red } }", 2, item("Blue"))
    assert "pigment { color Blue }" in novo and "Red" not in novo


def test_objeto_mais_interno_e_fora_de_objeto():
    t = "union {\n    sphere { 0, 1 }\n    box { 0, 1 pigment { Red } }\n}\n"
    novo, _ = T.aplicar(t, t.index("box") + 1, item("Gold_Metal"))
    assert "box { 0, 1 texture { Gold_Metal } }" in novo and "sphere { 0, 1 }" in novo
    with pytest.raises(T.SemObjeto):
        T.aplicar("#declare A = 1;\n", 3, item("Jade"))


def test_include_entra_depois_dos_outros_e_nao_repete():
    t = '#version 3.7;\n#include "colors.inc"\n#include "woods.inc"\nbox { 0, 1 }\n'
    novo, _ = T.aplicar(t, t.index("box"), item("T_Wood1"))
    assert novo.count("#include") == 2
    novo, _ = T.garantir_include("box { 0, 1 }", "metals.inc")
    assert novo == '#include "metals.inc"\nbox { 0, 1 }'


@precisa_povray
def test_um_de_cada_categoria_renderiza_sem_erro(tmp_path):
    t = "#version 3.7;\nglobal_settings { assumed_gamma 1.0 }\ncamera { location <0, 1, -4> look_at 0 }\n" \
        "light_source { <2, 4, -3> rgb 1 }\n"
    linhas = {}
    for cid, _ in T.CATEGORIAS:
        it = next(i for i in T.catalogo() if i.categoria == cid)
        t += f"sphere {{ <{len(linhas)}, 0, 0>, 0.4 pigment {{ rgb 1 }} }}\n"
        linhas[cid] = it
    for k, it in enumerate(linhas.values()):
        alvo = [b for b in sdl.blocos(t) if b.kw == "sphere"][k]
        t, _ = T.aplicar(t, alvo.kw_ini, it)
    _, log = renderizar(t, tmp_path, 80, 60)
    assert "Parse Warning" not in log and "Possible Parse Error" not in log, log[-600:]


@precisa_povray
def test_gerador_de_miniaturas(qapp, tmp_path):
    from povlive_app.biblioteca import GeradorMiniaturas
    itens = [item(n) for n in ("Jade", "T_Wood10", "M_Ruby_Glass", "Mirror", "Red")]
    g = GeradorMiniaturas(pasta=str(tmp_path / "mini"), processos=2)
    prontas = []
    g.pronta.connect(prontas.append)
    assert g.gerar(itens) == 5
    assert esperar(qapp, lambda: not g.rodando(), 60)
    assert sorted(p.nome for p in prontas) == sorted(i.nome for i in itens)
    cores = set()
    for it in itens:
        img = QImage(T.arquivo_miniatura(it, str(tmp_path / "mini")))
        assert img.width() == T.TAMANHO
        cores.add(img.pixel(T.TAMANHO // 2, T.TAMANHO // 2))
    assert len(cores) == 5             # cada miniatura é diferente
    assert g.gerar(itens) == 0         # já estão no cache


@precisa_povray
def test_arrastar_textura_ate_o_objeto(qapp, tmp_path, monkeypatch):
    from test_app import janela as _j, ok, _pixel_do_objeto  # noqa: F401
    from PyQt5.QtCore import QSettings
    QSettings.setPath(QSettings.NativeFormat, QSettings.UserScope, str(tmp_path / "config"))
    from povlive_app.janela import Janela
    j = Janela([cena("boneco.pov", tmp_path)])
    j.show()
    try:
        j.painel_tex.gerador.gerar = lambda itens: 0      # sem gerar miniaturas neste teste
        j.a_tex.trigger()
        assert j.painel_tex.isVisible()
        assert esperar(qapp, lambda: ok(j) and j.sel is not None)
        texto = j.cena.toPlainText()
        linha_caixa = texto[:texto.index("box {")].count("\n") + 1
        nx, ny = _pixel_do_objeto(j, linha_caixa)
        j.visor.soltou_textura.emit(nx, ny, "woods.inc\tT_Wood10")
        novo = j.cena.toPlainText()
        caixa = [b for b in sdl.blocos(novo) if b.kw == "box"][0]
        assert "texture { T_Wood10 }" in novo[caixa.abre:caixa.fecha] and "Blue" not in novo[caixa.abre:caixa.fecha]
        assert '#include "woods.inc"' in novo
        assert esperar(qapp, lambda: ok(j))       # a cena nova renderiza sem erro
        j.cena.undo()
        assert j.cena.toPlainText() == texto
        # duplo clique com o cursor no cone
        c = j.cena.textCursor()
        c.setPosition(texto.index("cone") + 1)
        j.cena.setTextCursor(c)
        w = j.painel_tex.widgets[("golds.inc", "T_Gold_3C")]
        j.painel_tex.lista.itemDoubleClicked.emit(w)
        assert "texture { T_Gold_3C }" in j.cena.toPlainText()
    finally:
        j.cena.document().setModified(False)
        j.close()
