"""Biblioteca de texturas: catálogo das texturas prontas do POV-Ray, aplicar uma num objeto do código
e gerar as miniaturas (uma esfera com cada textura).

O catálogo vem dos próprios .inc instalados (textures.inc, metals.inc, stones.inc...), então mostra
o que o POV-Ray da máquina realmente tem.
"""
import os, re
from collections import namedtuple

from . import pov, sdl, plataforma
from .i18n import N_

Item = namedtuple("Item", "nome tipo include categoria")   # tipo: texture|material|pigment|finish|color

CATEGORIAS = [
    ("metais", N_("Metais")),
    ("madeiras", N_("Madeiras")),
    ("pedras", N_("Pedras e mármores")),
    ("vidros", N_("Vidros e água")),
    ("ceu", N_("Céu e nuvens")),
    ("outros", N_("Outras")),
    ("acabamentos", N_("Acabamentos (finish)")),
    ("cores", N_("Cores")),
]

# arquivo lido -> (include que o usuário põe na cena, tipos aceitos)
ARQUIVOS = [
    ("textures.inc", "textures.inc", {"texture", "material", "pigment"}),
    ("metals.inc", "metals.inc", {"texture"}),
    ("golds.inc", "golds.inc", {"texture"}),
    ("stones1.inc", "stones.inc", {"texture"}),
    ("stones2.inc", "stones.inc", {"texture"}),
    ("woods.inc", "woods.inc", {"texture"}),
    ("finish.inc", "finish.inc", {"finish"}),
    ("colors.inc", "colors.inc", {"color"}),
]
# includes que precisam de outro antes
DEPENDE = {"stones.inc": ["colors.inc"], "textures.inc": ["colors.inc"], "woods.inc": ["colors.inc"]}

# nomes que não valem como amostra: camadas transparentes de granito, rachaduras (só fazem sentido
# por cima de outra textura), apelidos repetidos de golds.inc e vidros sem interior (os M_ têm)
IGNORAR = re.compile(r"^(T_Grnt\d+a|T_Crack\d+|T\d\d|P_WoodGrain\w*|Glass\d?|\w+_Glass|NB\w+|Glass_Finish"
                     r"|Water|Lightning\d|Starfield|\w*Gradient|Peel)$")
RX_DECL = re.compile(r"#declare\s+([A-Za-z_]\w*)\s*=\s*(texture|material|pigment|finish|color|colour|rgb\w*)\b")


def _categoria(nome, tipo, arquivo):
    if tipo == "finish":
        return "acabamentos"
    if tipo == "color":
        return "cores"
    if tipo == "material" or "Glass" in nome or "Water" in nome:
        return "vidros"
    if arquivo in ("metals.inc", "golds.inc"):
        return "metais"
    if arquivo == "woods.inc" or re.search(r"Wood|Pine|Oak|Rosewood|Sandalwood", nome):
        return "madeiras"
    if arquivo.startswith("stones") or re.search(r"Marble|Agate|Granite|Alabaster|Jade", nome):
        return "pedras"
    if re.search(r"Sky|Cloud|Apocalypse", nome):
        return "ceu"
    if re.search(r"Chrome|Brass|Gold|Silver|Copper|Bronze|Alumin|Metal|Penny|Rust|Iron|Tin", nome):
        return "metais"
    return "outros"


_cache = {}


def catalogo(pastas=None):
    """Lista de Item com as texturas dos .inc padrão (na ordem dos arquivos)."""
    pastas = pov.BIBLIOTECA if pastas is None else pastas
    chave = tuple(pastas)
    if chave in _cache:
        return _cache[chave]
    itens, vistos = [], set()
    for arquivo, include, tipos in ARQUIVOS:
        caminho = next((os.path.join(d, arquivo) for d in pastas if os.path.isfile(os.path.join(d, arquivo))), None)
        if not caminho:
            continue
        texto = sdl.mascarar(open(caminho, encoding="latin-1").read())
        for m in RX_DECL.finditer(texto):
            nome, tipo = m.group(1), m.group(2)
            if tipo in ("colour",) or tipo.startswith("rgb"):
                tipo = "color"
            if tipo not in tipos or nome in vistos or (tipo != "material" and IGNORAR.match(nome)):
                continue
            vistos.add(nome)
            itens.append(Item(nome, tipo, include, _categoria(nome, tipo, arquivo)))
    _cache[chave] = itens
    return itens


def codigo(item):
    """O trecho que vai no objeto: texture { T_Wood1 }, pigment { color Red }..."""
    if item.tipo == "color":
        return f"pigment {{ color {item.nome} }}"
    return f"{item.tipo} {{ {item.nome} }}"


def includes(item):
    return DEPENDE.get(item.include, []) + [item.include]


# ==================================================================== editar o código

APARENCIA = {"texture", "pigment", "finish", "normal", "material"}
RX_TRANSF = re.compile(r"\b(translate|rotate|scale|matrix|transform)\b")


class SemObjeto(Exception):
    pass


def _filhos(b, kws):
    return [f for f in b.filhos if f.kw in kws and f.fecha is not None]


def _apagar(texto, ini, fim):
    """(ini, fim) a apagar, incluindo a linha inteira se ela ficar vazia."""
    li = texto.rfind("\n", 0, ini) + 1
    lf = texto.find("\n", fim)
    lf = len(texto) if lf < 0 else lf
    if not texto[li:ini].strip() and not texto[fim:lf].strip():
        return li, min(len(texto), lf + 1)
    while fim < len(texto) and texto[fim] == " ":
        fim += 1
    return ini, fim


