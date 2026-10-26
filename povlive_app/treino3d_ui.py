"""Janela do treino 3D: transformações 3D, câmera e projeção, iluminação de Phong.

À esquerda o enunciado e os campos; à direita uma vista 3D que gira com o mouse e, nas questões de câmera,
a tela com os pontos projetados."""
import math, random

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QColor, QPainter, QPen, QFont, QPolygonF
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton,
                             QComboBox, QTextBrowser, QWidget, QSpinBox, QSplitter, QSizePolicy, QScrollArea,
                             QMessageBox)

from . import treino3d as T
from .i18n import tr, N_

MODOS = [("transformacoes", N_("Transformações 3D")), ("camera", N_("Câmera e projeção")),
         ("phong", N_("Iluminação (Phong)"))]
NIVEIS = [("facil", N_("Fácil")), ("medio", N_("Médio")), ("dificil", N_("Difícil"))]
OK = "background:#1f4d2b;color:#e8ffe8"
ERRO = "background:#5a1f1f;color:#ffe8e8"
CORES_EIXOS = {"x": "#ff6b6b", "y": "#6fdc8c", "z": "#5aa9ff"}


class Vista3D(QWidget):
    """Vista em arame com projeção ortográfica que gira arrastando o mouse (roda = zoom).

    Mostra como o POV-Ray: x para a direita, y para cima e z entrando na tela (mão esquerda)."""

    def __init__(self):
        super().__init__()
        self.prims = []
        self.yaw, self.pitch, self.zoom = 30.0, 25.0, 1.0
        self._arrasto = None
        self.setMinimumSize(320, 280)
        self.setToolTip(tr("Arraste para girar a vista; a roda do mouse aproxima"))

    def mostrar(self, prims):
        self.prims = prims
        self.update()

    def _girar(self, p):
        x, y, z = p
        a, b = math.radians(self.yaw), math.radians(self.pitch)
        x1 = x * math.cos(a) + z * math.sin(a)
        z1 = -x * math.sin(a) + z * math.cos(a)
        return x1, y * math.cos(b) + z1 * math.sin(b)

    def mousePressEvent(self, ev):
        self._arrasto = (ev.pos(), self.yaw, self.pitch)

    def mouseMoveEvent(self, ev):
        if self._arrasto:
            p0, yaw, pitch = self._arrasto
            d = ev.pos() - p0
            self.yaw = yaw - d.x() * 0.5
            self.pitch = max(-89.0, min(89.0, pitch + d.y() * 0.5))
            self.update()

    def mouseReleaseEvent(self, ev):
        self._arrasto = None

    def wheelEvent(self, ev):
        self.zoom = max(0.3, min(5.0, self.zoom * (1.15 if ev.angleDelta().y() > 0 else 1 / 1.15)))
        self.update()

    def _pontos(self):
        for pr in self.prims:
            if pr[0] in ("linha", "seta"):
                yield pr[1]
                yield pr[2]
            else:
                yield pr[1]

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#1e1e1e"))
        pts = list(self._pontos()) or [(0, 0, 0)]
        alcance = max(3.0, max(max(abs(c) for c in q) for q in pts) + 1)
        esc = min(self.width(), self.height()) / (2.6 * alcance) * self.zoom
        cx, cy = self.width() / 2, self.height() / 2

        def tela(q):
            x, y = self._girar(q)
            return QPointF(cx + x * esc, cy - y * esc)

        # chão (plano y = 0) e eixos
        n = int(math.ceil(alcance))
        p.setPen(QPen(QColor("#2c2c2c"), 1))
        for k in range(-n, n + 1):
            p.drawLine(tela((k, 0, -n)), tela((k, 0, n)))
            p.drawLine(tela((-n, 0, k)), tela((n, 0, k)))
        p.setFont(QFont(self.font().family(), 9))
        for i, e in enumerate("xyz"):
            fim = [0.0, 0.0, 0.0]
            fim[i] = n
            ini = [0.0, 0.0, 0.0]
            ini[i] = -n
            p.setPen(QPen(QColor(CORES_EIXOS[e]).darker(170), 1, Qt.DashLine))
            p.drawLine(tela(ini), tela((0, 0, 0)))
            p.setPen(QPen(QColor(CORES_EIXOS[e]), 1.5))
            p.drawLine(tela((0, 0, 0)), tela(fim))
            p.drawText(tela(fim) + QPointF(4, 4), e)
            for k in range(1, n + 1):
                m = [0.0, 0.0, 0.0]
                m[i] = k
                q = tela(m)
                p.drawEllipse(q, 1.5, 1.5)
        for pr in self.prims:
            if pr[0] == "linha":
                _, a, b, cor, tracejado = pr
                p.setPen(QPen(QColor(cor), 2.0, Qt.DashLine if tracejado else Qt.SolidLine))
                p.drawLine(tela(a), tela(b))
            elif pr[0] == "seta":
                _, a, b, cor, rotulo = pr
                qa, qb = tela(a), tela(b)
                p.setPen(QPen(QColor(cor), 2.2))
                p.drawLine(qa, qb)
                d = qb - qa
                comp = math.hypot(d.x(), d.y())
                if comp > 1:
                    ux, uy = d.x() / comp, d.y() / comp
                    ponta = QPolygonF([qb, qb - QPointF(ux * 9 - uy * 4, uy * 9 + ux * 4),
                                       qb - QPointF(ux * 9 + uy * 4, uy * 9 - ux * 4)])
                    p.setBrush(QColor(cor))
                    p.drawPolygon(ponta)
                p.drawText(qb + QPointF(5, -5), rotulo)
            else:
                _, a, cor, rotulo = pr
                q = tela(a)
                p.setPen(QPen(QColor(cor), 1.5))
                p.setBrush(QColor(cor))
                p.drawEllipse(q, 3.5, 3.5)
                p.drawText(q + QPointF(6, -6), rotulo)
        p.setPen(QColor("#777"))
        p.drawText(QRectF(6, self.height() - 20, self.width() - 12, 16), Qt.AlignLeft,
                   tr("x vermelho · y verde · z azul (entra na tela, como no POV-Ray)"))
        p.end()


