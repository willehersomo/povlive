"""Exibição das imagens: visor com zoom/arraste/câmera livre, quatro vistas e histórico."""
import hashlib, json, os, time

from PyQt5.QtCore import Qt, QSize, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QIcon, QFont, QPixmap
from PyQt5.QtWidgets import QWidget, QGridLayout, QListWidget, QListWidgetItem, QListView


class Visor(QWidget):
    """Mostra uma imagem. Modos:
       - normal: roda = zoom no ponto do mouse, arrastar = mover, duplo clique = ajustar à janela
       - câmera: arrastar = girar, botão direito/meio = mover, roda = aproximar (sinais para a janela)
       - orto: roda = mudar a escala da vista ortográfica"""
    camera = pyqtSignal(str, float, float)   # ("girar"|"mover"|"zoom"|"escala", dx, dy)
    soltou = pyqtSignal()
    pixel = pyqtSignal(str)
    clicou = pyqtSignal(float, float)        # clique sem arrastar: posição na imagem (0..1)
    objeto = pyqtSignal(str, float, float, int)  # Ctrl+arrastar: ("inicio"|"mover"|"fim", x, y, modificadores)

    def __init__(self, titulo="", modo="normal"):
        super().__init__()
        self.titulo = titulo
        self.modo = modo
        self.modo_camera = False
        self.pix = None
        self.nominal = QSize(640, 480)
        self.zoom = None            # None = ajustar à janela
        self.centro = QPointF(320, 240)  # ponto da imagem (coords nominais) no meio da tela
        self.arrasto = None
        self.inicio_clique = None
        self.movendo_objeto = False
        self.destaque = None   # QImage com o contorno do objeto selecionado
        self.warp = (1.0, 0.0, 0.0)  # (escala, dx, dy em frações da imagem): resposta imediata no zoom/mover
        self.vazio = "Sem imagem ainda"
        self.setMouseTracking(True)
        self.setMinimumSize(80, 60)
        self.setAttribute(Qt.WA_OpaquePaintEvent)

    def sizeHint(self):
        return QSize(400, 300)

    def mostrar(self, pix, nominal=None):
        if nominal and nominal != self.nominal:
            if self.zoom is not None:  # mantém o mesmo ponto da cena no centro
                self.centro = QPointF(self.centro.x() * nominal.width() / self.nominal.width(),
                                      self.centro.y() * nominal.height() / self.nominal.height())
                self.zoom *= self.nominal.width() / nominal.width()
            self.nominal = nominal
        self.pix = pix
        self.warp = (1.0, 0.0, 0.0)
        self.update()

    def set_destaque(self, img):
        self.destaque = img
        self.update()

    def largura_desenhada(self):
        return self._retangulo().width()

    def _normalizado(self, pos):
        r = self._retangulo()
        return (pos.x() - r.x()) / r.width(), (pos.y() - r.y()) / r.height()

    def set_warp(self, escala, dx, dy):
        self.warp = (escala, dx, dy)
        self.update()

    def ajustar(self):
        self.zoom = None
        self.update()

    def tamanho_real(self):
        self.zoom = 1.0
        self.centro = QPointF(self.nominal.width() / 2, self.nominal.height() / 2)
        self.update()

    def _escala(self):
        if self.zoom is not None:
            return self.zoom
        return min(self.width() / max(1, self.nominal.width()), self.height() / max(1, self.nominal.height()))

    def _retangulo(self):
        e = self._escala()
        nw, nh = self.nominal.width() * e, self.nominal.height() * e
        if self.zoom is None:
            return QRectF((self.width() - nw) / 2, (self.height() - nh) / 2, nw, nh)
        return QRectF(self.width() / 2 - self.centro.x() * e, self.height() / 2 - self.centro.y() * e, nw, nh)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#111"))
        if self.pix and not self.pix.isNull():
            r = self._retangulo()
            e, dx, dy = self.warp
            if (e, dx, dy) != (1.0, 0.0, 0.0):
                c = r.center()
                w, h = r.width() * e, r.height() * e
                r = QRectF(c.x() - w / 2 + dx * r.width(), c.y() - h / 2 + dy * r.height(), w, h)
            pixels_por_px = r.width() / self.pix.width()
            p.setRenderHint(QPainter.SmoothPixmapTransform, pixels_por_px < 3)
            p.drawPixmap(r, self.pix, QRectF(self.pix.rect()))
            if self.destaque is not None:
                p.setRenderHint(QPainter.SmoothPixmapTransform, False)
                p.drawImage(r, self.destaque, QRectF(self.destaque.rect()))
        else:
            p.setPen(QColor("#666"))
            p.drawText(self.rect(), Qt.AlignCenter, self.vazio)
        p.setFont(QFont(self.font().family(), 9))
        linhas = []
        if self.titulo:
            linhas.append(self.titulo)
        if self.modo_camera:
            linhas.append("Câmera livre: arraste = girar · botão direito = mover · roda = aproximar")
        if self.movendo_objeto:
            linhas.append("Movendo objeto (Shift = passos de 0.1)")
        if linhas:
            texto = "   ".join(linhas)
            larg = p.fontMetrics().horizontalAdvance(texto) + 12
            p.fillRect(4, 4, larg, 18, QColor(0, 0, 0, 160))
            p.setPen(QColor("#ddd"))
            p.drawText(10, 17, texto)
        if self.zoom is not None:
            t = f"{self._escala() * 100:.0f}%  (duplo clique: ajustar)"
            larg = p.fontMetrics().horizontalAdvance(t) + 12
            p.fillRect(self.width() - larg - 4, self.height() - 22, larg, 18, QColor(0, 0, 0, 160))
            p.setPen(QColor("#ddd"))
            p.drawText(self.width() - larg + 2, self.height() - 9, t)

    # ----- mouse

    def wheelEvent(self, ev):
        passos = ev.angleDelta().y() / 120
        if self.modo_camera:
            self.camera.emit("zoom", passos, 0)
            return
        if self.modo == "orto":
            self.camera.emit("escala", passos, 0)
            return
        if not self.pix:
            return
        # zoom mantendo fixo o ponto sob o mouse
        e_antes = self._escala()
        r = self._retangulo()
        ponto = QPointF((ev.pos().x() - r.x()) / e_antes, (ev.pos().y() - r.y()) / e_antes)
        e = max(0.05, min(64, e_antes * (1.25 ** passos)))
        self.zoom = e
        self.centro = QPointF(ponto.x() - (ev.pos().x() - self.width() / 2) / e,
                              ponto.y() - (ev.pos().y() - self.height() / 2) / e)
        self.update()

    def mousePressEvent(self, ev):
        self.inicio_clique = ev.pos()
        if ev.button() == Qt.LeftButton and ev.modifiers() & Qt.ControlModifier and self.pix:
            self.movendo_objeto = True
            nx, ny = self._normalizado(ev.pos())
            self.objeto.emit("inicio", nx, ny, int(ev.modifiers()))
            return
        self.arrasto = (ev.pos(), ev.button())

    def mouseMoveEvent(self, ev):
        if self.movendo_objeto:
            d = ev.pos() - self.inicio_clique
            self.objeto.emit("mover", d.x(), d.y(), int(ev.modifiers()))
            return
        if self.arrasto:
            ini, botao = self.arrasto
            dx, dy = ev.x() - ini.x(), ev.y() - ini.y()
            self.arrasto = (ev.pos(), botao)
            if self.modo_camera:
                self.camera.emit("girar" if botao == Qt.LeftButton else "mover", dx, dy)
            elif self.modo == "normal" and self.pix:
                if self.zoom is None:
                    self.zoom = self._escala()
                    self.centro = QPointF(self.nominal.width() / 2, self.nominal.height() / 2)
                self.centro -= QPointF(dx / self.zoom, dy / self.zoom)
                self.update()
            return
        self._info_pixel(ev.pos())

    def mouseReleaseEvent(self, ev):
        if self.movendo_objeto:
            self.movendo_objeto = False
            d = ev.pos() - self.inicio_clique
            self.objeto.emit("fim", d.x(), d.y(), int(ev.modifiers()))
            return
        clique = (self.inicio_clique is not None and ev.button() == Qt.LeftButton
                  and (ev.pos() - self.inicio_clique).manhattanLength() < 4)
        if self.arrasto and self.modo_camera and not clique:
            self.soltou.emit()
        self.arrasto = None
        if clique and self.pix:
            nx, ny = self._normalizado(ev.pos())
            if 0 <= nx <= 1 and 0 <= ny <= 1:
                self.clicou.emit(nx, ny)

    def mouseDoubleClickEvent(self, ev):
        if not self.modo_camera:
            self.ajustar()

    def _info_pixel(self, pos):
        if not self.pix or self.pix.isNull():
            return
        r = self._retangulo()
        if not r.contains(QPointF(pos)):
            self.pixel.emit("")
            return
        nx = (pos.x() - r.x()) / r.width() * self.nominal.width()
        ny = (pos.y() - r.y()) / r.height() * self.nominal.height()
        px = int((pos.x() - r.x()) / r.width() * self.pix.width())
        py = int((pos.y() - r.y()) / r.height() * self.pix.height())
        img = self.pix.toImage()
        if 0 <= px < img.width() and 0 <= py < img.height():
            c = QColor(img.pixel(px, py))
            self.pixel.emit(f"pixel ({int(nx)}, {int(ny)})   rgb <{c.redF():.3f}, {c.greenF():.3f}, {c.blueF():.3f}>")


