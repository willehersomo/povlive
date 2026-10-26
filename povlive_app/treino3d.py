"""Treino 3D para a prova (cálculo à mão), em três modos, na notação da aula (CGRA):

- transformações 3D: matrizes 4×4, ponto em coluna [x y z 1]ᵀ, última transformação à esquerda
  (M = Mn···M1). M_rx, M_ry, M_rz giram no sentido HORÁRIO (a extensão do M_r 2D: M_rz é o M_r do
  plano xy); M_rahx, M_rahy, M_rahz são as anti-horárias, que são o rotate do POV-Ray. M_fx troca o
  sinal de x (idem y, z).
- câmera e projeção: a câmera do POV-Ray (location, look_at, céu = y). Matriz de visão V leva o mundo
  para a câmera (x = right, y = up, z = para onde a câmera olha); depois a projeção perspectiva no
  plano a d = |direction| (x' = d·x/z) ou ortográfica, e o pixel da imagem.
- iluminação: o modelo de Phong como o POV-Ray calcula (ambient, diffuse, phong, phong_size).

As contas são conferidas contra o próprio POV-Ray nos testes (vtransform, posição do pixel e cor).
"""
import math, random

import numpy as np

from .i18n import idioma
from .treino2d import EntradaInvalida, fmt, igual, ler_numero, limpar, matriz_html  # noqa: F401

NIVEIS = {"facil": (1, 2), "medio": (2, 3), "dificil": (3, 4)}
ANGULOS = [30, 45, 60, 90, 120, 135, 180, 270]
EIXOS = "xyz"


def _pt():
    return idioma() == "pt"


def _v(p):
    return "(" + ", ".join(fmt(c) for c in p) + ")"


def _pov(p):
    return "<" + ", ".join(fmt(c) for c in p) + ">"


# ================================================================ matrizes 4×4

def M_t(tx, ty, tz):
    m = np.eye(4)
    m[:3, 3] = (tx, ty, tz)
    return m


def M_s(sx, sy, sz):
    return np.diag([sx, sy, sz, 1.0])


def M_rah(eixo, graus):
    """Rotação anti-horária (mão direita) em torno do eixo: os mesmos números do rotate do POV-Ray."""
    c, s = math.cos(math.radians(graus)), math.sin(math.radians(graus))
    m = np.eye(4)
    if eixo == "x":      # y -> z
        m[1, 1], m[1, 2], m[2, 1], m[2, 2] = c, -s, s, c
    elif eixo == "y":    # z -> x
        m[0, 0], m[0, 2], m[2, 0], m[2, 2] = c, s, -s, c
    else:                # x -> y
        m[0, 0], m[0, 1], m[1, 0], m[1, 1] = c, -s, s, c
    return m


def M_r(eixo, graus):
    """Rotação HORÁRIA (convenção da aula): a transposta da anti-horária. M_r('z') é o M_r do 2D."""
    return M_rah(eixo, -graus)


def M_f(eixo):
    m = np.eye(4)
    m[EIXOS.index(eixo), EIXOS.index(eixo)] = -1.0
    return m


# ================================================================ modo 1: transformações 3D

FIGURAS = [
    [("A", (1, 1, 0)), ("B", (2, 1, 0)), ("C", (2, 2, 0)), ("D", (1, 1, 2))],
    [("A", (0, 0, 0)), ("B", (2, 0, 0)), ("C", (0, 2, 0)), ("D", (0, 0, 2))],
    [("A", (1, 0, 1)), ("B", (3, 0, 1)), ("C", (1, 2, 1)), ("D", (1, 0, 3))],
    [("A", (0, 1, 0)), ("B", (1, 1, 0)), ("C", (0, 1, 1)), ("D", (0, 3, 0))],
    [("A", (1, 1, 1)), ("B", (2, 1, 1)), ("C", (1, 2, 1)), ("D", (1, 1, 2))],
]
ARESTAS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]      # as figuras são tetraedros


def matrizes_da_op(op):
    """Lista de (nome, matriz) da operação, na ordem em que são aplicadas."""
    tipo = op[0]
    if tipo == "T":
        return [(f"M_t({fmt(op[1])}, {fmt(op[2])}, {fmt(op[3])})", M_t(*op[1:4]))]
    if tipo == "S":
        return [(f"M_s({fmt(op[1])}, {fmt(op[2])}, {fmt(op[3])})", M_s(*op[1:4]))]
    if tipo == "R":
        return [(f"M_r{op[1]}({fmt(op[2])}°)", M_r(op[1], op[2]))]
    if tipo == "Rah":
        return [(f"M_rah{op[1]}({fmt(op[2])}°)", M_rah(op[1], op[2]))]
    if tipo == "F":
        return [(f"M_f{op[1]}", M_f(op[1]))]
    if tipo == "Rp":
        _, e, g, *p = op
        return [(f"M_t({fmt(-p[0])}, {fmt(-p[1])}, {fmt(-p[2])})", M_t(*(-c for c in p))),
                (f"M_r{e}({fmt(g)}°)", M_r(e, g)),
                (f"M_t({fmt(p[0])}, {fmt(p[1])}, {fmt(p[2])})", M_t(*p))]
    if tipo == "Sp":
        _, sx, sy, sz, *p = op
        return [(f"M_t({fmt(-p[0])}, {fmt(-p[1])}, {fmt(-p[2])})", M_t(*(-c for c in p))),
                (f"M_s({fmt(sx)}, {fmt(sy)}, {fmt(sz)})", M_s(sx, sy, sz)),
                (f"M_t({fmt(p[0])}, {fmt(p[1])}, {fmt(p[2])})", M_t(*p))]
    raise ValueError(tipo)