class Tela(QWidget):
    """A imagem da câmera (4:3) com os pontos projetados: a resposta do aluno e a certa."""

    def __init__(self):
        super().__init__()
        self.dados = None
        self.setMinimumSize(320, 200)

    def mostrar(self, dados):
        self.dados = dados
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#1e1e1e"))
        if not self.dados:
            p.end()
            return
        larg = min(self.width() - 20, (self.height() - 30) * 4 / 3)
        alt = larg * 3 / 4
        x0, y0 = (self.width() - larg) / 2, (self.height() - alt) / 2 + 6
        p.setPen(QPen(QColor("#888"), 1.5))
        p.setBrush(QColor("#111"))
        p.drawRect(QRectF(x0, y0, larg, alt))
        p.setPen(QPen(QColor("#333"), 1, Qt.DashLine))
        p.drawLine(QPointF(x0 + larg / 2, y0), QPointF(x0 + larg / 2, y0 + alt))
        p.drawLine(QPointF(x0, y0 + alt / 2), QPointF(x0 + larg, y0 + alt / 2))
        p.setPen(QColor("#777"))
        p.setFont(QFont(self.font().family(), 8))
        p.drawText(QPointF(x0, y0 - 4), tr("imagem da câmera (400×300)"))
        r, u = self.dados["right"], self.dados["up"]
        for pontos, cor, nomes in self.dados["figuras"]:
            p.setPen(QPen(QColor(cor), 1.8))
            p.setBrush(QColor(cor))
            for (x, y), n in zip(pontos, nomes):
                q = QPointF(x0 + (x / r + 0.5) * larg, y0 + (0.5 - y / u) * alt)
                p.drawEllipse(q, 4, 4)
                p.drawText(q + QPointF(6, -6), n)
        p.end()


