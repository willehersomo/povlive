"""Janela principal do POV-Ray ao vivo."""
import glob, math, os, re, shutil, sys, tempfile, time

from PyQt5.QtCore import Qt, QTimer, QProcess, QFileSystemWatcher, QSettings, QSize
from PyQt5.QtGui import QColor, QFont, QPalette, QKeySequence, QTextCursor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPlainTextEdit, QWidget, QLabel, QSplitter,
                             QToolBar, QComboBox, QCheckBox, QFileDialog, QMessageBox, QAction,
                             QSlider, QDoubleSpinBox, QVBoxLayout, QInputDialog, QProgressDialog,
                             QToolButton, QTabWidget, QStackedWidget)

from . import pov
from .editor import Editor, BarraBusca
from .visor import Visor, QuatroVistas, Historico
from .cache_orbita import CacheOrbita, angulo_dif
from .recursos import RecursosMixin

MAX_LIVE = 4   # renders simultâneos enquanto arrasta a câmera livre

QUALIDADES = [("Rascunho (sem texturas)", 4, False), ("Normal", 9, False), ("Final + AA", 11, True)]
TAMANHOS = [(320, 240), (640, 480), (800, 600), (1024, 768)]
MAX_RECENTES = 10

ATALHOS = """<table cellspacing=4>
<tr><td colspan=2><b>Edição</b></td></tr>
<tr><td>Ctrl + arrastar num número</td><td>muda o valor (Shift junto = ajuste fino)</td></tr>
<tr><td>Ctrl + clique num #include</td><td>abre o arquivo numa aba</td></tr>
<tr><td>Ctrl+Espaço</td><td>autocompletar</td></tr>
<tr><td>Ctrl+F / Ctrl+H</td><td>buscar / substituir</td></tr>
<tr><td>Ctrl+L</td><td>ir para linha</td></tr>
<tr><td>Ctrl+/</td><td>comentar / descomentar linhas</td></tr>
<tr><td>Tab / Shift+Tab</td><td>indentar / desindentar seleção</td></tr>
<tr><td>Ctrl+Shift+D</td><td>duplicar linha</td></tr>
<tr><td>Ctrl+Shift+F</td><td>formatar (reindentar) o código</td></tr>
<tr><td>Ctrl+Shift+C ou botão direito</td><td>escolher cor do rgb sob o cursor</td></tr>
<tr><td>Mouse parado numa palavra</td><td>ajuda da sintaxe</td></tr>
<tr><td colspan=2><b>Render e visualização</b></td></tr>
<tr><td>Ctrl+Enter / Ctrl+R</td><td>renderizar agora</td></tr>
<tr><td>F5</td><td>render grande (1280×960 com antialiasing)</td></tr>
<tr><td>F6 / Shift+F6</td><td>câmera livre / copiar câmera para o código</td></tr>
<tr><td>F7</td><td>quatro vistas (perspectiva, frente, topo, lado)</td></tr>
<tr><td>F8</td><td>histórico de versões</td></tr>
<tr><td>Ctrl+E</td><td>eixos X/Y/Z</td></tr>
<tr><td>Ctrl+P</td><td>fixar imagem para comparar</td></tr>
<tr><td>F9</td><td>painel de matrizes do objeto sob o cursor</td></tr>
<tr><td>Clique na imagem</td><td>vai para a linha do objeto clicado</td></tr>
<tr><td>Ctrl + arrastar na imagem</td><td>move o objeto (Shift = passos de 0.1)</td></tr>
<tr><td>Roda / arrastar / duplo clique na imagem</td><td>zoom / mover / ajustar</td></tr>
<tr><td>Ctrl+0 / Ctrl+1</td><td>ajustar à janela / tamanho real</td></tr>
<tr><td colspan=2><b>Ajuda</b></td></tr>
<tr><td>F1 / Shift+F1</td><td>guia do POV-Ray com exemplos / esta lista de atalhos</td></tr>
<tr><td>Ctrl+Shift+V</td><td>verificar o exercício aberto</td></tr>
<tr><td colspan=2><b>Arquivo</b></td></tr>
<tr><td>Ctrl+N / Ctrl+O / Ctrl+S / Ctrl+Shift+S</td><td>novo / abrir / salvar / salvar como</td></tr>
<tr><td>Ctrl+W</td><td>fechar aba</td></tr>
<tr><td>Ctrl+Shift+E / Ctrl+G</td><td>salvar PNG / exportar GIF</td></tr>
<tr><td>Ctrl+Shift+X</td><td>exportar entrega (.zip)</td></tr>
</table>"""


