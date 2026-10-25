"""Fila simples de renders em segundo plano (um processo por vez, sem travar a interface)."""
import os, shutil, tempfile

from PyQt5.QtCore import QObject, QProcess

from . import pov


class FilaRender(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.itens = []
        self.proc = None
        self.atual = None

    def adicionar(self, texto, saida, args, pronto, pasta_extra=None, arquivos=None):
        """Renderiza 'texto' em 'saida' (PNG). pronto(ok, log) é chamado no fim.
        arquivos: {caminho relativo: conteúdo} para gravar junto (ex.: .inc alterados).
        pasta_extra: pasta adicionada à busca de #include (+L)."""
        self.itens.append((texto, saida, list(args), pronto, pasta_extra, arquivos or {}))
        if self.proc is None:
            self._proximo()

    def cancelar(self):
        self.itens = []
        if self.proc and self.proc.state() != QProcess.NotRunning:
            self.proc.finished.disconnect()
            self.proc.kill()
            self.proc.waitForFinished(1000)
        self._limpar()

    def ocupada(self):
        return self.proc is not None or bool(self.itens)

    def _limpar(self):
        if self.atual and os.path.isdir(self.atual[0]):
            shutil.rmtree(self.atual[0], ignore_errors=True)
        self.proc = None
        self.atual = None

    def _proximo(self):
        if not self.itens:
            return
        texto, saida, args, pronto, pasta_extra, arquivos = self.itens.pop(0)
        trab = tempfile.mkdtemp(prefix="povlive_fila_")
        with open(os.path.join(trab, "cena.pov"), "w", encoding="utf-8") as f:
            f.write(texto)
        for rel, conteudo in arquivos.items():
            destino = os.path.join(trab, rel)
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            with open(destino, "w", encoding="utf-8") as f:
                f.write(conteudo)
        tmp_png = os.path.join(trab, "saida.png")
        self.atual = (trab, saida, pronto, tmp_png)
        p = self.proc = QProcess(self)
        p.setWorkingDirectory(trab)
        p.setProcessChannelMode(QProcess.MergedChannels)
        p.finished.connect(self._terminou)
        a = ["+Icena.pov", f"+O{tmp_png}"] + args
        if pasta_extra:
            a.append(f"+L{pasta_extra}")
        pov.iniciar(p, a)

    def _terminou(self, rc, _status):
        trab, saida, pronto, tmp_png = self.atual
        log = bytes(self.proc.readAll()).decode(errors="replace")
        ok = rc == 0 and os.path.exists(tmp_png)
        if ok:
            os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
            shutil.move(tmp_png, saida)
        self._limpar()
        try:
            pronto(ok, log)
        finally:
            self._proximo()
