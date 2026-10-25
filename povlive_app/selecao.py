"""Clicar na imagem e achar o objeto no código.

Truque: renderiza uma cópia da cena em que cada objeto ganha uma cor única e "chapada"
(emission 1, sem luz, sem gama, sem antialiasing). A cor do pixel clicado diz qual
bloco do código gerou aquele ponto da imagem.
"""
import re

from . import sdl

NAO_MARCAR_DENTRO = {"clipped_by", "bounded_by", "contained_by"}
FINAL = "\n// ---- seleção do povlive ----\nglobal_settings { assumed_gamma 1.0 ambient_light 0 }\nbackground { rgb 0 }\n"
ARGS_EXTRA = ["-A", "File_Gamma=1.0"]


def cor_do_id(i):
    return (i % 16) / 15, (i // 16 % 16) / 15, (i // 256 % 16) / 15


def id_da_cor(r, g, b):
    return round(r * 15 / 255) + 16 * round(g * 15 / 255) + 256 * round(b * 15 / 255)


APARENCIA = {"pigment", "texture", "finish", "normal", "material", "interior_texture"}


def marcar(texto):
    """(texto com cores únicas, {id: Bloco}). Os blocos têm as posições do texto ORIGINAL.

    - as aparências originais (pigment, texture...) são apagadas, para não esconder as cores únicas;
    - objetos dentro de um #declare não são marcados: assim, cada uso (object { Nome }) tem a
      própria cor, e clicar numa cópia leva à linha daquela cópia."""
    todos = sdl.blocos(texto)
    chars = list(texto)
    for b in todos:
        if b.kw in APARENCIA and b.fecha is not None:
            for k in range(b.abre + 1, b.fecha):
                if chars[k] != "\n":
                    chars[k] = " "
    base = "".join(chars)

    def em_declare(b):
        while b is not None:
            if b.declarado and b.kw in sdl.OBJETOS:
                return True
            b = b.pai
        return False

    alvos = [b for b in todos if b.kw in sdl.OBJETOS and b.fecha is not None
             and not (b.pai and b.pai.kw in NAO_MARCAR_DENTRO) and not em_declare(b)]
    mapa = {}
    insercoes = []
    for i, b in enumerate(alvos[:4095], 1):
        r, g, bl = cor_do_id(i)
        mapa[i] = b
        insercoes.append((b.fecha, f" texture {{ pigment {{ rgb <{r:.7f}, {g:.7f}, {bl:.7f}> }} "
                                   "finish { emission 1 ambient 0 diffuse 0 specular 0 phong 0 reflection 0 } } "))
    partes, ultimo = [], 0
    for pos, txt in sorted(insercoes):
        partes.append(base[ultimo:pos])
        partes.append(txt)
        ultimo = pos
    partes.append(base[ultimo:])
    return "".join(partes) + FINAL, mapa


def topo(b):
    """O objeto de primeiro nível que contém o bloco (é ele que se move ao arrastar)."""
    while b.pai is not None and b.pai.kw in sdl.OBJETOS:
        b = b.pai
    return b


def caminho(b):
    """Descrição do bloco e dos que o contêm: 'sphere em union em difference'."""
    nomes = []
    while b is not None:
        if b.kw in sdl.OBJETOS:
            nomes.append(b.kw + (f" (#declare {b.declarado})" if b.declarado else ""))
        b = b.pai
    return " dentro de ".join(nomes)


def translate_final(texto, b):
    """Se o bloco termina com 'translate <a, b, c>' literal, devolve (início, fim, (a,b,c)) do vetor."""
    m = sdl.mascarar(texto)
    corpo = m[b.abre + 1:b.fecha]
    mt = re.search(r"\btranslate\s*(<[^<>{}]*>)\s*$", corpo)
    if not mt:
        return None
    try:
        v, _ = sdl.avaliar(mt.group(1))
    except sdl.Desconhecido:
        return None
    if not isinstance(v, tuple):
        return None
    ini = b.abre + 1 + mt.start(1)
    return ini, b.abre + 1 + mt.end(1), v


def inserir_translate(texto, b):
    """Texto com 'translate <0, 0, 0>' no fim do bloco, e (início, fim) do vetor inserido."""
    fecha = b.fecha
    linha_ini = texto.rfind("\n", 0, b.kw_ini) + 1
    indent = re.match(r"[ \t]*", texto[linha_ini:]).group()
    mesma_linha = "\n" not in texto[b.abre:fecha]
    vetor = "<0, 0, 0>"
    if mesma_linha:
        antes = texto[:fecha].rstrip(" ")
        novo = antes + " translate " + vetor + " "
    else:
        antes = texto[:fecha]
        # se o "}" está sozinho na linha, insere numa linha nova antes dele
        ini_linha_fecha = antes.rfind("\n") + 1
        if not antes[ini_linha_fecha:].strip():
            antes = antes[:ini_linha_fecha]
            novo = antes + indent + "    translate " + vetor + "\n" + indent
        else:
            novo = antes.rstrip(" ") + "\n" + indent + "    translate " + vetor + "\n" + indent
    ini_vetor = novo.rfind(vetor)
    return novo + texto[fecha:], (ini_vetor, ini_vetor + len(vetor))
