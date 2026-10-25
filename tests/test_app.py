"""Testes de integração: abrem o app (sem janela visível) e simulam o uso."""
import os, zipfile

import pytest
from PyQt5.QtCore import Qt, QPointF, QEvent
from PyQt5.QtGui import QColor, QMouseEvent, QTextCursor
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QMessageBox, QFileDialog

from conftest import precisa_povray, esperar, cena
from povlive_app import selecao, sdl, exercicios as X

pytestmark = precisa_povray


@pytest.fixture
def janela(qapp, monkeypatch, tmp_path):
    # o Qt guarda o local das configurações na primeira leitura; aponta cada teste para a sua pasta
    from PyQt5.QtCore import QSettings
    QSettings.setPath(QSettings.NativeFormat, QSettings.UserScope, str(tmp_path / "config"))
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "config"))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
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


def ok(j):
    return j.status.currentMessage().startswith("OK")


def test_abre_renderiza_e_marca_erro(janela, qapp, tmp_path):
    j = janela(cena("boneco.pov", tmp_path))
    assert esperar(qapp, lambda: ok(j))
    assert j.ultima_pix is not None and not j.log.isVisible()
    c = j.cena.textCursor()
    c.movePosition(QTextCursor.End)
    c.insertText("\nsphere { <0,0,0> 1 ")
    assert esperar(qapp, lambda: j.log.isVisible())
    assert j.cena.linha_erro == j.cena.blockCount()
    assert "Falta fechar uma chave" in j.log.toPlainText() or "falta fechar uma chave" in j.log.toPlainText()


def test_editor_pares_comentar_e_formatar(janela, qapp):
    j = janela()
    e = j.ed()
    j.ck_auto.setChecked(False)
    e.setPlainText("")
    e.setFocus()
    QTest.keyClicks(e, "sphere {")
    QTest.keyClick(e, Qt.Key_Return)
    QTest.keyClicks(e, "<0, 1, 0")
    assert e.toPlainText() == "sphere {\n    <0, 1, 0>\n}"
    e.selectAll()
    e.comentar()
    assert all(l.startswith("// ") for l in e.toPlainText().split("\n"))
    e.comentar()
    e.setPlainText("box{\n0,1\n}")
    j.formatar_codigo()
    assert e.toPlainText() == "box{\n    0,1\n}"


def _pixel_do_objeto(j, linha):
    img = j.sel["img"]
    for i, b in j.sel["mapa"].items():
        if sdl.linha_de(j.sel["texto"], b.kw_ini) == linha:
            for y in range(0, img.height(), 2):
                for x in range(0, img.width(), 2):
                    c = QColor(img.pixel(x, y))
                    if selecao.id_da_cor(c.red(), c.green(), c.blue()) == i:
                        return (x + 0.5) / img.width(), (y + 0.5) / img.height()
    raise AssertionError(f"objeto da linha {linha} não aparece")


def test_clicar_e_arrastar_objeto_na_imagem(janela, qapp, tmp_path):
    j = janela(cena("boneco.pov", tmp_path))
    assert esperar(qapp, lambda: ok(j) and j.sel is not None)
    texto = j.cena.toPlainText()
    linha_cone = texto[:texto.index("cone")].count("\n") + 1
    nx, ny = _pixel_do_objeto(j, linha_cone)
    j.visor.clicou.emit(nx, ny)
    assert j.cena.textCursor().selectedText() == "cone"
    assert j.cena.textCursor().blockNumber() + 1 == linha_cone

    # Ctrl+arrastar a caixa para a direita: o translate final dela aumenta em x
    linha_caixa = texto[:texto.index("box {")].count("\n") + 1
    nx, ny = _pixel_do_objeto(j, linha_caixa)
    j.visor.objeto.emit("inicio", nx, ny, 0)
    j.visor.objeto.emit("mover", 80, 0, 0)
    j.visor.objeto.emit("fim", 80, 0, 0)
    novo = j.cena.toPlainText()
    v = selecao.translate_final(novo, [b for b in sdl.blocos(novo) if b.kw == "box"][0])[2]
    assert v[0] > 2.5 and abs(v[1]) < 1e-6
    j.cena.undo()
    assert j.cena.toPlainText() == texto


