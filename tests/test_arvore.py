"""Árvore da cena."""
from conftest import cena, esperar
from povlive_app import arvore


def test_itens_em_hierarquia():
    t = """camera { location -5*z look_at 0 }
light_source { <1, 2, 3> rgb 1 }
#declare Bola = sphere { 0, 1 pigment { rgb 1 } }
difference {
    box { -1, 1 }
    union { sphere { 0, 1.2 } cylinder { -2*x, 2*x, 0.3 } }
}
object { Bola translate x }
#for (i, 0, 3) box { i, i + 0.5 } #end
"""
    r = [(rot, [(r2, [r3 for _, r3, _ in f2]) for _, r2, f2 in f]) for _, rot, f in arvore.itens(t)]
    assert r == [("▷ camera", []), ("☀ light_source", []), ("● Bola = sphere", []),
                 ("− difference", [("■ box", []), ("∪ union", ["● sphere", "▮ cylinder"])]),
                 ("↳ object Bola", []), ("■ box  ↻ #for", [])]


def test_painel_na_janela(qapp, tmp_path):
    from PyQt5.QtCore import QSettings
    QSettings.setPath(QSettings.NativeFormat, QSettings.UserScope, str(tmp_path / "config"))
    from povlive_app.janela import Janela
    j = Janela([cena("boneco.pov", tmp_path)])
    j.show()
    try:
        j.a_arv.trigger()
        p = j.painel_arv
        assert p.isVisible() and p.arv.topLevelItemCount() >= 6
        nomes = [p.arv.topLevelItem(i).text(0) for i in range(p.arv.topLevelItemCount())]
        assert "∪ union" in nomes and "▲ cone" in nomes
        # clicar no cone leva o cursor do editor até ele
        it = next(p.arv.topLevelItem(i) for i in range(p.arv.topLevelItemCount())
                  if p.arv.topLevelItem(i).text(0) == "▲ cone")
        p.arv.itemClicked.emit(it, 0)
        assert j.cena.textCursor().selectedText() == "cone"
        # o cursor no código seleciona o item da árvore; o filtro esconde o resto
        texto = j.cena.toPlainText()
        c = j.cena.textCursor()
        c.setPosition(texto.index("box {") + 2)
        j.cena.setTextCursor(c)
        assert esperar(qapp, lambda: p.arv.currentItem() is not None and p.arv.currentItem().text(0) == "■ box", 3)
        p.filtro.setText("cone")
        assert [p.arv.topLevelItem(i).isHidden() for i in range(p.arv.topLevelItemCount())].count(False) == 1
    finally:
        j.cena.document().setModified(False)
        j.close()
