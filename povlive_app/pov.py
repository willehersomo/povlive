"""Tudo que é específico do POV-Ray: vocabulário, includes, câmera, eixos, vistas, ajuda e modelos."""
import glob, math, os, re, shutil

from .i18n import N_, tr, idioma

BIBLIOTECA = sorted(glob.glob("/usr/share/povray-3*/include"))[-1:]
# programa do POV-Ray (POVLIVE_POVRAY escolhe outro)
EXECUTAVEL = os.environ.get("POVLIVE_POVRAY") or shutil.which("povray") or "povray"

PALAVRAS = """camera light_source sphere box cylinder cone plane torus disc triangle smooth_triangle
prism lathe sor superellipsoid blob height_field text union difference intersection
merge object pigment finish normal texture interior color colour rgb rgbf rgbt rgbft
translate rotate scale matrix transform location look_at right up direction angle sky
background global_settings ambient ambient_light diffuse specular phong phong_size roughness
reflection refraction ior checker gradient bozo marble wood agate granite image_map
media fog area_light shadowless spotlight point_at radius falloff tightness
open sturm inverse no_shadow hollow photons radiosity assumed_gamma emission brilliance
metallic crand conserve_energy fresnel turbulence octaves omega lambda frequency phase
color_map pigment_map normal_map texture_map bump_map bumps dents ripples waves wrinkles
leopard onion spiral1 spiral2 radial hexagon brick mandel quilted crackle cells
orthographic perspective fisheye panoramic focal_point aperture blur_samples
sky_sphere rainbow fade_distance fade_power looks_like jitter adaptive circular orient
max_trace_level number_of_waves sin cos tan sqrt pow abs min max mod int floor ceil
vlength vnormalize vcross vdot vrotate radians degrees rand seed concat str clock
image_width image_height""".split()

DIRETIVAS = ["#" + d for d in """include declare local macro end if else elseif ifdef ifndef
while for switch case break version default undef debug warning error""".split()]

RX_DECLARE = re.compile(r"#(?:declare|local|macro)\s+([A-Za-z_]\w*)[^\n]*")
RX_INCLUDE = re.compile(r'#include\s+"([^"]+)"')
RX_NUMERO = re.compile(r"(?<![\w.])-?\d*\.?\d+")
NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
RX_VETOR = re.compile(rf"<\s*({NUM})\s*,\s*({NUM})\s*,\s*({NUM})\s*>")
RX_RGB = re.compile(rf"\b(rgb[ft]{{0,2}})\s*(?:<\s*({NUM})\s*,\s*({NUM})\s*,\s*({NUM})|({NUM})(?![\w.]))")

_cache_inc = {}


def achar_include(nome, pasta):
    for d in [pasta] + BIBLIOTECA:
        c = os.path.join(d, nome)
        if os.path.isfile(c):
            return c
    return None


def declaracoes_de_include(caminho):
    """{nome: linha da declaração} de um .inc (com cache por data de modificação)."""
    try:
        mt = os.path.getmtime(caminho)
    except OSError:
        return {}
    if caminho not in _cache_inc or _cache_inc[caminho][0] != mt:
        texto = open(caminho, encoding="latin-1").read()
        _cache_inc[caminho] = (mt, {m.group(1): m.group(0).strip() for m in RX_DECLARE.finditer(texto)})
    return _cache_inc[caminho][1]


def declaracoes(texto, pasta):
    """Nomes declarados no texto e nos includes que ele usa."""
    nomes = {}
    for inc in RX_INCLUDE.findall(texto):
        c = achar_include(inc, pasta)
        if c:
            nomes.update(declaracoes_de_include(c))
    nomes.update({m.group(1): m.group(0).strip() for m in RX_DECLARE.finditer(texto)})
    return nomes


# ---------------------------------------------------------------- vetores

def sub(a, b): return [a[i] - b[i] for i in range(3)]
def soma(a, b): return [a[i] + b[i] for i in range(3)]
def mult(a, k): return [a[i] * k for i in range(3)]
def norma(a): return math.sqrt(sum(x * x for x in a))
def unit(a):
    n = norma(a) or 1
    return [x / n for x in a]
def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def fmt_num(x):
    s = f"{x:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def fmt_vetor(v):
    return "<" + ", ".join(fmt_num(x) for x in v) + ">"


# ---------------------------------------------------------------- câmera

