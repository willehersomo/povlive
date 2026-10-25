"""Leitura da estrutura de uma cena POV-Ray (SDL): blocos { }, transformações e expressões.

Não é um parser completo do POV-Ray: entende o suficiente para
  - achar o objeto em que o cursor está e as transformações dele (painel de matrizes);
  - marcar cada objeto com uma cor única (clicar na imagem e ir para o código);
  - calcular expressões simples (números, vetores, pi, clock, x/y/z, #declare, funções).
"""
import math, re

OBJETOS = set("""sphere box cylinder cone torus plane disc triangle smooth_triangle prism lathe sor
superellipsoid blob height_field text union difference intersection merge object mesh mesh2
isosurface polygon quadric cubic quartic poly sphere_sweep julia_fractal bicubic_patch
parametric ovus lemon""".split())
COM_TRANSFORMACAO = OBJETOS | {"camera", "light_source"}


# ==================================================================== blocos

class Bloco:
    def __init__(self, kw, kw_ini, abre, pai):
        self.kw = kw            # palavra antes do "{" (sphere, union, pigment...)
        self.kw_ini = kw_ini    # posição da palavra no texto
        self.abre = abre        # posição do "{"
        self.fecha = None       # posição do "}"
        self.pai = pai
        self.filhos = []
        self.declarado = None   # nome, se o bloco é o valor de um #declare

    def contem(self, pos):
        return self.abre < pos <= (self.fecha if self.fecha is not None else 10 ** 9) or self.kw_ini <= pos <= self.abre

    def __repr__(self):
        return f"<{self.kw} {self.kw_ini}..{self.fecha}>"


def mascarar(texto):
    """Troca comentários e strings por espaços (mantendo as posições), para analisar só o código."""
    out = list(texto)
    i, n = 0, len(texto)
    while i < n:
        c = texto[i]
        if texto.startswith("//", i):
            j = texto.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif texto.startswith("/*", i):
            j = texto.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        elif c == '"':
            j = texto.find('"', i + 1)
            j = n - 1 if j < 0 else j
            for k in range(i + 1, j):
                out[k] = " "
            i = j + 1
        else:
            i += 1
    return "".join(out)


RX_ANTES_CHAVE = re.compile(r"([A-Za-z_]\w*)\s*$")
RX_DECLARE_ANTES = re.compile(r"#(?:declare|local)\s+([A-Za-z_]\w*)\s*=\s*$")


def blocos(texto, mascara=None):
    """Lista de todos os blocos { } do texto, em ordem (com pai/filhos ligados)."""
    m = mascara if mascara is not None else mascarar(texto)
    todos, pilha = [], []
    for i, c in enumerate(m):
        if c == "{":
            ini = max(0, i - 80)
            antes = m[ini:i]
            mk = RX_ANTES_CHAVE.search(antes)
            kw = mk.group(1) if mk else ""
            kw_ini = ini + mk.start(1) if mk else i
            b = Bloco(kw, kw_ini, i, pilha[-1] if pilha else None)
            md = RX_DECLARE_ANTES.search(m[max(0, kw_ini - 120):kw_ini])
            if md:
                b.declarado = md.group(1)
            if pilha:
                pilha[-1].filhos.append(b)
            todos.append(b)
            pilha.append(b)
        elif c == "}" and pilha:
            pilha.pop().fecha = i
    return todos


def objeto_em(texto, pos, tipos=COM_TRANSFORMACAO):
    """O bloco de objeto mais interno que contém a posição (ou None)."""
    melhor = None
    for b in blocos(texto):
        if b.kw in tipos and b.contem(pos):
            if melhor is None or b.abre > melhor.abre:
                melhor = b
    return melhor


def linha_de(texto, pos):
    return texto.count("\n", 0, pos) + 1


# ==================================================================== expressões

class Desconhecido(Exception):
    """A expressão depende de algo que não dá para saber sem rodar o POV-Ray (ex.: variável do #for)."""