class Janela(RecursosMixin, QMainWindow):
    def __init__(self, arquivos=()):
        super().__init__()
        self.cfg = QSettings("povlive", "povlive")
        self.cena = None          # editor da cena que está sendo renderizada (.pov)
        self.procs = []           # processos do render atual (1, ou 4 nas quatro vistas)
        self.job = None           # "previa", "final" ou "grande"
        self.trab = None          # pasta temporária do render atual
        self.pendente = False
        self.tocando = False
        self.orbita = None        # câmera livre
        self.interagindo = False  # arrastando a câmera livre
        self.gif = None
        self.incs = set()
        self.ultima_pix = None
        self.guia = None
        # câmera livre fluida: renders em paralelo + cache de órbita
        self.live = []
        self.live_seq = 0
        self.live_mostrado = 0
        self.live_ultimo = None       # (pix, estado da câmera)
        self.live_pendente = False
        self.live_t = 0.0
        self.live_timer = QTimer(self, singleShot=True, interval=40)
        self.live_timer.timeout.connect(self._live_lancar)
        self.fim_zoom = QTimer(self, singleShot=True, interval=350)
        self.fim_zoom.timeout.connect(self._camera_soltou)
        self.cache = CacheOrbita(self)
        self.cache.novo_quadro.connect(self._cache_novo)
        self.cache_timer = QTimer(self, singleShot=True, interval=800)
        self.cache_timer.timeout.connect(self._cache_atualizar)

        self._montar()
        self._montar_recursos()
        self._menus()
        self._barras()

        self.timer = QTimer(singleShot=True, interval=400)
        self.timer.timeout.connect(self.pedir_render)
        self.vigia = QFileSystemWatcher()
        self.vigia.fileChanged.connect(self._mudou_fora)

        self._restaurar()
        abriu = False
        for a in arquivos:
            abriu |= bool(self.abrir_arquivo(a))
        if not abriu:
            for c in self._lista_cfg("sessao"):
                if os.path.exists(c):
                    abriu |= bool(self.abrir_arquivo(c, renderizar=False))
            if abriu:
                i = int(self.cfg.value("aba_atual", 0))
                self.abas.setCurrentIndex(min(i, self.abas.count() - 1))
                self._aba_mudou()
        if not abriu:
            self.novo()

    # ================================================================ interface

    def _montar(self):
        self.abas = QTabWidget()
        self.abas.setTabsClosable(True)
        self.abas.setMovable(True)
        self.abas.setDocumentMode(True)
        self.abas.tabCloseRequested.connect(self.fechar_aba)
        self.abas.currentChanged.connect(self._aba_mudou)
        self.busca = BarraBusca(self.ed)
        self.busca.hide()
        caixa = QWidget()
        lay = QVBoxLayout(caixa)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.abas)
        lay.addWidget(self.busca)

        self.log = QPlainTextEdit(readOnly=True)
        self.log.setMaximumHeight(170)
        self.log.setStyleSheet("background:#2b0f0f;color:#ff9b9b;font-family:monospace;border:none")
        self.log.hide()
        self.log.mouseDoubleClickEvent = lambda ev: self._ir_para_erro()

        self.visor = Visor()
        self.quatro = QuatroVistas()
        self.pilha = QStackedWidget()
        self.pilha.addWidget(self.visor)
        self.pilha.addWidget(self.quatro)
        for v in [self.visor, self.quatro.persp]:
            v.camera.connect(self._camera_mouse)
            v.soltou.connect(self._camera_soltou)
        for v in self.quatro.orto:
            v.camera.connect(self._camera_mouse)
        for v in [self.visor] + self.quatro.visores():
            v.pixel.connect(lambda t: self.lb_pixel.setText(t))

        self.fixa = Visor("Fixada (antes)")
        self.fixa.hide()
        self.historico = Historico()
        self.historico.ver.connect(self._ver_historico)
        self.historico.restaurar.connect(self._restaurar_historico)
        self.historico.hide()

        self.sp_esq = QSplitter(Qt.Vertical)
        self.sp_esq.addWidget(caixa)
        self.sp_esq.addWidget(self.log)
        self.sp_dir = QSplitter(Qt.Vertical)
        self.sp_dir.addWidget(self.fixa)
        self.sp_dir.addWidget(self.pilha)
        self.sp_dir.addWidget(self.historico)
        self.sp_dir.setCollapsible(1, False)
        self.sp_meio = QSplitter(Qt.Horizontal)
        self.sp_meio.addWidget(self.sp_esq)
        self.sp_meio.addWidget(self.sp_dir)
        self.sp_meio.setSizes([650, 650])
        self.setCentralWidget(self.sp_meio)

        self.status = self.statusBar()
        self.lb_pixel = QLabel()
        self.lb_pixel.setStyleSheet("color:#999;font-family:monospace")
        self.status.addPermanentWidget(self.lb_pixel)

    def _acao(self, nome, func, atalho=None, checavel=False, dica=None):
        a = QAction(nome, self)
        if atalho:
            a.setShortcuts(atalho if isinstance(atalho, list) else [atalho])
        a.setCheckable(checavel)
        if dica:
            a.setToolTip(dica)
        # o Qt passa "checked" para o slot; só repassa quando a ação é de liga/desliga
        a.triggered.connect((lambda ligado: func(ligado)) if checavel else (lambda _=False: func()))
        return a

    def _menus(self):
        mb = self.menuBar()
        m = mb.addMenu("&Arquivo")
        m.addAction(self._acao("Nova cena", self.novo, QKeySequence.New))
        m.addAction(self._acao("Abrir…", self.abrir, QKeySequence.Open))
        self.menu_recentes = m.addMenu("Recentes")
        m.addSeparator()
        m.addAction(self._acao("Salvar", self.salvar, QKeySequence.Save))
        m.addAction(self._acao("Salvar como…", self.salvar_como, "Ctrl+Shift+S"))
        m.addAction(self._acao("Salvar todas", self.salvar_todas))
        m.addAction(self._acao("Fechar aba", lambda: self.fechar_aba(self.abas.currentIndex()), "Ctrl+W"))
        m.addSeparator()
        m.addAction(self._acao("Salvar imagem PNG…", self.exportar_png, "Ctrl+Shift+E"))
        m.addAction(self._acao("Exportar animação GIF…", self.exportar_gif, "Ctrl+G"))
        m.addAction(self._acao("Exportar entrega (.zip)…", self.exportar_entrega, "Ctrl+Shift+X",
                               dica="Cena, .inc, imagem em alta, GIF (se animada) e LEIAME num .zip"))
        m.addSeparator()
        m.addAction(self._acao("Sair", self.close, QKeySequence.Quit))

        m = mb.addMenu("&Editar")
        m.addAction(self._acao("Desfazer", lambda: self.ed().undo(), QKeySequence.Undo))
        m.addAction(self._acao("Refazer", lambda: self.ed().redo(), QKeySequence.Redo))
        m.addSeparator()
        m.addAction(self._acao("Buscar…", lambda: self.busca.abrir(), QKeySequence.Find))
        m.addAction(self._acao("Substituir…", lambda: self.busca.abrir(True), "Ctrl+H"))
        m.addAction(self._acao("Ir para linha…", self.ir_para_linha, "Ctrl+L"))
        m.addSeparator()
        m.addAction(self._acao("Comentar/descomentar", lambda: self.ed().comentar(), "Ctrl+/"))
        m.addAction(self._acao("Duplicar linha", lambda: self.ed().duplicar_linha(), "Ctrl+Shift+D"))
        m.addAction(self._acao("Escolher cor do rgb sob o cursor…", self.escolher_cor, "Ctrl+Shift+C"))
        m.addAction(self._acao("Formatar código", self.formatar_codigo, "Ctrl+Shift+F"))

        m = mb.addMenu("&Inserir")
        for item in pov.MODELOS:
            if item is None:
                m.addSeparator()
            else:
                nome, trecho = item
                m.addAction(self._acao(nome, lambda t=trecho: self.ed().inserir_modelo(t)))

        m = mb.addMenu("E&xibir")
        self.a_eixos = self._acao("Eixos X/Y/Z", lambda _: self.pedir_render(), "Ctrl+E", True,
                                  "Mostrar eixos X (vermelho), Y (verde) e Z (azul)")
        self.a_previa = self._acao("Prévia rápida antes do render completo", lambda _: self.pedir_render(), None, True)
        self.a_quatro = self._acao("Quatro vistas", self.quatro_vistas, "F7", True,
                                   "Perspectiva, frente, topo e lado (F7)")
        self.a_livre = self._acao("Câmera livre", self.camera_livre, "F6", True,
                                  "Girar a câmera arrastando na imagem (F6)")
        self.a_copiar = self._acao("Copiar câmera para o código", self.copiar_camera, "Shift+F6",
                                   dica="Grava a posição da câmera livre na câmera da cena (Shift+F6)")
        self.a_fixar = self._acao("Fixar imagem para comparar", self.fixar, "Ctrl+P", True,
                                  "Mostra a imagem atual em cima para comparar com as próximas (Ctrl+P)")
        self.a_hist = self._acao("Histórico de versões", self._mostrar_historico, "F8", True,
                                 "Miniaturas de cada render (F8)")
        self.a_mat = self._acao("Painel de matrizes", self.mostrar_matrizes, "F9", True,
                                "Matrizes das transformações do objeto sob o cursor (F9)")
        for acao, curto in ((self.a_eixos, "Eixos"), (self.a_quatro, "4 vistas"), (self.a_copiar, "Copiar câmera"),
                            (self.a_fixar, "Comparar"), (self.a_hist, "Histórico"), (self.a_mat, "Matrizes")):
            acao.setIconText(curto)  # texto mais curto na barra de ferramentas
        for a in (self.a_eixos, self.a_previa, None, self.a_quatro, self.a_livre, self.a_copiar, None,
                  self.a_fixar, self.a_hist, self.a_mat, None):
            m.addSeparator() if a is None else m.addAction(a)
        m.addAction(self._acao("Ajustar imagem à janela", lambda: [v.ajustar() for v in self._visores()], "Ctrl+0"))
        m.addAction(self._acao("Imagem em tamanho real", lambda: self.visor.tamanho_real(), "Ctrl+1"))

        m = mb.addMenu("Aj&uda")
        m.addAction(self._acao("Guia do POV-Ray…", self.abrir_guia, "F1"))
        m.addAction(self._acao("Exercícios…", lambda: self.abrir_guia(exercicios=True)))
        m.addAction(self._acao("Verificar exercício", self.verificar_exercicio, "Ctrl+Shift+V"))
        m.addAction(self._acao("Atalhos do app", lambda: QMessageBox.information(self, "Atalhos", ATALHOS), "Shift+F1"))

    def _barras(self):
        tb = QToolBar("Render")
        tb.setMovable(False)
        self.addToolBar(tb)
        tb.addWidget(QLabel(" Qualidade "))
        self.cb_q = QComboBox()
        self.cb_q.addItems([q[0] for q in QUALIDADES])
        self.cb_q.setCurrentIndex(1)
        self.cb_q.currentIndexChanged.connect(lambda _: self.pedir_render())
        tb.addWidget(self.cb_q)
        tb.addWidget(QLabel(" Tamanho "))
        self.cb_t = QComboBox()
        self.cb_t.addItems([f"{w}×{h}" for w, h in TAMANHOS])
        self.cb_t.setCurrentIndex(1)
        self.cb_t.currentIndexChanged.connect(lambda _: self.pedir_render())
        tb.addWidget(self.cb_t)
        self.ck_auto = QCheckBox("Ao vivo")
        self.ck_auto.setChecked(True)
        tb.addWidget(self.ck_auto)
        tb.addAction(self._acao("Renderizar", self.pedir_render, ["Ctrl+Return", "Ctrl+R"]))
        tb.addAction(self._acao("Render grande", lambda: self.pedir_render(grande=True), "F5"))
        tb.addSeparator()
        tb.addAction(self.a_eixos)
        self.sp_eixos = QDoubleSpinBox()
        self.sp_eixos.setRange(0.1, 1000)
        self.sp_eixos.setValue(3)
        self.sp_eixos.setToolTip("Comprimento dos eixos")
        self.sp_eixos.valueChanged.connect(lambda _: self.a_eixos.isChecked() and self.pedir_render())
        tb.addWidget(self.sp_eixos)
        tb.addSeparator()
        tb.addAction(self.a_quatro)
        self.a_lb_escala = tb.addWidget(QLabel(" escala "))
        self.sp_escala = QDoubleSpinBox()
        self.sp_escala.setRange(0.05, 10000)
        self.sp_escala.setSingleStep(0.25)
        self.sp_escala.setValue(3)
        self.sp_escala.setToolTip("Metade da altura visível nas vistas ortográficas (roda do mouse nelas também muda)")
        self.sp_escala.valueChanged.connect(lambda _: self.a_quatro.isChecked() and self.pedir_render())
        self.a_sp_escala = tb.addWidget(self.sp_escala)

        self.addToolBarBreak()
        tb = QToolBar("Câmera e animação")
        tb.setMovable(False)
        self.addToolBar(tb)
        tb.addAction(self.a_livre)
        tb.addAction(self.a_copiar)
        tb.addSeparator()
        tb.addAction(self.a_fixar)
        tb.addAction(self.a_hist)
        tb.addAction(self.a_mat)
        tb.addSeparator()
        self.bt_play = QToolButton(text="▶", toolTip="Tocar animação (varia o clock de 0 a 1)")
        self.bt_play.clicked.connect(self.tocar)
        tb.addWidget(self.bt_play)
        tb.addWidget(QLabel(" clock "))
        self.sl_clock = QSlider(Qt.Horizontal)
        self.sl_clock.setRange(0, 1000)
        self.sl_clock.setMinimumWidth(250)
        self.sl_clock.valueChanged.connect(self._clock_mudou)
        self.sl_clock.keyPressEvent = self._tecla_clock
        tb.addWidget(self.sl_clock)
        self.lb_clock = QLabel(" 0.000 ")
        self.lb_clock.setFont(QFont("Monospace"))
        tb.addWidget(self.lb_clock)
        tb.addAction(self._acao("Exportar GIF", self.exportar_gif))
        self._atualizar_barra_vistas()

    def _tecla_clock(self, ev):
        if ev.key() == Qt.Key_Space:
            self.tocar()
        else:
            QSlider.keyPressEvent(self.sl_clock, ev)

    def _visores(self):
        return [self.visor] + self.quatro.visores()

    # ================================================================ preferências e sessão

    def _lista_cfg(self, chave):
        v = self.cfg.value(chave, [])
        return [v] if isinstance(v, str) else list(v or [])

    def _restaurar(self):
        c = self.cfg
        if c.value("geometria"):
            self.restoreGeometry(c.value("geometria"))
        else:
            self.resize(1450, 880)
        for sp, k in ((self.sp_meio, "sp_meio"), (self.sp_esq, "sp_esq"), (self.sp_dir, "sp_dir")):
            if c.value(k):
                sp.restoreState(c.value(k))
        ws = (self.cb_q, self.cb_t, self.ck_auto, self.sp_eixos, self.a_eixos, self.a_previa, self.a_hist)
        for w in ws:
            w.blockSignals(True)
        self.cb_q.setCurrentIndex(int(c.value("qualidade", 1)))
        self.cb_t.setCurrentIndex(int(c.value("tamanho", 1)))
        self.ck_auto.setChecked(c.value("auto", "true") == "true")
        self.sp_eixos.setValue(float(c.value("eixos_tam", 3)))
        self.a_eixos.setChecked(c.value("eixos", "false") == "true")
        self.a_previa.setChecked(c.value("previa", "true") == "true")
        self.a_hist.setChecked(c.value("historico", "false") == "true")
        for w in ws:
            w.blockSignals(False)
        self._mostrar_historico(self.a_hist.isChecked())
        if c.value("conv_matrizes", "aula") == "pov":
            self.rb_pov.setChecked(True)
        if c.value("matrizes", "false") == "true":
            self.a_mat.setChecked(True)
            self.mostrar_matrizes(True)
        self._montar_recentes()

    def _guardar(self):
        c = self.cfg
        c.setValue("geometria", self.saveGeometry())
        for sp, k in ((self.sp_meio, "sp_meio"), (self.sp_esq, "sp_esq"), (self.sp_dir, "sp_dir")):
            c.setValue(k, sp.saveState())
        c.setValue("qualidade", self.cb_q.currentIndex())
        c.setValue("tamanho", self.cb_t.currentIndex())
        c.setValue("auto", "true" if self.ck_auto.isChecked() else "false")
        c.setValue("eixos_tam", self.sp_eixos.value())
        c.setValue("eixos", "true" if self.a_eixos.isChecked() else "false")
        c.setValue("previa", "true" if self.a_previa.isChecked() else "false")
        c.setValue("historico", "true" if self.a_hist.isChecked() else "false")
        c.setValue("matrizes", "true" if self.a_mat.isChecked() else "false")
        c.setValue("conv_matrizes", "aula" if self.rb_aula.isChecked() else "pov")
        c.setValue("sessao", [e.caminho for e in self._editores() if e.caminho])
        c.setValue("aba_atual", self.abas.currentIndex())

    def _add_recente(self, caminho):
        r = [caminho] + [x for x in self._lista_cfg("recentes") if x != caminho]
        self.cfg.setValue("recentes", r[:MAX_RECENTES])
        self._montar_recentes()

    def _montar_recentes(self):
        self.menu_recentes.clear()
        r = [x for x in self._lista_cfg("recentes") if os.path.exists(x)]
        for i, c in enumerate(r):
            a = self.menu_recentes.addAction(f"&{i + 1}  {os.path.basename(c)}   —  {os.path.dirname(c)}")
            a.triggered.connect(lambda _, c=c: self.abrir_arquivo(c))
        self.menu_recentes.setEnabled(bool(r))

    # ================================================================ abas e arquivos

    def ed(self):
        """Editor da aba atual."""
        return self.abas.currentWidget()

    def _editores(self):
        return [self.abas.widget(i) for i in range(self.abas.count())]

    def _editor_de(self, caminho):
        for e in self._editores():
            if e.caminho == caminho:
                return e
        return None

    def _novo_editor(self, caminho, texto, titulo=None):
        e = Editor()
        e.caminho = caminho
        e.titulo = titulo
        e.pasta = os.path.dirname(caminho) if caminho else os.path.expanduser("~")
        e.setPlainText(texto)
        e.document().setModified(False)
        e.textChanged.connect(lambda e=e: self._mudou(e))
        e.modificationChanged.connect(lambda _, e=e: self._rotulo(e))
        e.arrasteValor.connect(lambda v: self.status.showMessage(f"valor: {v}"))
        e.arrasteFim.connect(self.pedir_render)
        e.abrirInclude.connect(lambda nome, e=e: self._abrir_include(e, nome))
        e.cursorPositionChanged.connect(self._mat_agendar)
        i = self.abas.addTab(e, "")
        self._rotulo(e)
        e.atualizar_palavras(pov.declaracoes(texto, e.pasta))
        self.abas.setCurrentIndex(i)
        return e

    def _rotulo(self, e):
        i = self.abas.indexOf(e)
        if i < 0:
            return
        nome = os.path.basename(e.caminho) if e.caminho else (e.titulo or "sem título")
        self.abas.setTabText(i, ("● " if e.document().isModified() else "") + nome)
        self.abas.setTabToolTip(i, e.caminho or "")
        self._titulo()

    def _titulo(self):
        e = self.ed()
        if not e:
            return
        nome = os.path.basename(e.caminho) if e.caminho else "sem título"
        cena = ""
        if self.cena is not None and self.cena is not e:
            cena = f"  (renderizando {os.path.basename(self.cena.caminho or 'sem título')})"
        sujo = "*" if e.document().isModified() else ""
        self.setWindowTitle(f"{sujo}{nome}{cena} — POV-Ray ao vivo")

    def _e_cena(self, e):
        return not e.caminho or not e.caminho.lower().endswith(".inc")

    def _aba_mudou(self, *_):
        e = self.ed()
        if not e:
            return
        if self._e_cena(e) or self.cena is None or self.abas.indexOf(self.cena) < 0:
            if e is not self.cena:
                self.cena = e
                self.historico.carregar(e.caminho)
                self.sel = None
                if self.orbita:
                    self.orbita = pov.Orbita(pov.ler_camera(e.toPlainText()))
                self._atualizar_includes()
                self.pedir_render()
        self.busca._mudou() if self.busca.isVisible() else None
        self._mat_agendar()
        self._titulo()

    def abrir_arquivo(self, caminho, renderizar=True):
        caminho = os.path.abspath(caminho)
        e = self._editor_de(caminho)
        if e:
            self.abas.setCurrentWidget(e)
            return e
        if not os.path.exists(caminho):
            QMessageBox.warning(self, "Arquivo não encontrado", caminho)
            return None
        texto = open(caminho, encoding="utf-8", errors="replace").read()
        # aba "sem título" vazia e intocada é substituída
        atual = self.ed()
        if atual and not atual.caminho and not atual.document().isModified() and self.abas.count() == 1:
            self.abas.removeTab(0)
            if self.cena is atual:
                self.cena = None
        e = self._novo_editor(caminho, texto)
        self.vigia.addPath(caminho)
        self._add_recente(caminho)
        if renderizar:
            self._aba_mudou()
        return e

    def _abrir_include(self, e, nome):
        c = pov.achar_include(nome, e.pasta)
        if c:
            self.abrir_arquivo(c)
        else:
            self.status.showMessage(f"Não achei {nome}", 3000)

    def novo(self):
        modelo = pov.MODELOS[0][1]
        e = self._novo_editor(None, modelo.replace("|", ""))
        c = e.textCursor()
        c.setPosition(modelo.index("|"))
        e.setTextCursor(c)
        self._aba_mudou()

    def abrir_guia(self, exercicios=False):
        if not self.guia:
            from .guia import Guia
            self.guia = Guia(self)
        if exercicios:
            self.guia.ir_para_exercicios()
        self.guia.show()
        self.guia.raise_()
        self.guia.activateWindow()

    def abrir_exemplo(self, nome, texto):
        self._novo_editor(None, texto, f"exemplo: {nome}")
        self._aba_mudou()
        self.raise_()
        self.activateWindow()

    def abrir(self):
        pasta = self.ed().pasta if self.ed() else os.path.expanduser("~")
        cs, _ = QFileDialog.getOpenFileNames(self, "Abrir", pasta, "POV-Ray (*.pov *.inc);;Todos (*)")
        for c in cs:
            self.abrir_arquivo(c)

    def salvar(self, e=None):
        e = e or self.ed()
        if not e.caminho:
            return self.salvar_como(e)
        if e.caminho in self.vigia.files():
            self.vigia.removePath(e.caminho)
        with open(e.caminho, "w", encoding="utf-8") as f:
            f.write(e.toPlainText())
        self.vigia.addPath(e.caminho)
        e.document().setModified(False)
        self.status.showMessage(f"Salvo: {os.path.basename(e.caminho)}", 2000)
        return True

    def salvar_como(self, e=None):
        e = e or self.ed()
        c, _ = QFileDialog.getSaveFileName(self, "Salvar", e.caminho or os.path.join(e.pasta, "cena.pov"),
                                           "POV-Ray (*.pov *.inc)")
        if not c:
            return False
        if not c.lower().endswith((".pov", ".inc")):
            c += ".pov"
        if e.caminho and e.caminho in self.vigia.files():
            self.vigia.removePath(e.caminho)
        e.caminho = os.path.abspath(c)
        e.pasta = os.path.dirname(e.caminho)
        if e is self.cena:
            self.historico.pasta = self.historico.pasta_para(e.caminho)
        self.salvar(e)
        self._rotulo(e)
        self._add_recente(e.caminho)
        return True

    def salvar_todas(self):
        for e in self._editores():
            if e.document().isModified():
                self.salvar(e)

    def _pode_fechar(self, e):
        if not e.document().isModified():
            return True
        self.abas.setCurrentWidget(e)
        nome = os.path.basename(e.caminho) if e.caminho else "sem título"
        r = QMessageBox.question(self, "Alterações não salvas", f"Salvar {nome} antes de fechar?",
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if r == QMessageBox.Save:
            return bool(self.salvar(e))
        return r == QMessageBox.Discard

    def fechar_aba(self, i):
        e = self.abas.widget(i)
        if e is None or not self._pode_fechar(e):
            return
        if e.caminho and e.caminho in self.vigia.files():
            self.vigia.removePath(e.caminho)
        self.abas.removeTab(i)
        if self.cena is e:
            self.cena = None
            # outra aba de cena assume
            for o in self._editores():
                if self._e_cena(o):
                    self.cena = o
                    break
        e.deleteLater()
        if self.abas.count() == 0:
            self.novo()
        else:
            self._aba_mudou()

    def closeEvent(self, ev):
        for e in self._editores():
            if not self._pode_fechar(e):
                ev.ignore()
                return
        self.tocando = False
        self._parar()
        self._live_parar()
        self.cache.parar()
        self.fila.cancelar()
        if self._sel_tmp is not None:
            self._sel_tmp.cleanup()
            self._sel_tmp = None
        self._gif_cancelar()
        self._guardar()
        ev.accept()

    def ir_para_linha(self):
        e = self.ed()
        n, ok = QInputDialog.getInt(self, "Ir para linha", f"Linha (1–{e.blockCount()}):",
                                    e.textCursor().blockNumber() + 1, 1, e.blockCount())
        if ok:
            e.ir_para(n)

    def escolher_cor(self):
        if not self.ed().escolher_cor():
            self.status.showMessage("Coloque o cursor sobre um rgb <r, g, b> para escolher a cor", 3000)

    def exportar_png(self):
        if not self.ultima_pix:
            return
        base = os.path.splitext(self.cena.caminho)[0] + ".png" if self.cena and self.cena.caminho \
            else os.path.expanduser("~/cena.png")
        c, _ = QFileDialog.getSaveFileName(self, "Salvar imagem", base, "PNG (*.png)")
        if c:
            self.ultima_pix.save(c, "PNG")
            self.status.showMessage(f"Imagem salva em {c}", 3000)

    # ================================================================ mudanças no código e no disco

    def _mudou(self, e):
        self._titulo()
        self._mat_agendar()
        for v in (self.visor, self.quatro.persp):
            if v.destaque is not None:
                v.set_destaque(None)
        if e.arraste:
            self.pedir_render()      # arrastando número/cor: renderiza na hora
        elif self.ck_auto.isChecked():
            self.timer.start()

    def _pasta(self):
        return self.cena.pasta if self.cena else os.path.expanduser("~")

    def _atualizar_includes(self):
        """Vigia os .inc usados pela cena e alimenta o autocompletar/ajuda com os nomes declarados."""
        if not self.cena:
            return
        texto = self.cena.toPlainText()
        novos = set()
        for inc in pov.RX_INCLUDE.findall(texto):
            c = pov.achar_include(inc, self._pasta())
            if c and not c.startswith(tuple(pov.BIBLIOTECA)):
                novos.add(c)
        abertos = {e.caminho for e in self._editores()}
        for c in self.incs - novos:
            if c not in abertos:
                self.vigia.removePath(c)
        for c in novos - self.incs:
            self.vigia.addPath(c)
        self.incs = novos
        for e in self._editores():
            e.atualizar_palavras(pov.declaracoes(e.toPlainText(), e.pasta))

    def _mudou_fora(self, caminho):
        # editores costumam salvar trocando o arquivo, então o vigia precisa ser recolocado
        QTimer.singleShot(150, lambda: self._recarregar_de_fora(caminho))

    def _recarregar_de_fora(self, caminho):
        if not os.path.exists(caminho):
            return
        if caminho not in self.vigia.files():
            self.vigia.addPath(caminho)
        e = self._editor_de(caminho)
        if e:
            texto = open(caminho, encoding="utf-8", errors="replace").read()
            if texto != e.toPlainText():
                if e.document().isModified():
                    self.status.showMessage(f"{os.path.basename(caminho)} mudou fora daqui, "
                                            "mas você tem alterações não salvas", 5000)
                    return
                cur = e.textCursor().position()
                barra = e.verticalScrollBar().value()
                c = QTextCursor(e.document())
                c.select(QTextCursor.Document)
                c.insertText(texto)          # assim dá para desfazer com Ctrl+Z
                e.document().setModified(False)
                c = e.textCursor()
                c.setPosition(min(cur, len(texto)))
                e.setTextCursor(c)
                e.verticalScrollBar().setValue(barra)
                self.status.showMessage(f"{os.path.basename(caminho)} recarregado (alterado em outro editor)", 2500)
        elif caminho in self.incs:
            self.status.showMessage(f"{os.path.basename(caminho)} mudou — renderizando", 2000)
        else:
            return
        self._atualizar_includes()
        self.pedir_render()

    # ================================================================ câmera livre, vistas, comparação, histórico

    def camera_livre(self, ligado):
        if ligado and self.cena:
            cam = pov.ler_camera(self.cena.toPlainText())
            self.orbita = pov.Orbita(cam)
            if not cam["achou"]:
                self.status.showMessage("Não achei location/look_at com números na câmera; começando de um ponto padrão", 5000)
        else:
            self.orbita = None
            self.a_livre.setChecked(False)
            self._live_parar()
            self.cache.parar()
            self.cache_timer.stop()
        self.live_ultimo = None
        for v in (self.visor, self.quatro.persp):
            v.modo_camera = self.orbita is not None
            v.update()
        self.pedir_render()

    def copiar_camera(self):
        if not self.orbita or not self.cena:
            self.status.showMessage("Ligue a câmera livre (F6), ajuste a vista e então copie", 3000)
            return
        novo = pov.gravar_camera(self.cena.toPlainText(), self.orbita.posicao(), self.orbita.alvo)
        c = QTextCursor(self.cena.document())
        c.select(QTextCursor.Document)
        c.insertText(novo)
        self.a_livre.setChecked(False)
        self.camera_livre(False)
        self.status.showMessage("Câmera copiada para o código (Ctrl+Z desfaz)", 4000)

    def _camera_mouse(self, tipo, dx, dy):
        if tipo == "escala":
            self.sp_escala.setValue(self.sp_escala.value() * (0.9 ** dx))
            return
        if not self.orbita:
            return
        if not self.interagindo:
            self.interagindo = True
            self._parar()            # o render normal espera; durante o arraste usamos o modo rápido
            self.timer.stop()
        if tipo == "girar":
            self.orbita.girar(dx, dy)
        elif tipo == "mover":
            self.orbita.mover(dx, dy)
        elif tipo == "zoom":
            self.orbita.zoom(dx)
            self.fim_zoom.start()    # a roda não tem "soltar": considera solto após uma pausa
        p = self.orbita.posicao()
        self.status.showMessage(f"câmera: location {pov.fmt_vetor(p)}  look_at {pov.fmt_vetor(self.orbita.alvo)}")
        self._mostrar_melhor()
        self.live_pendente = True
        self._live_lancar()

    def _camera_soltou(self):
        if not self.interagindo:
            return
        self.interagindo = False
        self.fim_zoom.stop()
        self._live_parar()
        self.pedir_render()

    # ----- câmera livre fluida

    def _visor_persp(self):
        return self.quatro.persp if self.a_quatro.isChecked() else self.visor

    def _tamanho_nominal(self):
        w, h = TAMANHOS[self.cb_t.currentIndex()]
        if self.a_quatro.isChecked():
            w, h = w // 2, h // 2
        return w, h

    def _live_lancar(self):
        """Durante o arraste: dispara renders da posição atual, vários ao mesmo tempo."""
        if not self.live_pendente or not self.orbita or not self.cena:
            return
        ativos = [l for l in self.live if l["proc"].state() != QProcess.NotRunning]
        if len(ativos) >= MAX_LIVE or time.time() - self.live_t < 0.05:
            if not self.live_timer.isActive():
                self.live_timer.start()
            return
        self.live_pendente = False
        self.live_t = time.time()
        nome, q, _aa = QUALIDADES[self.cb_q.currentIndex()]
        w, h = self._tamanho_nominal()
        trab = self._preparar_trabalho()
        fonte = self._nome_cena()
        with open(os.path.join(trab, fonte), "w", encoding="utf-8") as f:
            f.write(self._texto_cena())
        png = os.path.join(trab, "live.png")
        self.live_seq += 1
        l = {"proc": QProcess(self), "png": png, "trab": trab, "seq": self.live_seq,
             "estado": self.orbita.estado()}
        p = l["proc"]
        p.setWorkingDirectory(trab)
        p.setProcessChannelMode(QProcess.MergedChannels)
        p.setStandardOutputFile(QProcess.nullDevice())
        p.finished.connect(lambda rc, _s, l=l: self._live_terminou(l, rc))
        self.live.append(l)
        p.start("povray", self._args(fonte, png, max(80, w // 2), max(60, h // 2), q, False, self._clock()))

    def _live_terminou(self, l, rc):
        from PyQt5.QtGui import QPixmap
        pix = QPixmap(l["png"]) if rc == 0 else None
        shutil.rmtree(l["trab"], ignore_errors=True)
        if l in self.live:
            self.live.remove(l)
        if pix and not pix.isNull() and l["seq"] > self.live_mostrado and self.orbita:
            self.live_mostrado = l["seq"]
            self.live_ultimo = (pix, l["estado"])
            self._mostrar_melhor()
        self._live_lancar()

    def _live_parar(self):
        self.live_timer.stop()
        self.live_pendente = False
        for l in self.live:
            if l["proc"].state() != QProcess.NotRunning:
                l["proc"].finished.disconnect()
                l["proc"].kill()
                l["proc"].waitForFinished(1000)
            shutil.rmtree(l["trab"], ignore_errors=True)
        self.live = []

    def _mostrar_melhor(self):
        """Mostra a imagem mais próxima da câmera atual: um quadro do cache ou o último render rápido.
        Se ela foi feita com outro zoom/alvo, é ampliada/deslocada para acompanhar o mouse."""
        if not self.orbita:
            return
        yaw, pitch, dist, alvo = self.orbita.estado()
        candidatos = []
        if self.live_ultimo:
            pix, (y, p, d, a) = self.live_ultimo
            erro = angulo_dif(y, yaw) + abs(p - pitch) + 0.02  # leve preferência ao cache, que é mais nítido
            candidatos.append((erro, pix, (y, p, d, a)))
        if self.cache.quadros and self.cache.chave == self._cache_chave():
            m = self.cache.melhor(yaw, pitch)
            if m:
                candidatos.append((m[0], m[1], (m[2], m[3], self.cache.dist, tuple(self.cache.alvo))))
        if not candidatos:
            return
        _, pix, (y, p, d, a) = min(candidatos, key=lambda c: c[0])
        v = self._visor_persp()
        w, h = self._tamanho_nominal()
        v.mostrar(pix, QSize(w, h))
        # deformação para zoom/mover: compara a câmera da imagem com a atual
        escala = d / dist
        cp = math.cos(p)
        pos = pov.soma(list(a), [d * cp * math.sin(y), d * math.sin(p), -d * cp * math.cos(y)])
        f = pov.unit(pov.sub(list(a), pos))
        r = pov.unit(pov.cross([0, 1, 0], f))
        u = pov.cross(f, r)
        delta = pov.sub(list(alvo), list(a))
        larg = 2 * d * math.tan(self.orbita.fov(w / h) / 2)
        alt = larg * h / w
        dx = -sum(delta[i] * r[i] for i in range(3)) / larg * escala
        dy = sum(delta[i] * u[i] for i in range(3)) / alt * escala
        if abs(escala - 1) > 1e-6 or abs(dx) > 1e-6 or abs(dy) > 1e-6:
            v.set_warp(escala, dx, dy)

    def _cache_chave(self):
        """Tudo que, se mudar, invalida o cache (exceto o ângulo, que é o que o cache cobre)."""
        if not self.orbita or not self.cena:
            return None
        incs = tuple((e.caminho, e.toPlainText()) for e in self._editores()
                     if e is not self.cena and e.document().isModified())
        _, pitch, dist, alvo = self.orbita.estado()
        return hash((self._texto_cena(com_camera=False), incs, self._clock(), self.cb_q.currentIndex(),
                     self._tamanho_nominal(), round(dist, 6), tuple(round(x, 6) for x in alvo),
                     round(pitch / math.radians(30))))

    def _cache_atualizar(self):
        if not self.orbita or self.interagindo or self.tocando:
            return
        chave = self._cache_chave()
        if chave == self.cache.chave:
            return
        nome, q, _aa = QUALIDADES[self.cb_q.currentIndex()]
        w, h = self._tamanho_nominal()
        self.cache.iniciar(chave, self._texto_cena(com_camera=False), self.orbita, self._preparar_trabalho(),
                           lambda fonte, saida: self._args(fonte, saida, max(80, w // 2), max(60, h // 2), q, False)
                           + [f"+KI{self._clock():.4f}", f"+KF{self._clock():.4f}"])

    def _cache_novo(self):
        if self.interagindo:
            self._mostrar_melhor()

    def quatro_vistas(self, ligado):
        if ligado and self.cena:
            # escala inicial: parecida com o que a câmera da cena enxerga
            cam = pov.ler_camera(self.cena.toPlainText())
            d = pov.norma(pov.sub(cam["location"], cam["look_at"]))
            self.sp_escala.blockSignals(True)
            self.sp_escala.setValue(max(0.5, round(d * 0.6, 2)))
            self.sp_escala.blockSignals(False)
        self.pilha.setCurrentWidget(self.quatro if ligado else self.visor)
        self._atualizar_barra_vistas()
        self.pedir_render()

    def _atualizar_barra_vistas(self):
        on = self.a_quatro.isChecked()
        self.a_lb_escala.setVisible(on)
        self.a_sp_escala.setVisible(on)

    def fixar(self, ligado):
        if ligado and self.ultima_pix:
            self._mostrar_fixa(self.ultima_pix, "Fixada (antes)")
        else:
            self.a_fixar.setChecked(False)
            self.fixa.hide()
            self.visor.titulo = ""
            self.visor.update()

    def _mostrar_fixa(self, pix, titulo):
        self.fixa.titulo = titulo
        self.fixa.mostrar(pix, self.visor.nominal)
        self.fixa.show()
        self.a_fixar.setChecked(True)
        self.visor.titulo = "Atual"
        self.visor.update()
        tam = self.sp_dir.sizes()
        if tam[0] < 50:
            resto = sum(tam) - tam[2]
            self.sp_dir.setSizes([resto // 2, resto - resto // 2, tam[2]])

    def _mostrar_historico(self, ligado):
        self.historico.setVisible(ligado)
        tam = self.sp_dir.sizes()
        if ligado and tam[2] < 60:  # garante altura (o tamanho salvo pode estar zerado)
            tam[1] = max(100, tam[1] - 130)
            tam[2] = 130
            self.sp_dir.setSizes(tam)

    def _ver_historico(self, pix, rotulo):
        self._mostrar_fixa(pix, f"Versão das {rotulo}  (duplo clique na miniatura volta o código)")

    def _restaurar_historico(self, codigo):
        if not self.cena:
            return
        c = QTextCursor(self.cena.document())
        c.select(QTextCursor.Document)
        c.insertText(codigo)
        self.abas.setCurrentWidget(self.cena)
        self.status.showMessage("Código voltou para a versão do histórico (Ctrl+Z desfaz)", 4000)

    def _ir_para_erro(self):
        if self.cena and self.cena.linha_erro:
            self.abas.setCurrentWidget(self.cena)
            self.cena.ir_para(self.cena.linha_erro)

    # ================================================================ animação

    def _clock(self):
        return self.sl_clock.value() / 1000

    def _clock_mudou(self, v):
        self.lb_clock.setText(f" {v / 1000:.3f} ")
        self.pedir_render()

    def tocar(self):
        self.tocando = not self.tocando
        self.bt_play.setText("⏸" if self.tocando else "▶")
        if self.tocando:
            self._avancar_clock()
        else:
            self.pedir_render()

    def _avancar_clock(self):
        self.sl_clock.setValue((self.sl_clock.value() + 25) % 1000)  # dispara pedir_render

    # ================================================================ render

    def _rodando(self):
        return any(p.state() != QProcess.NotRunning for p, _ in self.procs)

    def _parar(self):
        for p, _ in self.procs:
            if p.state() != QProcess.NotRunning:
                p.finished.disconnect()
                p.kill()
                p.waitForFinished(1000)
        self.procs = []
        self._limpar_trab()

    def _limpar_trab(self):
        if self.trab:
            shutil.rmtree(self.trab, ignore_errors=True)
            self.trab = None

    def _preparar_trabalho(self):
        """Pasta temporária com as cópias das abas .inc alteradas (assim o render usa o que está na tela)."""
        trab = tempfile.mkdtemp(prefix="povlive_")
        pasta = self._pasta()
        for e in self._editores():
            if e is self.cena or not e.caminho or not e.document().isModified():
                continue
            rel = os.path.relpath(e.caminho, pasta)
            if rel.startswith(".."):
                continue
            destino = os.path.join(trab, rel)
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            with open(destino, "w", encoding="utf-8") as f:
                f.write(e.toPlainText())
        return trab

    def _nome_cena(self):
        return os.path.basename(self.cena.caminho) if self.cena and self.cena.caminho else "cena.pov"

    def _texto_cena(self, com_camera=True):
        texto = self.cena.toPlainText()
        if self.a_eixos.isChecked():
            texto += pov.eixos_pov(self.sp_eixos.value())
        if com_camera and self.orbita:
            texto += self.orbita.pov()
        return texto

    def _args(self, fonte, saida, w, h, q, aa, clock=None):
        a = [f"+I{fonte}", f"+O{saida}", f"+W{w}", f"+H{h}", "-D", "-V", "+FN", f"+Q{q}",
             f"+L{self._pasta()}"]
        if clock is not None:
            a.append(f"+K{clock:.4f}")
        if aa:
            a.append("+A0.3")
        return a

    def pedir_render(self, *_, grande=False):
        if not self.cena:
            return
        if grande:
            self._parar()
            return self._iniciar("grande")
        if self._rodando():
            if self.job == "previa":
                self.pendente = True   # deixa a prévia terminar e renderiza de novo em seguida
                return
            self._parar()
        self._iniciar("previa" if self.a_previa.isChecked() else "final")

    def _iniciar(self, job):
        self._limpar_trab()
        self.pendente = False
        nome, q, aa = QUALIDADES[self.cb_q.currentIndex()]
        w, h = TAMANHOS[self.cb_t.currentIndex()]
        quatro = self.a_quatro.isChecked() and job != "grande"
        if quatro:
            w, h = w // 2, h // 2
        self.nominal = QSize(w, h)
        if job == "previa":
            w, h, aa = max(80, w // 3), max(60, h // 3), False
        elif job == "grande":
            w, h, aa, q = 1280, 960, True, max(q, 9)
            self.nominal = QSize(w, h)

        self.trab = self._preparar_trabalho()
        texto = self._texto_cena()
        variantes = [texto]
        if quatro:
            cam = pov.ler_camera(self.cena.toPlainText())
            centro = self.orbita.alvo if self.orbita else cam["look_at"]
            base = self._texto_cena(com_camera=False)
            variantes += [base + pov.camera_orto(d, sky, centro, self.sp_escala.value()) for _, d, sky in pov.VISTAS]
        nome_base = os.path.splitext(self._nome_cena())[0]

        self.job = job
        self.job_estado = self.orbita.estado() if self.orbita else None  # câmera usada neste render
        self._t0 = time.time()
        self.procs = []
        self.resultados = [None] * len(variantes)
        for i, t in enumerate(variantes):
            fonte = f"{nome_base}.pov" if i == 0 else f"{nome_base}_vista{i}.pov"
            with open(os.path.join(self.trab, fonte), "w", encoding="utf-8") as f:
                f.write(t)
            png = os.path.join(self.trab, f"saida{i}.png")
            p = QProcess(self)
            p.setWorkingDirectory(self.trab)
            p.setProcessChannelMode(QProcess.MergedChannels)
            p.finished.connect(lambda rc, _s, i=i: self._um_terminou(i, rc))
            p.errorOccurred.connect(self._falhou)
            self.procs.append((p, png))
            p.start("povray", self._args(fonte, png, w, h, q, aa, self._clock()))
        if job != "previa":
            self.status.showMessage(f"Renderizando {w}×{h}" + (" (4 vistas)" if quatro else "") + "…")

    def _falhou(self, erro):
        if erro == QProcess.FailedToStart:
            self.status.showMessage("Não achei o povray. Instale com: sudo apt install povray")

    def _um_terminou(self, i, rc):
        p, png = self.procs[i]
        saida = bytes(p.readAll()).decode(errors="replace")
        pix = None
        if rc == 0:
            from PyQt5.QtGui import QPixmap
            pix = QPixmap(png)
            if pix.isNull():
                pix = None
        self.resultados[i] = (pix, saida)
        if all(r is not None for r in self.resultados):
            self._terminou_tudo()

    def _terminou_tudo(self):
        ms = int((time.time() - self._t0) * 1000)
        job = self.job
        resultados = self.resultados
        self.procs = []
        self._limpar_trab()
        ok = all(pix for pix, _ in resultados)

        if ok:
            pixs = [pix for pix, _ in resultados]
            self.ultima_pix = pixs[0]
            if len(pixs) == 4:
                self.quatro.mostrar(pixs, self.nominal)
            else:
                if job == "grande" and self.a_quatro.isChecked():  # o render grande é só da perspectiva
                    self.a_quatro.setChecked(False)
                    self.pilha.setCurrentWidget(self.visor)
                    self._atualizar_barra_vistas()
                self.visor.mostrar(pixs[0], self.nominal)
            self.cena.set_erro(None)
            self.log.hide()
            if self.orbita and self.job_estado:
                # serve de base para o zoom/mover responder na hora no próximo arraste
                self.live_ultimo = (pixs[0], self.job_estado)
                self.live_mostrado = self.live_seq
            if job != "previa":
                self.status.showMessage(f"OK em {ms} ms" + ("  (1280×960)" if job == "grande" else ""))
                self.historico.adicionar(self.cena.toPlainText(), pixs[0])
        else:
            saida = next(s for pix, s in resultados if not pix)
            self._mostrar_erro(saida)
            if self.tocando:
                self.tocando = False
                self.bt_play.setText("▶")

        if job in ("final", "grande"):
            self._atualizar_includes()
            if ok and self.orbita:
                self.cache_timer.start()
            if ok:
                self._mostrar_avisos(resultados[0][1])
                if not self.interagindo and not self.cena.arraste:
                    self.sel_timer.start()   # prepara a seleção por clique em segundo plano
        if self.pendente:
            self.pedir_render()
        elif self.tocando:
            self._avancar_clock()
        elif ok and job == "previa" and not self.interagindo and not (self.cena and self.cena.arraste):
            self._iniciar("final")

    def _mostrar_erro(self, saida):
        nome = self._nome_cena()
        base = os.path.splitext(nome)[0]
        saida = re.sub(re.escape(base) + r"_vista\d\.pov", nome, saida)
        m = re.search(r"File '([^']*)' line (\d+):", saida)
        linha, dica = None, ""
        if m:
            arquivo, linha = m.group(1), int(m.group(2))
            if os.path.basename(arquivo) != nome:   # erro dentro de um .inc
                dica = f"\n\nO erro está em {arquivo} (Ctrl+clique no #include para abrir)."
                linha = None
            elif linha > self.cena.blockCount():
                linha = self.cena.blockCount()
                dica = ("\n\nO erro aconteceu depois do fim do seu código: provavelmente falta fechar uma chave }."
                        " (Eixos e câmera livre são acrescentados no fim da cena, por isso podem aparecer na mensagem.)")
        self.cena.set_erro(linha)
        from . import avisos
        explicacao = avisos.explicar_erro(saida)
        if explicacao and not dica:
            dica = "\n\n💡 " + explicacao
        linhas = [l for l in saida.splitlines() if l.strip()]
        inicio = next((i for i, l in enumerate(linhas) if l.startswith("File '")),
                      next((i for i, l in enumerate(linhas) if "error" in l.lower()), max(0, len(linhas) - 8)))
        self.log.setPlainText("\n".join(linhas[inicio:]) + dica +
                              ("\n\n(duplo clique aqui para ir até a linha do erro)" if linha else ""))
        self.log.show()
        self.status.showMessage("Erro no render" + (f" — linha {linha}" if linha else ""))

    # ================================================================ exportar GIF

    def exportar_gif(self):
        if self.gif or not self.cena:
            return
        n, ok = QInputDialog.getInt(self, "Exportar GIF",
                                    "Quantos quadros? (o clock vai de 0 até 1;\n"
                                    "use a variável clock na cena para animar)", 30, 2, 500)
        if not ok:
            return
        base = os.path.splitext(self.cena.caminho)[0] + ".gif" if self.cena.caminho else os.path.expanduser("~/cena.gif")
        saida, _ = QFileDialog.getSaveFileName(self, "Salvar GIF", base, "GIF (*.gif)")
        if not saida:
            return
        nome, q, aa = QUALIDADES[self.cb_q.currentIndex()]
        w, h = TAMANHOS[self.cb_t.currentIndex()]
        trab = self._preparar_trabalho()
        fonte = self._nome_cena()
        with open(os.path.join(trab, fonte), "w", encoding="utf-8") as f:
            f.write(self._texto_cena())
        os.makedirs(os.path.join(trab, "quadros"))
        g = self.gif = {"n": n, "trab": trab, "saida": saida}
        # animação nativa do POV-Ray: quadros 0..n-1 com clock = i/n (o último quadro emenda no primeiro)
        args = self._args(fonte, os.path.join("quadros", "q.png"), w, h, q, aa)
        args += ["+KFI0", f"+KFF{n - 1}", "+KI0", f"+KF{(n - 1) / n:.6f}"]
        self.prog = QProgressDialog("Renderizando quadros…", "Cancelar", 0, n, self)
        self.prog.setWindowModality(Qt.WindowModal)
        self.prog.setMinimumDuration(0)
        self.prog.canceled.connect(self._gif_cancelar)
        g["timer"] = QTimer(self, interval=300)
        g["timer"].timeout.connect(
            lambda: self.prog.setValue(len(glob.glob(os.path.join(trab, "quadros", "*.png")))))
        g["timer"].start()
        p = g["proc"] = QProcess(self)
        p.setWorkingDirectory(trab)
        p.setProcessChannelMode(QProcess.MergedChannels)
        p.finished.connect(self._gif_terminou)
        p.start("povray", args)

    def _gif_terminou(self, rc, _status):
        g = self.gif
        if not g:
            return
        g["timer"].stop()
        quadros = sorted(glob.glob(os.path.join(g["trab"], "quadros", "*.png")))
        if rc != 0 or len(quadros) < g["n"]:
            erro = bytes(g["proc"].readAll()).decode(errors="replace")
            self._gif_cancelar()
            QMessageBox.warning(self, "Erro no GIF", "O POV-Ray falhou:\n\n" + erro[-800:])
            return
        try:
            from PIL import Image
            imgs = [Image.open(f).convert("RGB") for f in quadros]
            imgs[0].save(g["saida"], save_all=True, append_images=imgs[1:], duration=66, loop=0)
            self.status.showMessage(f"GIF salvo em {g['saida']}", 5000)
        except ImportError:
            QMessageBox.warning(self, "Falta o Pillow", "Instale com: sudo apt install python3-pil")
        self._gif_cancelar()

    def _gif_cancelar(self):
        g, self.gif = self.gif, None
        if not g:
            return
        g["timer"].stop()
        if g["proc"].state() != QProcess.NotRunning:
            g["proc"].finished.disconnect()
            g["proc"].kill()
            g["proc"].waitForFinished(1000)
        shutil.rmtree(g["trab"], ignore_errors=True)
        self.prog.close()


def tema_escuro(app):
    app.setStyle("Fusion")
    p = QPalette()
    cores = {QPalette.Window: "#2b2b2b", QPalette.WindowText: "#dddddd", QPalette.Base: "#1e1e1e",
             QPalette.AlternateBase: "#2b2b2b", QPalette.ToolTipBase: "#333333", QPalette.ToolTipText: "#dddddd",
             QPalette.Text: "#dddddd", QPalette.Button: "#3a3a3a", QPalette.ButtonText: "#dddddd",
             QPalette.Highlight: "#3d6fb4", QPalette.HighlightedText: "#ffffff", QPalette.Link: "#6fa8ff"}
    for papel, cor in cores.items():
        p.setColor(papel, QColor(cor))
    for papel in (QPalette.Text, QPalette.ButtonText, QPalette.WindowText):
        p.setColor(QPalette.Disabled, papel, QColor("#777777"))
    app.setPalette(p)
    app.setStyleSheet("QToolTip { color: #ddd; background: #333; border: 1px solid #555; }")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("POV-Ray ao vivo")
    app.setDesktopFileName("povlive")
    tema_escuro(app)
    j = Janela(sys.argv[1:])
    j.show()
    sys.exit(app.exec_())
