"""Painel da biblioteca de texturas: miniaturas, busca, aplicar no objeto e arrastar até a imagem."""
import os, re, shutil, tempfile

from PyQt5.QtCore import Qt, QObject, QProcess, QTimer, QSize, QMimeData, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap, QRadialGradient, QTextCursor
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QListWidget,
                             QListWidgetItem, QListView, QLabel, QPushButton, QAbstractItemView)

from . import texturas, sdl, pov
from .i18n import tr

MIME = "application/x-povlive-textura"


class GeradorMiniaturas(QObject):
    """Renderiza as miniaturas que faltam no cache, em vários processos do POV-Ray de baixa prioridade.

    Cada processo recebe uma parte dos itens e renderiza uma "animação" em que o quadro k é o item k
    (o POV-Ray gasta ~0,75 s só para iniciar; assim esse custo é pago uma vez por processo)."""
    pronta = pyqtSignal(object)    # Item
    acabou = pyqtSignal()

    def __init__(self, parent=None, pasta=None, processos=None):
        super().__init__(parent)
        self.pasta = pasta or texturas.pasta_cache()
        self.nproc = processos or max(1, min(8, (os.cpu_count() or 2) - 1))
        self.procs = []       # {"proc", "trab", "itens", "prox"}
        self.timer = QTimer(self, interval=200)
        self.timer.timeout.connect(self._coletar)

    def rodando(self):
        return bool(self.procs)

    def gerar(self, itens):
        self.parar()
        faltam = [it for it in itens if not os.path.exists(texturas.arquivo_miniatura(it, self.pasta))]
        if not faltam:
            self.acabou.emit()
            return 0
        os.makedirs(self.pasta, exist_ok=True)
        for k in range(min(self.nproc, len(faltam))):
            parte = faltam[k::self.nproc]          # intercalado: o começo da lista aparece primeiro
            trab = tempfile.mkdtemp(prefix="povlive_mini_")
            with open(os.path.join(trab, "m.pov"), "w", encoding="utf-8") as f:
                f.write(texturas.cena_miniaturas(parte))
            t = texturas.TAMANHO
            a = ["+Im.pov", "+Om.png", f"+W{t}", f"+H{t}", "+A0.3", "+Q9", "-D", "-V", "+FN",
                 "+KFI1", f"+KFF{len(parte)}", "-GA"]
            p = QProcess(self)
            p.setWorkingDirectory(trab)
            p.setProcessChannelMode(QProcess.MergedChannels)
            p.setStandardOutputFile(QProcess.nullDevice())
            pov.iniciar(p, a, baixa_prioridade=True)
            self.procs.append({"proc": p, "trab": trab, "itens": parte, "prox": 1})
        self.timer.start()
        return len(faltam)

    def _quadro(self, d, i):
        return os.path.join(d["trab"], f"m{i:0{len(str(len(d['itens'])))}d}.png")

    def _coletar(self):
        for d in list(self.procs):
            terminou = d["proc"].state() == QProcess.NotRunning
            n = len(d["itens"])
            while d["prox"] <= n:
                i = d["prox"]
                atual = self._quadro(d, i)
                # um quadro está completo quando o seguinte já começou (ou o processo acabou)
                completo = os.path.exists(atual) and (terminou or (i < n and os.path.exists(self._quadro(d, i + 1))))
                if not completo:
                    if terminou:       # quadro que falhou: pula
                        d["prox"] += 1
                        continue
                    break
                item = d["itens"][i - 1]
                try:
                    shutil.move(atual, texturas.arquivo_miniatura(item, self.pasta))
                except OSError:
                    pass
                else:
                    self.pronta.emit(item)
                d["prox"] += 1
            if terminou and d["prox"] > n:
                shutil.rmtree(d["trab"], ignore_errors=True)
                self.procs.remove(d)
        if not self.procs:
            self.timer.stop()
            self.acabou.emit()

    def parar(self):
        self.timer.stop()
        for d in self.procs:
            p = d["proc"]
            if p.state() != QProcess.NotRunning:
                p.kill()
                p.waitForFinished(1000)
            shutil.rmtree(d["trab"], ignore_errors=True)
        self.procs = []


def _icone_vazio(t=texturas.TAMANHO):
    pix = QPixmap(t, t)
    pix.fill(QColor("#2a2a2a"))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    g = QRadialGradient(t * 0.4, t * 0.38, t * 0.45)
    g.setColorAt(0, QColor("#666"))
    g.setColorAt(1, QColor("#333"))
    p.setBrush(g)
    p.setPen(Qt.NoPen)
    p.drawEllipse(int(t * 0.12), int(t * 0.12), int(t * 0.76), int(t * 0.76))
    p.end()
    return QIcon(pix)