FUNCOES = {
    "sin": math.sin, "cos": math.cos, "tan": math.tan, "asin": math.asin, "acos": math.acos,
    "atan": math.atan, "atan2": math.atan2, "sqrt": math.sqrt, "abs": abs, "exp": math.exp,
    "ln": math.log, "log": math.log10, "pow": math.pow, "radians": math.radians, "degrees": math.degrees,
    "min": min, "max": max, "int": lambda v: float(int(v)), "floor": math.floor, "ceil": math.ceil,
    "mod": math.fmod, "div": lambda a, b: float(int(a / b)),
}
CONSTANTES = {"pi": math.pi, "x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0),
              "true": 1.0, "false": 0.0, "on": 1.0, "off": 0.0, "yes": 1.0, "no": 0.0}
RX_TOKEN = re.compile(r"\s*(?:(\d+\.?\d*(?:[eE][-+]?\d+)?|\.\d+(?:[eE][-+]?\d+)?)|([A-Za-z_]\w*)|(.))", re.S)


def _op(a, b, f):
    if isinstance(a, tuple) or isinstance(b, tuple):
        a = a if isinstance(a, tuple) else (a,) * 3
        b = b if isinstance(b, tuple) else (b,) * 3
        return tuple(f(p, q) for p, q in zip(a, b))
    return f(a, b)


class Expressao:
    """Avaliador recursivo. Para no primeiro token que não continua a expressão
    (assim 'rotate 45*y translate ...' lê só '45*y')."""

    def __init__(self, texto, pos, variaveis):
        self.t, self.p, self.vars = texto, pos, variaveis

    def _espiar(self):
        m = RX_TOKEN.match(self.t, self.p)
        if not m or m.end() == m.start() or self.p >= len(self.t):
            return None, None, self.p
        if m.group(1):
            return "num", m.group(1), m.end()
        if m.group(2):
            return "id", m.group(2), m.end()
        return "sim", m.group(3), m.end()

    def _comer(self):
        tipo, val, fim = self._espiar()
        self.p = fim
        return tipo, val

    def expr(self):
        v = self.termo()
        while True:
            tipo, val, _ = self._espiar()
            if tipo == "sim" and val in "+-":
                self._comer()
                w = self.termo()
                v = _op(v, w, (lambda a, b: a + b) if val == "+" else (lambda a, b: a - b))
            else:
                return v

    def termo(self):
        v = self.unario()
        while True:
            tipo, val, _ = self._espiar()
            if tipo == "sim" and val in "*/":
                self._comer()
                w = self.unario()
                v = _op(v, w, (lambda a, b: a * b) if val == "*" else (lambda a, b: a / b))
            else:
                return v

    def unario(self):
        tipo, val, _ = self._espiar()
        if tipo == "sim" and val in "+-":
            self._comer()
            v = self.unario()
            return v if val == "+" else _op(v, -1.0, lambda a, b: a * b)
        return self.primario()

    def primario(self):
        tipo, val = self._comer()
        if tipo == "num":
            return float(val)
        if tipo == "sim" and val == "(":
            v = self.expr()
            self._esperar(")")
            return v
        if tipo == "sim" and val == "<":
            comps = [self.expr()]
            while self._espiar()[1] == ",":
                self._comer()
                comps.append(self.expr())
            self._esperar(">")
            if not all(isinstance(c, float) for c in comps):
                raise Desconhecido("vetor dentro de vetor")
            if len(comps) == 2:
                comps.append(0.0)
            return tuple(comps[:3])
        if tipo == "id":
            if self._espiar()[1] == "(":
                if val not in FUNCOES:
                    raise Desconhecido(val)
                self._comer()
                args = [self.expr()]
                while self._espiar()[1] == ",":
                    self._comer()
                    args.append(self.expr())
                self._esperar(")")
                if any(isinstance(a, tuple) for a in args):
                    raise Desconhecido(val)
                return float(FUNCOES[val](*args))
            if val in self.vars:
                return self.vars[val]
            if val in CONSTANTES:
                return CONSTANTES[val]
            raise Desconhecido(val)
        raise Desconhecido(str(val))

    def _esperar(self, s):
        tipo, val = self._comer()
        if val != s:
            raise Desconhecido(f"esperava {s}")


