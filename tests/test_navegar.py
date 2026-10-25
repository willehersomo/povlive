"""Ir para a definição e renomear."""
import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QInputDialog

from conftest import cena
from povlive_app import navegar as N


TEXTO = """#declare Raio = 1; // Raio da bola
#macro Bola(R) sphere { 0, R } #end
#declare Raio2 = Raio * 2;
object { Bola(Raio) }
#debug "Raio"
"""


def test_definicao_e_ocorrencias():
    assert N.definicao(TEXTO, "Raio") == TEXTO.index("Raio")
    assert N.definicao(TEXTO, "Bola") == TEXTO.index("Bola")
    assert N.definicao(TEXTO, "Nada") is None
    # fora do comentário e da string, e sem pegar Raio2
    assert len(N.ocorrencias(TEXTO, "Raio")) == 3


def test_renomear_e_validar():
    novo, n = N.renomear(TEXTO, "Raio", "Tamanho")
    assert n == 3 and "#declare Tamanho = 1; // Raio da bola" in novo and '"Raio"' in novo
    assert "Raio2 = Tamanho * 2" in novo and "Bola(Tamanho)" in novo
    for ruim, motivo in (("2x", "formato"), ("sphere", "reservada"), ("Raio2", "existe"), ("x", "reservada")):
        with pytest.raises(N.NomeInvalido, match=motivo):
            N.renomear(TEXTO, "Raio", ruim)


def test_achar_em_include(tmp_path):
    (tmp_path / "a.inc").write_text('#include "b.inc"\n')
    (tmp_path / "b.inc").write_text("// cores\n#declare Laranja = rgb <1, 0.5, 0>;\n")
    t = '#include "a.inc"\nsphere { 0, 1 pigment { Laranja } }'
    onde, pos = N.achar(t, str(tmp_path), "Laranja")
    assert onde.endswith("b.inc") and pos == len("// cores\n#declare ")
    # aba aberta e não salva vale mais que o arquivo
    onde, pos = N.achar(t, str(tmp_path), "Laranja", [(str(tmp_path / "b.inc"), "#declare Laranja = 1;")])
    assert pos == len("#declare ")
    assert N.achar(t, str(tmp_path), "Roxo") is None


def test_ctrl_clique_e_f2_na_janela(qapp, tmp_path, monkeypatch):
    from PyQt5.QtCore import QSettings
    QSettings.setPath(QSettings.NativeFormat, QSettings.UserScope, str(tmp_path / "config"))
    from povlive_app.janela import Janela
    j = Janela([cena("boneco.pov", tmp_path)])
    j.show()
    try:
        e = j.cena
        j.ck_auto.setChecked(False)
        texto = e.toPlainText()
        # Ctrl+clique em CorNariz (definida em cor.inc): abre o .inc na definição
        c = e.textCursor()
        c.setPosition(texto.index("CorNariz") + 2)
        e.setTextCursor(c)
        e.ensureCursorVisible()
        QTest.mouseClick(e.viewport(), Qt.LeftButton, Qt.ControlModifier, e.cursorRect().center())
        inc = j.ed()
        assert inc is not e and inc.caminho.endswith("cor.inc")
        assert inc.textCursor().selectedText() == "CorNariz"
        # F2 em Bola: renomeia as três ocorrências; um Ctrl+Z desfaz
        j.abas.setCurrentWidget(e)
        c = e.textCursor()
        c.setPosition(texto.index("Bola") + 1)
        e.setTextCursor(c)
        monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Esfera", True)))
        j.renomear()
        assert "Bola" not in e.toPlainText() and e.toPlainText().count("Esfera") == 3
        e.undo()
        assert e.toPlainText() == texto
    finally:
        for x in j._editores():
            x.document().setModified(False)
        j.close()
