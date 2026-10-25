"""Editor de código POV-Ray (QPlainTextEdit com os extras)."""
import re

from PyQt5.QtCore import Qt, QRect, QSize, QRegExp, QStringListModel, pyqtSignal, QEvent
from PyQt5.QtGui import (QColor, QFont, QPainter, QSyntaxHighlighter, QTextCharFormat, QTextFormat,
                         QTextCursor, QTextDocument)
from PyQt5.QtWidgets import (QPlainTextEdit, QWidget, QTextEdit, QCompleter, QToolTip, QColorDialog,
                             QHBoxLayout, QLineEdit, QCheckBox, QToolButton, QLabel, QAction)

from . import pov, plataforma
from .i18n import tr

PARES = {"{": "}", "(": ")", "[": "]", "<": ">", '"': '"'}
FECHA = {v: k for k, v in PARES.items()}


class Realce(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)

        def fmt(cor, negrito=False, italico=False):
            f = QTextCharFormat()
            f.setForeground(QColor(cor))
            if negrito:
                f.setFontWeight(QFont.Bold)
            f.setFontItalic(italico)
            return f

        diret = "|".join(d[1:] for d in pov.DIRETIVAS)
        self.regras = [
            (QRegExp(r"\b(" + "|".join(pov.PALAVRAS) + r")\b"), fmt("#66d9ef")),
            (QRegExp(r"\b(x|y|z|t|u|v|pi|true|false|on|off|yes|no)\b"), fmt("#ae81ff")),
            (QRegExp(r"#(" + diret + r")\b"), fmt("#f92672", True)),
            (QRegExp(r"\b[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?\b"), fmt("#ae81ff")),
            (QRegExp(r"\b[A-Z][A-Za-z0-9_]*\b"), fmt("#a6e22e")),
            (QRegExp(r'"[^"]*"'), fmt("#e6db74")),
        ]
        self.comentario = fmt("#75715e", italico=True)
        self.linha = QRegExp(r"//[^\n]*")
        self.ini, self.fim = QRegExp(r"/\*"), QRegExp(r"\*/")

    def highlightBlock(self, texto):
        for rx, f in self.regras:
            i = rx.indexIn(texto)
            while i >= 0:
                n = rx.matchedLength()
                self.setFormat(i, n, f)
                i = rx.indexIn(texto, i + n)
        i = self.linha.indexIn(texto)
        if i >= 0:
            self.setFormat(i, len(texto) - i, self.comentario)
        self.setCurrentBlockState(0)
        ini = 0 if self.previousBlockState() == 1 else self.ini.indexIn(texto)
        while ini >= 0:
            fim = self.fim.indexIn(texto, ini)
            if fim < 0:
                self.setCurrentBlockState(1)
                n = len(texto) - ini
            else:
                n = fim - ini + 2
            self.setFormat(ini, n, self.comentario)
            ini = self.ini.indexIn(texto, ini + n)


class AreaNumeros(QWidget):
    def __init__(self, ed):
        super().__init__(ed)
        self.ed = ed

    def sizeHint(self):
        return QSize(self.ed.largura_numeros(), 0)

    def paintEvent(self, ev):
        self.ed.pintar_numeros(ev)


def _sel(cursor, fundo, frente=None, linha_toda=False):
    s = QTextEdit.ExtraSelection()
    s.format.setBackground(QColor(fundo))
    if frente:
        s.format.setForeground(QColor(frente))
    if linha_toda:
        s.format.setProperty(QTextFormat.FullWidthSelection, True)
    s.cursor = cursor
    return s