def pov_da_op(op):
    """A mesma operação escrita em SDL do POV-Ray (o rotate do POV-Ray é a anti-horária)."""
    tipo = op[0]

    def rot(e, g):
        v = [0, 0, 0]
        v[EIXOS.index(e)] = g
        return f"rotate {_pov(v)}"
    if tipo == "T":
        return f"translate {_pov(op[1:4])}"
    if tipo == "S":
        return f"scale {_pov(op[1:4])}"
    if tipo == "R":
        return rot(op[1], -op[2])
    if tipo == "Rah":
        return rot(op[1], op[2])
    if tipo == "F":
        v = [1, 1, 1]
        v[EIXOS.index(op[1])] = -1
        return f"scale {_pov(v)}"
    if tipo == "Rp":
        _, e, g, *p = op
        return f"translate {_pov([-c for c in p])} {rot(e, -g)} translate {_pov(p)}"
    if tipo == "Sp":
        _, sx, sy, sz, *p = op
        return f"translate {_pov([-c for c in p])} scale {_pov((sx, sy, sz))} translate {_pov(p)}"
    raise ValueError(tipo)


def descrever(op):
    pt = _pt()
    tipo = op[0]
    if tipo == "T":
        return f"translação de {_v(op[1:4])}" if pt else f"translation by {_v(op[1:4])}"
    if tipo == "S":
        return (f"escala de {_v(op[1:4])} em relação à origem" if pt else
                f"scale by {_v(op[1:4])} about the origin")
    if tipo == "R":
        return (f"rotação de {fmt(op[2])}° em torno do eixo {op[1]}, sentido horário (M_r{op[1]})" if pt else
                f"rotation by {fmt(op[2])}° about the {op[1]} axis, clockwise (M_r{op[1]})")
    if tipo == "Rah":
        return (f"rotação de {fmt(op[2])}° em torno do eixo {op[1]}, sentido anti-horário (M_rah{op[1]})" if pt
                else f"rotation by {fmt(op[2])}° about the {op[1]} axis, counterclockwise (M_rah{op[1]})")
    if tipo == "F":
        return (f"reflexão M_f{op[1]} (troca o sinal de {op[1]})" if pt else
                f"reflection M_f{op[1]} (flips the sign of {op[1]})")
    if tipo == "Rp":
        _, e, g, *p = op
        return (f"rotação de {fmt(g)}° no sentido horário em torno da reta paralela ao eixo {e} que passa por "
                f"{_v(p)}" if pt else
                f"rotation by {fmt(g)}° clockwise about the line parallel to the {e} axis through {_v(p)}")
    if tipo == "Sp":
        _, sx, sy, sz, *p = op
        return (f"escala de {_v((sx, sy, sz))} em relação ao ponto {_v(p)}" if pt else
                f"scale by {_v((sx, sy, sz))} about the point {_v(p)}")
    raise ValueError(tipo)


def _secao(titulo, valores, rotulos=None, colunas=None, tol=None):
    """Um grupo de campos da resposta: linhas de números (com rótulos) e a tolerância da correção."""
    return {"titulo": titulo, "valores": [list(map(float, linha)) for linha in valores],
            "rotulos": rotulos or [""] * len(valores), "colunas": colunas, "tol": tol}


def _figura(pontos, nomes, arestas, cor, tracejado=False, linha=""):
    prims = [("linha", pontos[a], pontos[b], cor, tracejado) for a, b in arestas]
    prims += [("ponto", p, cor, n + linha) for p, n in zip(pontos, nomes)]
    return prims


def _linhas_completas(aluno_secao, n):
    """As linhas da resposta do aluno, se todas estiverem preenchidas com números."""
    if aluno_secao is None or len(aluno_secao) < n or any(v is None for linha in aluno_secao[:n] for v in linha):
        return None
    return [tuple(linha) for linha in aluno_secao[:n]]