class Treino3D(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Treino 3D: transformações, câmera e iluminação"))
        self.resize(1180, 820)
        lay = QVBoxLayout(self)
        topo = QHBoxLayout()
        self.cb_modo = QComboBox()
        for k, nome in MODOS:
            self.cb_modo.addItem(tr(nome), k)
        topo.addWidget(self.cb_modo)
        self.cb_nivel = QComboBox()
        for k, nome in NIVEIS:
            self.cb_nivel.addItem(tr(nome), k)
        self.cb_nivel.setCurrentIndex(1)
        topo.addWidget(QLabel(tr("Nível")))
        topo.addWidget(self.cb_nivel)
        topo.addWidget(QLabel(tr("Questão nº")))
        self.sp_num = QSpinBox(minimum=1, maximum=99999)
        self.sp_num.setToolTip(tr("Cada número gera sempre a mesma questão: dá para combinar com os colegas"))
        topo.addWidget(self.sp_num)
        bt_nova = QPushButton(tr("Nova questão"))
        bt_nova.clicked.connect(lambda: self.sp_num.setValue(random.randint(1, 99999)))
        topo.addWidget(bt_nova)
        topo.addStretch()
        bt_form = QPushButton(tr("Fórmulas"))
        bt_form.clicked.connect(self.mostrar_formulas)
        topo.addWidget(bt_form)
        self.bt_pov = QPushButton(tr("Ver no POV-Ray"))
        self.bt_pov.setToolTip(tr("Abre a cena da questão numa aba do editor para renderizar"))
        self.bt_pov.clicked.connect(self.ver_no_povray)
        self.bt_pov.setEnabled(hasattr(parent, "abrir_exemplo"))
        topo.addWidget(self.bt_pov)
        lay.addLayout(topo)

        sp = QSplitter(Qt.Horizontal)
        esq = QWidget()
        le = QVBoxLayout(esq)
        le.setContentsMargins(0, 0, 0, 0)
        self.enunciado = QLabel(wordWrap=True, textFormat=Qt.RichText)
        self.enunciado.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        le.addWidget(self.enunciado)
        self.rolagem = QScrollArea(widgetResizable=True)
        le.addWidget(self.rolagem, 2)
        dica = QLabel(tr("Aceita 0,866 · -1/2 · √3/2 · sqrt(2)/2 · cos(30)"))
        dica.setStyleSheet("color:#999")
        le.addWidget(dica)
        botoes = QHBoxLayout()
        bt_conf = QPushButton(tr("Conferir"))
        bt_conf.setDefault(True)
        bt_conf.clicked.connect(self.conferir)
        bt_sol = QPushButton(tr("Mostrar solução"))
        bt_sol.clicked.connect(self.mostrar_solucao)
        botoes.addWidget(bt_conf)
        botoes.addWidget(bt_sol)
        le.addLayout(botoes)
        self.resultado = QLabel(wordWrap=True)
        le.addWidget(self.resultado)
        self.solucao = QTextBrowser()
        le.addWidget(self.solucao, 2)
        sp.addWidget(esq)
        dir_ = QSplitter(Qt.Vertical)
        self.vista = Vista3D()
        self.tela = Tela()
        dir_.addWidget(self.vista)
        dir_.addWidget(self.tela)
        dir_.setSizes([500, 260])
        sp.addWidget(dir_)
        sp.setSizes([560, 560])
        lay.addWidget(sp, 1)
        self.legenda = QLabel()
        lay.addWidget(self.legenda)

        self.cb_modo.currentIndexChanged.connect(lambda _: self.nova())
        self.cb_nivel.currentIndexChanged.connect(lambda _: self.nova())
        self.sp_num.valueChanged.connect(lambda _: self.nova())
        self.sp_num.blockSignals(True)
        self.sp_num.setValue(random.randint(1, 99999))
        self.sp_num.blockSignals(False)
        self.nova()

    # ------------------------------------------------------------ questão

    def nova(self):
        self.q = T.questao(self.cb_modo.currentData(), self.sp_num.value(), self.cb_nivel.currentData())
        self.enunciado.setText(self.q.enunciado())
        self.secoes = self.q.respostas()
        caixa = QWidget()
        lc = QVBoxLayout(caixa)
        lc.setContentsMargins(0, 0, 0, 0)
        self.campos = []
        for s in self.secoes:
            lc.addWidget(QLabel(f"<b>{s['titulo']}</b>"))
            grade = QGridLayout()
            linhas = []
            for i, (rotulo, valores) in enumerate(zip(s["rotulos"], s["valores"])):
                if rotulo:
                    grade.addWidget(QLabel(rotulo), i, 0)
                linha = []
                for j in range(len(valores)):
                    c = QLineEdit(maximumWidth=86)
                    if s["colunas"]:
                        c.setPlaceholderText(s["colunas"][j])
                    c.textChanged.connect(lambda _: self._desenhar())
                    grade.addWidget(c, i, j + 1)
                    linha.append(c)
                linhas.append(linha)
            grade.setColumnStretch(len(s["valores"][0]) + 1, 1)
            lc.addLayout(grade)
            self.campos.append(linhas)
        lc.addStretch()
        self.rolagem.setWidget(caixa)          # o widget antigo é apagado pelo QScrollArea
        self.resultado.clear()
        self.solucao.clear()
        self.mostrou_certa = False
        camera = self.q.modo == "camera"
        self.tela.setVisible(camera)
        legenda = ("<span style='color:#5aa9ff'>■</span> " + tr("figura original") +
                   " &nbsp; <span style='color:#ffb347'>■</span> " + tr("sua resposta") +
                   " &nbsp; <span style='color:#6fdc8c'>■</span> " + tr("resposta certa (depois de conferir)"))
        if camera:
            legenda = ("<span style='color:#5aa9ff'>■</span> " + tr("pontos") +
                       " &nbsp; <span style='color:#d58cff'>■</span> " + tr("câmera (u, v, w e a vista)") +
                       " &nbsp; <span style='color:#ffb347'>■</span> " + tr("sua projeção") +
                       " &nbsp; <span style='color:#6fdc8c'>■</span> " + tr("resposta certa (depois de conferir)"))
        elif self.q.modo == "phong":
            legenda = ("<span style='color:#ddd'>■</span> N &nbsp; <span style='color:#ffe066'>■</span> L &nbsp; "
                       "<span style='color:#5aa9ff'>■</span> V &nbsp; <span style='color:#ffb347'>■</span> "
                       + tr("seu R") + " &nbsp; <span style='color:#6fdc8c'>■</span> "
                       + tr("R certo (depois de conferir)"))
        self.legenda.setText(legenda)
        self._desenhar()

    def _valores_do_aluno(self):
        r = []
        for linhas in self.campos:
            sec = []
            for linha in linhas:
                vals = []
                for c in linha:
                    try:
                        vals.append(T.ler_numero(c.text()))
                    except T.EntradaInvalida:
                        vals.append(None)
                sec.append(vals)
            r.append(sec)
        return r

    def _desenhar(self):
        d = self.q.desenho(self._valores_do_aluno(), self.mostrou_certa)
        self.vista.mostrar(d["cena"])
        self.tela.mostrar(d["tela"])

    def conferir(self):
        certos = total = 0
        for s, linhas in zip(self.secoes, self.campos):
            for valores, campos in zip(s["valores"], linhas):
                for v, c in zip(valores, campos):
                    try:
                        x = T.ler_numero(c.text())
                        ok = abs(x - v) <= s["tol"] if s["tol"] is not None else T.igual(x, v)
                    except T.EntradaInvalida:
                        ok = False
                    certos += ok
                    total += 1
                    c.setStyleSheet(OK if ok else ERRO)
        self.mostrou_certa = True
        self._desenhar()
        if certos == total:
            self.resultado.setText("✔ " + tr("Tudo certo!"))
            self.resultado.setStyleSheet("color:#6fdc8c;font-weight:bold")
        else:
            self.resultado.setText(tr("{} de {} campos certos").format(certos, total))
            self.resultado.setStyleSheet("color:#ffb347")
        return certos, total

    def mostrar_solucao(self):
        self.solucao.setHtml(self.q.solucao_html())
        self.mostrou_certa = True
        self._desenhar()

    def mostrar_formulas(self):
        QMessageBox.information(self, tr("Fórmulas"), T.formulas_html(self.q.modo))

    def ver_no_povray(self):
        pai = self.parent()
        if hasattr(pai, "abrir_exemplo"):
            pai.abrir_exemplo(tr("treino 3D nº {}").format(self.q.numero), self.q.pov_cena())