class QuatroVistas(QWidget):
    """Perspectiva + frente + topo + lado, em grade 2x2."""

    def __init__(self):
        super().__init__()
        g = QGridLayout(self)
        g.setContentsMargins(0, 0, 0, 0)
        g.setSpacing(2)
        self.persp = Visor("Perspectiva")
        self.orto = [Visor("Frente (olhando para +z)", "orto"), Visor("Topo (olhando para −y)", "orto"),
                     Visor("Lado direito (olhando para −x)", "orto")]
        g.addWidget(self.persp, 0, 0)
        g.addWidget(self.orto[0], 0, 1)
        g.addWidget(self.orto[1], 1, 0)
        g.addWidget(self.orto[2], 1, 1)

    def visores(self):
        return [self.persp] + self.orto

    def mostrar(self, pixs, nominal):
        for v, p in zip(self.visores(), pixs):
            v.mostrar(p, nominal)


class Historico(QListWidget):
    """Miniaturas dos renders completos. Clique = comparar; duplo clique = voltar ao código."""
    ver = pyqtSignal(object, str)      # (pixmap, rótulo)
    restaurar = pyqtSignal(str)        # código

    def __init__(self):
        super().__init__()
        self.setViewMode(QListView.IconMode)
        self.setFlow(QListView.LeftToRight)
        self.setWrapping(False)
        self.setIconSize(QSize(120, 90))
        self.setMovement(QListView.Static)
        self.setFixedHeight(130)
        self.setSpacing(4)
        self.setToolTip("Clique: comparar com a imagem atual · Duplo clique: voltar o código para esta versão")
        self.itemClicked.connect(lambda it: self.ver.emit(it.data(Qt.UserRole + 1), it.text()))
        self.itemDoubleClicked.connect(lambda it: self.restaurar.emit(it.data(Qt.UserRole)))
        self.ultimo = None
        self.pasta = None

    @staticmethod
    def pasta_para(caminho):
        """Pasta onde fica o histórico de uma cena (uma por arquivo)."""
        base = os.path.join(os.path.expanduser("~/.local/share"), "povlive", "historico")
        return os.path.join(base, hashlib.sha1(caminho.encode()).hexdigest()[:16])

    def carregar(self, caminho):
        """Troca para o histórico da cena (None = cena sem arquivo: histórico só na memória)."""
        self.limpar()
        self.pasta = self.pasta_para(caminho) if caminho else None
        if not self.pasta:
            return
        try:
            with open(os.path.join(self.pasta, "indice.json"), encoding="utf-8") as f:
                indice = json.load(f)
        except (OSError, ValueError):
            return
        for item in indice.get("versoes", []):
            try:
                codigo = open(os.path.join(self.pasta, item["pov"]), encoding="utf-8").read()
            except OSError:
                continue
            pix = QPixmap(os.path.join(self.pasta, item["png"]))
            if not pix.isNull():
                self._item(codigo, pix, item["rotulo"])
        self.ultimo = self.item(self.count() - 1).data(Qt.UserRole) if self.count() else None
        self.scrollToBottom()

    def _item(self, codigo, pix, rotulo):
        it = QListWidgetItem(QIcon(pix.scaled(240, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)), rotulo)
        it.setData(Qt.UserRole, codigo)
        it.setData(Qt.UserRole + 1, pix)
        self.addItem(it)
        return it

    def adicionar(self, codigo, pix, maximo=60):
        if codigo == self.ultimo or not pix or pix.isNull():
            return
        self.ultimo = codigo
        rotulo = time.strftime("%d/%m %H:%M:%S")
        self._item(codigo, pix, rotulo)
        while self.count() > maximo:
            self.takeItem(0)
        self.scrollToBottom()
        if self.pasta:
            self._salvar(codigo, pix, rotulo, maximo)

    def _salvar(self, codigo, pix, rotulo, maximo):
        try:
            os.makedirs(self.pasta, exist_ok=True)
            arq_indice = os.path.join(self.pasta, "indice.json")
            try:
                with open(arq_indice, encoding="utf-8") as f:
                    indice = json.load(f)
            except (OSError, ValueError):
                indice = {"versoes": []}
            nome = time.strftime("%Y%m%d-%H%M%S") + f"-{len(indice['versoes'])}"
            with open(os.path.join(self.pasta, nome + ".pov"), "w", encoding="utf-8") as f:
                f.write(codigo)
            pix.save(os.path.join(self.pasta, nome + ".png"), "PNG")
            indice["versoes"].append({"pov": nome + ".pov", "png": nome + ".png", "rotulo": rotulo})
            while len(indice["versoes"]) > maximo:
                velho = indice["versoes"].pop(0)
                for k in ("pov", "png"):
                    try:
                        os.remove(os.path.join(self.pasta, velho[k]))
                    except OSError:
                        pass
            with open(arq_indice, "w", encoding="utf-8") as f:
                json.dump(indice, f, ensure_ascii=False, indent=1)
        except OSError:
            pass  # histórico em disco é um extra: se falhar, continua só na memória

    def limpar(self):
        self.clear()
        self.ultimo = None