def rotulo(nome):
    """Nome curto para baixo da miniatura: sem o prefixo M_/T_ e com espaços (o nome exato fica na dica)."""
    return re.sub(r"^[MTP]_", "", nome).replace("_", " ")


class ListaTexturas(QListWidget):
    """Lista em ícones; arrastar leva o item (para a imagem) e o código (para o editor)."""

    def mimeData(self, itens):
        md = QMimeData()
        if itens:
            it = itens[0].data(Qt.UserRole)
            md.setData(MIME, f"{it.include}\t{it.nome}".encode())
            md.setText(texturas.codigo(it))
        return md

    def mimeTypes(self):
        return [MIME, "text/plain"]


class PainelTexturas(QWidget):
    aplicar = pyqtSignal(object)    # Item

    def __init__(self):
        super().__init__()
        ordem = {cid: k for k, (cid, _) in enumerate(texturas.CATEGORIAS)}
        self.itens = sorted(texturas.catalogo(), key=lambda it: ordem[it.categoria])
        self.por_chave = {(it.include, it.nome): it for it in self.itens}
        self.gerador = GeradorMiniaturas(self)
        self.gerador.pronta.connect(self._pronta)
        self.gerador.acabou.connect(self._acabou)
        self.iniciado = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 4)
        topo = QHBoxLayout()
        topo.addWidget(QLabel("<b>" + tr("Texturas") + "</b>"))
        self.cb_cat = QComboBox()
        self.cb_cat.addItem(tr("Todas"), "")
        for cid, nome in texturas.CATEGORIAS:
            n = sum(1 for it in self.itens if it.categoria == cid)
            if n:
                self.cb_cat.addItem(f"{tr(nome)} ({n})", cid)
        self.cb_cat.currentIndexChanged.connect(lambda _: self._filtrar())
        topo.addWidget(self.cb_cat, 1)
        lay.addLayout(topo)
        self.busca = QLineEdit(placeholderText=tr("Buscar textura…"))
        self.busca.setClearButtonEnabled(True)
        self.busca.textChanged.connect(lambda _: self._filtrar())
        lay.addWidget(self.busca)

        self.lista = ListaTexturas()
        self.lista.setViewMode(QListView.IconMode)
        self.lista.setIconSize(QSize(72, 72))
        self.lista.setGridSize(QSize(100, 120))
        self.lista.setResizeMode(QListView.Adjust)
        self.lista.setMovement(QListView.Static)
        self.lista.setWordWrap(True)
        self.lista.setDragEnabled(True)
        self.lista.setDragDropMode(QAbstractItemView.DragOnly)
        self.lista.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lista.itemDoubleClicked.connect(lambda i: self.aplicar.emit(i.data(Qt.UserRole)))
        self.lista.currentItemChanged.connect(lambda *_: self._mostrar_codigo())
        lay.addWidget(self.lista, 1)

        self.lb_codigo = QLabel()
        self.lb_codigo.setStyleSheet("font-family:monospace;color:#bbb")
        self.lb_codigo.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.lb_codigo)
        self.bt_aplicar = QPushButton(tr("Aplicar ao objeto do cursor"))
        self.bt_aplicar.setToolTip(tr("Aplica a textura escolhida ao objeto onde está o cursor do editor "
                                      "(clique num objeto na imagem para pôr o cursor nele)"))
        self.bt_aplicar.clicked.connect(self._aplicar_atual)
        lay.addWidget(self.bt_aplicar)
        self.lb_dica = QLabel(tr("Clique num objeto na imagem e dê duplo clique numa textura, "
                                 "ou arraste a textura até o objeto."))
        self.lb_dica.setWordWrap(True)
        self.lb_dica.setStyleSheet("color:#999")
        lay.addWidget(self.lb_dica)

        vazio = _icone_vazio()
        self.widgets = {}
        for it in self.itens:
            w = QListWidgetItem(rotulo(it.nome))
            w.setData(Qt.UserRole, it)
            w.setToolTip(f"<b>{it.nome}</b><br>#include \"{it.include}\"<br><code>{texturas.codigo(it)}</code>")
            arq = texturas.arquivo_miniatura(it, self.gerador.pasta)
            w.setIcon(QIcon(arq) if os.path.exists(arq) else vazio)
            self.lista.addItem(w)
            self.widgets[(it.include, it.nome)] = w

    def item_da_chave(self, chave):
        include, _, nome = chave.partition("\t")
        return self.por_chave.get((include, nome))

    def showEvent(self, ev):
        super().showEvent(ev)
        if not self.iniciado:
            self.iniciado = True
            faltam = self.gerador.gerar(self._ordem_visivel())
            if faltam:
                self.lb_dica.setText(tr("Gerando miniaturas ({} faltam; só na primeira vez)…").format(faltam))

    def _ordem_visivel(self):
        return [self.lista.item(i).data(Qt.UserRole) for i in range(self.lista.count())
                if not self.lista.item(i).isHidden()] + \
               [self.lista.item(i).data(Qt.UserRole) for i in range(self.lista.count())
                if self.lista.item(i).isHidden()]

    def _pronta(self, it):
        w = self.widgets.get((it.include, it.nome))
        if w:
            w.setIcon(QIcon(texturas.arquivo_miniatura(it, self.gerador.pasta)))

    def _acabou(self):
        self.lb_dica.setText(tr("Clique num objeto na imagem e dê duplo clique numa textura, "
                                "ou arraste a textura até o objeto."))

    def _filtrar(self):
        cat = self.cb_cat.currentData()
        q = self.busca.text().strip().lower().replace(" ", "_")
        for i in range(self.lista.count()):
            w = self.lista.item(i)
            it = w.data(Qt.UserRole)
            w.setHidden(bool((cat and it.categoria != cat) or (q and q not in it.nome.lower())))

    def _mostrar_codigo(self):
        w = self.lista.currentItem()
        self.lb_codigo.setText(texturas.codigo(w.data(Qt.UserRole)) if w else "")

    def _aplicar_atual(self):
        w = self.lista.currentItem()
        if w:
            self.aplicar.emit(w.data(Qt.UserRole))

    def parar(self):
        self.gerador.parar()


