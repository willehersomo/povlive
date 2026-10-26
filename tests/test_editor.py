"""Editor de código: pares, Enter, Backspace, Tab, autocompletar, arrastar números, busca e cor."""
from PyQt5.QtCore import Qt, QPoint, QEvent
from PyQt5.QtGui import QTextCursor, QMouseEvent
from PyQt5.QtTest import QTest

from povlive_app.editor import Editor, BarraBusca


def novo(qapp, texto=""):
    e = Editor()
    e.resize(700, 400)
    e.show()
    e.setPlainText(texto)
    e.setFocus()
    return e


def cursor_em(e, pos):
    c = e.textCursor()
    c.setPosition(pos)
    e.setTextCursor(c)


def test_pares_pular_fechamento_e_backspace(qapp):
    e = novo(qapp)
    QTest.keyClicks(e, "box <")
    assert e.toPlainText() == "box <>"
    QTest.keyClicks(e, "1>")                          # digitar o ">" que já está ali só pula
    assert e.toPlainText() == "box <1>"
    QTest.keyClicks(e, ' "')
    QTest.keyClick(e, Qt.Key_Backspace)               # apaga o par vazio inteiro
    assert e.toPlainText() == "box <1> "
    e.setPlainText("#if (a < b)")
    e.moveCursor(QTextCursor.End)
    QTest.keyClicks(e, " <")                          # em condição, < é comparação: não fecha
    assert e.toPlainText().endswith(" <")
    e.setPlainText("// comentário ")
    e.moveCursor(QTextCursor.End)
    QTest.keyClicks(e, "(")
    assert e.toPlainText().endswith("(") and not e.toPlainText().endswith("()")


def test_enter_tab_e_chave_volta_nivel(qapp):
    e = novo(qapp)
    QTest.keyClicks(e, "union {")
    QTest.keyClick(e, Qt.Key_Return)
    QTest.keyClicks(e, "sphere {")
    QTest.keyClick(e, Qt.Key_Return)
    QTest.keyClicks(e, "0, 1")
    assert e.toPlainText() == "union {\n    sphere {\n        0, 1\n    }\n}"
    e.setPlainText("a\nb")
    e.selectAll()
    QTest.keyClick(e, Qt.Key_Tab)
    assert e.toPlainText() == "    a\n    b"
    QTest.keyClick(e, Qt.Key_Backtab)
    assert e.toPlainText() == "a\nb"
    e.setPlainText("x {\n        ")
    e.moveCursor(QTextCursor.End)
    QTest.keyClick(e, Qt.Key_Backspace)               # apaga um nível de indentação
    assert e.toPlainText() == "x {\n    "
    QTest.keyClicks(e, "}")                           # "}" sozinho volta um nível
    assert e.toPlainText() == "x {\n}"


def test_duplicar_e_autocompletar(qapp):
    e = novo(qapp, "sphere { 0, 1 }")
    e.duplicar_linha()
    assert e.toPlainText() == "sphere { 0, 1 }\nsphere { 0, 1 }"
    e.atualizar_palavras({"MinhaCorFavorita": "#declare MinhaCorFavorita = rgb 1;"})
    e.setPlainText("")
    QTest.keyClicks(e, "MinhaC")
    pop = e.completer.popup()
    assert pop.isVisible() and e.completer.currentCompletion() == "MinhaCorFavorita"
    e.completer.activated[str].emit("MinhaCorFavorita")
    assert e.toPlainText() == "MinhaCorFavorita"


def test_ctrl_arrastar_numero(qapp):
    e = novo(qapp, "sphere { 0, 1.5 }")
    valores = []
    e.arrasteValor.connect(valores.append)
    fim = []
    e.arrasteFim.connect(lambda: fim.append(True))
    cursor_em(e, e.toPlainText().index("1.5") + 1)
    p = e.cursorRect().center()
    QTest.mousePress(e.viewport(), Qt.LeftButton, Qt.ControlModifier, p)
    # 40 px para a direita = +10 passos de 0.1 (o QTest.mouseMove não manda o botão apertado)
    qapp.sendEvent(e.viewport(), QMouseEvent(QEvent.MouseMove, p + QPoint(40, 0), Qt.LeftButton, Qt.LeftButton,
                                             Qt.ControlModifier))
    QTest.mouseRelease(e.viewport(), Qt.LeftButton, Qt.ControlModifier, p + QPoint(40, 0))
    assert e.toPlainText() == "sphere { 0, 2.5 }" and valores[-1] == "2.5" and fim
    e.undo()                                          # um Ctrl+Z desfaz o arraste inteiro
    assert e.toPlainText() == "sphere { 0, 1.5 }"


