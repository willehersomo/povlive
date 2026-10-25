"""Treino de transformações 2D para a prova (cálculo à mão), na notação da aula (CGRA):
ponto em coluna [x y 1]ᵀ, última transformação à esquerda (M = Mn···M1), M_r = rotação HORÁRIA,
M_rah = anti-horária, M_fx troca o sinal de x e M_fy o de y.

O app sorteia uma sequência de transformações e uma figura; o aluno calcula a matriz final e os
pontos transformados; o app confere e mostra a solução passo a passo.
"""
import ast, math, random, re

import numpy as np

from .i18n import idioma

FIGURA_AULA = [("A", (1, 1)), ("B", (2, 1)), ("C", (2, 2)), ("D", (1, 4))]
OUTRAS_FIGURAS = [
    [("A", (0, 0)), ("B", (2, 0)), ("C", (1, 2))],
    [("A", (1, 0)), ("B", (3, 0)), ("C", (3, 1)), ("D", (1, 1))],
    [("A", (-1, 1)), ("B", (1, 1)), ("C", (0, 3))],
    [("A", (2, 1)), ("B", (4, 1)), ("C", (4, 3)), ("D", (2, 3))],
]
ANGULOS = [30, 45, 60, 90, 120, 135, 180, 270]
NIVEIS = {"facil": (1, 2), "medio": (2, 3), "dificil": (3, 4)}


# ---------------------------------------------------------------- matrizes

def M_t(tx, ty):
    return np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1]], float)


def M_s(sx, sy):
    return np.diag([sx, sy, 1.0])


def M_r(graus):
    """Rotação HORÁRIA (convenção da aula)."""
    c, s = math.cos(math.radians(graus)), math.sin(math.radians(graus))
    return np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])


def M_rah(graus):
    """Rotação anti-horária."""
    return M_r(-graus)


M_fx = np.diag([-1.0, 1, 1])
M_fy = np.diag([1.0, -1, 1])


def limpar(M):
    M = np.where(np.abs(M) < 1e-12, 0.0, M)
    return M


# ---------------------------------------------------------------- operações

def matrizes_da_op(op):
    """Lista de (nome, matriz) da operação, na ordem em que são aplicadas (a primeira primeiro)."""
    tipo = op[0]
    if tipo == "T":
        return [(f"M_t({fmt(op[1])}, {fmt(op[2])})", M_t(op[1], op[2]))]
    if tipo == "S":
        return [(f"M_s({fmt(op[1])}, {fmt(op[2])})", M_s(op[1], op[2]))]
    if tipo == "R":
        return [(f"M_r({fmt(op[1])}°)", M_r(op[1]))]
    if tipo == "Rah":
        return [(f"M_rah({fmt(op[1])}°)", M_rah(op[1]))]
    if tipo == "Fx":
        return [("M_fx", M_fx)]
    if tipo == "Fy":
        return [("M_fy", M_fy)]
    if tipo == "Rp":
        _, g, px, py = op
        return [(f"M_t({fmt(-px)}, {fmt(-py)})", M_t(-px, -py)), (f"M_r({fmt(g)}°)", M_r(g)),
                (f"M_t({fmt(px)}, {fmt(py)})", M_t(px, py))]
    if tipo == "Sp":
        _, sx, sy, px, py = op
        return [(f"M_t({fmt(-px)}, {fmt(-py)})", M_t(-px, -py)), (f"M_s({fmt(sx)}, {fmt(sy)})", M_s(sx, sy)),
                (f"M_t({fmt(px)}, {fmt(py)})", M_t(px, py))]
    raise ValueError(tipo)