class QuestaoTransformacao:
    modo = "transformacoes"

    def __init__(self, numero, nivel="medio"):
        self.numero, self.nivel = numero, nivel
        r = random.Random(f"3d-{nivel}-{numero}")
        self.figura = r.choice(FIGURAS)
        n = r.randint(*NIVEIS[nivel])
        tipos = ["T", "S", "R", "Rah", "F"] + (["Rp", "Sp"] if nivel == "dificil" else [])
        angulos = ANGULOS if nivel == "dificil" else [90, 180, 270, 30, 45, 60]
        self.ops = []
        for _ in range(n):
            t = r.choice(tipos)
            if t == "T":
                op = ("T", r.choice([-3, -2, -1, 1, 2, 3]), r.choice([-2, -1, 0, 1, 2]), r.choice([-2, -1, 0, 1, 2]))
            elif t == "S":
                op = ("S", r.choice([0.5, 2, 3]), r.choice([0.5, 1, 2]), r.choice([0.5, 1, 2]))
            elif t in ("R", "Rah"):
                op = (t, r.choice(EIXOS), r.choice(angulos))
            elif t == "F":
                op = ("F", r.choice(EIXOS))
                if self.ops and self.ops[-1] == op:          # duas reflexões iguais seguidas se anulam
                    op = ("T", r.choice([-2, -1, 1, 2]), 0, r.choice([-1, 1]))
            elif t == "Rp":
                op = ("Rp", r.choice(EIXOS), r.choice([90, 180, 45, 60]), *r.choice(self.figura)[1])
            else:
                op = ("Sp", r.choice([2, 0.5]), r.choice([2, 0.5, 1]), r.choice([1, 2]), *r.choice(self.figura)[1])
            self.ops.append(op)

    def passos(self):
        return [p for op in self.ops for p in matrizes_da_op(op)]

    def matriz(self):
        M = np.eye(4)
        for _n, A in self.passos():
            M = A @ M                       # a última aplicada fica à esquerda
        return limpar(M)

    def pontos(self):
        M = self.matriz()
        return [(n, tuple(limpar(M @ np.array([*p, 1.0]))[:3])) for n, p in self.figura]

    def respostas(self):
        pt = _pt()
        return [_secao("M =", self.matriz()),
                _secao("Pontos transformados" if pt else "Transformed points", [p for _, p in self.pontos()],
                       [n + "' =" for n, _ in self.figura], ["x", "y", "z"])]

    def enunciado(self):
        pt = _pt()
        figura = ", ".join(f"{n}{_v(p)}" for n, p in self.figura)
        passos = "".join(f"<li>{descrever(op)}</li>" for op in self.ops)
        if pt:
            return (f"<p>Aplique ao tetraedro <b>{figura}</b>, nesta ordem:</p><ol>{passos}</ol>"
                    "<p>Calcule a matriz final <b>M</b> (4×4, ponto em coluna) e os pontos transformados.</p>")
        return (f"<p>Apply to the tetrahedron <b>{figura}</b>, in this order:</p><ol>{passos}</ol>"
                "<p>Compute the final matrix <b>M</b> (4×4, column points) and the transformed points.</p>")

    def solucao_html(self):
        pt = _pt()
        passos = self.passos()
        partes = [f"<h3>{'Solução' if pt else 'Solution'}</h3>"]
        for k, (nome, A) in enumerate(passos, 1):
            partes.append(f"<p><b>M{k} = {nome}</b></p>" + matriz_html(A))
        ordem = "·".join(f"M{k}" for k in range(len(passos), 0, -1))
        partes.append(f"<p><b>M = {ordem}</b> " + ("(a última transformação fica à esquerda)" if pt else
                                                     "(the last transformation is on the left)") + "</p>")
        partes.append(matriz_html(self.matriz()))
        partes.append("<p><b>" + ("Pontos" if pt else "Points") + "</b> (M · [x y z 1]ᵀ):</p><ul>")
        for (n, p), (_, q) in zip(self.figura, self.pontos()):
            partes.append(f"<li>{n}{_v(p)} → {n}'{_v(q)}</li>")
        partes.append("</ul>")
        codigo = " ".join(pov_da_op(op) for op in self.ops)
        partes.append("<p>" + ("No POV-Ray, a mesma sequência é:" if pt else "In POV-Ray, the same sequence is:")
                      + f"<br><code>{codigo}</code></p>")
        if any(op[0] in ("R", "Rah", "Rp") for op in self.ops):
            partes.append("<p style='color:#999'>" + (
                "Lembrete: M_rx, M_ry e M_rz são horárias (como o M_r da aula); as anti-horárias, M_rahx, M_rahy "
                "e M_rahz, são o rotate do POV-Ray. Por isso M_rz(θ) vira rotate &lt;0, 0, −θ&gt;."
                if pt else "Reminder: M_rx, M_ry and M_rz are clockwise (like the course's M_r); the "
                           "counterclockwise ones, M_rahx, M_rahy and M_rahz, are POV-Ray's rotate. That is why "
                           "M_rz(θ) becomes rotate &lt;0, 0, −θ&gt;.") + "</p>")
        return "".join(partes)

    def desenho(self, aluno, mostrar_certa):
        nomes = [n for n, _ in self.figura]
        cena = _figura([p for _, p in self.figura], nomes, ARESTAS, "#5aa9ff")
        pts = _linhas_completas(aluno[1] if len(aluno) > 1 else None, len(nomes))
        if pts:
            cena += _figura(pts, nomes, ARESTAS, "#ffb347", linha="'")
        if mostrar_certa:
            cena += _figura([p for _, p in self.pontos()], nomes, ARESTAS, "#6fdc8c", True, "'")
        return {"cena": cena, "tela": None}

    def pov_cena(self):
        pt = _pt()
        pontos = [p for _, p in self.figura]
        corpo = "\n".join(
            f"  cylinder {{ {_pov(pontos[a])}, {_pov(pontos[b])}, 0.04 }}" for a, b in ARESTAS) + "\n" + "\n".join(
            f"  sphere {{ {_pov(p)}, 0.08 }}" for p in pontos)
        cab = ("// Treino 3D, questão {} ({}): azul = figura original, verde = depois das transformações"
               if pt else "// 3D practice, question {} ({}): blue = original figure, green = after the transformations")
        return f"""{cab.format(self.numero, self.nivel)}
#version 3.7;
global_settings {{ assumed_gamma 1 }}
camera {{ location <6, 7, -10> look_at <0, 0.5, 0> angle 60 }}
light_source {{ <10, 20, -15> rgb 1 }}
background {{ rgb 0.12 }}
plane {{ y, -0.01 pigment {{ checker rgb 0.3 rgb 0.35 }} }}
// eixos: x vermelho, y verde, z azul
cylinder {{ 0, x*5, 0.02 pigment {{ rgb <1, 0.2, 0.2> }} }}
cylinder {{ 0, y*5, 0.02 pigment {{ rgb <0.2, 1, 0.2> }} }}
cylinder {{ 0, z*5, 0.02 pigment {{ rgb <0.3, 0.5, 1> }} }}
#declare Figura = union {{
{corpo}
}}
object {{ Figura pigment {{ rgb <0.35, 0.65, 1> }} }}
object {{ Figura
  {" ".join(pov_da_op(op) for op in self.ops)}
  pigment {{ rgb <0.4, 0.86, 0.55> }}
}}
"""


# ================================================================ modo 2: câmera e projeção

W, H = 400, 300                      # imagem da questão (4:3)
PERSP_RIGHT, PERSP_UP = 4 / 3, 1.0   # padrão do POV-Ray: right x*4/3, up y
ORTO_RIGHT, ORTO_UP = 8.0, 6.0       # câmera ortográfica: a vista cobre 8 × 6 unidades

OLHOS = {
    "facil": [(0, 0, -5), (0, 0, -4), (5, 0, 0), (-5, 0, 0), (0, 0, 6), (4, 0, 0), (-4, 0, 0)],
    "medio": [(4, 0, -4), (-4, 0, -4), (3, 0, -4), (-3, 0, -4), (4, 0, -3), (-4, 0, 3), (5, 0, 5), (4, 0, 3)],
    "dificil": [(0, 3, -4), (0, 4, -3), (3, 4, 0), (-3, 4, 0), (0, 3, 4), (4, 3, 0), (0, -3, -4), (4, 4, -2)],
}
DESLOCAMENTOS = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 1, 1), (-1, 1, 0), (1, -1, 1),
                 (2, 1, 0), (0, 2, 1), (-1, 0, -1), (1, 2, -1), (-2, 1, 1), (2, 0, 2)]


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def base_da_camera(olho, alvo, ceu=(0, 1, 0)):
    """(u, v, w) como o look_at do POV-Ray: w = direção, u = céu × w (right), v = w × u (up)."""
    w = _unit(np.subtract(alvo, olho))
    u = _unit(np.cross(ceu, w))
    v = np.cross(w, u)
    return limpar(u), limpar(v), limpar(w)


