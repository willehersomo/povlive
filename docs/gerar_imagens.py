"""Gera os prints do README a partir do próprio app (sem janela visível).

Uso:  QT_QPA_PLATFORM=offscreen python3 docs/gerar_imagens.py
"""
import os, sys, tempfile, time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
import atexit, shutil
os.environ["HOME"] = tempfile.mkdtemp(prefix="povlive_docs_")   # não usa as configurações do usuário
atexit.register(shutil.rmtree, os.environ["HOME"], True)

from PyQt5.QtCore import Qt, QPointF, QEvent, QRect
from PyQt5.QtGui import QMouseEvent, QTextCursor
from PyQt5.QtWidgets import QApplication
from povlive_app import janela as J, guia as G, exercicios as X

IMG = os.path.join(AQUI, "img")
os.makedirs(IMG, exist_ok=True)
app = QApplication([])
J.tema_escuro(app)


def esperar(cond, t=60):
    fim = time.time() + t
    while time.time() < fim:
        app.processEvents()
        if cond():
            return True
        time.sleep(0.02)
    raise TimeoutError


def ok(j):
    return j.status.currentMessage().startswith("OK")


def novo_render(j, acao):
    """Executa a ação e espera o render que ela dispara terminar."""
    j.status.clearMessage()
    acao()
    esperar(lambda: ok(j))


def salvar(widget, nome):
    widget.grab().save(os.path.join(IMG, nome))
    print("gerado", nome)


j = J.Janela([os.path.join(AQUI, "vitrine.pov")])
j.resize(1500, 900)
j.show()
j.cb_t.setCurrentIndex(2)
esperar(lambda: ok(j))
salvar(j, "janela.png")

novo_render(j, lambda: (j.a_eixos.trigger(), j.a_quatro.trigger()))
salvar(j, "quatro_vistas.png")
novo_render(j, lambda: (j.a_quatro.trigger(), j.a_eixos.trigger()))

# painel de matrizes com o exemplo da porta (rotação em torno da dobradiça)
novo_render(j, lambda: j.abrir_exemplo("pivo", G.exemplos()["pivo"]))
j.a_mat.trigger()
e = j.cena
c = e.textCursor()
c.setPosition(e.toPlainText().index("object { Porta pigment { color Brown }") + 5)
e.setTextCursor(c)
j._mat_atualizar()
j.txt_mat.verticalScrollBar().setValue(j.txt_mat.verticalScrollBar().maximum())
salvar(j, "matrizes.png")
j.a_mat.trigger()

# guia e exercício
j.abrir_guia()
j.guia.lista.setCurrentRow(6)
app.processEvents()
salvar(j.guia, "guia.png")
j.guia.close()
j.comecar_exercicio("porta")
ex = j.ed()
ex.moveCursor(QTextCursor.End)
j.verificar_exercicio()
esperar(lambda: getattr(j, "_dlg_exercicio", None) is not None)
app.processEvents()
salvar(j._dlg_exercicio, "exercicio.png")
j._dlg_exercicio.close()

# GIF da câmera livre girando (usa o cache de órbita)
for x in j._editores():
    x.document().setModified(False)
novo_render(j, lambda: j.abas.setCurrentIndex(0))
j.a_livre.trigger()
esperar(lambda: ok(j) and j.cache.quadros and not j.cache.construindo(), 120)
v = j.visor
quadros = []
centro = QPointF(v.rect().center())
app.sendEvent(v, QMouseEvent(QEvent.MouseButtonPress, centro, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
for k in range(1, 49):
    app.sendEvent(v, QMouseEvent(QEvent.MouseMove, centro + QPointF(k * 13, 0), Qt.LeftButton, Qt.LeftButton,
                                 Qt.NoModifier))
    app.processEvents()
    quadros.append(j.grab(QRect(j.sp_dir.mapTo(j, j.sp_dir.rect().topLeft()), j.sp_dir.size())).toImage())
app.sendEvent(v, QMouseEvent(QEvent.MouseButtonRelease, centro, Qt.LeftButton, Qt.NoButton, Qt.NoModifier))

from PIL import Image
imgs = []
for q in quadros:
    q = q.scaledToWidth(480, Qt.SmoothTransformation).convertToFormat(q.Format_RGB888)
    ptr = q.constBits()
    ptr.setsize(q.byteCount())
    imgs.append(Image.frombuffer("RGB", (q.width(), q.height()), bytes(ptr), "raw", "RGB", q.bytesPerLine(), 1))
imgs[0].save(os.path.join(IMG, "camera_livre.gif"), save_all=True, append_images=imgs[1:], duration=50, loop=0,
             optimize=True)
print("gerado camera_livre.gif")
for x in j._editores():
    x.document().setModified(False)
j.close()