def test_busca_e_substituir(qapp):
    e = novo(qapp, "Red red RED\nred")
    b = BarraBusca(lambda: e)
    b.abrir(substituir=True)
    b.campo.setText("red")
    assert "4" in b.info.text()                       # sem diferenciar maiúsculas: 4 ocorrências
    b.maiusc.setChecked(True)
    assert "2" in b.info.text()
    b.troca.setText("blue")
    b.substituir_todos()
    assert e.toPlainText() == "Red blue RED\nblue"
    e.undo()
    assert e.toPlainText() == "Red red RED\nred"


def test_rgb_no_cursor(qapp):
    e = novo(qapp, "pigment { rgb <1, 0.5, 0> }")
    cursor_em(e, e.toPlainText().index("0.5"))
    r = e.rgb_no_cursor()
    assert r is not None


def _clicar_no_texto(e, indice):
    c = e.textCursor()
    c.setPosition(indice)
    r = e.cursorRect(c)
    QTest.mouseClick(e.viewport(), Qt.LeftButton, Qt.NoModifier, QPoint(r.x() + 3, r.center().y()))


def test_clique_no_rgb_abre_a_escala(qapp):
    e = novo(qapp, "sphere { 0, 1 pigment { rgb <1, 0.5, 0> } }")
    fins = []
    e.arrasteFim.connect(lambda: fins.append(1))
    _clicar_no_texto(e, e.toPlainText().index("0.5"))       # clicar num número não abre
    assert e.seletor_rgb is None
    _clicar_no_texto(e, e.toPlainText().index("rgb") + 1)
    sel = e.seletor_rgb
    assert sel is not None and sel.isVisible()
    assert [b.value() for b in sel.barras] == [1000, 500, 0]
    sel.barras[2].setValue(250)                              # arrastar a barra do azul muda o código ao vivo
    assert "rgb <1, 0.5, 0.25>" in e.toPlainText()
    sel.campos[1].setValue(0.8)                              # e o campo também
    assert "rgb <1, 0.8, 0.25>" in e.toPlainText()
    QTest.keyClick(sel, Qt.Key_Return)
    assert e.seletor_rgb is None and fins == [1]
    e.undo()                                                 # tudo vira um único Ctrl+Z
    assert "rgb <1, 0.5, 0>" in e.toPlainText()


def test_escala_rgb_esc_desfaz_e_escalar(qapp):
    e = novo(qapp, "pigment { rgb 0.4 }")
    _clicar_no_texto(e, e.toPlainText().index("rgb"))
    sel = e.seletor_rgb
    assert [round(c.value(), 3) for c in sel.campos] == [0.4, 0.4, 0.4]
    sel.barras[0].setValue(900)
    assert "rgb <0.9, 0.4, 0.4>" in e.toPlainText()          # um rgb escalar vira vetor
    QTest.keyClick(sel, Qt.Key_Escape)
    assert e.toPlainText() == "pigment { rgb 0.4 }"


def test_escala_rgb_preserva_valor_acima_de_1(qapp):
    e = novo(qapp, "pigment { rgb <2, 0, 0> }")
    assert e.abrir_escala_rgb(e.rgb_na_palavra(QPoint(-100, -100)) or None) is False   # cursor fora de um rgb
    cursor_em(e, e.toPlainText().index("2"))
    assert e.abrir_escala_rgb()
    sel = e.seletor_rgb
    sel.barras[1].setValue(500)
    assert "rgb <2, 0.5, 0>" in e.toPlainText()
    sel.close()