def descrever(op):
    pt = idioma() == "pt"
    tipo = op[0]
    if tipo == "T":
        return (f"translação de ({fmt(op[1])}, {fmt(op[2])})" if pt else
                f"translation by ({fmt(op[1])}, {fmt(op[2])})")
    if tipo == "S":
        return (f"escala de ({fmt(op[1])}, {fmt(op[2])}) em relação à origem" if pt else
                f"scale by ({fmt(op[1])}, {fmt(op[2])}) about the origin")
    if tipo == "R":
        return (f"rotação de {fmt(op[1])}° no sentido horário em torno da origem" if pt else
                f"rotation by {fmt(op[1])}° clockwise about the origin")
    if tipo == "Rah":
        return (f"rotação de {fmt(op[1])}° no sentido anti-horário em torno da origem" if pt else
                f"rotation by {fmt(op[1])}° counterclockwise about the origin")
    if tipo == "Fx":
        return "reflexão M_fx (troca o sinal de x)" if pt else "reflection M_fx (flips the sign of x)"
    if tipo == "Fy":
        return "reflexão M_fy (troca o sinal de y)" if pt else "reflection M_fy (flips the sign of y)"
    if tipo == "Rp":
        return (f"rotação de {fmt(op[1])}° no sentido horário em torno do ponto ({fmt(op[2])}, {fmt(op[3])})" if pt
                else f"rotation by {fmt(op[1])}° clockwise about the point ({fmt(op[2])}, {fmt(op[3])})")
    if tipo == "Sp":
        return (f"escala de ({fmt(op[1])}, {fmt(op[2])}) em relação ao ponto ({fmt(op[3])}, {fmt(op[4])})" if pt
                else f"scale by ({fmt(op[1])}, {fmt(op[2])}) about the point ({fmt(op[3])}, {fmt(op[4])})")
    raise ValueError(tipo)


class Questao:
    def __init__(self, numero, nivel="medio"):
        self.numero = numero
        self.nivel = nivel
        r = random.Random(f"{nivel}-{numero}")
        self.figura = FIGURA_AULA if r.random() < 0.4 else r.choice(OUTRAS_FIGURAS)
        n = r.randint(*NIVEIS[nivel])
        tipos = ["T", "S", "R", "Rah", "Fx", "Fy"] + (["Rp", "Sp"] if nivel == "dificil" else [])
        self.ops = []
        for _ in range(n):
            t = r.choice(tipos)
            if self.ops and self.ops[-1][0] == t and t in ("Fx", "Fy"):
                t = "T"                       # duas reflexões iguais seguidas se anulam: troca
            if t == "T":
                op = ("T", r.choice([-3, -2, -1, 1, 2, 3]), r.choice([-2, -1, 0, 1, 2]))
            elif t == "S":
                op = ("S", r.choice([0.5, 2, 3]), r.choice([0.5, 1, 2]))
            elif t in ("R", "Rah"):
                op = (t, r.choice(ANGULOS[:6] if nivel != "dificil" else ANGULOS))
            elif t in ("Fx", "Fy"):
                op = (t,)
            elif t == "Rp":
                op = ("Rp", r.choice([90, 180, 45, 60]), *r.choice(self.figura)[1])
            else:
                op = ("Sp", r.choice([2, 0.5]), r.choice([2, 0.5, 1]), *r.choice(self.figura)[1])
            self.ops.append(op)

    # ------------------------------------------------------------ respostas certas

    def passos(self):
        """Lista de (nome, matriz) na ordem de aplicação."""
        return [p for op in self.ops for p in matrizes_da_op(op)]

    def matriz(self):
        M = np.eye(3)
        for _n, A in self.passos():
            M = A @ M                 # a última aplicada fica à esquerda
        return limpar(M)

    def pontos(self):
        M = self.matriz()
        return [(nome, tuple(limpar(M @ np.array([x, y, 1.0]))[:2])) for nome, (x, y) in self.figura]

    def enunciado(self):
        pt = idioma() == "pt"
        figura = ", ".join(f"{n}({fmt(x)}, {fmt(y)})" for n, (x, y) in self.figura)
        passos = "".join(f"<li>{descrever(op)}</li>" for op in self.ops)
        if pt:
            return (f"<p>Aplique à figura <b>{figura}</b>, nesta ordem:</p><ol>{passos}</ol>"
                    "<p>Calcule a matriz final <b>M</b> (3×3, ponto em coluna) e os pontos transformados.</p>")
        return (f"<p>Apply to the figure <b>{figura}</b>, in this order:</p><ol>{passos}</ol>"
                "<p>Compute the final matrix <b>M</b> (3×3, column points) and the transformed points.</p>")

    def solucao_html(self):
        pt = idioma() == "pt"
        passos = self.passos()
        partes = [f"<h3>{'Solução' if pt else 'Solution'}</h3>"]
        for k, (nome, A) in enumerate(passos, 1):
            partes.append(f"<p><b>M{k} = {nome}</b></p>" + matriz_html(A))
        ordem = "·".join(f"M{k}" for k in range(len(passos), 0, -1))
        partes.append(f"<p><b>M = {ordem}</b> " + ("(a última transformação fica à esquerda)" if pt else
                                                     "(the last transformation is on the left)") + "</p>")
        partes.append(matriz_html(self.matriz()))
        partes.append("<p><b>" + ("Pontos" if pt else "Points") + "</b> (M · [x y 1]ᵀ):</p><ul>")
        for (nome, (x, y)), (_, (nx, ny)) in zip(self.figura, self.pontos()):
            partes.append(f"<li>{nome}({fmt(x)}, {fmt(y)}) → {nome}'({fmt(nx)}, {fmt(ny)})</li>")
        partes.append("</ul>")
        if any(op[0] in ("R", "Rp", "Rah") for op in self.ops):
            partes.append("<p style='color:#999'>" + (
                "Lembrete: na aula, M_r é a rotação horária [[cos, sen], [−sen, cos]]; a anti-horária é M_rah."
                if pt else "Reminder: in this course M_r is the clockwise rotation [[cos, sin], [−sin, cos]]; "
                           "the counterclockwise one is M_rah.") + "</p>")
        return "".join(partes)


