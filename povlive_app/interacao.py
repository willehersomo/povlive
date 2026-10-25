"""Prévia instantânea (OpenGL) e setas para mover/girar objetos na imagem. (Mixin da Janela.)"""
import math, time

import numpy as np
from PyQt5.QtCore import QSize, QTimer, Qt
from PyQt5.QtGui import QPixmap

from . import pov, matrizes, selecao, previa3d
from .i18n import tr

PASSO_ROTACAO = 0.6   # graus por pixel ao arrastar o anel


class InteracaoMixin:

    def _montar_interacao(self):
        self.r3d = None            # renderizador OpenGL (criado na primeira vez)
        self.r3d_testado = False
        self.cena3d = None
        self.cena3d_chave = None
        self.giz_kw = None         # objeto com as setas (posição da palavra-chave no código)
        self.giz = None            # dados do arraste de uma seta
        self.play_timer = QTimer(self, interval=33)
        self.play_timer.timeout.connect(self._play_quadro)
        self.play_t0 = 0.0
        for v in (self.visor, self.quatro.persp):
            v.gizmo_sinal.connect(lambda fase, alca, dx, dy, mods, v=v: self._gizmo_mouse(v, fase, alca, dx, dy, mods))
            v.esc.connect(self.soltar_selecao)
        self.sl_clock.sliderReleased.connect(self.pedir_render)

    # ================================================================ prévia

    def _renderizador(self):
        if not self.r3d_testado:
            self.r3d_testado = True
            self.r3d = previa3d.Renderizador()
            if not self.r3d.disponivel:
                self.status.showMessage(tr("OpenGL indisponível: a prévia instantânea fica desligada"), 5000)
        return self.r3d if self.r3d and self.r3d.disponivel else None

    def _cena3d(self):
        if not self.cena:
            return None
        texto = self.cena.toPlainText()
        incs = {e.caminho: e.toPlainText() for e in self._editores()
                if e is not self.cena and e.caminho and e.document().isModified()}
        chave = hash((texto, self._clock(), tuple(sorted(incs.items()))))
        if chave != self.cena3d_chave:
            try:
                self.cena3d = previa3d.interpretar(texto, self._pasta(), self._clock(), incs)
            except Exception:   # código no meio da digitação: sem prévia
                self.cena3d = None
            self.cena3d_chave = chave
        return self.cena3d

    def previa_ativa(self):
        if not self.a_previa3d.isChecked() or not self._renderizador():
            return False
        c = self._cena3d()
        return bool(c and c.pecas)

    def _camera_previa(self, aspecto):
        """(posição, alvo, fov, orto) da câmera atual: livre, senão a da cena."""
        if self.orbita:
            return self.orbita.posicao(), list(self.orbita.alvo), self.orbita.fov(aspecto), None
        cam = self.cena3d.camera if self.cena3d and self.cena3d.camera else None
        if cam is None:
            c = pov.ler_camera(self.cena.toPlainText())
            cam = {"location": c["location"], "look_at": c["look_at"], "angle": c["angle"], "orto": None}
        fov = math.radians(cam["angle"]) if cam["angle"] else 2 * math.atan(aspecto / 2)
        return cam["location"], cam["look_at"], fov, cam["orto"]

    def mostrar_previa(self):
        """Desenha a prévia instantânea no(s) visor(es). Devolve False se não deu."""
        if not self.previa_ativa():
            return False
        r = self._renderizador()
        cena = self.cena3d
        w, h = self._tamanho_nominal()
        linhas = []
        if self.a_eixos.isChecked():
            L = self.sp_eixos.value()
            linhas = [((0, 0, 0), (L, 0, 0), (1, 0.2, 0.2)), ((0, 0, 0), (0, L, 0), (0.2, 1, 0.2)),
                      ((0, 0, 0), (0, 0, L), (0.3, 0.5, 1))]
        pos, alvo, fov, orto = self._camera_previa(w / h)
        img = r.desenhar(cena, pos, alvo, fov, w, h, orto, linhas)
        if self.a_quatro.isChecked():
            centro = list(self.orbita.alvo) if self.orbita else list(pov.ler_camera(self.cena.toPlainText())["look_at"])
            esc = self.sp_escala.value()
            imgs = [img]
            for _n, d, _sky in pov.VISTAS:   # na vista de cima o renderizador já põe z para cima
                loc = pov.soma(centro, pov.mult(list(d), 1000))
                imgs.append(r.desenhar(cena, loc, centro, fov, w, h, esc, linhas))
            self.quatro.mostrar([QPixmap.fromImage(i) for i in imgs], QSize(w, h))
            for v in self.quatro.visores():
                v.previa = True
        else:
            self.visor.mostrar(QPixmap.fromImage(img), QSize(w, h), previa=True)
        self._gizmo_atualizar()
        return True

    # ================================================================ animação suave

    def _play_quadro(self):
        """Tocando com a prévia: o clock avança em tempo real (1 ciclo a cada 4 s)."""
        t = ((time.time() - self.play_t0) / 4.0) % 1.0
        self.sl_clock.blockSignals(True)
        self.sl_clock.setValue(int(t * 1000))
        self.sl_clock.blockSignals(False)
        self.lb_clock.setText(f" {t:.3f} ")
        if not self.mostrar_previa():
            self.play_timer.stop()

    # ================================================================ setas (gizmo)

    def soltar_selecao(self):
        self.giz_kw = None
        for v in (self.visor, self.quatro.persp):
            v.set_gizmo(None)
            v.set_destaque(None)

    def _gizmo_bloco(self):
        if self.giz_kw is None or not self.cena:
            return None
        return selecao.bloco_em(self.cena.toPlainText(), self.giz_kw)

    def _pivo(self, texto, b):
        """Ponto do mundo onde fica a origem local do objeto (onde as setas aparecem)."""
        try:
            d = matrizes.analisar(texto, b.abre + 1, self._clock())
            if d and d["total"]:
                return list(matrizes.aplicar(d["total"], (0, 0, 0)))
        except Exception:
            pass
        return None

    def _gizmo_atualizar(self):
        v = self._visor_persp()
        outros = self.visor if v is self.quatro.persp else self.quatro.persp
        outros.set_gizmo(None)
        b = self._gizmo_bloco()
        if b is None:
            v.set_gizmo(None)
            return
        texto = self.cena.toPlainText()
        o = self._pivo(texto, b)
        if o is None:
            v.set_gizmo(None)
            return
        w, h = self._tamanho_nominal()
        pos, alvo, fov, orto = self._camera_previa(w / h)
        if orto:
            v.set_gizmo(None)
            return
        L = 0.15 * max(0.2, pov.norma(pov.sub(o, list(pos))))
        pts = [o, pov.soma(o, [L, 0, 0]), pov.soma(o, [0, L, 0]), pov.soma(o, [0, 0, L])]
        anel = [pov.soma(o, [0.8 * L * math.cos(a), 0, 0.8 * L * math.sin(a)])
                for a in np.linspace(0, 2 * math.pi, 33)[:-1]]
        proj = previa3d.projetar(pts + anel, pos, alvo, fov, w / h)
        if proj[0] is None:
            v.set_gizmo(None)
            return
        v.set_gizmo({"o": proj[0], "x": proj[1], "y": proj[2], "z": proj[3], "anel": proj[4:], "L": L,
                     "mundo": o})

    def _gizmo_mouse(self, visor, fase, alca, dx, dy, mods):
        e = self.cena
        if fase == "inicio":
            b = self._gizmo_bloco()
            if b is None or not visor.gizmo:
                return
            texto = e.toPlainText()
            if alca == "anel":
                novo, (ini, fim, base) = selecao.garantir_rotate(texto, b)
            else:
                novo, (ini, fim, base) = selecao.garantir_translate(texto, b)
            inseriu = novo != texto
            if inseriu:
                self._substituir_texto(e, novo)
            g = visor.gizmo
            r = visor._retangulo()
            o = np.array([g["o"][0] * r.width(), g["o"][1] * r.height()])
            vetor_tela = {}
            for k in ("x", "y", "z"):
                if g.get(k) is not None:
                    vetor_tela[k] = np.array([g[k][0] * r.width(), g[k][1] * r.height()]) - o
            self.giz = {"alca": alca, "a": {"ini": ini, "len": fim - ini, "primeiro": not inseriu},
                        "base": list(base), "tela": vetor_tela, "L": g["L"]}
            e.arraste = self.giz["a"]
            self.status.showMessage(tr("Arrastando a seta {}").format(alca.upper()) if alca != "anel" else
                                    tr("Girando em torno de y (Shift: de 15° em 15°)"))
        elif fase == "mover" and self.giz:
            gz = self.giz
            fino = bool(mods & int(Qt.ShiftModifier))
            novo = list(gz["base"])
            if gz["alca"] == "anel":
                ang = dx * PASSO_ROTACAO
                ang = round(ang / 15) * 15 if fino else round(ang)
                novo[1] = gz["base"][1] + ang
            else:
                s = gz["tela"].get(gz["alca"])
                if s is None or np.linalg.norm(s) < 1:
                    return
                t = (dx * s[0] + dy * s[1]) / (s @ s) * gz["L"]   # quanto andou ao longo da seta, em unidades
                passo = 0.1 if fino else 0.01
                i = "xyz".index(gz["alca"])
                novo[i] = round((gz["base"][i] + t) / passo) * passo
            e._trocar_trecho(gz["a"], pov.fmt_vetor(novo))
        elif fase == "fim" and self.giz:
            self.giz = None
            e.arraste = None
            self.status.showMessage(tr("Pronto (Ctrl+Z desfaz)"), 3000)
            self.pedir_render()
            self._gizmo_atualizar()
