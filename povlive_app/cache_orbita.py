"""Cache de órbita da câmera livre.

Cada render do POV-Ray tem um custo fixo de ~0,7 s (inicialização), então não dá para
renderizar a cada movimento do mouse. Enquanto a câmera livre está parada, este cache
pré-renderiza a cena em volta do alvo: 36 ângulos (de 10 em 10 graus) x 7 alturas.
Ao arrastar, o quadro mais próximo aparece na hora.

Usa o modo de animação do POV-Ray: cada processo renderiza uma faixa de quadros
(+SF/+EF), e o próprio arquivo da cena calcula a câmera de cada quadro a partir de
frame_number. A ordem é escolhida para que os ângulos mais próximos da vista atual
fiquem prontos primeiro.
"""
import glob, math, os, re, shutil

from PyQt5.QtCore import QObject, QProcess, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap

from . import pov

PASSO = math.radians(10)
NY = 36                              # ângulos na volta (yaw)
LINHAS = [0, 1, -1, 2, -2, 3, -3]    # alturas (pitch) em passos, em ordem de prioridade
NPROC = 12
CHUNK = NY * len(LINHAS) // NPROC    # quadros por processo (21)
LIMITE_PITCH = math.radians(85)


def deslocamento(i):
    """Índice na volta -> passos a partir do ângulo inicial: 0, +1, -1, +2, -2, ..."""
    return (i + 1) // 2 if i % 2 else -(i // 2)


def quadro_para_posicao(f):
    """Número do quadro (1..N) -> (linha, deslocamento)."""
    p, m = divmod(f - 1, CHUNK)
    g = m * NPROC + p                # intercalado: todos os processos fazem os mais prioritários primeiro
    r, i = divmod(g, NY)
    return r, deslocamento(i)


def angulo_dif(a, b):
    d = (a - b) % (2 * math.pi)
    return min(d, 2 * math.pi - d)


class CacheOrbita(QObject):
    novo_quadro = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.procs = []
        self.trab = None
        self.chave = None
        self.quadros = {}     # f -> (pix, yaw, pitch)
        self.timer = QTimer(self, interval=150)
        self.timer.timeout.connect(self._coletar)

    def construindo(self):
        return any(p.state() != QProcess.NotRunning for p, _ in self.procs)

    def parar(self):
        self.timer.stop()
        for p, _ in self.procs:
            if p.state() != QProcess.NotRunning:
                p.finished.disconnect()
                p.kill()
                p.waitForFinished(1000)
        self.procs = []
        if self.trab:
            shutil.rmtree(self.trab, ignore_errors=True)
            self.trab = None
        self.quadros = {}
        self.chave = None

    def iniciar(self, chave, texto, orbita, trab, args):
        """texto: cena sem câmera; args(fonte, saida) -> argumentos do povray (tamanho, qualidade...)."""
        self.parar()
        self.chave = chave
        self.trab = trab
        self.yaw0 = orbita.yaw
        self.alvo = list(orbita.alvo)
        self.dist = orbita.dist
        self.pitches = [max(-LIMITE_PITCH, min(LIMITE_PITCH, orbita.pitch + k * PASSO)) for k in LINHAS]
        os.makedirs(os.path.join(trab, "orbita"), exist_ok=True)
        fonte = "cena_orbita.pov"
        with open(os.path.join(trab, fonte), "w", encoding="utf-8") as f:
            f.write(texto + self._camera_sdl(orbita))
        for p in range(NPROC):
            a = args(fonte, os.path.join("orbita", "c.png"))
            a += ["+KFI1", f"+KFF{NPROC * CHUNK}", f"+SF{p * CHUNK + 1}", f"+EF{(p + 1) * CHUNK}"]
            proc = QProcess(self)
            proc.setWorkingDirectory(trab)
            proc.setProcessChannelMode(QProcess.MergedChannels)
            proc.setStandardOutputFile(QProcess.nullDevice())
            proc.finished.connect(self._coletar)
            pov.iniciar(proc, a, baixa_prioridade=True)   # não atrapalha o resto do computador
            self.procs.append((proc, range(p * CHUNK + 1, (p + 1) * CHUNK + 1)))
        self.timer.start()

    def _camera_sdl(self, o):
        alvo = pov.fmt_vetor(o.alvo)
        pitches = ", ".join(f"{x:.6f}" for x in self.pitches)
        ang = f" angle {pov.fmt_num(o.angle)}" if o.angle else ""
        return f"""
// ---- câmera do cache de órbita do povlive ----
#declare PLV_F = frame_number - 1;
#declare PLV_G = mod(PLV_F, {CHUNK}) * {NPROC} + div(PLV_F, {CHUNK});
#declare PLV_I = mod(PLV_G, {NY});
#if (mod(PLV_I, 2) = 1) #declare PLV_O = (PLV_I + 1) / 2; #else #declare PLV_O = -PLV_I / 2; #end
#declare PLV_PITCHES = array[{len(LINHAS)}] {{ {pitches} }};
#declare PLV_Y = {self.yaw0:.6f} + PLV_O * {PASSO:.6f};
#declare PLV_P = PLV_PITCHES[div(PLV_G, {NY})];
camera {{ perspective
    location {alvo} + {self.dist:.6f} * <cos(PLV_P) * sin(PLV_Y), sin(PLV_P), -cos(PLV_P) * cos(PLV_Y)>
    look_at {alvo} right x*image_width/image_height{ang} }}
"""

    def _coletar(self, *_):
        if not self.trab:
            return
        novos = False
        arquivos = {}
        for c in glob.glob(os.path.join(self.trab, "orbita", "c*.png")):
            m = re.search(r"(\d+)\.png$", c)
            if m:
                arquivos[int(m.group(1))] = c
        for proc, faixa in self.procs:
            rodando = proc.state() != QProcess.NotRunning
            presentes = [f for f in faixa if f in arquivos]
            # enquanto o processo roda, o último arquivo dele pode estar sendo escrito
            prontos = presentes[:-1] if rodando and presentes else presentes
            for f in prontos:
                if f in self.quadros:
                    continue
                pix = QPixmap(arquivos[f])
                if pix.isNull():
                    continue
                r, o = quadro_para_posicao(f)
                self.quadros[f] = (pix, self.yaw0 + o * PASSO, self.pitches[r])
                novos = True
        if novos:
            self.novo_quadro.emit()
        if not self.construindo():
            self.timer.stop()
            shutil.rmtree(self.trab, ignore_errors=True)
            self.trab = None

    def melhor(self, yaw, pitch):
        """(erro, pix, yaw, pitch) do quadro mais próximo, ou None."""
        melhor = None
        for pix, y, p in self.quadros.values():
            erro = angulo_dif(y, yaw) + abs(p - pitch)
            if melhor is None or erro < melhor[0]:
                melhor = (erro, pix, y, p)
        return melhor