def test_inc_alterado_sem_salvar_entra_no_render(janela, qapp, tmp_path):
    j = janela(cena("boneco.pov", tmp_path))
    assert esperar(qapp, lambda: ok(j))
    j._abrir_include(j.cena, "cor.inc")
    inc = j.ed()
    assert inc.caminho.endswith("cor.inc") and j.cena is not inc
    def azuis():
        img = j.ultima_pix.toImage()
        return sum(1 for y in range(0, img.height(), 2) for x in range(0, img.width(), 2)
                   if (lambda c: c.blue() > 150 and c.red() < 90 and c.green() < 90)(QColor(img.pixel(x, y))))
    antes = azuis()
    c = QTextCursor(inc.document())
    c.select(QTextCursor.Document)
    c.insertText("#declare CorNariz = color rgb <0, 0, 1>;\n")
    assert esperar(qapp, lambda: ok(j) and azuis() > antes + 5), (antes, azuis())   # o nariz ficou azul
    assert open(os.path.join(str(tmp_path), "cor.inc")).read().startswith("#declare CorNariz = color rgb <1")


def test_camera_livre_copiar_para_o_codigo(janela, qapp, tmp_path):
    j = janela(cena("boneco.pov", tmp_path))
    assert esperar(qapp, lambda: ok(j))
    j.a_livre.trigger()
    v = j.visor
    centro = QPointF(v.rect().center())
    qapp.sendEvent(v, QMouseEvent(QEvent.MouseButtonPress, centro, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    for dx in range(0, 80, 8):
        qapp.sendEvent(v, QMouseEvent(QEvent.MouseMove, centro + QPointF(dx, 0), Qt.LeftButton, Qt.LeftButton,
                                      Qt.NoModifier))
    qapp.sendEvent(v, QMouseEvent(QEvent.MouseButtonRelease, centro + QPointF(80, 0), Qt.LeftButton, Qt.NoButton,
                                  Qt.NoModifier))
    assert esperar(qapp, lambda: ok(j))
    j.a_copiar.trigger()
    assert "location <0, 3, -7>" not in j.cena.toPlainText() and not j.a_livre.isChecked()


def test_exercicio_certo_e_errado(janela, qapp):
    j = janela()
    j.comecar_exercicio("boneco")
    e = j.ed()
    e.moveCursor(QTextCursor.End)
    e.insertPlainText(X.POR_ID["boneco"]["gabarito"].split("\n", 1)[1])
    j.verificar_exercicio()
    assert esperar(qapp, lambda: getattr(j, "_dlg_exercicio", None) is not None, 40)
    assert "Correto" in j._dlg_exercicio.findChildren(type(j.lb_pixel))[0].text()
    j._dlg_exercicio.close()
    j._dlg_exercicio = None
    j.comecar_exercicio("porta")
    j.verificar_exercicio()
    assert esperar(qapp, lambda: getattr(j, "_dlg_exercicio", None) is not None, 40)
    assert "Quase" in j._dlg_exercicio.findChildren(type(j.lb_pixel))[0].text()


def test_exportar_entrega(janela, qapp, tmp_path, monkeypatch):
    j = janela(cena("anim.pov", tmp_path))
    assert esperar(qapp, lambda: ok(j))
    destino = str(tmp_path / "entrega.zip")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (destino, "")))
    j.exportar_entrega()
    assert esperar(qapp, lambda: os.path.exists(destino), 60)
    nomes = sorted(zipfile.ZipFile(destino).namelist())
    assert nomes == ["anim/LEIAME.txt", "anim/anim.gif", "anim/anim.png", "anim/anim.pov"]


def test_historico_fica_salvo_entre_sessoes(janela, qapp, tmp_path):
    arq = cena("boneco.pov", tmp_path)
    j = janela(arq)
    assert esperar(qapp, lambda: j.historico.count() >= 1)
    j.close()
    j2 = janela(arq)
    assert j2.historico.count() >= 1


def test_progresso_e_cancelar_render_grande(janela, qapp, tmp_path):
    import shutil
    from conftest import RAIZ
    shutil.copy(os.path.join(RAIZ, "docs", "vitrine.pov"), tmp_path / "v.pov")
    j = janela(str(tmp_path / "v.pov"))
    assert esperar(qapp, lambda: ok(j), 60)
    j.pedir_render(grande=True)
    assert esperar(qapp, lambda: j.pb_render.isVisible() and j.pb_render.value() > 0, 60)
    assert "%" in j.status.currentMessage()
    j.bt_cancelar.click()
    assert not j._rodando() and not j.pb_render.isVisible()
    assert j.status.currentMessage() == "Render cancelado"
    # o próximo render normal funciona e a saída não tem as linhas de progresso
    j.pedir_render()
    assert esperar(qapp, lambda: ok(j), 60)
