"""Formatar código POV-Ray: reindenta pelas chaves e pelas diretivas #if/#for/#while/#macro ... #end."""
import re

from . import sdl

ABRE_DIRETIVA = re.compile(r"#(if|ifdef|ifndef|while|for|macro|switch)\b")
MEIO_DIRETIVA = re.compile(r"#(else|elseif|case|range)\b")
FECHA_DIRETIVA = re.compile(r"#end\b")


def formatar(texto, tab="    "):
    mascara = sdl.mascarar(texto)
    linhas = texto.split("\n")
    mlinhas = mascara.split("\n")
    saida = []
    nivel = 0
    em_comentario = False
    brancos = 0
    for linha, ml in zip(linhas, mlinhas):
        crua = linha.rstrip().replace("\t", tab)
        conteudo = crua.strip()
        codigo = ml.strip()
        # linhas dentro de /* ... */ ficam como estão (só tira espaço no fim)
        if em_comentario:
            saida.append(crua)
            if "*/" in linha:
                em_comentario = False
            continue
        if not conteudo:
            brancos += 1
            if brancos <= 2:   # no máximo duas linhas em branco seguidas
                saida.append("")
            continue
        brancos = 0
        # quanto esta linha "volta" antes de ser escrita
        recuo = 0
        k = 0
        while k < len(codigo) and codigo[k] == "}":
            recuo += 1
            k += 1
            while k < len(codigo) and codigo[k] == " ":
                k += 1
        if FECHA_DIRETIVA.match(codigo) or MEIO_DIRETIVA.match(codigo):
            recuo += 1
        saida.append(tab * max(0, nivel - recuo) + conteudo)
        # novo nível depois da linha
        nivel += codigo.count("{") - codigo.count("}")
        if ABRE_DIRETIVA.match(codigo):
            nivel += 1
        if FECHA_DIRETIVA.match(codigo):
            nivel -= 1
        nivel = max(0, nivel)
        if "/*" in linha and "*/" not in linha[linha.index("/*"):]:
            em_comentario = True
    while saida and saida[-1] == "":
        saida.pop()
    return "\n".join(saida) + ("\n" if texto.endswith("\n") else "")