class Editor(QPlainTextEdit):
    arrasteValor = pyqtSignal(str)   # novo valor enquanto arrasta um número
    arrasteFim = pyqtSignal()
    abrirInclude = pyqtSignal(str)   # Ctrl+clique num #include "x.inc"

    def __init__(self):
        super().__init__()
        f = plataforma.fonte_mono(11)
        f.setStyleHint(QFont.TypeWriter)
        self.setFont(f)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setStyleSheet("QPlainTextEdit{background:#272822;color:#f8f8f2;"
                           "selection-background-color:#49483e;border:none}")
        self.numeros = AreaNumeros(self)
        self.linha_erro = None
        self.arraste = None
        self.busca = ""            # termo destacado pela barra de busca
        self.busca_maiusc = False
        self.nomes = {}            # nome declarado -> linha da declaração (para a ajuda)
        self.pasta = ""
        self.viewport().setMouseTracking(True)
        self.blockCountChanged.connect(lambda _: self.setViewportMargins(self.largura_numeros(), 0, 0, 0))
        self.updateRequest.connect(self._atualiza_numeros)
        self.cursorPositionChanged.connect(self.marcar)
        self.textChanged.connect(self.marcar)
        self.setViewportMargins(self.largura_numeros(), 0, 0, 0)
        self.realce = Realce(self.document())  # precisa guardar a referência

        self.modelo = QStringListModel()
        self.atualizar_palavras({})
        self.completer = QCompleter(self.modelo, self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setModelSorting(QCompleter.CaseInsensitivelySortedModel)
        self.completer.activated[str].connect(self._completar)
        self.dlg_cor = None

    # ================================================================ números de linha

    def largura_numeros(self):
        return 14 + self.fontMetrics().horizontalAdvance("9") * len(str(max(1, self.blockCount())))

    def _atualiza_numeros(self, rect, dy):
        if dy:
            self.numeros.scroll(0, dy)
        else:
            self.numeros.update(0, rect.y(), self.numeros.width(), rect.height())

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        cr = self.contentsRect()
        self.numeros.setGeometry(QRect(cr.left(), cr.top(), self.largura_numeros(), cr.height()))

    def pintar_numeros(self, ev):
        p = QPainter(self.numeros)
        p.fillRect(ev.rect(), QColor("#1e1f1c"))
        p.setFont(self.font())
        bloco = self.firstVisibleBlock()
        n = bloco.blockNumber()
        topo = round(self.blockBoundingGeometry(bloco).translated(self.contentOffset()).top())
        h = self.fontMetrics().height()
        while bloco.isValid() and topo <= ev.rect().bottom():
            if bloco.isVisible():
                p.setPen(QColor("#ff6b6b" if self.linha_erro == n + 1 else "#75715e"))
                p.drawText(0, topo, self.numeros.width() - 6, h, Qt.AlignRight, str(n + 1))
            bloco = bloco.next()
            topo += round(self.blockBoundingRect(bloco).height()) if bloco.isValid() else h
            n += 1

    def wheelEvent(self, ev):
        super().wheelEvent(ev)
        if ev.modifiers() & Qt.ControlModifier:
            self.setViewportMargins(self.largura_numeros(), 0, 0, 0)

    # ================================================================ destaques

    def marcar(self):
        """Linha atual, linha com erro, resultados da busca e par de chaves."""
        sel = []
        c = self.textCursor()
        c.clearSelection()
        sel.append(_sel(c, "#3e3d32", linha_toda=True))
        if self.linha_erro:
            b = self.document().findBlockByNumber(self.linha_erro - 1)
            if b.isValid():
                sel.append(_sel(QTextCursor(b), "#5a1e1e", linha_toda=True))
        if self.busca:
            flags = QTextDocument.FindCaseSensitively if self.busca_maiusc else QTextDocument.FindFlags()
            c = self.document().find(self.busca, 0, flags)
            n = 0
            while not c.isNull() and n < 2000:
                sel.append(_sel(c, "#6b5b00"))
                c = self.document().find(self.busca, c, flags)
                n += 1
        sel += self._par_de_chaves()
        self.setExtraSelections(sel)

    def _par_de_chaves(self):
        doc = self.document()
        pos = self.textCursor().position()
        texto = doc.toPlainText()
        for p in (pos - 1, pos):
            if 0 <= p < len(texto) and texto[p] in "{}()[]":
                alvo = self._achar_par(texto, p)
                cor_ok, cor_erro = "#4a6b8a", "#8a2b2b"
                c1 = QTextCursor(doc)
                c1.setPosition(p)
                c1.setPosition(p + 1, QTextCursor.KeepAnchor)
                if alvo is None:
                    return [_sel(c1, cor_erro, "#ffffff")]
                c2 = QTextCursor(doc)
                c2.setPosition(alvo)
                c2.setPosition(alvo + 1, QTextCursor.KeepAnchor)
                return [_sel(c1, cor_ok, "#ffffff"), _sel(c2, cor_ok, "#ffffff")]
        return []

    @staticmethod
    def _achar_par(texto, p):
        ch = texto[p]
        if ch in "{([":
            abre, fecha, passo = ch, PARES[ch], 1
        else:
            abre, fecha, passo = ch, FECHA[ch], -1
        nivel, i = 0, p
        while 0 <= i < len(texto):
            if texto[i] == abre:
                nivel += 1
            elif texto[i] == fecha:
                nivel -= 1
                if nivel == 0:
                    return i
            i += passo
        return None

    def set_erro(self, linha):
        self.linha_erro = linha
        self.marcar()
        self.numeros.update()

    def ir_para(self, linha):
        b = self.document().findBlockByNumber(max(0, linha - 1))
        if b.isValid():
            self.setTextCursor(QTextCursor(b))
            self.centerCursor()
            self.setFocus()

    # ================================================================ mouse: arrastar números, includes, ajuda

    def _numero_em(self, pos):
        c = self.cursorForPosition(pos)
        bloco, col = c.block(), c.positionInBlock()
        texto = bloco.text()
        if "//" in texto and col > texto.index("//"):
            return None
        for m in pov.RX_NUMERO.finditer(texto):
            if m.start() <= col <= m.end():
                return bloco.position() + m.start(), m.group()
        return None

    def _include_em(self, pos):
        c = self.cursorForPosition(pos)
        for m in pov.RX_INCLUDE.finditer(c.block().text()):
            if m.start() <= c.positionInBlock() <= m.end():
                return m.group(1)
        return None

    def _palavra_em(self, pos):
        c = self.cursorForPosition(pos)
        texto, col = c.block().text(), c.positionInBlock()
        for m in re.finditer(r"#?[A-Za-z_]\w*", texto):
            if m.start() <= col < m.end():
                return m.group()
        return None

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton and ev.modifiers() & Qt.ControlModifier:
            inc = self._include_em(ev.pos())
            if inc:
                self.abrirInclude.emit(inc)
                return
            achado = self._numero_em(ev.pos())
            if achado:
                ini, txt = achado
                dec = len(txt.split(".")[1]) if "." in txt else 0
                self.arraste = {"ini": ini, "len": len(txt), "valor": float(txt), "atual": float(txt),
                                "dec": dec, "x0": ev.x(), "primeiro": True, "fino": False}
                return
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        a = self.arraste
        if a:
            fino = bool(ev.modifiers() & Qt.ShiftModifier)
            if fino != a["fino"]:  # trocou o modo: recomeça do valor atual
                a.update(fino=fino, valor=a["atual"], x0=ev.x())
            dec = a["dec"] + (1 if fino else 0)
            novo = a["valor"] + round((ev.x() - a["x0"]) / 4) * 10 ** -dec
            a["atual"] = novo
            txt = f"{novo:.{dec}f}"
            if float(txt) == 0:
                txt = txt.lstrip("-")
            self._trocar_trecho(a, txt)
            return
        ctrl = ev.modifiers() & Qt.ControlModifier
        if ctrl and (self._numero_em(ev.pos())):
            self.viewport().setCursor(Qt.SizeHorCursor)
        elif ctrl and self._include_em(ev.pos()):
            self.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.viewport().setCursor(Qt.IBeamCursor)
        super().mouseMoveEvent(ev)

    def _trocar_trecho(self, a, txt):
        """Troca o trecho a['ini']..+a['len'] juntando tudo num único Ctrl+Z."""
        c = QTextCursor(self.document())
        c.setPosition(a["ini"])
        c.setPosition(a["ini"] + a["len"], QTextCursor.KeepAnchor)
        if c.selectedText() == txt:
            return
        if a["primeiro"]:
            c.beginEditBlock()
            a["primeiro"] = False
        else:
            c.joinPreviousEditBlock()
        c.insertText(txt)
        c.endEditBlock()
        a["len"] = len(txt)
        self.arrasteValor.emit(txt)

    def mouseReleaseEvent(self, ev):
        if self.arraste:
            mudou = not self.arraste["primeiro"]
            self.arraste = None
            if mudou:
                self.arrasteFim.emit()
            return
        super().mouseReleaseEvent(ev)

    def event(self, ev):
        if ev.type() == QEvent.ToolTip:
            pos = self.viewport().mapFromGlobal(ev.globalPos())
            palavra = self._palavra_em(pos)
            dica = pov.ajuda(palavra)
            if dica is None and palavra in self.nomes:
                dica = self.nomes[palavra]
            if dica:
                QToolTip.showText(ev.globalPos(), "<pre style='margin:0'>" + dica.replace("&", "&amp;")
                                  .replace("<", "&lt;").replace(">", "&gt;") + "</pre>", self)
            else:
                QToolTip.hideText()
            return True
        return super().event(ev)

    # ================================================================ seletor de cor

    def rgb_no_cursor(self):
        """(início, fim, (r,g,b), resto) do rgb sob o cursor, ou None."""
        c = self.textCursor()
        bloco, col = c.block(), c.positionInBlock()
        for m in pov.RX_RGB.finditer(bloco.text()):
            if m.start() <= col <= m.end() + 12:  # aceita o cursor um pouco depois (componentes extras)
                if m.group(5) is not None:
                    v = float(m.group(5))
                    rgb, ini, fim = (v, v, v), m.start(5), m.end(5)
                else:
                    rgb = tuple(float(m.group(i)) for i in (2, 3, 4))
                    ini, fim = m.start(2), m.end(4)
                return bloco.position() + ini, bloco.position() + fim, rgb, m.group(5) is not None
        return None

    def escolher_cor(self):
        achado = self.rgb_no_cursor()
        if not achado:
            return False
        ini, fim, rgb, escalar = achado
        a = {"ini": ini, "len": fim - ini, "primeiro": True}
        texto_original = self.document().toPlainText()[ini:fim]
        inicial = QColor.fromRgbF(*[max(0.0, min(1.0, v)) for v in rgb])
        dlg = self.dlg_cor = QColorDialog(inicial, self)
        dlg.setWindowTitle(tr("Escolher cor (atualiza ao vivo)"))
        dlg.setOption(QColorDialog.DontUseNativeDialog)

        def mudar(cor):
            txt = ", ".join(pov.fmt_num(round(x, 3)) for x in (cor.redF(), cor.greenF(), cor.blueF()))
            if escalar:
                txt = "<" + txt + ">"
            self._trocar_trecho(a, txt)

        dlg.currentColorChanged.connect(mudar)

        def fim_dialogo(r):
            if r == 0 and not a["primeiro"]:  # cancelou: volta o original
                self._trocar_trecho(a, texto_original)
            self.window().activateWindow()
            self.setFocus()
            self.arrasteFim.emit()
        dlg.finished.connect(fim_dialogo)
        dlg.open()
        return True

    def contextMenuEvent(self, ev):
        if not self.textCursor().hasSelection():
            self.setTextCursor(self.cursorForPosition(ev.pos()))
        menu = self.createStandardContextMenu()
        if self.rgb_no_cursor():
            primeira = menu.actions()[0]
            acao = QAction(tr("Escolher cor…"), menu)
            acao.triggered.connect(self.escolher_cor)
            menu.insertAction(primeira, acao)
            menu.insertSeparator(primeira)
        menu.exec_(ev.globalPos())

    # ================================================================ edição: comentar, indentar, pares

    def _linhas_selecionadas(self):
        c = self.textCursor()
        doc = self.document()
        ini, fim = c.selectionStart(), c.selectionEnd()
        if fim > ini and doc.findBlock(fim).position() == fim:  # seleção termina no começo de uma linha
            fim -= 1
        blocos, b, ultimo = [], doc.findBlock(ini), doc.findBlock(fim)
        while b.isValid():
            blocos.append(b)
            if b == ultimo:
                break
            b = b.next()
        return blocos

    def comentar(self):
        blocos = self._linhas_selecionadas()
        com_texto = [b for b in blocos if b.text().strip()]
        tirar = com_texto and all(b.text().lstrip().startswith("//") for b in com_texto)
        indent = min((len(b.text()) - len(b.text().lstrip()) for b in com_texto), default=0)
        c = QTextCursor(self.document())
        c.beginEditBlock()
        for b in blocos:
            t = b.text()
            if tirar:
                if "//" not in t:  # linha em branco no meio da seleção
                    continue
                i = t.index("//")
                n = 3 if t[i:i + 3] == "// " else 2
                c.setPosition(b.position() + i)
                c.setPosition(b.position() + i + n, QTextCursor.KeepAnchor)
                c.removeSelectedText()
            elif t.strip():
                c.setPosition(b.position() + indent)
                c.insertText("// ")
        c.endEditBlock()

    def indentar(self, menos=False):
        c = QTextCursor(self.document())
        c.beginEditBlock()
        for b in self._linhas_selecionadas():
            if menos:
                t = b.text()
                n = len(t) - len(t.lstrip(" "))
                n = min(4, n) if n else (1 if t.startswith("\t") else 0)
                if n:
                    c.setPosition(b.position())
                    c.setPosition(b.position() + n, QTextCursor.KeepAnchor)
                    c.removeSelectedText()
            else:
                c.setPosition(b.position())
                c.insertText("    ")
        c.endEditBlock()

    def duplicar_linha(self):
        c = self.textCursor()
        t = c.block().text()
        c.movePosition(QTextCursor.EndOfBlock)
        c.insertText("\n" + t)
        self.setTextCursor(c)

    def _char(self, deslocamento):
        p = self.textCursor().position() + deslocamento
        t = self.document()
        return t.characterAt(p) if 0 <= p < t.characterCount() else ""

    def _dentro_de_comentario_ou_texto(self):
        c = self.textCursor()
        antes = c.block().text()[:c.positionInBlock()]
        return "//" in antes or antes.count('"') % 2 == 1

    # ================================================================ autocompletar

    def atualizar_palavras(self, nomes):
        self.nomes = nomes
        self.modelo.setStringList(sorted(set(pov.PALAVRAS + pov.DIRETIVAS + list(nomes)), key=str.lower))

    def _prefixo(self):
        c = self.textCursor()
        m = re.search(r"#?[A-Za-z_]\w*$", c.block().text()[:c.positionInBlock()])
        return m.group() if m else ""

    def _completar(self, palavra):
        c = self.textCursor()
        c.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, len(self._prefixo()))
        c.insertText(palavra)
        self.setTextCursor(c)

    def inserir_modelo(self, modelo):
        """Insere um trecho respeitando a indentação da linha; '|' marca onde o cursor fica."""
        c = self.textCursor()
        linha = c.block().text()
        indent = re.match(r"\s*", linha).group()
        if linha.strip() and c.positionInBlock() == len(linha):
            c.insertText("\n" + indent)
        antes, _, depois = modelo.partition("|")
        antes = antes.replace("\n", "\n" + indent)
        depois = depois.replace("\n", "\n" + indent)
        c.beginEditBlock()
        c.insertText(antes)
        pos = c.position()
        c.insertText(depois)
        c.endEditBlock()
        c.setPosition(pos)
        self.setTextCursor(c)
        self.setFocus()

    # ================================================================ teclado

    def keyPressEvent(self, ev):
        popup = self.completer.popup()
        k, mods, txt = ev.key(), ev.modifiers(), ev.text()
        if popup.isVisible() and k in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab):
            ev.ignore()
            return
        c = self.textCursor()
        ctrl = mods & Qt.ControlModifier

        if ctrl and k == Qt.Key_Space:
            self._mostrar_completar(forcar=True)
            return
        if k == Qt.Key_Tab and not mods and c.hasSelection():
            return self.indentar()
        if k == Qt.Key_Backtab:
            return self.indentar(menos=True)
        if k == Qt.Key_Tab and not mods:
            return self.insertPlainText("    ")

        # Enter: mantém a indentação; entre { } abre um bloco
        if k in (Qt.Key_Return, Qt.Key_Enter) and not mods:
            linha = c.block().text()[:c.positionInBlock()]
            indent = re.match(r"\s*", linha).group()
            if linha.rstrip().endswith("{"):
                if self._char(0) == "}":
                    c.beginEditBlock()
                    c.insertText("\n" + indent + "    ")
                    pos = c.position()
                    c.insertText("\n" + indent)
                    c.endEditBlock()
                    c.setPosition(pos)
                    self.setTextCursor(c)
                    return
                indent += "    "
            c.insertText("\n" + indent)
            self.setTextCursor(c)
            return

        # Backspace entre um par vazio apaga os dois
        if k == Qt.Key_Backspace and not mods and not c.hasSelection():
            a, d = self._char(-1), self._char(0)
            if a in PARES and PARES[a] == d:
                c.beginEditBlock()
                c.deletePreviousChar()
                c.deleteChar()
                c.endEditBlock()
                return
            linha = c.block().text()[:c.positionInBlock()]
            if linha and not linha.strip(" ") and len(linha) % 4 == 0:  # apaga um nível de indentação
                c.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, 4)
                c.removeSelectedText()
                return

        if txt and len(txt) == 1 and not ctrl:
            proximo = self._char(0)
            # digitar o fechamento quando ele já está ali: só pula por cima
            if (txt in FECHA or txt == '"') and proximo == txt and not c.hasSelection():
                c.movePosition(QTextCursor.Right)
                self.setTextCursor(c)
                return
            # fechar pares automaticamente ( { ( [ < " )
            linha_txt = c.block().text().lstrip()
            menor_em_condicao = txt == "<" and re.match(r"#(if|while|elseif|declare|local)", linha_txt)
            if txt in PARES and not self._dentro_de_comentario_ou_texto() and not menor_em_condicao:
                if c.hasSelection():  # envolve a seleção
                    c.insertText(txt + c.selectedText() + PARES[txt])
                    return
                if not proximo or proximo.isspace() or proximo in ")]}>,;":
                    c.insertText(txt + PARES[txt])
                    c.movePosition(QTextCursor.Left)
                    self.setTextCursor(c)
                    return
            # "}" numa linha só com espaços volta um nível
            if txt == "}":
                linha = c.block().text()
                if not linha.strip() and len(linha) >= 4 and c.positionInBlock() == len(linha):
                    c.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, 4)
                    c.removeSelectedText()

        super().keyPressEvent(ev)
        if txt and (txt.isalnum() or txt in "_#"):
            self._mostrar_completar()
        elif k not in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt):
            popup.hide()

    def _mostrar_completar(self, forcar=False):
        popup = self.completer.popup()
        prefixo = self._prefixo()
        if not prefixo or (len(prefixo) < 2 and not forcar):
            popup.hide()
            return
        self.completer.setCompletionPrefix(prefixo)
        n = self.completer.completionCount()
        if n == 0 or (n == 1 and self.completer.currentCompletion() == prefixo):
            popup.hide()
            return
        popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
        r = self.cursorRect()
        r.translate(self.viewportMargins().left(), 0)
        r.setWidth(popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width() + 10)
        self.completer.complete(r)


