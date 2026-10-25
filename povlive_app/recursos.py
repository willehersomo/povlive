"""Recursos da janela: painel de matrizes, avisos, clicar/arrastar objetos na imagem,
formatar código, exercícios e exportar entrega. (Mixin da classe Janela.)"""
import math, os, tempfile

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QImage, QPixmap, QTextCursor
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton, QTextBrowser,
                             QListWidget, QListWidgetItem, QToolButton, QMessageBox, QDialog,
                             QFileDialog, QProgressDialog, QButtonGroup, QGridLayout, QPushButton)

from . import pov, sdl, matrizes, selecao, formatador, avisos, exercicios
from .fila import FilaRender
from .entrega import Exportador


class RecursosMixin:

    # ================================================================ montagem

    def _montar_recursos(self):
        self.fila = FilaRender(self)
        self.sel = None              # {"chave", "img", "mapa", "texto"}
        self.sel_esperando = []      # funções a chamar quando a seleção ficar pronta
        self.sel_chave_pendente = None
        self.sel_dir = tempfile.mkdtemp(prefix="povlive_sel_")
        self.mov = None              # objeto sendo arrastado na imagem
        self.lista_de_avisos = []

        # painel de matrizes
        self.painel_mat = QWidget()
        lay = QVBoxLayout(self.painel_mat)
        lay.setContentsMargins(4, 2, 4, 2)
        topo = QHBoxLayout()
        topo.addWidget(QLabel("<b>Matrizes</b>"))
        self.rb_aula = QRadioButton("Aula (coluna)")
        self.rb_pov = QRadioButton("POV-Ray (linha)")
        self.rb_aula.setChecked(True)
        grupo = QButtonGroup(self.painel_mat)
        grupo.addButton(self.rb_aula)
        grupo.addButton(self.rb_pov)
        self.rb_aula.toggled.connect(lambda _: self._mat_atualizar())
        topo.addStretch()
        topo.addWidget(self.rb_aula)
        topo.addWidget(self.rb_pov)
        lay.addLayout(topo)
        self.txt_mat = QTextBrowser()
        lay.addWidget(self.txt_mat)
        self.painel_mat.hide()
        self.mat_timer = QTimer(self, singleShot=True, interval=150)
        self.mat_timer.timeout.connect(self._mat_atualizar)

        # painel de avisos
        self.lista_avisos = QListWidget()
        self.lista_avisos.setStyleSheet("QListWidget{background:#2b2a14;color:#ffd77a;border:none}")
        self.lista_avisos.setWordWrap(True)
        self.lista_avisos.itemDoubleClicked.connect(self._aviso_clicado)
        self.lista_avisos.setToolTip("Duplo clique: vai para a linha (e oferece a correção, quando houver)")
        self.lista_avisos.hide()
        self.bt_avisos = QToolButton(text="⚠ 0 avisos")
        self.bt_avisos.setAutoRaise(True)
        self.bt_avisos.setStyleSheet("color:#ffd77a")
        self.bt_avisos.clicked.connect(lambda: self.lista_avisos.setVisible(not self.lista_avisos.isVisible()))
        self.bt_avisos.hide()
        self.status.addPermanentWidget(self.bt_avisos)

        self.sp_esq.addWidget(self.lista_avisos)
        self.sp_esq.addWidget(self.painel_mat)

        for v in (self.visor, self.quatro.persp):
            v.clicou.connect(lambda x, y, v=v: self._clicou_imagem(v, x, y))
            v.objeto.connect(lambda fase, a, b, mods, v=v: self._objeto_mouse(v, fase, a, b, mods))
        self.sel_timer = QTimer(self, singleShot=True, interval=600)
        self.sel_timer.timeout.connect(lambda: self._sel_preparar())

    # ================================================================ painel de matrizes

    def mostrar_matrizes(self, ligado):
        self.painel_mat.setVisible(ligado)
        if ligado:
            tam = self.sp_esq.sizes()
            i = self.sp_esq.indexOf(self.painel_mat)
            if tam[i] < 80:
                tam[0] = max(150, tam[0] - 300)
                tam[i] = 300
                self.sp_esq.setSizes(tam)
            self._mat_atualizar()

    def _mat_agendar(self):
        if self.painel_mat.isVisible():
            self.mat_timer.start()

    def _mat_atualizar(self):
        e = self.ed()
        if not e or not self.painel_mat.isVisible():
            return
        try:
            dados = matrizes.analisar(e.toPlainText(), e.textCursor().position(), self._clock())
        except Exception as ex:  # o código pode estar no meio da digitação
            dados = None
            self.txt_mat.setHtml(f"<p style='color:#999'>Não consegui ler este trecho ({ex}).</p>")
            return
        barra = self.txt_mat.verticalScrollBar().value()
        self.txt_mat.setHtml(matrizes.html(dados, "aula" if self.rb_aula.isChecked() else "pov"))
        self.txt_mat.verticalScrollBar().setValue(barra)

    # ================================================================ avisos

    def _mostrar_avisos(self, saida):
        ignorar = bool(self.orbita) or self.a_quatro.isChecked()
        lista = avisos.ler(saida, ignorar_cameras=ignorar)
        self.lista_de_avisos = lista
        self.lista_avisos.clear()
        for a in lista:
            onde = f"linha {a['linha']}: " if a["linha"] else ""
            extra = "  [duplo clique corrige]" if a["correcao"] else ""
            it = QListWidgetItem(f"⚠ {onde}{a['texto']}{extra}")
            it.setToolTip(a["original"])
            it.setData(Qt.UserRole, a)
            self.lista_avisos.addItem(it)
        n = len(lista)
        self.bt_avisos.setText(f"⚠ {n} aviso" + ("s" if n != 1 else ""))
        self.bt_avisos.setVisible(n > 0)
        if n == 0:
            self.lista_avisos.hide()

    def _aviso_clicado(self, it):
        a = it.data(Qt.UserRole)
        if a["linha"] and self.cena:
            self.abas.setCurrentWidget(self.cena)
            self.cena.ir_para(a["linha"])
        if a["correcao"] and self.cena:
            r = QMessageBox.question(self, "Corrigir aviso", a["texto"] + "\n\nAplicar a correção no código?")
            if r == QMessageBox.Yes:
                self._substituir_texto(self.cena, avisos.corrigir(self.cena.toPlainText(), a["correcao"]))

    # ================================================================ utilidades de edição

    def _substituir_texto(self, e, novo):
        """Troca o texto do editor mexendo só no trecho que mudou (um Ctrl+Z desfaz)."""
        velho = e.toPlainText()
        if novo == velho:
            return None
        i = 0
        lim = min(len(velho), len(novo))
        while i < lim and velho[i] == novo[i]:
            i += 1
        j = 0
        while j < lim - i and velho[-1 - j] == novo[-1 - j]:
            j += 1
        c = QTextCursor(e.document())
        c.setPosition(i)
        c.setPosition(len(velho) - j, QTextCursor.KeepAnchor)
        c.insertText(novo[i:len(novo) - j])
        return i, len(novo) - j

    def formatar_codigo(self):
        e = self.ed()
        linha = e.textCursor().blockNumber()
        barra = e.verticalScrollBar().value()
        if self._substituir_texto(e, formatador.formatar(e.toPlainText())) is None:
            self.status.showMessage("O código já está formatado", 2000)
            return
        b = e.document().findBlockByNumber(linha)
        if b.isValid():
            c = e.textCursor()
            c.setPosition(b.position() + len(b.text()) - len(b.text().lstrip()))
            e.setTextCursor(c)
        e.verticalScrollBar().setValue(barra)
        self.status.showMessage("Código formatado (Ctrl+Z desfaz)", 3000)

    # ================================================================ seleção pela imagem

    def _arquivos_inc_alterados(self):
        pasta = self._pasta()
        r = {}
        for e in self._editores():
            if e is self.cena or not e.caminho or not e.document().isModified():
                continue
            rel = os.path.relpath(e.caminho, pasta)
            if not rel.startswith(".."):
                r[rel] = e.toPlainText()
        return r

    def _sel_chave(self):
        if not self.cena:
            return None
        return hash((self.cena.toPlainText(), self.orbita.estado() if self.orbita else None,
                     self._tamanho_nominal(), self._clock(), tuple(sorted(self._arquivos_inc_alterados().items()))))

    def _sel_preparar(self, depois=None):
        """Garante a imagem de seleção (cores únicas) da cena atual; chama depois() quando pronta."""
        chave = self._sel_chave()
        if chave is None:
            return
        if self.sel and self.sel["chave"] == chave:
            if depois:
                depois()
            return
        if depois:
            self.sel_esperando.append(depois)
        if self.sel_chave_pendente == chave:
            return
        self.sel_chave_pendente = chave
        texto = self.cena.toPlainText()
        marcado, mapa = selecao.marcar(texto)
        if self.orbita:
            marcado += self.orbita.pov()
        w, h = self._tamanho_nominal()
        png = os.path.join(self.sel_dir, f"sel_{abs(chave)}.png")
        args = [f"+W{w}", f"+H{h}", "-D", "-V", "+Q4", f"+K{self._clock():.4f}"] + selecao.ARGS_EXTRA
        self.fila.adicionar(marcado, png, args,
                            lambda ok, log: self._sel_pronta(ok, log, chave, mapa, texto, png),
                            pasta_extra=self._pasta(), arquivos=self._arquivos_inc_alterados())

    def _sel_pronta(self, ok, log, chave, mapa, texto, png):
        if self.sel_chave_pendente == chave:
            self.sel_chave_pendente = None
        esperando, self.sel_esperando = self.sel_esperando, []
        if not ok:
            self.status.showMessage("Não deu para preparar a seleção (a cena tem erro?)", 3000)
            return
        img = QImage(png).convertToFormat(QImage.Format_RGB32)
        try:
            os.remove(png)
        except OSError:
            pass
        self.sel = {"chave": chave, "img": img, "mapa": mapa, "texto": texto}
        if chave != self._sel_chave():   # a cena mudou enquanto renderizava
            self.sel = None
            return
        for f in esperando:
            f()

    def _id_em(self, nx, ny):
        img = self.sel["img"]
        px = min(img.width() - 1, max(0, int(nx * img.width())))
        py = min(img.height() - 1, max(0, int(ny * img.height())))
        c = QColor(img.pixel(px, py))
        return selecao.id_da_cor(c.red(), c.green(), c.blue())

    def _clicou_imagem(self, visor, nx, ny):
        if not self.cena:
            return
        if not (self.sel and self.sel["chave"] == self._sel_chave()):
            self.status.showMessage("Preparando seleção…")
        self._sel_preparar(lambda: self._selecionar(visor, nx, ny))

    def _selecionar(self, visor, nx, ny):
        i = self._id_em(nx, ny)
        b = self.sel["mapa"].get(i)
        if not b:
            visor.set_destaque(None)
            self.status.showMessage("Nada aqui (fundo)", 2000)
            return
        texto = self.sel["texto"]
        self.abas.setCurrentWidget(self.cena)
        c = self.cena.textCursor()
        c.setPosition(b.kw_ini)
        c.setPosition(b.kw_ini + len(b.kw), QTextCursor.KeepAnchor)
        self.cena.setTextCursor(c)
        self.cena.centerCursor()
        self.cena.setFocus()
        self.status.showMessage(f"{selecao.caminho(b)} — linha {sdl.linha_de(texto, b.kw_ini)}   "
                                "(Ctrl+arrastar na imagem move o objeto)", 6000)
        visor.set_destaque(self._mascara(i))
        QTimer.singleShot(2500, lambda: visor.set_destaque(None))

    def _mascara(self, i):
        """Imagem transparente com o objeto i destacado (preenchimento leve + contorno)."""
        import numpy as np
        img = self.sel["img"]
        w, h = img.width(), img.height()
        ptr = img.constBits()
        ptr.setsize(img.byteCount())
        arr = np.frombuffer(ptr, np.uint8).reshape(h, img.bytesPerLine() // 4, 4)[:, :w, :3]
        r, g, bl = (round(v * 15) for v in selecao.cor_do_id(i))
        alvo = np.array([bl * 17, g * 17, r * 17])  # QImage RGB32 em memória é BGRA
        m = (np.abs(arr.astype(np.int16) - alvo).max(axis=2) <= 8)
        borda = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
        rgba = np.zeros((h, w, 4), np.uint8)
        rgba[m] = (255, 220, 0, 70)
        rgba[borda] = (255, 220, 0, 255)
        self._mascara_buf = rgba.copy()
        return QImage(self._mascara_buf.data, w, h, 4 * w, QImage.Format_RGBA8888)

    # ================================================================ arrastar objetos na imagem

    def _camera_atual(self, aspecto):
        if self.orbita:
            return self.orbita.posicao(), list(self.orbita.alvo), self.orbita.fov(aspecto)
        cam = pov.ler_camera(self.cena.toPlainText())
        fov = math.radians(cam["angle"]) if cam["angle"] else 2 * math.atan(aspecto / 2)
        return cam["location"], cam["look_at"], fov

    def _objeto_mouse(self, visor, fase, a, b, mods):
        if not self.cena:
            return
        if fase == "inicio":
            self.mov = None
            if not (self.sel and self.sel["chave"] == self._sel_chave()):
                self._sel_preparar()
                self.status.showMessage("Preparando seleção… tente arrastar de novo em 1 segundo", 3000)
                return
            bloco = self.sel["mapa"].get(self._id_em(a, b))
            if not bloco:
                self.status.showMessage("Nenhum objeto aqui", 2000)
                return
            self._mover_inicio(visor, selecao.topo(bloco))
        elif fase == "mover" and self.mov:
            m = self.mov
            passo = 0.1 if mods & int(Qt.ShiftModifier) else 0.01
            delta = pov.soma(pov.mult(m["r"], a * m["k"]), pov.mult(m["u"], -b * m["k"]))
            novo = [round((m["base"][i] + delta[i]) / passo) * passo for i in range(3)]
            self.cena._trocar_trecho(m["a"], pov.fmt_vetor(novo))
        elif fase == "fim" and self.mov:
            self.cena.arraste = None
            self.mov = None
            self.sel = None
            self.status.showMessage("Objeto movido (Ctrl+Z desfaz)", 3000)
            self.pedir_render()

    def _mover_inicio(self, visor, bloco):
        e = self.cena
        texto = e.toPlainText()
        tf = selecao.translate_final(texto, bloco)
        primeiro = True
        if tf:
            ini, fim, base = tf
        else:
            novo, (ini, fim) = selecao.inserir_translate(texto, bloco)
            self._substituir_texto(e, novo)
            base, primeiro = (0.0, 0.0, 0.0), False   # os movimentos entram no mesmo Ctrl+Z da inserção
            texto = novo
        w, h = self._tamanho_nominal()
        pos, alvo, fov = self._camera_atual(w / h)
        f = pov.unit(pov.sub(alvo, pos))
        r = pov.unit(pov.cross([0, 1, 0], f))
        u = pov.cross(f, r)
        # profundidade: onde o objeto está (pela matriz das transformações), senão o alvo da câmera
        prof = pov.norma(pov.sub(alvo, pos))
        try:
            d = matrizes.analisar(texto, bloco.abre + 1, self._clock())
            if d and d["total"]:
                p = matrizes.aplicar(d["total"], d["ponto"] or (0, 0, 0))
                z = sum((p[i] - pos[i]) * f[i] for i in range(3))
                if z > 0.1:
                    prof = z
        except Exception:
            pass
        largura_mundo = 2 * prof * math.tan(fov / 2)
        self.mov = {"a": {"ini": ini, "len": fim - ini, "primeiro": primeiro}, "base": list(base),
                    "r": r, "u": u, "k": largura_mundo / max(1.0, visor.largura_desenhada())}
        e.arraste = self.mov["a"]   # faz o editor renderizar a cada mudança, como no Ctrl+arrastar número
        self.status.showMessage(f"Movendo {bloco.kw} da linha {sdl.linha_de(texto, bloco.kw_ini)}…")

    # ================================================================ exercícios

    def comecar_exercicio(self, id_):
        ex = exercicios.POR_ID[id_]
        e = self._novo_editor(None, exercicios.texto_inicial(ex), f"exercício: {ex['titulo']}")
        c = e.textCursor()
        c.movePosition(QTextCursor.End)
        e.setTextCursor(c)
        self._aba_mudou()
        self.raise_()
        self.activateWindow()

    def verificar_exercicio(self):
        e = self.ed()
        id_ = exercicios.id_no_texto(e.toPlainText()) if e else None
        if not id_ and self.cena:
            e = self.cena
            id_ = exercicios.id_no_texto(e.toPlainText())
        if not id_:
            QMessageBox.information(self, "Verificar exercício",
                                    "Esta aba não é um exercício.\nAbra um em Ajuda > Guia do POV-Ray > Exercícios.")
            return
        ex = exercicios.POR_ID[id_]
        w, h = exercicios.TAMANHO
        args = [f"+W{w}", f"+H{h}"] + exercicios.ARGS
        arquivos = {"vazio": exercicios.arquivo_cache(exercicios.texto_vazio(ex), w, h),
                    "gabarito": exercicios.arquivo_cache(exercicios.texto_gabarito(ex), w, h),
                    "sua": os.path.join(self.sel_dir, "exercicio_sua.png")}
        textos = {"vazio": exercicios.texto_vazio(ex), "gabarito": exercicios.texto_gabarito(ex),
                  "sua": e.toPlainText()}
        faltando = [k for k in arquivos if k == "sua" or not os.path.exists(arquivos[k])]
        estado = {"n": len(faltando), "erro": None}
        self.status.showMessage("Conferindo o exercício…")

        def pronto(k, ok, log):
            if not ok:
                estado["erro"] = log
            estado["n"] -= 1
            if estado["n"] == 0:
                self._resultado_exercicio(ex, arquivos, estado["erro"])
        for k in faltando:
            self.fila.adicionar(textos[k], arquivos[k], args, lambda ok, log, k=k: pronto(k, ok, log))

    def _resultado_exercicio(self, ex, arquivos, erro):
        if erro:
            QMessageBox.warning(self, "Verificar exercício", "A cena tem erro e não renderizou:\n\n"
                                + "\n".join(l for l in erro.splitlines() if "rror" in l)[-600:])
            self.status.clearMessage()
            return
        import numpy as np
        from PIL import Image
        imgs = {k: np.array(Image.open(v).convert("RGB")) for k, v in arquivos.items()}
        nota, dif = exercicios.comparar(imgs["sua"], imgs["gabarito"], imgs["vazio"])
        self.status.showMessage(f"Exercício {ex['titulo']}: {nota * 100:.0f}% igual ao gabarito", 6000)
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Exercício: {ex['titulo']}")
        g = QGridLayout(dlg)
        aprovado = nota >= exercicios.NOTA_MINIMA
        msg = QLabel(f"<h2 style='color:{'#a6e22e' if aprovado else '#ffb86c'}'>"
                     + ("Correto! 🎉" if aprovado else f"Quase: {nota * 100:.0f}% igual ao gabarito") + "</h2>"
                     + ("" if aprovado else f"<p>Dica: {ex['dica']}</p>"
                        "<p>Na diferença: <span style='color:#ff6060'>vermelho</span> = sobrando na sua, "
                        "<span style='color:#6090ff'>azul</span> = faltando, "
                        "<span style='color:#ffd200'>amarelo</span> = diferente.</p>"))
        msg.setWordWrap(True)
        g.addWidget(msg, 0, 0, 1, 3)
        dif_img = QImage(dif.data, dif.shape[1], dif.shape[0], 3 * dif.shape[1], QImage.Format_RGB888).copy()
        for col, (titulo, pix) in enumerate((("Sua", QPixmap(arquivos["sua"])),
                                             ("Gabarito", QPixmap(arquivos["gabarito"])),
                                             ("Diferença", QPixmap.fromImage(dif_img)))):
            g.addWidget(QLabel(f"<b>{titulo}</b>"), 1, col)
            lb = QLabel()
            lb.setPixmap(pix)
            g.addWidget(lb, 2, col)
        bt = QPushButton("Fechar")
        bt.clicked.connect(dlg.accept)
        g.addWidget(bt, 3, 2)
        dlg.show()
        self._dlg_exercicio = dlg

    # ================================================================ exportar entrega

    def exportar_entrega(self):
        if not self.cena:
            return
        nome = self._nome_cena()
        base = os.path.join(self._pasta(), os.path.splitext(nome)[0] + "_entrega.zip")
        saida, _ = QFileDialog.getSaveFileName(self, "Exportar entrega", base, "ZIP (*.zip)")
        if not saida:
            return
        if not saida.lower().endswith(".zip"):
            saida += ".zip"
        conteudos = {e.caminho: e.toPlainText() for e in self._editores() if e.caminho}
        exp = self._exportador = Exportador(self, nome, self.cena.toPlainText(), self._pasta(), conteudos, saida)
        prog = QProgressDialog("Preparando…", "Cancelar", 0, 100, self)
        prog.setWindowTitle("Exportar entrega")
        prog.setWindowModality(Qt.WindowModal)
        prog.setMinimumDuration(0)
        prog.canceled.connect(exp.cancelar)
        exp.progresso.connect(lambda msg, pct: (prog.setLabelText(msg), prog.setValue(pct)))

        def fim(ok, msg):
            prog.close()
            if ok:
                self.status.showMessage(f"Entrega salva em {msg}", 6000)
                QMessageBox.information(self, "Exportar entrega", f"Entrega salva em:\n{msg}")
            else:
                QMessageBox.warning(self, "Exportar entrega", msg)
        exp.terminou.connect(fim)
        exp.iniciar()