def bloco_camera(texto):
    """(início, fim) do primeiro bloco camera { ... } fora de comentários, ou None."""
    for m in re.finditer(r"\bcamera\s*\{", texto):
        linha = texto[texto.rfind("\n", 0, m.start()) + 1:m.start()]
        if "//" in linha:
            continue
        nivel, i = 1, m.end()
        while i < len(texto) and nivel:
            if texto[i] == "{":
                nivel += 1
            elif texto[i] == "}":
                nivel -= 1
            i += 1
        return m.start(), i
    return None


def ler_camera(texto):
    """Lê location, look_at e angle da câmera da cena (só valores literais)."""
    cam = {"location": [0.0, 0.0, 0.0], "look_at": [0.0, 0.0, 1.0], "angle": None, "achou": False}
    b = bloco_camera(texto)
    if not b:
        cam["location"] = [0.0, 0.0, 0.0]  # padrão do POV-Ray
        return cam
    corpo = texto[b[0]:b[1]]
    for chave in ("location", "look_at"):
        m = re.search(chave + r"\s*" + RX_VETOR.pattern, corpo)
        if m:
            cam[chave] = [float(m.group(i)) for i in (1, 2, 3)]
            cam["achou"] = True
    m = re.search(r"\bangle\s+(" + NUM + ")", corpo)
    if m:
        cam["angle"] = float(m.group(1))
    if norma(sub(cam["look_at"], cam["location"])) < 1e-6:
        cam["look_at"] = soma(cam["location"], [0, 0, 1])
    return cam


def gravar_camera(texto, location, look_at):
    """Troca location/look_at da primeira câmera do texto (ou cria uma câmera)."""
    loc, alvo = fmt_vetor(location), fmt_vetor(look_at)
    b = bloco_camera(texto)
    if not b:
        return f"camera {{\n    location {loc}\n    look_at {alvo}\n}}\n\n" + texto
    corpo = texto[b[0]:b[1]]
    for chave, val in (("location", loc), ("look_at", alvo)):
        rx = re.compile(chave + r"\s*<[^>]*>")
        if rx.search(corpo):
            corpo = rx.sub(lambda _: f"{chave} {val}", corpo, count=1)
        else:
            fim = corpo.rfind("}")
            corpo = corpo[:fim].rstrip() + f"\n    {chave} {val}\n" + corpo[fim:]
    return texto[:b[0]] + corpo + texto[b[1]:]


class Orbita:
    """Câmera livre: gira em volta de um alvo (estilo Blender)."""

    def __init__(self, cam):
        self.angle = cam["angle"]
        self.alvo = list(cam["look_at"])
        off = sub(cam["location"], self.alvo)
        self.dist = max(norma(off), 0.01)
        self.yaw = math.atan2(off[0], -off[2])
        self.pitch = math.asin(max(-1, min(1, off[1] / self.dist)))

    def posicao(self):
        cp = math.cos(self.pitch)
        off = [self.dist * cp * math.sin(self.yaw), self.dist * math.sin(self.pitch),
               -self.dist * cp * math.cos(self.yaw)]
        return soma(self.alvo, off)

    def girar(self, dx, dy):
        self.yaw -= dx * 0.01
        self.pitch = max(-1.55, min(1.55, self.pitch + dy * 0.01))

    def mover(self, dx, dy):
        f = unit(sub(self.alvo, self.posicao()))
        r = unit(cross([0, 1, 0], f))
        u = cross(f, r)
        k = self.dist * 0.0025
        self.alvo = soma(self.alvo, soma(mult(r, -dx * k), mult(u, dy * k)))

    def zoom(self, passos):
        self.dist = max(0.05, self.dist * (0.9 ** passos))

    def estado(self):
        return (self.yaw, self.pitch, self.dist, tuple(self.alvo))

    def fov(self, aspecto):
        """Ângulo horizontal de visão em radianos (o padrão do POV-Ray depende do formato da imagem)."""
        return math.radians(self.angle) if self.angle else 2 * math.atan(aspecto / 2)

    def pov(self):
        ang = f" angle {fmt_num(self.angle)}" if self.angle else ""
        return ("\n\n// ---- câmera livre do povlive ----\n"
                f"camera {{ perspective location {fmt_vetor(self.posicao())} "
                f"look_at {fmt_vetor(self.alvo)} right x*image_width/image_height{ang} }}\n")


VISTAS = [("Frente", (0, 0, -1), "y"), ("Topo", (0, 1, 0), "z"), ("Lado direito", (1, 0, 0), "y")]


