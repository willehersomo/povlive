"""Janela do treino de transformações 2D: enunciado, campos para a matriz e os pontos, gráfico e solução."""
import random

from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QColor, QPainter, QPen, QPolygonF, QFont
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton,
                             QComboBox, QTextBrowser, QWidget, QSpinBox, QSplitter, QSizePolicy)

from . import treino2d as T
from .i18n import tr, N_

NIVEIS = [("facil", N_("Fácil (1–2 transformações)")), ("medio", N_("Médio (2–3)")),
          ("dificil", N_("Difícil (3–4, em torno de pontos)"))]
OK = "background:#1f4d2b;color:#e8ffe8"
ERRO = "background:#5a1f1f;color:#ffe8e8"


class Grafico(QWidget):
    """Plano cartesiano com a figura original, a resposta certa e a do aluno."""

    def __init__(self):
        super().__init__()
        self.figuras = []          # (pontos, cor, rótulos, tracejado)
        self.setMinimumSize(320, 320)

    def mostrar(self, figuras):
        self.figuras = figuras
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#1e1e1e"))
        pts = [pt for f in self.figuras for pt in f[0]] or [(0, 0)]
        alcance = max(4, max(max(abs(x), abs(y)) for x, y in pts) + 1)
        alcance = int(alcance + 0.999)
        lado = min(self.width(), self.height()) - 20
        esc = lado / (2 * alcance)
        cx, cy = self.width() / 2, self.height() / 2
        tela = lambda x, y: QPointF(cx + x * esc, cy - y * esc)
        p.setPen(QPen(QColor("#333"), 1))
        for k in range(-alcance, alcance + 1):
            p.drawLine(tela(k, -alcance), tela(k, alcance))
            p.drawLine(tela(-alcance, k), tela(alcance, k))
        p.setPen(QPen(QColor("#888"), 1.5))
        p.drawLine(tela(-alcance, 0), tela(alcance, 0))
        p.drawLine(tela(0, -alcance), tela(0, alcance))
        p.setFont(QFont(self.font().family(), 8))
        passo = 1 if alcance <= 6 else 2 if alcance <= 12 else 5
        for k in range(-alcance, alcance + 1, passo):
            if k:
                p.drawText(tela(k, 0) + QPointF(-4, 14), str(k))
                p.drawText(tela(0, k) + QPointF(4, 4), str(k))
        for pontos, cor, rotulos, tracejado in self.figuras:
            pen = QPen(QColor(cor), 2.2, Qt.DashLine if tracejado else Qt.SolidLine)
            p.setPen(pen)
            c = QColor(cor)
            c.setAlpha(40)
            p.setBrush(c)
            p.drawPolygon(QPolygonF([tela(x, y) for x, y in pontos]))
            p.setBrush(QColor(cor))
            for (x, y), r in zip(pontos, rotulos):
                q = tela(x, y)
                p.drawEllipse(q, 3, 3)
                p.drawText(q + QPointF(5, -5), r)
        p.end()


