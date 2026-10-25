"""Exercícios do guia: enunciado, código inicial, gabarito e correção automática por imagem."""
import hashlib, os, re

from .i18n import idioma
from . import plataforma

CENARIO = """#version 3.7;
global_settings {{ assumed_gamma 1.0 }}
#include "colors.inc"

camera {{ location <0, 3.2, -7> look_at <0, 1.3, 0> }}
light_source {{ <4, 8, -6> rgb 1 }}
light_source {{ <-6, 5, -3> rgb 0.3 shadowless }}
background {{ rgb <0.55, 0.7, 0.9> }}
plane {{ y, 0 pigment {{ checker rgb 0.85, rgb 0.6 }} }}
"""

CABECALHO = """// ===== EXERCÍCIO {id}: {titulo} =====
// {enunciado_linha}
// Não mude a câmera nem as luzes: escreva sua resposta embaixo.
// Para conferir: Ajuda > Verificar exercício (Ctrl+Shift+V).
""" + CENARIO + """
// ---------- sua resposta ----------
"""

CABECALHO_EN = """// ===== EXERCISE {id}: {titulo} =====
// {enunciado_linha}
// Do not change the camera or the lights: write your answer below.
// To check it: Help > Check exercise (Ctrl+Shift+V).
""" + CENARIO + """
// ---------- your answer ----------
"""

EXERCICIOS = [
    {"id": "boneco", "titulo": "Boneco de neve",
     "enunciado": "Empilhe três esferas brancas: a base com centro <0, 0.8, 0> e raio 0.8; o meio com "
                  "centro <0, 2, 0> e raio 0.55; a cabeça com centro <0, 2.85, 0> e raio 0.35. "
                  "Coloque um nariz: um cone laranja (Orange) que sai de <0, 2.85, -0.3> com raio 0.08 "
                  "e termina em ponta em <0, 2.85, -0.75>.",
     "dica": "cone { <base>, raio_base, <ponta>, 0 }. A base já está pronta.",
     "inicio": "sphere { <0, 0.8, 0>, 0.8 pigment { color White } }  // base\n",
     "gabarito": """sphere { <0, 0.8, 0>, 0.8 pigment { color White } }
sphere { <0, 2, 0>, 0.55 pigment { color White } }
sphere { <0, 2.85, 0>, 0.35 pigment { color White } }
cone { <0, 2.85, -0.3>, 0.08, <0, 2.85, -0.75>, 0 pigment { color Orange } }
"""},
    {"id": "mesa", "titulo": "Mesa",
     "enunciado": "O tampo já está pronto. Faça as quatro pernas: cilindros marrons (Brown) de raio 0.1, "
                  "do chão (y = 0) até o tampo (y = 1.2), nas posições x = ±1.3 e z = ±0.8.",
     "dica": "cylinder { <x, 0, z>, <x, 1.2, z>, 0.1 }. Dá para usar #for, mas quatro linhas também resolvem.",
     "inicio": "box { <-1.5, 1.2, -1>, <1.5, 1.4, 1> pigment { color Brown } }  // tampo\n",
     "gabarito": """box { <-1.5, 1.2, -1>, <1.5, 1.4, 1> pigment { color Brown } }
cylinder { < 1.3, 0,  0.8>, < 1.3, 1.2,  0.8>, 0.1 pigment { color Brown } }
cylinder { < 1.3, 0, -0.8>, < 1.3, 1.2, -0.8>, 0.1 pigment { color Brown } }
cylinder { <-1.3, 0,  0.8>, <-1.3, 1.2,  0.8>, 0.1 pigment { color Brown } }
cylinder { <-1.3, 0, -0.8>, <-1.3, 1.2, -0.8>, 0.1 pigment { color Brown } }
"""},
    {"id": "porta", "titulo": "Porta na dobradiça",
     "enunciado": "A porta está fechada, com a dobradiça na borda direita (x = 1). Abra a porta girando "
                  "−60° em torno do eixo y, mas em volta da DOBRADIÇA (o ponto <1, 0, 0>), não da origem.",
     "dica": "Leve a dobradiça até a origem (translate), gire (rotate) e traga de volta (translate). "
             "É o T(P)·R·T(−P) da aula.",
     "inicio": "box { <-1, 0, 0>, <1, 2.5, 0.1>\n    pigment { color rgb <0.6, 0.35, 0.2> }\n    // escreva as transformações aqui\n}\n",
     "gabarito": """box { <-1, 0, 0>, <1, 2.5, 0.1>
    pigment { color rgb <0.6, 0.35, 0.2> }
    translate <-1, 0, 0>
    rotate <0, -60, 0>
    translate <1, 0, 0>
}
"""},
    {"id": "furo", "titulo": "Cubo furado",
     "enunciado": "Faça um cubo vermelho de lado 1.6 centrado em <0, 1, 0> com um furo cilíndrico de "
                  "raio 0.4 atravessando de frente para trás (na direção do eixo z).",
     "dica": "difference { box {...} cylinder {...} }. Faça o cilindro mais comprido que o cubo, "
             "senão sobra uma película fina.",
     "inicio": "",
     "gabarito": """difference {
    box { <-0.8, 0.2, -0.8>, <0.8, 1.8, 0.8> }
    cylinder { <0, 1, -1>, <0, 1, 1>, 0.4 }
    pigment { color Red }
}
"""},
    {"id": "anel", "titulo": "Anel com #for",
     "enunciado": "Faça 8 esferas douradas (Gold) de raio 0.3 num círculo de raio 2 em volta do eixo y, "
                  "com os centros em y = 0.3. A primeira fica em <2, 0.3, 0> e as outras a cada 45°.",
     "dica": "#for (i, 0, 7) ... #end com sphere { <2, 0.3, 0>, 0.3 ... rotate <0, i*45, 0> }",
     "inicio": "",
     "gabarito": """#for (i, 0, 7)
    sphere { <2, 0.3, 0>, 0.3 pigment { color Gold } rotate <0, i*45, 0> }
#end
"""},
    {"id": "espelho", "titulo": "Espelhamento",
     "enunciado": "O L azul está do lado direito (x positivo). Faça uma cópia ciano (Cyan) espelhada "
                  "do lado esquerdo, refletindo no plano x = 0.",
     "dica": "object { L ... scale <-1, 1, 1> }. Na aula essa matriz é a M_fx (troca o sinal de x).",
     "inicio": """#declare L = union {
    box { <0.5, 0, 0>, <0.8, 2, 0.3> }
    box { <0.5, 0, 0>, <1.6, 0.3, 0.3> }
}
object { L pigment { color Blue } }
""",
     "gabarito": """#declare L = union {
    box { <0.5, 0, 0>, <0.8, 2, 0.3> }
    box { <0.5, 0, 0>, <1.6, 0.3, 0.3> }
}
object { L pigment { color Blue } }
object { L pigment { color Cyan } scale <-1, 1, 1> }
"""},
    {"id": "ordem", "titulo": "Ordem das transformações",
     "enunciado": "Use a caixa C já declarada duas vezes: uma VERDE girada 45° em y em volta do próprio "
                  "centro e colocada em x = 2; e uma VERMELHA que primeiro vai para x = 2 e depois gira "
                  "45° em y em volta da origem.",
     "dica": "A ordem importa: rotate antes de translate gira no lugar; translate antes de rotate faz orbitar.",
     "inicio": "#declare C = box { <-0.5, 0, -0.5>, <0.5, 1, 0.5> }\n",
     "gabarito": """#declare C = box { <-0.5, 0, -0.5>, <0.5, 1, 0.5> }
object { C pigment { color Green } rotate <0, 45, 0> translate <2, 0, 0> }
object { C pigment { color Red } translate <2, 0, 0> rotate <0, 45, 0> }
"""},
]
POR_ID = {e["id"]: e for e in EXERCICIOS}
RX_ID = re.compile(r"(?:EXERCÍCIO|EXERCISE) (\w+):")

