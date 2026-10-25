"""Diferenças entre Linux e Windows: caminhos para o POV-Ray, pastas do app e o autoteste."""
import os, subprocess, sys

from conftest import precisa_povray, RAIZ
from povlive_app import plataforma as PL


def test_argumentos_no_windows_usam_barra_normal(monkeypatch):
    monkeypatch.setattr(PL, "WINDOWS", True)
    a = PL.argumentos([r"+IC:\Users\ana\cena.pov", r"+OC:\Temp\x.png", "+W320", r"+LD:\inc", "-D"],
                      [r"C:\PovLive\povray\share\povray-3.7\include"])
    assert a == ["+IC:/Users/ana/cena.pov", "+OC:/Temp/x.png", "+W320", "+LD:/inc", "-D",
                 "+LC:/PovLive/povray/share/povray-3.7/include"]
    monkeypatch.setattr(PL, "WINDOWS", False)
    assert PL.argumentos(["+O/tmp/a b.png"], []) == ["+O/tmp/a b.png"]


def test_pastas_do_usuario(monkeypatch, tmp_path):
    monkeypatch.setattr(PL, "WINDOWS", True)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert PL.pasta_cache() == os.path.join(str(tmp_path), "povlive", "cache")
    assert PL.pasta_dados() == os.path.join(str(tmp_path), "povlive", "dados")
    monkeypatch.setattr(PL, "WINDOWS", False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "c"))
    assert PL.pasta_cache() == os.path.join(str(tmp_path / "c"), "povlive")


def test_povray_e_includes_por_variavel(monkeypatch, tmp_path):
    monkeypatch.setenv("POVLIVE_POVRAY", "/opt/x/povray")
    monkeypatch.setenv("POVLIVE_INCLUDE", str(tmp_path))
    assert PL.executavel() == "/opt/x/povray" and PL.biblioteca() == [str(tmp_path)]


@precisa_povray
def test_autoteste(tmp_path):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", POVLIVE_AUTOTESTE_LOG=str(tmp_path / "log.txt"))
    r = subprocess.run([sys.executable, os.path.join(RAIZ, "povlive.py"), "--autoteste"], env=env,
                       capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "log.txt").read_text(encoding="utf-8").startswith("autoteste: ok")


def test_relativo(tmp_path):
    assert PL.relativo(str(tmp_path / "a" / "b.inc"), str(tmp_path)) == os.path.join("a", "b.inc")
    assert PL.relativo(str(tmp_path / "x.inc"), str(tmp_path / "a")) is None
    assert PL.relativo(str(tmp_path), str(tmp_path / "a")) is None
