"""Exportar entrega: um .zip com a cena, os .inc locais, a imagem em alta, o GIF (se animada) e um LEIAME."""
import glob, os, re, shutil, tempfile, time, zipfile

from PyQt5.QtCore import QObject, QProcess, pyqtSignal

from . import pov
from .i18n import tr, idioma


def includes_locais(texto, pasta, conteudos, vistos=None):
    """{caminho absoluto: texto} dos .inc da pasta da cena usados (recursivo). conteudos: abas abertas."""
    vistos = vistos if vistos is not None else {}
    for nome in pov.RX_INCLUDE.findall(texto):
        c = os.path.join(pasta, nome)
        if not os.path.isfile(c) and c not in conteudos:
            continue  # include padrão do POV-Ray (colors.inc...) ou inexistente
        c = os.path.abspath(c)
        if c in vistos:
            continue
        t = conteudos.get(c)
        if t is None:
            t = open(c, encoding="utf-8", errors="replace").read()
        vistos[c] = t
        includes_locais(t, pasta, conteudos, vistos)
    return vistos


class Exportador(QObject):
    progresso = pyqtSignal(str, int)   # mensagem, porcentagem
    terminou = pyqtSignal(bool, str)   # ok, mensagem

    def __init__(self, parent, nome_cena, texto, pasta, conteudos, saida_zip, tamanho=(1280, 960), quadros=30):
        super().__init__(parent)
        self.nome = nome_cena if nome_cena.endswith(".pov") else nome_cena + ".pov"
        self.texto, self.pasta, self.saida = texto, pasta, saida_zip
        self.incs = includes_locais(texto, pasta, conteudos)
        self.tamanho, self.quadros = tamanho, quadros
        self.animada = bool(re.search(r"\bclock\b", pov.RX_INCLUDE.sub("", texto)))
        self.trab = tempfile.mkdtemp(prefix="povlive_entrega_")
        self.proc = None
        self.cancelado = False

    def iniciar(self):
        with open(os.path.join(self.trab, self.nome), "w", encoding="utf-8") as f:
            f.write(self.texto)
        for c, t in self.incs.items():
            destino = os.path.join(self.trab, os.path.relpath(c, self.pasta))
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            with open(destino, "w", encoding="utf-8") as f:
                f.write(t)
        w, h = self.tamanho
        self.progresso.emit(tr("Renderizando a imagem final ({} com antialiasing)…").format(f"{w}×{h}"), 5)
        self._rodar(["+Q11", "+A0.3", f"+W{w}", f"+H{h}", f"+O{os.path.splitext(self.nome)[0]}.png"], self._depois_png)

    def cancelar(self):
        self.cancelado = True
        if self.proc and self.proc.state() != QProcess.NotRunning:
            self.proc.finished.disconnect()
            self.proc.kill()
            self.proc.waitForFinished(1000)
        shutil.rmtree(self.trab, ignore_errors=True)

    def _rodar(self, extra, depois):
        p = self.proc = QProcess(self)
        p.setWorkingDirectory(self.trab)
        p.setProcessChannelMode(QProcess.MergedChannels)
        p.finished.connect(lambda rc, _s: depois(rc, bytes(p.readAll()).decode(errors="replace")))
        p.start(pov.EXECUTAVEL, [f"+I{self.nome}", "-D", "-V", "+FN", f"+L{self.pasta}"] + extra)

    def _depois_png(self, rc, log):
        if rc != 0:
            return self._falhar(tr("A imagem final não renderizou:") + "\n" + log[-600:])
        if self.animada:
            n = self.quadros
            self.progresso.emit(tr("Renderizando a animação ({} quadros)…").format(n), 40)
            os.makedirs(os.path.join(self.trab, "_quadros"))
            self._rodar(["+Q9", "+W480", "+H360", os.path.join("+O_quadros", "q.png"),
                         "+KFI0", f"+KFF{n - 1}", "+KI0", f"+KF{(n - 1) / n:.6f}"], self._depois_gif)
        else:
            self._empacotar()

    def _depois_gif(self, rc, log):
        if rc != 0:
            return self._falhar(tr("A animação não renderizou:") + "\n" + log[-600:])
        try:
            from PIL import Image
            quadros = sorted(glob.glob(os.path.join(self.trab, "_quadros", "*.png")))
            imgs = [Image.open(q).convert("RGB") for q in quadros]
            imgs[0].save(os.path.join(self.trab, os.path.splitext(self.nome)[0] + ".gif"),
                         save_all=True, append_images=imgs[1:], duration=66, loop=0)
        except ImportError:
            pass
        shutil.rmtree(os.path.join(self.trab, "_quadros"), ignore_errors=True)
        self._empacotar()

    def _empacotar(self):
        if self.cancelado:
            return
        self.progresso.emit(tr("Montando o .zip…"), 90)
        base = os.path.splitext(self.nome)[0]
        w, h = self.tamanho
        arquivos = sorted(os.path.relpath(os.path.join(r, f), self.trab)
                          for r, _, fs in os.walk(self.trab) for f in fs)
        data = time.strftime("%d/%m/%Y %H:%M" if idioma() == "pt" else "%Y-%m-%d %H:%M")
        leia = [tr("Entrega: {}").format(base), tr("Gerado em {} pelo PovLive.").format(data), "",
                tr("Arquivos:")] + [f"  {a}" for a in arquivos] + [
                "", tr("Para renderizar de novo:"),
                f"  povray +I{self.nome} +W{w} +H{h} +A0.3"]
        if self.animada:
            leia += ["", tr("Animação (usa a variável clock):"),
                     f"  povray +I{self.nome} +W480 +H360 +KFI0 +KFF{self.quadros - 1} +KI0 +KF{(self.quadros - 1) / self.quadros:.4f}"]
        with open(os.path.join(self.trab, tr("LEIAME.txt")), "w", encoding="utf-8") as f:
            f.write("\n".join(leia) + "\n")
        with zipfile.ZipFile(self.saida, "w", zipfile.ZIP_DEFLATED) as z:
            for r, _, fs in os.walk(self.trab):
                for f in fs:
                    c = os.path.join(r, f)
                    z.write(c, os.path.join(base, os.path.relpath(c, self.trab)))
        shutil.rmtree(self.trab, ignore_errors=True)
        self.progresso.emit("Pronto", 100)
        self.terminou.emit(True, self.saida)

    def _falhar(self, msg):
        shutil.rmtree(self.trab, ignore_errors=True)
        self.terminou.emit(False, msg)