def camera_orto(direcao, sky, centro, escala):
    """Câmera ortográfica olhando para o centro; escala = metade da altura visível."""
    loc = soma(centro, mult(list(direcao), 1000))
    return ("\n\n// ---- vista do povlive ----\n"
            f"camera {{ orthographic location {fmt_vetor(loc)} look_at {fmt_vetor(centro)} sky {sky} "
            f"right x*{fmt_num(2 * escala)}*image_width/image_height up y*{fmt_num(2 * escala)} }}\n")


def eixos_pov(L):
    """Eixos X (vermelho), Y (verde) e Z (azul), anexados no fim da cena."""
    r = L * 0.006

    def eixo(v, cor):
        a = fmt_vetor(mult(v, L))
        b = fmt_vetor(mult(v, L + r * 8))
        neg = fmt_vetor(mult(v, -L))
        return (f"  cylinder {{ <0,0,0>, {a}, {fmt_num(r)} pigment {{ rgb {cor} }} }}\n"
                f"  cone {{ {a}, {fmt_num(r * 3)}, {b}, 0 pigment {{ rgb {cor} }} }}\n"
                f"  cylinder {{ <0,0,0>, {neg}, {fmt_num(r * 0.6)} pigment {{ rgb {cor}*0.35 }} }}\n")
    return ("\n\n// ---- eixos do povlive ----\nunion {\n"
            + eixo([1, 0, 0], "<1,0.15,0.15>") + eixo([0, 1, 0], "<0.15,1,0.15>")
            + eixo([0, 0, 1], "<0.25,0.4,1>")
            + "  no_shadow finish { ambient 1 diffuse 0 }\n}\n")


# ---------------------------------------------------------------- ajuda ao passar o mouse