def avaliar(texto, pos=0, variaveis=None):
    """(valor, posição final). Lança Desconhecido se não der para calcular."""
    e = Expressao(texto, pos, variaveis or {})
    v = e.expr()
    return v, e.p


def variaveis(texto, ate=None, clock=0.0):
    """Valores dos #declare numéricos/vetoriais simples (na ordem do arquivo)."""
    m = mascarar(texto)
    vs = {"clock": clock, "image_width": 640.0, "image_height": 480.0}
    for d in re.finditer(r"#(?:declare|local)\s+([A-Za-z_]\w*)\s*=", m):
        if ate is not None and d.start() > ate:
            break
        try:
            v, fim = avaliar(m, d.end(), vs)
            resto = m[fim:fim + 3].lstrip()
            if resto.startswith(";") or not resto:
                vs[d.group(1)] = v
        except (Desconhecido, ValueError, ZeroDivisionError, OverflowError, TypeError):
            pass
    return vs


# ==================================================================== transformações de um bloco

RX_TRANSF = re.compile(r"\b(translate|rotate|scale|matrix)\b")


def transformacoes(texto, bloco, vs, mascara=None):
    """Transformações escritas direto no bloco (fora dos blocos filhos, menos transform { }),
    em ordem: lista de (tipo, valor ou None, texto original, posição)."""
    m = mascara if mascara is not None else mascarar(texto)
    fim = bloco.fecha if bloco.fecha is not None else len(m)
    # trechos do corpo que não estão dentro de blocos filhos (exceto transform { })
    pulos = [(f.abre, f.fecha or fim) for f in bloco.filhos if f.kw not in ("transform",)]
    lista = []
    for mt in RX_TRANSF.finditer(m, bloco.abre + 1, fim):
        if any(a <= mt.start() <= b for a, b in pulos):
            continue
        tipo = mt.group(1)
        try:
            val, p = avaliar(m, mt.end(), vs)
            if tipo == "matrix" and not isinstance(val, tuple):
                raise Desconhecido("matrix")
        except (Desconhecido, ValueError, ZeroDivisionError, OverflowError, TypeError) as ex:
            val, p = None, mt.end()
            seg = re.match(r"\s*(<[^>]*>|[^\s{}]+)", m[mt.end():])
            if seg:
                p = mt.end() + seg.end()
            lista.append((tipo, None, texto[mt.start():p].strip(), mt.start(), str(ex)))
            continue
        if tipo == "matrix":
            # matrix tem 12 números: <a,b,c, d,e,f, g,h,i, tx,ty,tz>
            nums = re.match(r"\s*<([^>]*)>", m[mt.end():])
            try:
                vals = [avaliar(x.strip(), 0, vs)[0] for x in nums.group(1).split(",")] if nums else []
                if len(vals) != 12 or any(isinstance(v, tuple) for v in vals):
                    raise Desconhecido("matrix precisa de 12 números")
                val = tuple(vals)
                p = mt.end() + nums.end()
            except Desconhecido as ex:
                lista.append((tipo, None, texto[mt.start():mt.end() + (nums.end() if nums else 0)].strip(),
                              mt.start(), str(ex)))
                continue
        lista.append((tipo, val, texto[mt.start():p].strip(), mt.start(), None))
    return lista


def primeiro_ponto(texto, bloco, vs, mascara=None):
    """Primeiro vetor literal do bloco (centro da esfera, canto da caixa...), se houver."""
    m = mascara if mascara is not None else mascarar(texto)
    corpo = m[bloco.abre + 1:(bloco.fecha or len(m))]
    mm = re.match(r"\s*<", corpo)
    if not mm:
        return None
    try:
        v, _ = avaliar(m, bloco.abre + 1, vs)
        return v if isinstance(v, tuple) else None
    except (Desconhecido, ValueError, ZeroDivisionError, TypeError):
        return None


def declarados(texto, todos=None):
    """{nome: bloco} dos objetos declarados com #declare Nome = algo { ... }."""
    return {b.declarado: b for b in (todos or blocos(texto)) if b.declarado}