class Treino2D(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Treino de transformações 2D"))
        self.resize(1080, 780)
        lay = QVBoxLayout(self)
        topo = QHBoxLayout()
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
        lay.addLayout(topo)

        sp = QSplitter(Qt.Horizontal)
        esq = QWidget()
        le = QVBoxLayout(esq)
        le.setContentsMargins(0, 0, 0, 0)
        self.enunciado = QLabel(wordWrap=True, textFormat=Qt.RichText)
        self.enunciado.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        le.addWidget(self.enunciado)
        le.addWidget(QLabel("<b>M =</b>"))
        grade = QGridLayout()
        self.campos_m = [[QLineEdit(maximumWidth=90) for _ in range(3)] for _ in range(3)]
        for i in range(3):
            for j in range(3):
                grade.addWidget(self.campos_m[i][j], i, j)
        le.addLayout(grade)
        le.addWidget(QLabel(tr("Pontos transformados")))
        self.grade_pts = QGridLayout()
        le.addLayout(self.grade_pts)
        self.campos_p = []
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
        le.addWidget(self.solucao, 1)
        sp.addWidget(esq)
        self.grafico = Grafico()
        sp.addWidget(self.grafico)
        sp.setSizes([520, 480])
        lay.addWidget(sp, 1)
        legenda = QLabel("<span style='color:#5aa9ff'>■</span> " + tr("figura original") +
                         " &nbsp; <span style='color:#ffb347'>■</span> " + tr("sua resposta") +
                         " &nbsp; <span style='color:#6fdc8c'>■</span> " + tr("resposta certa (depois de conferir)"))
        lay.addWidget(legenda)

        self.cb_nivel.currentIndexChanged.connect(lambda _: self.nova())
        self.sp_num.valueChanged.connect(lambda _: self.nova())
        self.sp_num.setValue(random.randint(1, 99999))
        self.nova()

    def nova(self):
        self.q = T.Questao(self.sp_num.value(), self.cb_nivel.currentData())
        self.enunciado.setText(self.q.enunciado())
        for linha in self.campos_m:
            for c in linha:
                c.clear()
                c.setStyleSheet("")
        while self.grade_pts.count():
            w = self.grade_pts.takeAt(0).widget()
            if w:
                w.hide()               # some na hora (o deleteLater só age na volta ao laço de eventos)
                w.setParent(None)
                w.deleteLater()
        self.campos_p = []
        for k, (nome, _) in enumerate(self.q.figura):
            self.grade_pts.addWidget(QLabel(f"{nome}' ="), k, 0)
            cx, cy = QLineEdit(maximumWidth=90, placeholderText="x"), QLineEdit(maximumWidth=90, placeholderText="y")
            cx.textChanged.connect(lambda _: self._desenhar())
            cy.textChanged.connect(lambda _: self._desenhar())
            self.grade_pts.addWidget(cx, k, 1)
            self.grade_pts.addWidget(cy, k, 2)
            self.campos_p.append((cx, cy))
        self.resultado.clear()
        self.solucao.clear()
        self.mostrou_certa = False
        self._desenhar()

    def _pontos_do_aluno(self):
        pts = []
        for cx, cy in self.campos_p:
            try:
                pts.append((T.ler_numero(cx.text()), T.ler_numero(cy.text())))
            except T.EntradaInvalida:
                return None
        return pts

    def _desenhar(self):
        nomes = [n for n, _ in self.q.figura]
        figs = [([p for _, p in self.q.figura], "#5aa9ff", nomes, False)]
        aluno = self._pontos_do_aluno()
        if aluno:
            figs.append((aluno, "#ffb347", [n + "'" for n in nomes], False))
        if self.mostrou_certa:
            figs.append(([p for _, p in self.q.pontos()], "#6fdc8c", [n + "'" for n in nomes], True))
        self.grafico.mostrar(figs)

    def conferir(self):
        M = self.q.matriz()
        certos_m = 0
        for i in range(3):
            for j in range(3):
                c = self.campos_m[i][j]
                try:
                    ok = T.igual(T.ler_numero(c.text()), M[i, j])
                except T.EntradaInvalida:
                    ok = False
                certos_m += ok
                c.setStyleSheet(OK if ok else ERRO)
        certos_p = 0
        for (cx, cy), (_, (x, y)) in zip(self.campos_p, self.q.pontos()):
            for c, v in ((cx, x), (cy, y)):
                try:
                    ok = T.igual(T.ler_numero(c.text()), v)
                except T.EntradaInvalida:
                    ok = False
                certos_p += ok
                c.setStyleSheet(OK if ok else ERRO)
        total_p = 2 * len(self.campos_p)
        self.mostrou_certa = True
        self._desenhar()
        if certos_m == 9 and certos_p == total_p:
            self.resultado.setText("✔ " + tr("Tudo certo!"))
            self.resultado.setStyleSheet("color:#6fdc8c;font-weight:bold")
        else:
            self.resultado.setText(tr("Matriz: {}/9 certos · pontos: {}/{} certos").format(certos_m, certos_p, total_p))
            self.resultado.setStyleSheet("color:#ffb347")
        return certos_m, certos_p

    def mostrar_solucao(self):
        self.solucao.setHtml(self.q.solucao_html())
        self.mostrou_certa = True
        self._desenhar()