AJUDA = {
    "camera": "camera { location <x,y,z> look_at <x,y,z> [angle graus] }\nDe onde a cena é vista. Só a última câmera da cena vale.",
    "location": "location <x, y, z>\nPosição (da câmera ou da luz).",
    "look_at": "look_at <x, y, z>\nPonto para onde a câmera aponta.",
    "angle": "angle graus\nÂngulo de abertura horizontal da câmera (padrão ≈ 67°).",
    "orthographic": "camera { orthographic ... }\nProjeção paralela: sem perspectiva, tamanhos não diminuem com a distância.",
    "sky": "sky <x,y,z>\nQual direção é 'para cima' para a câmera (padrão y).",
    "light_source": "light_source { <x,y,z> color }\nLuz pontual. Extras: spotlight, area_light, shadowless.",
    "area_light": "area_light <eixo1>, <eixo2>, n1, n2\nLuz com área: gera sombras suaves. Use com jitter/adaptive.",
    "spotlight": "spotlight point_at <x,y,z> radius r falloff f\nLuz em cone (lanterna).",
    "sphere": "sphere { <centro>, raio }\nEsfera.",
    "box": "box { <canto1>, <canto2> }\nCaixa alinhada aos eixos, definida por dois cantos opostos.",
    "cylinder": "cylinder { <base>, <topo>, raio [open] }\nCilindro entre dois pontos.",
    "cone": "cone { <base>, raio_base, <topo>, raio_topo [open] }\nCone ou tronco de cone.",
    "torus": "torus { raio_maior, raio_menor }\nRosca deitada no plano XZ, centrada na origem.",
    "plane": "plane { <normal>, distância }\nPlano infinito. Ex.: plane { y, 0 } é o chão.",
    "disc": "disc { <centro>, <normal>, raio [, raio_furo] }\nDisco fino.",
    "triangle": "triangle { <p1>, <p2>, <p3> }",
    "prism": "prism { linear_sweep y1, y2, n, <p1>, ..., <pn> }\nExtrusão de um polígono 2D ao longo de Y.",
    "lathe": "lathe { linear_spline n, <p1>, ..., <pn> }\nSólido de revolução em torno de Y.",
    "text": 'text { ttf "fonte.ttf" "texto" espessura, <deslocamento> }',
    "union": "union { obj1 obj2 ... }\nJunta objetos (as partes internas continuam existindo).",
    "merge": "merge { obj1 obj2 ... }\nComo union, mas remove as superfícies internas (melhor para transparentes).",
    "difference": "difference { A B C ... }\nA menos B, menos C... (CSG).",
    "intersection": "intersection { A B ... }\nSó a parte comum a todos (CSG).",
    "object": "object { Nome [transformações] [textura] }\nUsa um objeto declarado com #declare.",
    "translate": "translate <dx, dy, dz>\nMove o objeto.",
    "rotate": "rotate <ax, ay, az>\nGira em graus em torno de X, depois Y, depois Z (eixos do mundo, a partir da origem).\nNo POV-Ray (mão esquerda) o sentido positivo é horário olhando da ponta do eixo para a origem.",
    "scale": "scale <sx, sy, sz> ou scale s\nRedimensiona a partir da origem. Valor negativo espelha.",
    "matrix": "matrix < a,b,c, d,e,f, g,h,i, tx,ty,tz >\nTransformação afim 4x3 (as 3 linhas da matriz + translação).",
    "transform": "transform { ... } ou transform Nome\nAgrupa transformações.",
    "pigment": "pigment { color ... | padrão color_map {...} }\nCor/padrão da superfície.",
    "texture": "texture { pigment {...} normal {...} finish {...} }",
    "finish": "finish { ambient a diffuse d specular s phong p reflection r ... }\nComo a superfície reage à luz.",
    "normal": "normal { bumps 0.5 scale 0.1 }\nPerturba a normal (relevo falso).",
    "interior": "interior { ior 1.5 }\nPropriedades internas (índice de refração, media).",
    "rgb": "rgb <r, g, b> (0 a 1)\nCor. rgbf/rgbt acrescentam filter/transmit (transparência).",
    "rgbf": "rgbf <r, g, b, filter>\nfilter: transparência que tinge a luz.",
    "rgbt": "rgbt <r, g, b, transmit>\ntransmit: transparência que não tinge.",
    "ambient": "ambient valor\nLuz própria mínima da superfície (padrão 0.1).",
    "diffuse": "diffuse valor\nQuanto da luz direta é espalhada (padrão 0.6).",
    "specular": "specular valor [roughness r]\nBrilho especular.",
    "phong": "phong valor [phong_size n]\nBrilho tipo plástico.",
    "reflection": "reflection valor\nEspelhamento (0 a 1).",
    "ior": "ior valor\nÍndice de refração: 1.0 ar, 1.33 água, 1.5 vidro, 2.4 diamante.",
    "checker": "checker cor1, cor2\nPadrão xadrez com quadrados de 1 unidade.",
    "gradient": "gradient <direção> color_map {...}\nDegradê ao longo de uma direção.",
    "color_map": "color_map { [0 cor1] [0.5 cor2] [1 cor3] }",
    "background": "background { color }\nCor de fundo onde nenhum raio acerta nada.",
    "global_settings": "global_settings { assumed_gamma 1.0 ambient_light ... max_trace_level ... }",
    "assumed_gamma": "assumed_gamma 1.0\nRecomendado no POV-Ray 3.7 para cores corretas.",
    "no_shadow": "no_shadow\nO objeto não projeta sombra.",
    "hollow": "hollow\nObjeto oco (necessário para media dentro dele).",
    "clock": "clock\nVariável de animação: vai de 0 a 1 (barra do clock no app).",
    "image_width": "image_width\nLargura da imagem em pixels.",
    "image_height": "image_height\nAltura da imagem em pixels.",
    "#declare": "#declare Nome = valor;\nCria uma variável/objeto global. Use object { Nome } para reutilizar.",
    "#local": "#local Nome = valor;\nVariável local (dentro de macro/arquivo).",
    "#include": '#include "arquivo.inc"\nInclui outro arquivo (colors.inc, textures.inc, ...).',
    "#macro": "#macro Nome(param1, param2) ... #end\nFunção reutilizável.",
    "#for": "#for (i, inicio, fim [, passo]) ... #end",
    "#while": "#while (condição) ... #end",
    "#if": "#if (condição) ... #else ... #end",
    "#version": "#version 3.7;\nVersão da linguagem usada pela cena.",
}

# ---------------------------------------------------------------- modelos (menu Inserir)
# "|" marca onde o cursor fica depois de inserir

