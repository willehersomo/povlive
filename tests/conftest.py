"""Configuração comum dos testes: Qt sem janela, HOME temporário e utilidades."""
import os, shutil, subprocess, sys, time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
CENAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cenas")

tem_povray = shutil.which("povray") is not None
precisa_povray = pytest.mark.skipif(not tem_povray, reason="povray não instalado")


@pytest.fixture(autouse=True)
def home_temporario(tmp_path, monkeypatch):
    """Configurações, histórico e cache vão para uma pasta temporária (não mexe no usuário)."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "home" / ".config"))
    (tmp_path / "home").mkdir()
    yield


@pytest.fixture(scope="session")
def qapp():
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def esperar(app, condicao, tempo=20.0):
    """Processa eventos do Qt até a condição ser verdadeira (ou estourar o tempo)."""
    fim = time.time() + tempo
    while time.time() < fim:
        app.processEvents()
        if condicao():
            return True
        time.sleep(0.02)
    return False


def cena(nome, destino):
    """Copia uma cena de exemplo (e os .inc) para uma pasta temporária e devolve o caminho."""
    for f in os.listdir(CENAS):
        shutil.copy(os.path.join(CENAS, f), destino)
    return os.path.join(str(destino), nome)


def renderizar(texto, pasta, w=160, h=120, extra=()):
    """Renderiza um texto com o povray e devolve a imagem (numpy) — para testes de baixo nível."""
    import numpy as np
    from PIL import Image
    fonte = os.path.join(str(pasta), "t.pov")
    saida = os.path.join(str(pasta), "t.png")
    with open(fonte, "w") as f:
        f.write(texto)
    r = subprocess.run(["povray", "+It.pov", "+Ot.png", f"+W{w}", f"+H{h}", "-D", "-V"] + list(extra),
                       cwd=str(pasta), capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    return np.array(Image.open(saida).convert("RGB")), r.stdout + r.stderr
