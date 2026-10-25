"""Árvore da cena: os objetos do código em hierarquia (CSG dentro de CSG, #declare, câmera, luzes).
Clicar num item leva ao código e destaca o objeto na imagem."""
import re

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QLineEdit

from . import sdl
from .i18n import tr

MOSTRAR = sdl.OBJETOS | {"camera", "light_source"}
SIMBOLO = {"sphere": "●", "box": "■", "cylinder": "▮", "cone": "▲", "torus": "◎", "plane": "▬", "disc": "◉",
           "union": "∪", "merge": "∪", "difference": "−", "intersection": "∩", "object": "↳", "camera": "▷",
           "light_source": "☀", "lathe": "⚱", "text": "T"}


def itens(texto):
    """Lista de (bloco, rótulo, filhos) da cena, na ordem do código."""
    m = sdl.mascarar(texto)
    todos = sdl.blocos(texto, m)
    lacos = _lacos(m)

    def rotulo(b):
        r = f"{SIMBOLO.get(b.kw, '◆')} {b.kw}"
        if b.declarado:
            r = f"{SIMBOLO.get(b.kw, '◆')} {b.declarado} = {b.kw}"
        elif b.kw == "object":
            mn = re.match(r"\s*([A-Za-z_]\w*)", m[b.abre + 1:b.fecha or len(m)])
            if mn:
                r += " " + mn.group(1)
        laco = next((tipo for a, z, tipo in lacos if a < b.kw_ini < z), None)
        if laco and not (b.pai and any(a < b.pai.kw_ini < z for a, z, _t in lacos)):
            r += f"  ↻ #{laco}"
        return r

    def montar(b):
        filhos = [montar(f) for f in b.filhos if f.kw in MOSTRAR and f.fecha is not None]
        return (b, rotulo(b), filhos)

    def tem_ancestral_mostrado(b):
        p = b.pai
        while p is not None:
            if p.kw in MOSTRAR:
                return True
            p = p.pai
        return False

    return [montar(b) for b in todos if b.kw in MOSTRAR and b.fecha is not None and not tem_ancestral_mostrado(b)]


def _lacos(m):
    """(início, fim, "for"|"while") de cada laço do código."""
    pilha, r = [], []
    for d in re.finditer(r"#\s*(for|while|if|ifdef|ifndef|macro|switch|end)\b", m):
        if d.group(1) == "end":
            if pilha:
                tipo, ini = pilha.pop()
                if tipo in ("for", "while"):
                    r.append((ini, d.start(), tipo))
        else:
            pilha.append((d.group(1), d.start()))
    return r


class PainelArvore(QWidget):
    escolheu = pyqtSignal(int)        # kw_ini do bloco

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 2, 0, 4)
        lay.addWidget(QLabel("<b>" + tr("Cena") + "</b>"))
        self.filtro = QLineEdit(placeholderText=tr("Filtrar…"))
        self.filtro.setClearButtonEnabled(True)
        self.filtro.textChanged.connect(lambda _: self._filtrar())
        lay.addWidget(self.filtro)
        self.arv = QTreeWidget()
        self.arv.setHeaderLabels([tr("Objeto"), tr("Linha")])
        self.arv.setColumnWidth(0, 170)
        self.arv.setUniformRowHeights(True)
        self.arv.itemClicked.connect(lambda it, _c: self.escolheu.emit(it.data(0, Qt.UserRole)))
        self.arv.itemActivated.connect(lambda it, _c: self.escolheu.emit(it.data(0, Qt.UserRole)))
        lay.addWidget(self.arv, 1)
        self.texto = None

    def atualizar(self, texto, pos_cursor=None):
        if texto == self.texto:
            self.marcar_cursor(pos_cursor)
            return
        self.texto = texto
        rolagem = self.arv.verticalScrollBar().value()
        fechados = {self._chave(it) for it in self._todos() if not it.isExpanded() and it.childCount()}
        self.arv.clear()
        contagem = {}

        def add(pai, no):
            b, rot, filhos = no
            it = QTreeWidgetItem([rot, str(sdl.linha_de(texto, b.kw_ini))])
            it.setData(0, Qt.UserRole, b.kw_ini)
            it.setData(1, Qt.UserRole, b.fecha)
            k = (rot, contagem.get(rot, 0))
            contagem[rot] = k[1] + 1
            it.setData(0, Qt.UserRole + 1, k)
            it.setToolTip(0, texto[b.kw_ini:min(b.fecha + 1, b.kw_ini + 300)])
            (pai.addChild(it) if pai else self.arv.addTopLevelItem(it))
            for f in filhos:
                add(it, f)
            it.setExpanded(k not in fechados)
        try:
            for no in itens(texto):
                add(None, no)
        except Exception:      # o código pode estar no meio da digitação
            pass
        self.arv.verticalScrollBar().setValue(rolagem)
        self._filtrar()
        self.marcar_cursor(pos_cursor)

    @staticmethod
    def _chave(it):
        return it.data(0, Qt.UserRole + 1)

    def _todos(self):
        pilha = [self.arv.topLevelItem(i) for i in range(self.arv.topLevelItemCount())]
        while pilha:
            it = pilha.pop()
            yield it
            pilha += [it.child(i) for i in range(it.childCount())]

    def marcar_cursor(self, pos):
        """Seleciona o item mais interno que contém o cursor do editor."""
        if pos is None:
            return
        melhor = None
        for it in self._todos():
            ini, fim = it.data(0, Qt.UserRole), it.data(1, Qt.UserRole)
            if ini <= pos <= fim and (melhor is None or ini > melhor.data(0, Qt.UserRole)):
                melhor = it
        self.arv.blockSignals(True)
        self.arv.setCurrentItem(melhor) if melhor else self.arv.clearSelection()
        self.arv.blockSignals(False)

    def _filtrar(self):
        q = self.filtro.text().strip().lower()
        for it in self._todos():
            it.setHidden(False)
        if not q:
            return
        for it in self._todos():
            if q not in it.text(0).lower():
                # esconde só se nenhum descendente combina
                pilha, combina = [it], False
                while pilha and not combina:
                    x = pilha.pop()
                    combina = q in x.text(0).lower()
                    pilha += [x.child(i) for i in range(x.childCount())]
                it.setHidden(not combina)