MODELOS = [
    (N_("Cena básica"), """#version 3.7;
global_settings { assumed_gamma 1.0 }
#include "colors.inc"

camera {
    location <0, 2, -5>
    look_at <0, 0.5, 0>
}

light_source { <5, 10, -5> rgb 1 }
background { rgb <0.3, 0.4, 0.6> }

plane { y, 0 pigment { checker White Gray70 } }

|"""),
    None,
    (N_("Câmera"), "camera {\n    location <0, 2, -5>\n    look_at <0, 0, 0>\n    |\n}\n"),
    (N_("Câmera ortográfica"), "camera {\n    orthographic\n    location <0, 0, -10>\n    look_at <0, 0, 0>\n    right x*8*image_width/image_height\n    up y*8\n}\n|"),
    (N_("Luz pontual"), "light_source { <5, 10, -5> rgb 1 }\n|"),
    (N_("Luz de área (sombra suave)"), "light_source {\n    <5, 10, -5> rgb 1\n    area_light <2, 0, 0>, <0, 0, 2>, 5, 5\n    adaptive 1 jitter\n}\n|"),
    (N_("Spotlight"), "light_source {\n    <0, 5, 0> rgb 1\n    spotlight\n    point_at <0, 0, 0>\n    radius 15 falloff 25\n}\n|"),
    None,
    (N_("Esfera"), "sphere {\n    <0, 1, 0>, 1\n    pigment { color Red }|\n}\n"),
    (N_("Caixa"), "box {\n    <-1, 0, -1>, <1, 2, 1>\n    pigment { color Blue }|\n}\n"),
    (N_("Cilindro"), "cylinder {\n    <0, 0, 0>, <0, 2, 0>, 0.5\n    pigment { color Green }|\n}\n"),
    (N_("Cone"), "cone {\n    <0, 0, 0>, 1, <0, 2, 0>, 0\n    pigment { color Yellow }|\n}\n"),
    (N_("Toro"), "torus {\n    1, 0.25\n    pigment { color Orange }|\n}\n"),
    (N_("Plano (chão)"), "plane { y, 0 pigment { checker White Gray70 } }\n|"),
    (N_("Prisma"), "prism {\n    linear_sweep 0, 1, 4,\n    <-1, -1>, <1, -1>, <0, 1>, <-1, -1>\n    pigment { color Cyan }|\n}\n"),
    (N_("Texto 3D"), 'text {\n    ttf "timrom.ttf" "Olá" 0.2, 0\n    pigment { color White }|\n}\n'),
    None,
    (N_("União"), "union {\n    |\n}\n"),
    (N_("Diferença (A − B)"), "difference {\n    box { <-1, 0, -1>, <1, 2, 1> }\n    sphere { <0, 2, 0>, 1.2 }\n    pigment { color Red }|\n}\n"),
    (N_("Interseção"), "intersection {\n    box { <-1, -1, -1>, <1, 1, 1> }\n    sphere { <0, 0, 0>, 1.35 }\n    pigment { color Blue }|\n}\n"),
    None,
    (N_("Textura completa"), "texture {\n    pigment { color rgb <0.8, 0.2, 0.2> }\n    normal { bumps 0.3 scale 0.1 }\n    finish { ambient 0.1 diffuse 0.7 phong 0.6 reflection 0.1 }\n}|"),
    (N_("Vidro"), "pigment { rgbf <1, 1, 1, 0.95> }\nfinish { specular 0.6 reflection 0.1 }\ninterior { ior 1.5 }|"),
    (N_("Metal"), "pigment { color rgb <0.8, 0.8, 0.85> }\nfinish { metallic ambient 0 diffuse 0.3 specular 0.8 roughness 0.01 reflection 0.6 }|"),
    None,
    ("#declare", "#declare Nome = |;\n"),
    (N_("Laço #for"), "#for (i, 0, 9)\n    sphere { <i, 0.5, 0>, 0.4 pigment { color rgb <i/9, 0.3, 1 - i/9> } }\n#end\n|"),
    ("#macro", "#macro Nome(param)\n    |\n#end\n"),
    (N_("Animação (gira com o clock)"), "rotate <0, clock*360, 0>|"),
]


def modelos():
    """Modelos do menu Inserir no idioma da interface."""
    if idioma() == "pt":
        return MODELOS
    from .traducoes_en import CODIGO_MODELOS
    return [None if m is None else (tr(m[0]), CODIGO_MODELOS.get(m[0], m[1])) for m in MODELOS]


def ajuda(palavra):
    """Ajuda da sintaxe (ao passar o mouse) no idioma da interface, ou None."""
    if idioma() != "pt":
        from .traducoes_en import AJUDA as AJUDA_EN
        return AJUDA_EN.get(palavra)
    return AJUDA.get(palavra)