def _posicao_padrao(texto, b, m):
    """Onde pôr a aparência num objeto que não tem nenhuma: antes da primeira transformação do
    próprio objeto (assim a textura acompanha o objeto), ou antes do '}'."""
    dentro = [(f.kw_ini, f.fecha) for f in b.filhos if f.fecha is not None]
    for mt in RX_TRANSF.finditer(m, b.abre + 1, b.fecha):
        if not any(a <= mt.start() <= z for a, z in dentro):
            return mt.start()
    return b.fecha


def _inserir(texto, pos, trecho):
    """Insere o trecho na posição, numa linha própria quando o código ao redor é de várias linhas."""
    li = texto.rfind("\n", 0, pos) + 1
    antes = texto[li:pos]
    if antes.strip():                       # há código antes, na mesma linha
        antes = texto[:pos].rstrip(" ")
        return antes + " " + trecho + " " + texto[pos:].lstrip(" "), len(antes) + 1
    indent = antes
    if texto[pos] == "}":                   # '}' sozinho na linha: entra com um nível a mais
        return texto[:li] + indent + "    " + trecho + "\n" + texto[li:], li + len(indent) + 4
    return texto[:li] + indent + trecho + "\n" + texto[li:], li + len(indent)


def aplicar(texto, pos, item):
    """Aplica o item ao objeto que contém a posição. Devolve (texto novo, posição do trecho inserido).

    - textura/material: troca toda a aparência do objeto (pigment, finish, normal, texture, material);
    - pigmento/cor: troca só o pigment (dentro da texture, se for o caso);
    - acabamento: troca só o finish.
    Também acrescenta o #include necessário."""
    b = sdl.objeto_em(texto, pos, sdl.OBJETOS)
    if b is None or b.fecha is None:
        raise SemObjeto()
    m = sdl.mascarar(texto)
    trecho = codigo(item)
    if item.tipo in ("texture", "material"):
        velhos = _filhos(b, APARENCIA)
    else:
        kw = "finish" if item.tipo == "finish" else "pigment"
        velhos = _filhos(b, {kw})
        if not velhos:
            for t in _filhos(b, {"texture"}):
                velhos = _filhos(t, {kw})
                if velhos:
                    break
                # textura sem esse elemento: entra no fim dela (um nome de textura tem que vir primeiro)
                antes = texto[:t.fecha].rstrip(" ")
                novo = antes + " " + trecho + " " + texto[t.fecha:]
                return _com_includes(novo, len(antes) + 1, item)
    if velhos:
        primeiro = velhos[0]
        partes = [(primeiro.kw_ini, primeiro.fecha + 1, trecho)]
        partes += [(*_apagar(texto, v.kw_ini, v.fecha + 1), "") for v in velhos[1:]]
        novo = texto
        for ini, fim, t in sorted(partes, reverse=True):
            novo = novo[:ini] + t + novo[fim:]
        return _com_includes(novo, primeiro.kw_ini, item)
    novo, onde = _inserir(texto, _posicao_padrao(texto, b, m), trecho)
    return _com_includes(novo, onde, item)


def _com_includes(texto, pos, item):
    for inc in includes(item):
        texto, n = garantir_include(texto, inc)
        if n:
            pos += n
    return texto, pos


RX_INCLUDE_LINHA = re.compile(r'^[ \t]*#include\s+"([^"]+)"[^\n]*\n?', re.M)
RX_VERSION_LINHA = re.compile(r"^[ \t]*#version\b[^\n]*\n?", re.M)


def garantir_include(texto, nome):
    """(texto, quantos caracteres entraram antes do resto) com o #include "nome" presente.
    Entra depois do último #include, ou depois do #version, ou no começo."""
    existentes = list(RX_INCLUDE_LINHA.finditer(texto))
    if any(m.group(1) == nome for m in existentes):
        return texto, 0
    if existentes:
        pos = existentes[-1].end()
    else:
        mv = RX_VERSION_LINHA.search(texto)
        pos = mv.end() if mv else 0
    linha = f'#include "{nome}"\n'
    if pos and texto[pos - 1] != "\n":
        linha = "\n" + linha
    return texto[:pos] + linha + texto[pos:], len(linha)


# ==================================================================== miniaturas

VERSAO_MINIATURA = 2   # mude quando a cena das miniaturas mudar (invalida o cache)
TAMANHO = 96

CENA = """#version 3.7;
global_settings { assumed_gamma 1.0 }
#include "colors.inc"
camera { location <0, 1.2, -3.9> look_at <0, 0.02, 0> right x up y angle 34 }
light_source { <-4, 6, -5> rgb 1.1 }
light_source { <5, 2, -3> rgb 0.35 shadowless }
sky_sphere { pigment { gradient y color_map { [0 rgb <0.75, 0.8, 0.9>] [1 rgb <0.35, 0.45, 0.65>] } } }
plane { y, -1 pigment { checker rgb 0.85 rgb 0.55 scale 0.5 } finish { diffuse 0.8 } }
#switch (frame_number)
"""


def cena_miniaturas(itens):
    """Cena de animação: o quadro k mostra o item k (1..n), com o include dele."""
    partes = [CENA]
    for k, it in enumerate(itens, 1):
        incs = "".join(f'#include "{i}"\n' for i in includes(it) if i != "colors.inc")
        if it.tipo == "finish":
            corpo = f"pigment {{ rgb <0.75, 0.2, 0.15> }} finish {{ {it.nome} }}"
        else:
            corpo = codigo(it)
        partes.append(f"#case ({k})\n{incs}sphere {{ 0, 1 {corpo} }}\n#break\n")
    partes.append("#end\n")
    return "".join(partes)


def pasta_cache():
    return os.path.join(plataforma.pasta_cache(), f"miniaturas{VERSAO_MINIATURA}_{TAMANHO}")


def arquivo_miniatura(item, pasta=None):
    return os.path.join(pasta or pasta_cache(), f"{item.include}-{item.nome}.png")