class ArvoreMixin:
    def _montar_arvore(self):
        self.painel_arv = PainelArvore()
        self.painel_arv.hide()
        self.painel_arv.escolheu.connect(self._arvore_escolheu)
        self.sp_meio.insertWidget(0, self.painel_arv)
        self.arv_timer = QTimer(self, singleShot=True, interval=300)
        self.arv_timer.timeout.connect(self._arvore_atualizar)

    def mostrar_arvore(self, ligado):
        self.painel_arv.setVisible(ligado)
        if ligado:
            tam = self.sp_meio.sizes()
            if tam[0] < 120:
                tam[0] = 240
                tam[1] = max(300, tam[1] - 240)
                self.sp_meio.setSizes(tam)
            self._arvore_atualizar()

    def _arvore_agendar(self):
        if self.painel_arv.isVisible():
            self.arv_timer.start()

    def _arvore_atualizar(self):
        e = self.ed()
        if e is None or not self.painel_arv.isVisible():
            return
        self.painel_arv.atualizar(e.toPlainText(), e.textCursor().position())

    def _arvore_escolheu(self, kw_ini):
        e = self.ed()
        texto = e.toPlainText()
        m = re.match(r"[A-Za-z_]\w*", texto[kw_ini:])
        c = e.textCursor()
        c.setPosition(kw_ini)
        c.setPosition(kw_ini + (m.end() if m else 0), QTextCursor.KeepAnchor)
        e.setTextCursor(c)
        e.centerCursor()
        if e is self.cena:
            self._sel_preparar(lambda: self._destacar_bloco(kw_ini))

    def _destacar_bloco(self, kw_ini):
        if not self.sel or self.sel["texto"] != self.cena.toPlainText():
            return
        ids = [i for i, b in self.sel["mapa"].items() if b.kw_ini == kw_ini or self._dentro(b, kw_ini)]
        if not ids:
            self.status.showMessage(tr("Este objeto não aparece na imagem"), 2500)
            return
        img = None
        for i in ids:
            m = self._mascara(i)
            if img is None:
                img = m.copy()
            else:
                from PyQt5.QtGui import QPainter
                p = QPainter(img)
                p.drawImage(0, 0, m)
                p.end()
        visor = self.quatro.persp if self.a_quatro.isChecked() else self.visor
        visor.set_destaque(img)
        QTimer.singleShot(1800, lambda: visor.set_destaque(None))

    @staticmethod
    def _dentro(b, kw_ini):
        """O bloco b está dentro do bloco que começa em kw_ini? (as peças de um CSG)"""
        p = b.pai
        while p is not None:
            if p.kw_ini == kw_ini:
                return True
            p = p.pai
        return False

