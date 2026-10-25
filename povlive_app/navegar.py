"""Navegar pelo código: ir para a definição de um nome (#declare, #local, #macro) e renomear."""
import re

from . import pov, sdl

RX_NOME = re.compile(r"^[A-Za-z_]\w*$")
RESERVADAS = set(pov.PALAVRAS) | {d.lstrip("#") for d in pov.DIRETIVAS} | {
    "x", "y", "z", "t", "u", "v", "pi", "true", "false", "yes", "no", "on", "off", "clock", "now"}


def definicao(texto, nome):
    """Posição do nome na linha que o define (#declare/#local/#macro), ou None."""
    m = sdl.mascarar(texto)
    d = re.search(r"#\s*(?:declare|local|macro)\s+(" + re.escape(nome) + r")\b", m)
    return d.start(1) if d else None


def achar(texto, pasta, nome, outros=()):
    """Onde está a definição: ("aqui", posição) | (caminho de um .inc, posição) | None.
    outros = [(caminho, texto)] de abas abertas (o texto delas pode não estar salvo)."""
    p = definicao(texto, nome)
    if p is not None:
        return "aqui", p
    abertos = dict(outros)
    vistos = set()
    fila = list(pov.RX_INCLUDE.findall(texto))
    while fila:
        inc = fila.pop(0)
        caminho = pov.achar_include(inc, pasta)
        if not caminho or caminho in vistos:
            continue
        vistos.add(caminho)
        if caminho in abertos:
            t = abertos[caminho]
        else:
            try:
                t = open(caminho, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
        p = definicao(t, nome)
        if p is not None:
            return caminho, p
        fila += pov.RX_INCLUDE.findall(t)       # includes dentro de includes
    return None


def ocorrencias(texto, nome):
    """(início, fim) de cada uso do nome no código (fora de comentários e strings)."""
    m = sdl.mascarar(texto)
    return [(a.start(), a.end()) for a in re.finditer(r"(?<![\w#.])" + re.escape(nome) + r"(?!\w)", m)]


class NomeInvalido(ValueError):
    pass


def validar(novo, texto, nome):
    if not RX_NOME.match(novo):
        raise NomeInvalido("formato")
    if novo in RESERVADAS:
        raise NomeInvalido("reservada")
    if novo != nome and definicao(texto, novo) is not None:
        raise NomeInvalido("existe")


def renomear(texto, nome, novo):
    """(texto novo, quantas trocas). O nome antigo tem que ser definido no próprio arquivo."""
    validar(novo, texto, nome)
    occ = ocorrencias(texto, nome)
    partes, ultimo = [], 0
    for a, b in occ:
        partes += [texto[ultimo:a], novo]
        ultimo = b
    partes.append(texto[ultimo:])
    return "".join(partes), len(occ)
