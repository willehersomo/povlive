"""O que muda entre Linux e Windows: onde está o POV-Ray, os includes, as pastas do app e como iniciar
o processo.

No Windows o app usa a versão de linha de comando do POV-Ray (a mesma do Linux, compilada com o Cygwin)
que vai junto no instalador, na pasta povray/. POVLIVE_POVRAY e POVLIVE_INCLUDE escolhem outros.
"""
import glob, os, re, shutil, sys

WINDOWS = sys.platform.startswith("win")


def pasta_app():
    """Pasta do app (no executável do PyInstaller, a pasta do .exe)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def recurso(rel):
    """Arquivo que vai junto com o app (no PyInstaller, dentro da pasta dos dados), ou None."""
    for base in (getattr(sys, "_MEIPASS", None), pasta_app()):
        if base and os.path.exists(os.path.join(base, rel)):
            return os.path.join(base, rel)
    return None


def _embutido():
    d = os.path.join(pasta_app(), "povray")
    exe = os.path.join(d, "bin", "povray.exe" if WINDOWS else "povray")
    return exe if os.path.isfile(exe) else None


def executavel():
    if os.environ.get("POVLIVE_POVRAY"):
        return os.environ["POVLIVE_POVRAY"]
    candidatos = [_embutido(), shutil.which("povray")]
    if WINDOWS:
        candidatos += [r"C:\cygwin64\bin\povray.exe", r"C:\cygwin\bin\povray.exe"]
    for c in candidatos:
        if c and os.path.isfile(c):
            return c
    return "povray"


def biblioteca():
    """Pastas com os includes padrão (colors.inc, textures.inc...)."""
    if os.environ.get("POVLIVE_INCLUDE"):
        return [os.environ["POVLIVE_INCLUDE"]]
    padroes = [os.path.join(pasta_app(), "povray", "share", "povray-3*", "include"),
               "/usr/share/povray-3*/include", "/usr/local/share/povray-3*/include"]
    exe = executavel()
    if os.path.isabs(exe):   # instalação ao lado do executável (bin/ e share/)
        padroes.append(os.path.join(os.path.dirname(os.path.dirname(exe)), "share", "povray-3*", "include"))
    if WINDOWS:
        docs = os.path.join(os.path.expanduser("~"), "Documents")
        padroes.append(os.path.join(docs, "POV-Ray", "v3.*", "include"))
    for p in padroes:
        achados = sorted(d for d in glob.glob(p) if os.path.isfile(os.path.join(d, "colors.inc")))
        if achados:
            return achados[-1:]
    return []


def relativo(caminho, pasta):
    """Caminho relativo à pasta, ou None se estiver fora dela (ou em outra unidade, no Windows)."""
    try:
        rel = os.path.relpath(caminho, pasta)
    except ValueError:
        return None
    return None if rel == ".." or rel.startswith(".." + os.sep) else rel


def caminho_pov(p):
    """Caminho no formato que o POV-Ray entende (o do Cygwin aceita C:/..., não barras invertidas)."""
    return p.replace("\\", "/") if WINDOWS else p


RX_OPCAO_CAMINHO = re.compile(r"^([+-][IOL])(.+)$")


def argumentos(args, biblioteca_=None):
    """Ajusta os caminhos das opções +I/+O/+L e acrescenta a pasta dos includes padrão."""
    saida = []
    for a in args:
        m = RX_OPCAO_CAMINHO.match(a)
        saida.append(m.group(1) + caminho_pov(m.group(2)) if m else a)
    for d in (biblioteca() if biblioteca_ is None else biblioteca_):
        saida.append("+L" + caminho_pov(d))
    return saida


def nice():
    """Programa para baixar a prioridade de renders em segundo plano (só no Linux)."""
    return None if WINDOWS else shutil.which("nice")


def _pasta_usuario(tipo):
    if WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "povlive", tipo)
    if tipo == "cache":
        base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "povlive")


def pasta_cache():
    return _pasta_usuario("cache")


def pasta_dados():
    return _pasta_usuario("dados")


def fonte_mono(tamanho=None):
    """Fonte de largura fixa: a do sistema, se for mesmo de largura fixa; senão, uma conhecida."""
    from PyQt5.QtGui import QFont, QFontDatabase, QFontInfo
    candidatas = [QFontDatabase.systemFont(QFontDatabase.FixedFont)]
    nomes = ["Consolas", "Cascadia Mono", "Courier New"] if WINDOWS else ["DejaVu Sans Mono", "Liberation Mono",
                                                                          "Monospace"]
    for nome in nomes:
        f = QFont(nome)
        f.setStyleHint(QFont.TypeWriter)
        candidatas.append(f)
    escolhida = next((f for f in candidatas if QFontInfo(f).fixedPitch()), candidatas[-1])
    if tamanho:
        escolhida.setPointSize(tamanho)
    return escolhida
