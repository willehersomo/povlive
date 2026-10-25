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
