"""Interface em inglês: todo texto marcado tem tradução e nada em português escapa para a tela."""
import ast, glob, os, re

import pytest

from conftest import RAIZ
from povlive_app import i18n, traducoes_en as EN, guia, guia_en, pov, exercicios as X, matrizes, avisos

# letras e palavras que só aparecem em português (para pegar textos que esqueceram o tr)
PORTUGUES = re.compile(r"[ãõçáéíóúâêôà]|\b(?:não|você|também|para o|da cena|do objeto|linha)\b", re.I)


def chaves_marcadas():
    """{texto: arquivo} de cada tr("...") / N_("...") no código."""
    r = {}
    for f in glob.glob(os.path.join(RAIZ, "povlive_app", "*.py")):
        for n in ast.walk(ast.parse(open(f, encoding="utf-8").read())):
            if (isinstance(n, ast.Call) and getattr(n.func, "id", None) in ("tr", "N_")
                    and n.args and isinstance(n.args[0], ast.Constant)):
                r[n.args[0].value] = os.path.basename(f)
    return r


def campos(s):
    return sorted(re.findall(r"\{\d*\}", s))


def test_todo_texto_marcado_tem_traducao():
    faltando = {k: f for k, f in chaves_marcadas().items() if k not in EN.TEXTOS}
    assert not faltando, faltando


def test_nenhuma_traducao_sobrando():
    sobrando = set(EN.TEXTOS) - set(chaves_marcadas())
    assert not sobrando, sobrando


def test_traducao_tem_os_mesmos_campos_e_nada_em_portugues():
    for pt, en in EN.TEXTOS.items():
        assert campos(pt) == campos(en), pt
        assert not PORTUGUES.search(en), en


def test_guia_em_ingles_tem_a_mesma_estrutura():
    assert len(guia_en.TOPICOS) == len(guia.TOPICOS)
    for (t_pt, b_pt), (t_en, b_en) in zip(guia.TOPICOS, guia_en.TOPICOS):
        assert t_pt.split(".")[0] == t_en.split(".")[0]
        assert [b[0] for b in b_pt] == [b[0] for b in b_en], t_en
        assert [b[1] for b in b_pt if b[0] == "ex"] == [b[1] for b in b_en if b[0] == "ex"], t_en
    for _, blocos in guia_en.TOPICOS:
        for b in blocos:
            texto = b[2] if b[0] == "ex" else b[1]
            assert not PORTUGUES.search(texto), texto[:200]


def test_ajuda_e_exercicios_em_ingles_completos():
    assert set(EN.AJUDA) == set(pov.AJUDA)
    assert set(EN.CODIGO_MODELOS) <= {m[0] for m in pov.MODELOS if m}
    for e in X.EXERCICIOS:
        assert {"titulo", "enunciado", "dica"} <= set(X.EN[e["id"]])


def test_idioma_do_sistema_e_preferencia(monkeypatch, tmp_path):
    from PyQt5.QtCore import QSettings
    monkeypatch.delenv("POVLIVE_LANG", raising=False)
    cfg = QSettings(str(tmp_path / "povlive.ini"), QSettings.IniFormat)
    cfg.setValue("idioma", "en")
    i18n.carregar(cfg)
    assert i18n.idioma() == "en" and i18n.tr("Salvar") == "Save"
    cfg.setValue("idioma", "pt")
    i18n.carregar(cfg)
    assert i18n.idioma() == "pt" and i18n.tr("Salvar") == "Salvar"
    monkeypatch.setenv("POVLIVE_LANG", "en")
    i18n.carregar(cfg)
    assert i18n.idioma() == "en"
    i18n.definir("xx")
    assert i18n.idioma() == "en"      # idioma desconhecido cai no inglês


@pytest.fixture
def ingles():
    i18n.definir("en")
    yield
    i18n.definir("pt")


def test_textos_gerados_em_ingles(ingles):
    textos = [guia.html_topico(i) for i in range(len(guia.topicos()))] + [guia.html_exercicios()]
    textos += list(guia.exemplos().values())
    textos += [X.texto_inicial(e) + X.texto_gabarito(e) for e in X.EXERCICIOS]
    t = "#version 3.7;\nunion {\n  object { L scale <-1,1,1> rotate <0,30,0> translate <1,0,0> }\n}\n" \
        "#declare L = box { 0, 1 }\nbox { 0, 1 scale 0 rotate <0, i, 0> }"
    for pos in (t.index("object") + 5, t.rindex("box") + 3, 0):
        try:
            textos.append(matrizes.html(matrizes.analisar(t, pos), "aula"))
        except Exception:
            pass
    textos.append(avisos.explicar_erro("Parse Error: No matching } in 'sphere'"))
    textos += [a["texto"] for a in avisos.ler("Parse Warning: Scale X by 0.0. Changed to 1.0.\n")]
    for s in textos:
        sem_html = re.sub(r"<[^>]+>", " ", s)
        assert not PORTUGUES.search(sem_html), PORTUGUES.search(sem_html).group(0) + " em: " + sem_html[:300]


def test_janela_em_ingles_sem_portugues(qapp, ingles, tmp_path):
    from PyQt5.QtCore import QSettings
    from PyQt5.QtWidgets import QAbstractButton, QLabel, QLineEdit, QMenu, QWidget
    QSettings.setPath(QSettings.NativeFormat, QSettings.UserScope, str(tmp_path / "config"))
    from povlive_app.janela import Janela, atalhos_html
    j = Janela([])
    j.show()
    try:
        j.abrir_guia()
        textos = [atalhos_html(), j.windowTitle(), j.guia.windowTitle()]
        for m in j.findChildren(QMenu):
            textos.append(m.title())
            for a in m.actions():
                textos += [a.text(), a.toolTip(), a.iconText()]
        for w in j.findChildren(QWidget) + j.guia.findChildren(QWidget):
            textos.append(w.toolTip())
            if isinstance(w, (QLabel, QAbstractButton)):
                textos.append(w.text())
            if isinstance(w, QLineEdit):
                textos.append(w.placeholderText())
        textos += [getattr(v, "titulo", "") for v in j._visores()] + [j.visor.vazio]
        textos += [j.guia.lista.item(i).text() for i in range(j.guia.lista.count())]
        ruins = [t for t in textos if t and PORTUGUES.search(re.sub(r"<[^>]+>", " ", t))
                 and "Português" not in t]
        assert not ruins, ruins
        assert j.menuBar().actions()[0].text() == "&File"
        assert any(a.text() == "Basic scene" for m in j.findChildren(QMenu) for a in m.actions())
    finally:
        j.guia.close()
        for e in j._editores():
            e.document().setModified(False)
        j.close()
