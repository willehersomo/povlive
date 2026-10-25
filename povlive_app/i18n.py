"""Idioma da interface: português (o original) ou inglês.

Os textos ficam em português no código e passam por tr(); a tradução inglesa está em traducoes_en.py.
Tabelas definidas no carregamento do módulo usam N_() só para marcar o texto e chamam tr() na hora de
mostrar, assim o idioma pode ser escolhido depois do import. Os testes conferem que todo texto marcado
tem tradução.
"""
import os

IDIOMAS = {"pt": "Português", "en": "English"}
_atual = "pt"


def idioma():
    return _atual


def definir(codigo):
    global _atual
    _atual = codigo if codigo in IDIOMAS else "en"


def do_sistema():
    from PyQt5.QtCore import QLocale
    return "pt" if QLocale.system().name().lower().startswith("pt") else "en"


def carregar(cfg=None):
    """Idioma escolhido no menu; na primeira vez, o do sistema. POVLIVE_LANG=pt|en força um idioma."""
    if os.environ.get("POVLIVE_LANG"):
        return definir(os.environ["POVLIVE_LANG"])
    if cfg is None:
        from .plataforma import configuracoes
        cfg = configuracoes()
    definir(cfg.value("idioma", "") or do_sistema())


def instalar_tradutor_qt(app):
    """Botões e diálogos do próprio Qt (Salvar/Descartar, seletor de cor) no idioma escolhido."""
    if _atual != "pt":
        return None
    from PyQt5.QtCore import QLibraryInfo, QTranslator
    t = QTranslator(app)
    if t.load("qtbase_pt_BR", QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
        app.installTranslator(t)
        return t
    return None


def tr(texto):
    if _atual == "pt":
        return texto
    from .traducoes_en import TEXTOS
    return TEXTOS.get(texto, texto)


def N_(texto):
    """Marca um texto para tradução sem traduzir agora (ele passa por tr() quando for mostrado)."""
    return texto


def por_idioma(pt, en):
    """Escolhe entre dois conteúdos inteiros (guia, exercícios, modelos de código)."""
    return pt if _atual == "pt" else en