# ==================================================================== barra de busca

class BarraBusca(QWidget):
    def __init__(self, obter_editor):
        super().__init__()
        self.ed = obter_editor
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        self.campo = QLineEdit(placeholderText=tr("Buscar"))
        self.troca = QLineEdit(placeholderText=tr("Substituir por"))
        self.maiusc = QCheckBox("Aa")
        self.maiusc.setToolTip(tr("Diferenciar maiúsculas"))
        self.info = QLabel()
        lay.addWidget(self.campo, 2)
        for txt, dica, f in (("↑", tr("Anterior (Shift+Enter)"), lambda: self.achar(True)),
                             ("↓", tr("Próximo (Enter)"), self.achar)):
            b = QToolButton(text=txt, toolTip=dica)
            b.clicked.connect(f)
            lay.addWidget(b)
        lay.addWidget(self.maiusc)
        lay.addWidget(self.troca, 2)
        for txt, f in ((tr("Substituir"), self.substituir), (tr("Todos"), self.substituir_todos)):
            b = QToolButton(text=txt)
            b.clicked.connect(f)
            lay.addWidget(b)
        lay.addWidget(self.info)
        fechar = QToolButton(text="✕", toolTip=tr("Fechar (Esc)"))
        fechar.clicked.connect(self.fechar)
        lay.addWidget(fechar)
        self.campo.textChanged.connect(self._mudou)
        self.maiusc.toggled.connect(self._mudou)
        self.campo.returnPressed.connect(self.achar)
        self.troca.returnPressed.connect(self.substituir)
        self.campo.installEventFilter(self)
        self.troca.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.KeyPress:
            if ev.key() == Qt.Key_Escape:
                self.fechar()
                return True
            if ev.key() in (Qt.Key_Return, Qt.Key_Enter) and ev.modifiers() & Qt.ShiftModifier and obj is self.campo:
                self.achar(True)
                return True
        return False

    def abrir(self, substituir=False):
        ed = self.ed()
        sel = ed.textCursor().selectedText()
        if sel and " " not in sel:
            self.campo.setText(sel)
        self.show()
        (self.troca if substituir and self.campo.text() else self.campo).setFocus()
        self.campo.selectAll()
        self._mudou()

    def fechar(self):
        self.hide()
        ed = self.ed()
        ed.busca = ""
        ed.marcar()
        ed.setFocus()

    def _flags(self, para_tras=False):
        f = QTextDocument.FindFlags()
        if self.maiusc.isChecked():
            f |= QTextDocument.FindCaseSensitively
        if para_tras:
            f |= QTextDocument.FindBackward
        return f

    def _mudou(self):
        ed = self.ed()
        ed.busca = self.campo.text()
        ed.busca_maiusc = self.maiusc.isChecked()
        ed.marcar()
        t = ed.toPlainText()
        termo = self.campo.text()
        if termo:
            n = t.count(termo) if self.maiusc.isChecked() else t.lower().count(termo.lower())
            self.info.setText(tr("{} achado(s)").format(n))
            self.campo.setStyleSheet("" if n else "background:#5a1e1e")
        else:
            self.info.setText("")
            self.campo.setStyleSheet("")

    def achar(self, para_tras=False):
        ed = self.ed()
        termo = self.campo.text()
        if not termo:
            return
        if not ed.find(termo, self._flags(para_tras)):
            c = ed.textCursor()
            c.movePosition(QTextCursor.End if para_tras else QTextCursor.Start)
            ed.setTextCursor(c)
            ed.find(termo, self._flags(para_tras))

    def substituir(self):
        ed = self.ed()
        c = ed.textCursor()
        termo = self.campo.text()
        if c.hasSelection() and (c.selectedText() == termo if self.maiusc.isChecked()
                                 else c.selectedText().lower() == termo.lower()):
            c.insertText(self.troca.text())
        self.achar()
        self._mudou()

    def substituir_todos(self):
        ed = self.ed()
        termo = self.campo.text()
        if not termo:
            return
        doc = ed.document()
        c = QTextCursor(doc)
        c.beginEditBlock()
        achado = doc.find(termo, 0, self._flags())
        n = 0
        while not achado.isNull():
            achado.insertText(self.troca.text())
            n += 1
            achado = doc.find(termo, achado, self._flags())
        c.endEditBlock()
        self._mudou()
        self.info.setText(tr("{} substituído(s)").format(n))