EN = {
    "boneco": {"titulo": "Snowman",
               "enunciado": "Stack three white spheres: the base with center <0, 0.8, 0> and radius 0.8; the "
                            "middle with center <0, 2, 0> and radius 0.55; the head with center <0, 2.85, 0> and "
                            "radius 0.35. Add a nose: an orange cone (Orange) that starts at <0, 2.85, -0.3> "
                            "with radius 0.08 and ends in a point at <0, 2.85, -0.75>.",
               "dica": "cone { <base>, base_radius, <tip>, 0 }. The base is already done.",
               "inicio": "sphere { <0, 0.8, 0>, 0.8 pigment { color White } }  // base\n"},
    "mesa": {"titulo": "Table",
             "enunciado": "The tabletop is already done. Make the four legs: brown cylinders (Brown) with radius "
                          "0.1, from the floor (y = 0) up to the top (y = 1.2), at x = ±1.3 and z = ±0.8.",
             "dica": "cylinder { <x, 0, z>, <x, 1.2, z>, 0.1 }. You can use #for, but four lines also work.",
             "inicio": "box { <-1.5, 1.2, -1>, <1.5, 1.4, 1> pigment { color Brown } }  // tabletop\n"},
    "porta": {"titulo": "Door on its hinge",
              "enunciado": "The door is closed, with the hinge on its right edge (x = 1). Open the door by "
                           "rotating it −60° around the y axis, but around the HINGE (the point <1, 0, 0>), "
                           "not around the origin.",
              "dica": "Move the hinge to the origin (translate), rotate (rotate) and move it back (translate). "
                      "That is T(P)·R·T(−P).",
              "inicio": "box { <-1, 0, 0>, <1, 2.5, 0.1>\n    pigment { color rgb <0.6, 0.35, 0.2> }\n"
                        "    // write the transformations here\n}\n"},
    "furo": {"titulo": "Cube with a hole",
             "enunciado": "Make a red cube with side 1.6 centered at <0, 1, 0> with a cylindrical hole of "
                          "radius 0.4 going through it from front to back (along the z axis).",
             "dica": "difference { box {...} cylinder {...} }. Make the cylinder longer than the cube, "
                     "otherwise a thin film is left."},
    "anel": {"titulo": "Ring with #for",
             "enunciado": "Make 8 golden spheres (Gold) with radius 0.3 on a circle of radius 2 around the y "
                          "axis, with their centers at y = 0.3. The first one is at <2, 0.3, 0> and the others "
                          "every 45°.",
             "dica": "#for (i, 0, 7) ... #end with sphere { <2, 0.3, 0>, 0.3 ... rotate <0, i*45, 0> }"},
    "espelho": {"titulo": "Mirroring",
                "enunciado": "The blue L is on the right side (positive x). Make a cyan copy (Cyan) mirrored "
                             "on the left side, reflecting it across the plane x = 0.",
                "dica": "object { L ... scale <-1, 1, 1> }. This is the reflection matrix that flips the "
                        "sign of x."},
    "ordem": {"titulo": "Order of transformations",
              "enunciado": "Use the declared box C twice: a GREEN one rotated 45° in y around its own center "
                           "and placed at x = 2; and a RED one that first moves to x = 2 and then rotates 45° "
                           "in y around the origin.",
              "dica": "Order matters: rotate before translate spins in place; translate before rotate makes "
                      "it orbit."},
}