def matriz_de_visao(olho, alvo, ceu=(0, 1, 0)):
    u, v, w = base_da_camera(olho, alvo, ceu)
    R = np.eye(4)
    R[0, :3], R[1, :3], R[2, :3] = u, v, w
    return limpar(R @ M_t(*(-c for c in olho)))


def matriz_perspectiva(d):
    """Projeção perspectiva no plano z = d (ponto em coluna): [x y z 1] -> [x y z z/d]."""
    m = np.eye(4)
    m[3] = (0, 0, 1 / d, 0)
    return m


class QuestaoCamera:
    modo = "camera"

    def __init__(self, numero, nivel="medio"):
        self.numero, self.nivel = numero, nivel
        r = random.Random(f"cam-{nivel}-{numero}")
        deslocar = nivel != "facil" and r.random() < 0.5
        self.alvo = tuple(r.choice([(1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (-1, 0, 1)])) if deslocar \
            else (0, 0, 0)
        d_olho = r.choice(OLHOS[nivel])
        self.olho = tuple(a + b for a, b in zip(self.alvo, d_olho))
        self.tipo = "persp" if nivel == "dificil" else r.choice(["persp", "orto"])
        self.d = r.choice([1, 2]) if nivel == "dificil" else 1
        self.com_pixel = nivel == "dificil"
        self.right, self.up = (PERSP_RIGHT, PERSP_UP) if self.tipo == "persp" else (ORTO_RIGHT, ORTO_UP)
        V = matriz_de_visao(self.olho, self.alvo)
        candidatos = DESLOCAMENTOS[:]
        r.shuffle(candidatos)
        k = 3 if nivel == "dificil" else 2
        escolhidos = []
        for dlc in candidatos:
            p = tuple(a + b for a, b in zip(self.alvo, dlc))
            c = V @ np.array([*p, 1.0])
            if c[2] < 1:
                continue
            x, y = self._projetar(c[:3])
            if abs(x) <= 0.47 * self.right and abs(y) <= 0.46 * self.up and p not in escolhidos:
                escolhidos.append(p)
            if len(escolhidos) == k:
                break
        if len(escolhidos) < k and self.alvo not in escolhidos:
            escolhidos.append(self.alvo)
        self.pontos_mundo = [("ABC"[i], p) for i, p in enumerate(escolhidos)]

    def _projetar(self, c):
        if self.tipo == "orto":
            return c[0], c[1]
        return self.d * c[0] / c[2], self.d * c[1] / c[2]

    def visao(self):
        return matriz_de_visao(self.olho, self.alvo)

    def na_camera(self):
        V = self.visao()
        return [(n, tuple(limpar(V @ np.array([*p, 1.0]))[:3])) for n, p in self.pontos_mundo]

    def projetados(self):
        return [(n, tuple(limpar(np.array(self._projetar(c))))) for n, c in self.na_camera()]

    def pixels(self):
        return [(n, ((x / self.right + 0.5) * W, (0.5 - y / self.up) * H)) for n, (x, y) in self.projetados()]

    def respostas(self):
        pt = _pt()
        nomes = [n + " =" for n, _ in self.pontos_mundo]
        r = [_secao("V =", self.visao()),
             _secao("Pontos na câmera (V · p)" if pt else "Points in camera space (V · p)",
                    [c for _, c in self.na_camera()], nomes, ["x", "y", "z"]),
             _secao("Projeção no plano (x', y')" if pt else "Projection on the plane (x', y')",
                    [c for _, c in self.projetados()], nomes, ["x'", "y'"])]
        if self.com_pixel:
            r.append(_secao("Pixel na imagem 400×300" if pt else "Pixel in the 400×300 image",
                            [c for _, c in self.pixels()], nomes, ["px", "py"], tol=1.0))
        return r

    def codigo_camera(self):
        if self.tipo == "orto":
            return (f"camera {{ orthographic location {_pov(self.olho)} right x*{fmt(self.right)} "
                    f"up y*{fmt(self.up)} look_at {_pov(self.alvo)} }}")
        return (f"camera {{ perspective location {_pov(self.olho)} direction <0, 0, {fmt(self.d)}> "
                f"right x*4/3 up y look_at {_pov(self.alvo)} }}")

    def enunciado(self):
        pt = _pt()
        pts = ", ".join(f"{n}{_v(p)}" for n, p in self.pontos_mundo)
        if pt:
            proj = (f"perspectiva, com o plano de projeção a <b>d = {fmt(self.d)}</b> da câmera "
                    f"(direction &lt;0, 0, {fmt(self.d)}&gt;)" if self.tipo == "persp" else
                    "<b>ortográfica</b> (a vista cobre 8 × 6 unidades)")
            txt = (f"<p>Uma câmera em <b>location {_v(self.olho)}</b> olha para <b>look_at {_v(self.alvo)}</b>, "
                   f"com o céu no eixo y. Projeção {proj}.</p><p>Pontos: <b>{pts}</b>.</p><ol>"
                   "<li>a matriz de visão <b>V</b> (4×4), que leva o mundo para a câmera: x da câmera = right, "
                   "y = up, z = a direção em que ela olha (como no POV-Ray);</li>"
                   "<li>cada ponto em coordenadas da câmera;</li><li>a projeção de cada ponto no plano;</li>")
            if self.com_pixel:
                txt += ("<li>o pixel de cada ponto na imagem 400×300 (origem no canto superior esquerdo, "
                        "right = 4/3, up = 1).</li>")
            return txt + "</ol>"
        proj = (f"perspective, with the projection plane at <b>d = {fmt(self.d)}</b> from the camera "
                f"(direction &lt;0, 0, {fmt(self.d)}&gt;)" if self.tipo == "persp" else
                "<b>orthographic</b> (the view covers 8 × 6 units)")
        txt = (f"<p>A camera at <b>location {_v(self.olho)}</b> looks at <b>look_at {_v(self.alvo)}</b>, "
               f"with the sky along y. Projection: {proj}.</p><p>Points: <b>{pts}</b>.</p><ol>"
               "<li>the view matrix <b>V</b> (4×4), which takes the world to the camera: camera x = right, "
               "y = up, z = the direction it looks at (as in POV-Ray);</li>"
               "<li>each point in camera coordinates;</li><li>the projection of each point on the plane;</li>")
        if self.com_pixel:
            txt += ("<li>the pixel of each point in the 400×300 image (origin at the top-left corner, "
                    "right = 4/3, up = 1).</li>")
        return txt + "</ol>"

    def solucao_html(self):
        pt = _pt()
        u, v, w = base_da_camera(self.olho, self.alvo)
        bruto_w = np.subtract(self.alvo, self.olho)
        bruto_u = np.cross((0, 1, 0), w)
        partes = [f"<h3>{'Solução' if pt else 'Solution'}</h3>",
                  "<p><b>1. " + ("Base da câmera" if pt else "Camera basis") + "</b></p><ul>",
                  f"<li>w = (look_at − location) / |…| = {_v(bruto_w)} / {fmt(np.linalg.norm(bruto_w))} = "
                  f"<b>{_v(w)}</b></li>",
                  f"<li>u = (y × w) / |…| = {_v(limpar(bruto_u))} / {fmt(np.linalg.norm(bruto_u))} = <b>{_v(u)}</b> "
                  "(right)</li>",
                  f"<li>v = w × u = <b>{_v(v)}</b> (up)</li></ul>",
                  "<p><b>2. V = R · M_t(−location)</b>, " + (
                      "com u, v, w nas linhas de R:" if pt else "with u, v, w as the rows of R:") + "</p>"]
        R = np.eye(4)
        R[0, :3], R[1, :3], R[2, :3] = u, v, w
        partes += ["<p>R =</p>", matriz_html(R), f"<p>M_t{_v([-c for c in self.olho])} =</p>",
                   matriz_html(M_t(*(-c for c in self.olho))), "<p><b>V =</b></p>", matriz_html(self.visao()),
                   "<p><b>3. " + ("Pontos na câmera" if pt else "Points in camera space") + "</b> (V · [x y z 1]ᵀ)</p><ul>"]
        for (n, p), (_, c) in zip(self.pontos_mundo, self.na_camera()):
            partes.append(f"<li>{n}{_v(p)} → {_v(c)}</li>")
        partes.append("</ul><p><b>4. " + ("Projeção" if pt else "Projection") + "</b></p>")
        if self.tipo == "persp":
            partes.append(("<p>Perspectiva: x' = d·x/z, y' = d·y/z. Em matriz, M_per leva [x y z 1]ᵀ a "
                           "[x y z z/d]ᵀ e depois divide pela última coordenada:</p>" if pt else
                           "<p>Perspective: x' = d·x/z, y' = d·y/z. As a matrix, M_per takes [x y z 1]ᵀ to "
                           "[x y z z/d]ᵀ and then divides by the last coordinate:</p>")
                          + matriz_html(matriz_perspectiva(self.d)))
        else:
            partes.append("<p>" + ("Ortográfica: x' = x, y' = y (o z só diz a profundidade)." if pt else
                                   "Orthographic: x' = x, y' = y (z only gives the depth).") + "</p>")
        partes.append("<ul>")
        for (n, c), (_, q) in zip(self.na_camera(), self.projetados()):
            conta = (f"{fmt(self.d)}·{fmt(c[0])}/{fmt(c[2])}, {fmt(self.d)}·{fmt(c[1])}/{fmt(c[2])} = "
                     if self.tipo == "persp" else "")
            partes.append(f"<li>{n}: ({conta}{fmt(q[0])}, {fmt(q[1])})</li>")
        partes.append("</ul>")
        if self.com_pixel:
            partes.append("<p><b>5. Pixel</b>: px = (x'/" + fmt(self.right) + " + 0,5)·400, py = (0,5 − y'/"
                          + fmt(self.up) + ")·300</p><ul>")
            for n, (px, py) in self.pixels():
                partes.append(f"<li>{n}: ({fmt(px)}, {fmt(py)})</li>")
            partes.append("</ul>")
        partes.append("<p>" + ("No POV-Ray:" if pt else "In POV-Ray:") + f"<br><code>{self.codigo_camera()}</code></p>")
        partes.append("<p style='color:#999'>" + (
            "O POV-Ray usa a mão esquerda: a câmera olha para +z, e o right = céu × direção. Nos livros "
            "(OpenGL), a câmera olha para −z; aí o sinal do z da câmera e da projeção troca." if pt else
            "POV-Ray is left-handed: the camera looks along +z, and right = sky × direction. In textbooks "
            "(OpenGL) the camera looks along −z, so the sign of the camera z and of the projection flips.")
            + "</p>")
        return "".join(partes)

    def desenho(self, aluno, mostrar_certa):
        cena = [("ponto", p, "#5aa9ff", n) for n, p in self.pontos_mundo]
        u, v, w = base_da_camera(self.olho, self.alvo)
        o = np.array(self.olho, float)
        cena += [("ponto", tuple(o), "#d58cff", "câmera" if _pt() else "camera"),
                 ("seta", tuple(o), tuple(o + u), "#ff6b6b", "u"), ("seta", tuple(o), tuple(o + v), "#6fdc8c", "v"),
                 ("seta", tuple(o), tuple(o + w), "#5aa9ff", "w"), ("linha", tuple(o), self.alvo, "#d58cff", True)]
        # a pirâmide da vista até o plano de projeção
        if self.tipo == "persp":
            centro, metade_u, metade_v = o + w * self.d, u * self.right / 2, v * self.up / 2
            cantos = [centro + a * metade_u + b * metade_v for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            cena += [("linha", tuple(o), tuple(c), "#8a6fb0", False) for c in cantos]
        else:
            metade_u, metade_v = u * self.right / 2, v * self.up / 2
            cantos = [o + a * metade_u + b * metade_v for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            cena += [("linha", tuple(c), tuple(c + w * 2), "#8a6fb0", False) for c in cantos]
        cena += [("linha", tuple(cantos[i]), tuple(cantos[(i + 1) % 4]), "#8a6fb0", False) for i in range(4)]
        for n, p in self.pontos_mundo:
            cena.append(("linha", tuple(o), p, "#444", True))
        nomes = [n for n, _ in self.pontos_mundo]
        tela = {"right": self.right, "up": self.up, "figuras": []}
        proj = _linhas_completas(aluno[2] if len(aluno) > 2 else None, len(nomes))
        if proj:
            tela["figuras"].append((proj, "#ffb347", nomes))
        if mostrar_certa:
            tela["figuras"].append(([q for _, q in self.projetados()], "#6fdc8c", nomes))
        return {"cena": cena, "tela": tela}

    def pov_cena(self):
        pt = _pt()
        cores = ["<1, 0.4, 0.3>", "<0.3, 0.8, 1>", "<1, 0.85, 0.3>"]
        esferas = "\n".join(f"sphere {{ {_pov(p)}, 0.12 pigment {{ rgb {cores[i]} }} }}   // {n}"
                            for i, (n, p) in enumerate(self.pontos_mundo))
        cab = ("// Treino de câmera, questão {} ({}): renderize em 400×300 e confira onde cada ponto aparece"
               if pt else "// Camera practice, question {} ({}): render at 400×300 and check where each point shows up")
        return f"""{cab.format(self.numero, self.nivel)}
#version 3.7;
global_settings {{ assumed_gamma 1 }}
{self.codigo_camera()}
light_source {{ <10, 20, -15> rgb 1 }}
background {{ rgb 0.12 }}
cylinder {{ 0, x*3, 0.03 pigment {{ rgb <1, 0.2, 0.2> }} }}
cylinder {{ 0, y*3, 0.03 pigment {{ rgb <0.2, 1, 0.2> }} }}
cylinder {{ 0, z*3, 0.03 pigment {{ rgb <0.3, 0.5, 1> }} }}
{esferas}
"""


# ================================================================ modo 3: iluminação (Phong)

def _direcoes():
    """Direções com comprimento inteiro (para normalizar à mão): permutações e sinais de (0,3,4), (1,2,2)..."""
    import itertools
    r = set()
    for base in ((0, 3, 4), (1, 2, 2), (2, 3, 6), (0, 0, 1)):
        for perm in itertools.permutations(base):
            for sinais in itertools.product((1, -1), repeat=3):
                r.add(tuple(a * b for a, b in zip(perm, sinais)))
    return sorted(r)


DIRECOES = _direcoes()
NORMAIS = [(0, 1, 0), (0, 1, 0), (0, 0, -1), (1, 0, 0), (-1, 0, 0)]


class QuestaoPhong:
    modo = "phong"

    def __init__(self, numero, nivel="medio"):
        self.numero, self.nivel = numero, nivel
        r = random.Random(f"phong-{nivel}-{numero}")
        self.N = np.array(r.choice(NORMAIS), float)
        boas = [d for d in DIRECOES if np.dot(self.N, d) / np.linalg.norm(d) > 0.3]
        self.dir_luz = np.array(r.choice(boas), float)
        self.dir_olho = np.array(r.choice([d for d in boas if not np.allclose(d, self.dir_luz)]), float)
        self.P = np.array(r.choice([(0, 0, 0), (1, 0, 2), (2, 0, 1), (-1, 0, 1), (0, 0, 3)]), float)
        if self.N[1] == 0:                   # parede: o ponto sai do chão
            self.P = self.P + (0, 1, 0)
        self.luz = self.P + self.dir_luz * r.choice([1, 2])
        self.olho = self.P + self.dir_olho * r.choice([1, 2])
        self.ka = 0.1
        self.kd = r.choice([0.5, 0.6])
        self.ks = r.choice([0.2, 0.3])
        self.n = r.choice({"facil": [2, 4], "medio": [5, 10], "dificil": [10, 20, 40]}[nivel])
        self.Il = r.choice([0.8, 1.0]) if nivel == "dificil" else 1.0
        self.Ia = r.choice([0.5, 1.0]) if nivel == "dificil" else 1.0
        self.dar_vetores = nivel == "facil"

    def vetores(self):
        L = limpar(_unit(self.luz - self.P))
        V = limpar(_unit(self.olho - self.P))
        nl = float(np.dot(self.N, L))
        R = limpar(2 * nl * self.N - L)
        rv = float(np.dot(R, V))
        I = self.ka * self.Ia + self.kd * self.Il * max(nl, 0) + self.ks * self.Il * max(rv, 0) ** self.n
        return {"L": L, "V": V, "NL": nl, "R": R, "RV": rv, "I": I}

    def respostas(self):
        pt = _pt()
        v = self.vetores()
        r = []
        if not self.dar_vetores:
            r += [_secao("L " + ("(unitário, do ponto para a luz)" if pt else "(unit, from the point to the light)"),
                         [v["L"]], ["L ="], ["x", "y", "z"]),
                  _secao("V " + ("(unitário, do ponto para a câmera)" if pt else "(unit, from the point to the camera)"),
                         [v["V"]], ["V ="], ["x", "y", "z"])]
        r += [_secao("N · L", [[v["NL"]]], ["N·L ="]),
              _secao("R = 2(N·L)N − L", [v["R"]], ["R ="], ["x", "y", "z"]),
              _secao("R · V", [[v["RV"]]], ["R·V ="]),
              _secao("I " + ("(intensidade no ponto)" if pt else "(intensity at the point)"), [[v["I"]]], ["I ="])]
        return r

    def enunciado(self):
        pt = _pt()
        v = self.vetores()
        coef = (f"k<sub>a</sub> = {fmt(self.ka)}, k<sub>d</sub> = {fmt(self.kd)}, k<sub>s</sub> = {fmt(self.ks)}, "
                f"n = {self.n}, I<sub>a</sub> = {fmt(self.Ia)}, I<sub>l</sub> = {fmt(self.Il)}")
        if self.dar_vetores:
            dados = (f"N = {_v(self.N)}, L = {_v(v['L'])}, V = {_v(v['V'])}" +
                     (" (já unitários)" if pt else " (already unit vectors)"))
        else:
            dados = ((f"ponto P = {_v(self.P)} com normal N = {_v(self.N)}, luz em {_v(self.luz)}, "
                      f"câmera em {_v(self.olho)}") if pt else
                     (f"point P = {_v(self.P)} with normal N = {_v(self.N)}, light at {_v(self.luz)}, "
                      f"camera at {_v(self.olho)}"))
        formula = ("I = k<sub>a</sub>·I<sub>a</sub> + k<sub>d</sub>·I<sub>l</sub>·max(N·L, 0) + "
                   "k<sub>s</sub>·I<sub>l</sub>·max(R·V, 0)<sup>n</sup>")
        if pt:
            return (f"<p>Modelo de Phong numa superfície branca: <b>{dados}</b>.</p><p>Coeficientes: {coef}.</p>"
                    f"<p>{formula}</p><p>Calcule os vetores e a intensidade I no ponto.</p>")
        return (f"<p>Phong model on a white surface: <b>{dados}</b>.</p><p>Coefficients: {coef}.</p>"
                f"<p>{formula}</p><p>Compute the vectors and the intensity I at the point.</p>")

    def solucao_html(self):
        pt = _pt()
        v = self.vetores()
        partes = [f"<h3>{'Solução' if pt else 'Solution'}</h3><ul>"]
        if not self.dar_vetores:
            dl, do = self.luz - self.P, self.olho - self.P
            partes += [f"<li>L = (luz − P)/|…| = {_v(dl)} / {fmt(np.linalg.norm(dl))} = <b>{_v(v['L'])}</b></li>"
                       if pt else f"<li>L = (light − P)/|…| = {_v(dl)} / {fmt(np.linalg.norm(dl))} = "
                                  f"<b>{_v(v['L'])}</b></li>",
                       f"<li>V = ({'câmera' if pt else 'camera'} − P)/|…| = {_v(do)} / {fmt(np.linalg.norm(do))} = "
                       f"<b>{_v(v['V'])}</b></li>"]
        partes += [f"<li>N·L = <b>{fmt(v['NL'])}</b></li>",
                   f"<li>R = 2·{fmt(v['NL'])}·{_v(self.N)} − {_v(v['L'])} = <b>{_v(v['R'])}</b></li>",
                   f"<li>R·V = <b>{fmt(v['RV'])}</b>" + (
                       (" (negativo: sem brilho, conta como 0)" if pt else " (negative: no highlight, counts as 0)")
                       if v["RV"] < 0 else "") + "</li></ul>"]
        amb = self.ka * self.Ia
        dif = self.kd * self.Il * max(v["NL"], 0)
        esp = self.ks * self.Il * max(v["RV"], 0) ** self.n
        partes.append(f"<p>I = {fmt(self.ka)}·{fmt(self.Ia)} + {fmt(self.kd)}·{fmt(self.Il)}·{fmt(v['NL'])} + "
                      f"{fmt(self.ks)}·{fmt(self.Il)}·{fmt(max(v['RV'], 0))}<sup>{self.n}</sup><br>"
                      f"&nbsp;&nbsp;= {fmt(amb)} + {fmt(dif)} + {fmt(esp)} = <b>{fmt(v['I'])}</b></p>")
        partes.append("<p>" + ("No POV-Ray, o mesmo material e a mesma luz:" if pt else
                               "In POV-Ray, the same material and light:")
                      + f"<br><code>finish {{ ambient {fmt(self.ka)} diffuse {fmt(self.kd)} phong {fmt(self.ks)} "
                      f"phong_size {self.n} }}</code><br><code>light_source {{ {_pov(self.luz)} rgb {fmt(self.Il)} }}"
                      f"</code><br><code>global_settings {{ ambient_light {fmt(self.Ia)} }}</code></p>")
        return "".join(partes)

    def desenho(self, aluno, mostrar_certa):
        pt = _pt()
        v = self.vetores()
        P = self.P
        k = max(1.5, 0.45 * min(np.linalg.norm(self.luz - P), np.linalg.norm(self.olho - P)))   # tamanho das setas
        # um quadrado da superfície em volta do ponto
        a = np.array((1.0, 0, 0)) if abs(self.N[0]) < 0.9 else np.array((0, 1.0, 0))
        e1 = _unit(np.cross(self.N, a)) * k
        e2 = np.cross(self.N, e1)
        cantos = [P + s * e1 + t * e2 for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        cena = [("linha", tuple(cantos[i]), tuple(cantos[(i + 1) % 4]), "#777", False) for i in range(4)]
        cena += [("ponto", tuple(P), "#ddd", "P"),
                 ("seta", tuple(P), tuple(P + self.N * k), "#ddd", "N"),
                 ("seta", tuple(P), tuple(P + v["L"] * k), "#ffe066", "L"),
                 ("seta", tuple(P), tuple(P + v["V"] * k), "#5aa9ff", "V"),
                 ("ponto", tuple(self.luz), "#ffe066", "luz" if pt else "light"),
                 ("ponto", tuple(self.olho), "#5aa9ff", "câmera" if pt else "camera"),
                 ("linha", tuple(P), tuple(self.luz), "#665c2e", True),
                 ("linha", tuple(P), tuple(self.olho), "#2e4a66", True)]
        i = (0 if self.dar_vetores else 2) + 1                        # a seção do R
        r_aluno = _linhas_completas(aluno[i] if len(aluno) > i else None, 1)
        if r_aluno:
            cena.append(("seta", tuple(P), tuple(P + np.array(r_aluno[0]) * k), "#ffb347", "R"))
        if mostrar_certa:
            cena.append(("seta", tuple(P), tuple(P + v["R"] * k), "#6fdc8c", "R"))
        return {"cena": cena, "tela": None}

    def pov_cena(self):
        pt = _pt()
        d = float(np.dot(self.N, self.P))
        cab = ("// Treino de Phong, questão {} ({}): o pixel do meio da imagem é o ponto P; com File_Gamma=1 "
               "a cor dele é I" if pt else
               "// Phong practice, question {} ({}): the middle pixel of the image is the point P; with "
               "File_Gamma=1 its color is I")
        return f"""{cab.format(self.numero, self.nivel)}
#version 3.7;
global_settings {{ assumed_gamma 1 ambient_light {fmt(self.Ia)} }}
camera {{ location {_pov(self.olho)} right x up y look_at {_pov(self.P)} }}
light_source {{ {_pov(self.luz)} rgb {fmt(self.Il)} }}
plane {{ {_pov(self.N)}, {fmt(d)}
  pigment {{ rgb 1 }}
  finish {{ ambient {fmt(self.ka)} diffuse {fmt(self.kd)} phong {fmt(self.ks)} phong_size {self.n} }}
}}
"""


# ================================================================ geral

MODOS = {"transformacoes": QuestaoTransformacao, "camera": QuestaoCamera, "phong": QuestaoPhong}


def questao(modo, numero, nivel="medio"):
    return MODOS[modo](numero, nivel)


def formulas_html(modo):
    pt = _pt()
    if modo == "transformacoes":
        partes = ["<p>" + ("Ponto em coluna [x y z 1]ᵀ; a última transformação fica à esquerda." if pt else
                           "Column point [x y z 1]ᵀ; the last transformation is on the left.") + "</p>"]
        for nome, M in (("M_t(tx, ty, tz)", np.array([["1", "0", "0", "tx"], ["0", "1", "0", "ty"],
                                                        ["0", "0", "1", "tz"], ["0", "0", "0", "1"]])),
                        ("M_rx(θ) " + ("horária" if pt else "clockwise"),
                         np.array([["1", "0", "0", "0"], ["0", "cos", "sen" if pt else "sin", "0"],
                                   ["0", "−sen" if pt else "−sin", "cos", "0"], ["0", "0", "0", "1"]])),
                        ("M_ry(θ) " + ("horária" if pt else "clockwise"),
                         np.array([["cos", "0", "−sen" if pt else "−sin", "0"], ["0", "1", "0", "0"],
                                   ["sen" if pt else "sin", "0", "cos", "0"], ["0", "0", "0", "1"]])),
                        ("M_rz(θ) " + ("horária" if pt else "clockwise"),
                         np.array([["cos", "sen" if pt else "sin", "0", "0"], ["−sen" if pt else "−sin", "cos", "0", "0"],
                                   ["0", "0", "1", "0"], ["0", "0", "0", "1"]]))):
            linhas = "".join("<tr>" + "".join(f"<td align='center' style='padding:0 8px'>{c}</td>" for c in linha)
                             + "</tr>" for linha in M)
            partes.append(f"<p><b>{nome}</b></p><table style='border-left:1px solid #888;border-right:1px solid "
                          f"#888'>{linhas}</table>")
        partes.append("<p>" + (
            "As anti-horárias (M_rahx, M_rahy, M_rahz) são as transpostas: trocam o sinal dos senos. "
            "São o rotate do POV-Ray. M_fx = diag(−1, 1, 1, 1) troca o sinal de x (idem M_fy, M_fz). "
            "Em torno de um ponto P: M_t(P) · M · M_t(−P)." if pt else
            "The counterclockwise ones (M_rahx, M_rahy, M_rahz) are the transposes: the sines flip sign. "
            "They are POV-Ray's rotate. M_fx = diag(−1, 1, 1, 1) flips the sign of x (same for M_fy, M_fz). "
            "About a point P: M_t(P) · M · M_t(−P).") + "</p>")
        return "".join(partes)
    if modo == "camera":
        return ("<ul><li>w = (look_at − location) / |look_at − location|</li><li>u = (y × w) / |y × w| "
                "(right)</li><li>v = w × u (up)</li><li>V = R · M_t(−location), " +
                ("com u, v e w nas três primeiras linhas de R" if pt else "with u, v and w as the first three rows "
                 "of R") + "</li><li>" + ("perspectiva" if pt else "perspective") +
                ": x' = d·x/z, y' = d·y/z &nbsp; (M_per: [x y z 1]ᵀ → [x y z z/d]ᵀ)</li><li>" +
                ("ortográfica" if pt else "orthographic") + ": x' = x, y' = y</li><li>pixel: px = (x'/right + "
                "0,5)·W, py = (0,5 − y'/up)·H</li></ul><p style='color:#999'>" +
                ("Câmera do POV-Ray (mão esquerda): olha para +z da câmera." if pt else
                 "POV-Ray camera (left-handed): looks along camera +z.") + "</p>")
    return ("<ul><li>L = (" + ("luz" if pt else "light") + " − P)/|…|, V = (" + ("câmera" if pt else "camera") +
            " − P)/|…|</li><li>R = 2(N·L)N − L</li><li>I = k<sub>a</sub>·I<sub>a</sub> + k<sub>d</sub>·I<sub>l</sub>"
            "·max(N·L, 0) + k<sub>s</sub>·I<sub>l</sub>·max(R·V, 0)<sup>n</sup></li></ul><p>" +
            ("No POV-Ray: ambient = k<sub>a</sub>, diffuse = k<sub>d</sub>, phong = k<sub>s</sub>, phong_size = n, "
             "a cor da luz = I<sub>l</sub> e o ambient_light = I<sub>a</sub>." if pt else
             "In POV-Ray: ambient = k<sub>a</sub>, diffuse = k<sub>d</sub>, phong = k<sub>s</sub>, phong_size = n, "
             "the light color = I<sub>l</sub> and ambient_light = I<sub>a</sub>.") + "</p>")