class TexturasMixin:
    """Liga o painel de texturas à janela (Mixin da classe Janela)."""

    def _montar_texturas(self):
        self.painel_tex = PainelTexturas()
        self.painel_tex.hide()
        self.painel_tex.aplicar.connect(lambda it: self.aplicar_textura(self.ed(), self.ed().textCursor().position(), it))
        self.sp_meio.addWidget(self.painel_tex)
        for v in (self.visor, self.quatro.persp):
            v.soltou_textura.connect(lambda x, y, chave, v=v: self._soltou_textura(v, x, y, chave))

    def mostrar_texturas(self, ligado):
        self.painel_tex.setVisible(ligado)
        if ligado:
            tam = self.sp_meio.sizes()
            i = self.sp_meio.indexOf(self.painel_tex)
            if tam[i] < 150:
                tam[i] = 330
                tam[1] = max(300, tam[1] - 330)
                self.sp_meio.setSizes(tam)

    def aplicar_textura(self, e, pos, item):
        if e is None:
            return False
        try:
            novo, onde = texturas.aplicar(e.toPlainText(), pos, item)
        except texturas.SemObjeto:
            self.status.showMessage(tr("Ponha o cursor dentro de um objeto (ou clique nele na imagem) "
                                       "para aplicar a textura."), 5000)
            return False
        b = sdl.objeto_em(e.toPlainText(), pos, sdl.OBJETOS)
        self._substituir_texto(e, novo)
        c = e.textCursor()
        c.setPosition(onde)
        c.setPosition(onde + len(texturas.codigo(item)), QTextCursor.KeepAnchor)
        e.setTextCursor(c)
        e.ensureCursorVisible()
        self.status.showMessage(tr("{} aplicada ao {} (Ctrl+Z desfaz)").format(item.nome, b.kw), 5000)
        return True

    def _soltou_textura(self, visor, nx, ny, chave):
        item = self.painel_tex.item_da_chave(chave)
        if not item or not self.cena:
            return
        if not (self.sel and self.sel["chave"] == self._sel_chave()):
            self.status.showMessage(tr("Preparando seleção…"))
        self._sel_preparar(lambda: self._textura_no_pixel(visor, nx, ny, item))

    def _textura_no_pixel(self, visor, nx, ny, item):
        i = self._id_em(nx, ny)
        b = self.sel["mapa"].get(i)
        if not b:
            self.status.showMessage(tr("Solte a textura em cima de um objeto."), 3000)
            return
        if self.sel["texto"] != self.cena.toPlainText():
            return
        self.abas.setCurrentWidget(self.cena)
        if self.aplicar_textura(self.cena, b.kw_ini, item):
            visor.set_destaque(self._mascara(i))
            QTimer.singleShot(1500, lambda: visor.set_destaque(None))