# ---------------------------------------------------------------- conferir

class EntradaInvalida(ValueError):
    pass


_FUNCOES = {"sqrt": math.sqrt, "sin": lambda g: math.sin(math.radians(g)), "cos": lambda g: math.cos(math.radians(g)),
            "sen": lambda g: math.sin(math.radians(g))}


def ler_numero(texto):
    """Número digitado pelo aluno: 0,866 | -1/2 | √3/2 | sqrt(3)/2 | cos(30)."""
    t = texto.strip().replace("√", "sqrt").replace("−", "-").replace("^", "**")
    if not t:
        raise EntradaInvalida("vazio")
    t = t.replace(",", ".")
    t = re.sub(r"sqrt(\d+(?:\.\d+)?)", r"sqrt(\1)", t)
    try:
        arvore = ast.parse(t, mode="eval")
    except SyntaxError:
        raise EntradaInvalida(texto)

    def calc(n):
        if isinstance(n, ast.Expression):
            return calc(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            v = calc(n.operand)
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
            a, b = calc(n.left), calc(n.right)
            if isinstance(n.op, ast.Add):
                return a + b
            if isinstance(n.op, ast.Sub):
                return a - b
            if isinstance(n.op, ast.Mult):
                return a * b
            if isinstance(n.op, ast.Pow):
                return a ** b
            if b == 0:
                raise EntradaInvalida(texto)
            return a / b
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCOES
                and len(n.args) == 1):
            return _FUNCOES[n.func.id](calc(n.args[0]))
        raise EntradaInvalida(texto)
    return calc(arvore)


def igual(a, b, tol=0.01):
    return abs(a - b) <= tol + 1e-3 * abs(b)


# ---------------------------------------------------------------- formatação

def fmt(x):
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.3f}".rstrip("0").rstrip(".") if abs(x) >= 1e-9 else "0"


def matriz_html(M):
    linhas = "".join("<tr>" + "".join(f"<td align='right' style='padding:0 8px'>{fmt(v)}</td>" for v in linha)
                     + "</tr>" for linha in limpar(M))
    return f"<table style='border-left:1px solid #888;border-right:1px solid #888;margin:2px 0 8px 0'>{linhas}</table>"