def campo(e, k):
    """Campo do exercício (titulo, enunciado, dica, inicio, gabarito) no idioma da interface."""
    if idioma() != "pt":
        return EN[e["id"]].get(k, e[k])
    return e[k]


def cabecalho(e):
    modelo = CABECALHO if idioma() == "pt" else CABECALHO_EN
    return modelo.format(id=e["id"], titulo=campo(e, "titulo"), enunciado_linha="")


def texto_inicial(e):
    enun = "\n".join("// " + l for l in _quebrar(campo(e, "enunciado"), 90))
    return cabecalho(e).replace("// \n", enun + "\n", 1) + campo(e, "inicio")


def texto_gabarito(e):
    return cabecalho(e) + campo(e, "gabarito")


def texto_vazio(e):
    return cabecalho(e)


def id_no_texto(texto):
    m = RX_ID.search(texto[:400])
    return m.group(1) if m and m.group(1) in POR_ID else None


def _quebrar(s, n):
    linhas, atual = [], ""
    for p in s.split():
        if len(atual) + len(p) + 1 > n:
            linhas.append(atual)
            atual = p
        else:
            atual = (atual + " " + p).strip()
    if atual:
        linhas.append(atual)
    return linhas


def pasta_cache():
    d = os.path.join(plataforma.pasta_cache(), "exercicios")
    os.makedirs(d, exist_ok=True)
    return d


def arquivo_cache(texto, w, h):
    chave = hashlib.sha1(f"{w}x{h}\n{texto}".encode()).hexdigest()[:16]
    return os.path.join(pasta_cache(), chave + ".png")


TAMANHO = (320, 240)
ARGS = ["-D", "-V", "+FN", "+Q9", "-A", "+K0"]


def comparar(sua, gabarito, vazio):
    """Recebe três imagens RGB (numpy uint8 HxWx3). Devolve (nota 0..1, imagem de diferença HxWx3).
    Só conta a região onde há objetos em alguma das duas (o fundo igual não infla a nota)."""
    import numpy as np
    a, b, e = (x.astype(np.int16) for x in (sua, gabarito, vazio))
    tem_a = np.abs(a - e).max(axis=2) > 25
    tem_b = np.abs(b - e).max(axis=2) > 25
    regiao = tem_a | tem_b
    igual = np.abs(a - b).max(axis=2) <= 35
    nota = float(igual[regiao].mean()) if regiao.any() else 1.0
    cinza = (b.mean(axis=2, keepdims=True) * 0.35).astype(np.int16).repeat(3, axis=2)
    dif = cinza.copy()
    sobra = regiao & ~igual & tem_a & ~tem_b
    falta = regiao & ~igual & tem_b & ~tem_a
    outro = regiao & ~igual & ~sobra & ~falta
    dif[igual & regiao] = (b[igual & regiao] * 0.6).astype(np.int16)
    dif[sobra] = (255, 60, 60)      # vermelho: tem na sua, não tem no gabarito
    dif[falta] = (60, 120, 255)     # azul: falta na sua
    dif[outro] = (255, 210, 0)      # amarelo: os dois têm algo, mas diferente
    return nota, dif.clip(0, 255).astype(np.uint8)

NOTA_MINIMA = 0.975
