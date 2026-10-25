"""Prévia instantânea (OpenGL) enquanto você mexe na câmera, arrasta números ou objetos.

O POV-Ray leva ~0,75 s por render, então durante o movimento o app desenha uma versão
aproximada da cena com OpenGL (mais de 60 quadros por segundo) e, ao soltar o mouse, volta
para o render de verdade.

Duas partes:
  - interpretar(): executa o básico da linguagem (#declare, #for, #while, #if) e transforma
    os objetos em triângulos (esfera, caixa, cilindro, cone, toro, disco, plano, prisma,
    lathe, blob, CSG). difference/intersection são recortadas de verdade (csg.py). É uma
    aproximação: texturas viram uma cor, não há sombras, e texto/malhas não aparecem.
  - Renderizador: desenha os triângulos numa área invisível do OpenGL e devolve um QImage.
"""
import math, os, re

import numpy as np

from . import sdl, matrizes, pov, csg

LIMITE_TRIANGULOS = 400_000
LIMITE_ITERACOES = 20_000


# ==================================================================== malhas (coordenadas locais)

def _grade_esfera(nu=28, nv=16):
    u = np.linspace(0, 2 * np.pi, nu + 1)
    v = np.linspace(-np.pi / 2, np.pi / 2, nv + 1)
    P = np.stack([np.cos(v)[None, :] * np.cos(u)[:, None], np.sin(v)[None, :].repeat(nu + 1, 0),
                  np.cos(v)[None, :] * np.sin(u)[:, None]], -1)
    return _quads(P)


def _quads(P):
    """Grade (n+1, m+1, 3) -> triângulos (2nm, 3, 3)."""
    a, b, c, d = P[:-1, :-1], P[1:, :-1], P[1:, 1:], P[:-1, 1:]
    t1 = np.stack([a, b, c], -2).reshape(-1, 3, 3)
    t2 = np.stack([a, c, d], -2).reshape(-1, 3, 3)
    return np.concatenate([t1, t2])


ESFERA = _grade_esfera()


def caixa(a, b):
    a, b = np.minimum(a, b), np.maximum(a, b)
    x0, y0, z0 = a
    x1, y1, z1 = b
    v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
    f = [(0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6), (0, 4, 5), (0, 5, 1),
         (3, 2, 6), (3, 6, 7), (0, 3, 7), (0, 7, 4), (1, 5, 6), (1, 6, 2)]
    return v[np.array(f)]


def _base_ortonormal(eixo):
    eixo = eixo / (np.linalg.norm(eixo) or 1)
    aux = np.array([1.0, 0, 0]) if abs(eixo[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(eixo, aux)
    e1 /= np.linalg.norm(e1)
    return e1, np.cross(eixo, e1)


def tronco(a, r1, b, r2, aberto=False, n=32):
    """Cilindro (r1 == r2) ou cone/tronco de a até b."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    eixo = b - a
    if np.linalg.norm(eixo) < 1e-9:
        return np.zeros((0, 3, 3))
    e1, e2 = _base_ortonormal(eixo)
    t = np.linspace(0, 2 * np.pi, n + 1)
    circ = np.cos(t)[:, None] * e1 + np.sin(t)[:, None] * e2
    P = np.stack([a + r1 * circ, b + r2 * circ], 1)          # (n+1, 2, 3)
    tris = [_quads(P)]
    if not aberto:
        for centro, r in ((a, r1), (b, r2)):
            if r > 0:
                anel = centro + r * circ
                tris.append(np.stack([np.repeat(centro[None], n, 0), anel[:-1], anel[1:]], 1))
    return np.concatenate(tris)


def toro(R, r, nu=40, nv=16):
    u = np.linspace(0, 2 * np.pi, nu + 1)[:, None]
    v = np.linspace(0, 2 * np.pi, nv + 1)[None, :]
    P = np.stack([(R + r * np.cos(v)) * np.cos(u), (r * np.sin(v)).repeat(nu + 1, 0),
                  (R + r * np.cos(v)) * np.sin(u)], -1)
    return _quads(P)


def disco(c, normal, r, furo=0.0, n=32):
    c = np.asarray(c, float)
    e1, e2 = _base_ortonormal(np.asarray(normal, float))
    t = np.linspace(0, 2 * np.pi, n + 1)
    circ = np.cos(t)[:, None] * e1 + np.sin(t)[:, None] * e2
    P = np.stack([c + furo * circ, c + r * circ], 1)
    return _quads(P)


def revolucao(perfil, n=32):
    """lathe/sor: perfil de pontos <raio, altura> girando em torno de y."""
    pts = np.asarray(perfil, float)
    t = np.linspace(0, 2 * np.pi, n + 1)
    P = np.stack([pts[None, :, 0] * np.cos(t)[:, None], pts[None, :, 1].repeat(n + 1, 0),
                  pts[None, :, 0] * np.sin(t)[:, None]], -1)
    return _quads(P)


def prisma(y1, y2, pontos):
    pts = np.asarray(pontos, float)
    if len(pts) > 1 and np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]
    n = len(pts)
    if n < 3:
        return np.zeros((0, 3, 3))
    baixo = np.stack([pts[:, 0], np.full(n, y1), pts[:, 1]], 1)
    cima = np.stack([pts[:, 0], np.full(n, y2), pts[:, 1]], 1)
    lados = []
    for i in range(n):
        j = (i + 1) % n
        lados += [[baixo[i], baixo[j], cima[j]], [baixo[i], cima[j], cima[i]]]
    tampas = [[baixo[0], baixo[i], baixo[i + 1]] for i in range(1, n - 1)]
    tampas += [[cima[0], cima[i + 1], cima[i]] for i in range(1, n - 1)]
    return np.array(lados + tampas)


def chao(normal, d, alcance=40, passo=1.0):
    """Plano como ladrilhos de 1 unidade (como o checker do POV-Ray)."""
    n = np.asarray(normal, float)
    n = n / (np.linalg.norm(n) or 1)
    e1, e2 = _base_ortonormal(n)
    if abs(n[1]) > 0.99:  # chão/teto: ladrilhos alinhados com x e z
        e1, e2 = np.array([1.0, 0, 0]), np.array([0, 0, 1.0])
    c0 = n * d
    k = np.arange(-alcance, alcance) * passo
    I, J = np.meshgrid(k, k, indexing="ij")
    canto = c0 + I[..., None] * e1 + J[..., None] * e2
    a, b, c, dd = canto, canto + passo * e1, canto + passo * (e1 + e2), canto + passo * e2
    t1 = np.stack([a, b, c], -2).reshape(-1, 3, 3)
    t2 = np.stack([a, c, dd], -2).reshape(-1, 3, 3)
    par = ((I + J).astype(int) % 2 == 0).reshape(-1)
    return np.concatenate([t1, t2]), np.concatenate([par, par])


# ==================================================================== cena

class Peca:
    """Triângulos de um objeto já no mundo, com cor e o bloco do código que o gerou."""
    __slots__ = ("tris", "cor", "cor2", "xadrez", "alfa", "topo", "solido")

    def __init__(self, tris, cor, topo, cor2=None, xadrez=None, alfa=1.0, solido=None):
        self.tris, self.cor, self.topo = tris, cor, topo
        self.cor2, self.xadrez, self.alfa = cor2, xadrez, alfa
        self.solido = solido      # csg.Solido do objeto (para difference/intersection), ou None


class Operandos(list):
    """Lista de peças que lembra onde termina cada objeto (cada operando de um CSG)."""

    def __init__(self):
        super().__init__()
        self.fins = []

    def marcar(self):
        if not self.fins or self.fins[-1] != len(self):
            self.fins.append(len(self))

    def grupos(self):
        ini, r = 0, []
        for f in self.fins:
            r.append(self[ini:f])
            ini = f
        if ini < len(self):
            r.append(self[ini:])
        return r


class Cena3D:
    def __init__(self):
        self.pecas = []
        self.luz = None
        self.fundo = (0.0, 0.0, 0.0)
        self.aviso = None
        self.gama = False      # assumed_gamma 1.0: as cores são lineares e clareiam na saída
        self.camera = None     # {"location", "look_at", "angle", "orto"} já com as transformações

    def n_triangulos(self):
        return sum(len(p.tris) for p in self.pecas)


_cores_padrao = None


def cores_padrao():
    """Cores do colors.inc (Red, SkyBlue, ...) para a prévia."""
    global _cores_padrao
    if _cores_padrao is None:
        _cores_padrao = {}
        for d in pov.BIBLIOTECA:
            c = os.path.join(d, "colors.inc")
            if os.path.exists(c):
                _cores_padrao = {k: (v if isinstance(v, tuple) else (v, v, v))
                                 for k, v in sdl.variaveis(open(c, encoding="latin-1").read()).items()}
    return _cores_padrao


RX_DIRETIVA = re.compile(r"#\s*(declare|local|for|while|if|ifdef|ifndef|else|elseif|end|macro|switch|case|"
                         r"range|break|include|version|debug|warning|error|default|undef|fopen|fclose|read|write)\b")
ABRE = {"for", "while", "if", "ifdef", "ifndef", "macro", "switch"}


# cores aproximadas das texturas prontas (textures.inc, metals.inc, woods.inc, stones.inc, glass.inc)
TEXTURAS_PRONTAS = [
    (r"\bT_Gold|\bGold_", (0.85, 0.65, 0.2)), (r"\bT_(Silver|Chrome)|\bSilver_|\bChrome_", (0.75, 0.75, 0.78)),
    (r"\bT_Copper|\bCopper_", (0.75, 0.4, 0.25)), (r"\bT_Brass|\bBrass_", (0.75, 0.6, 0.3)),
    (r"\bT_Wood|\bDMFWood|\bCherry_Wood|\bPine_Wood|\bWood_", (0.55, 0.35, 0.18)),
    (r"\bT_Stone|\bT_Grnt|\bGranite|\bMarble|\bJade", (0.62, 0.58, 0.52)),
    (r"\bT_Glass|\bT_Ruby_Glass|\bGlass", (0.9, 0.95, 0.95, 0.9)),
]


def _cor_de_textura_pronta(trecho):
    for rx, cor in TEXTURAS_PRONTAS:
        if re.search(rx, trecho):
            return cor
    return None


_cache_csg = {}    # chave do bloco CSG -> (peças no sistema do bloco, sólido)


class Interpretador:
    def __init__(self, texto, pasta="", clock=0.0, includes=None):
        self.texto = texto
        self.m = sdl.mascarar(texto)
        self.todos = sdl.blocos(texto, self.m)
        self.por_abre = {b.abre: b for b in self.todos}
        self.vs = dict(cores_padrao())
        self.vs.update({"clock": clock, "image_width": 640.0, "image_height": 480.0})
        self.declarados = {}      # nome -> Bloco
        self.macros = {}          # nome -> (parâmetros, início do corpo, fim do corpo)
        self.cena = Cena3D()
        self.iteracoes = 0
        self.pasta = pasta
        self.includes = includes or {}

    # ----------------------------------------------------------------- execução

    def executar(self, ini, fim, saida, topo=None, cor=None, dentro_de=None):
        m = self.m
        i = ini
        while i < fim:
            c = m[i]
            if c.isspace() or c in ";,":
                i += 1
                continue
            if c == "#":
                i = self._diretiva(i, fim, saida, topo, cor, dentro_de)
                continue
            mk = re.match(r"([A-Za-z_]\w*)\s*\{", m[i:fim])
            if mk:
                abre = i + mk.end() - 1
                b = self.por_abre.get(abre)
                if b is None or b.fecha is None:
                    return
                self._bloco(b, saida, topo, cor, dentro_de)
                i = b.fecha + 1
                continue
            mm = re.match(r"([A-Za-z_]\w*)\s*\(", m[i:fim])
            if mm and mm.group(1) in self.macros:
                i = self._chamar_macro(mm.group(1), i + mm.end() - 1, saida, topo, cor, dentro_de)
                continue
            mi = re.match(r"[A-Za-z_]\w*|\S", m[i:fim])
            i += mi.end() if mi else 1

    def _achar_fim(self, i, fim):
        """Posição do #end (e dos #else) que fecham a diretiva que começa em i."""
        nivel, meios = 0, []
        for md in RX_DIRETIVA.finditer(self.m, i, fim):
            d = md.group(1)
            if d in ABRE:
                nivel += 1
            elif d == "end":
                nivel -= 1
                if nivel == 0:
                    return md.start(), md.end(), meios
            elif d in ("else", "elseif") and nivel == 1:
                meios.append((md.start(), md.end(), d))
        return fim, fim, meios

    def _parenteses(self, i):
        """(início, fim) do primeiro ( ... ) a partir de i."""
        a = self.m.index("(", i)
        nivel = 0
        for k in range(a, len(self.m)):
            if self.m[k] == "(":
                nivel += 1
            elif self.m[k] == ")":
                nivel -= 1
                if nivel == 0:
                    return a, k + 1
        raise sdl.Desconhecido("parênteses")

    def _diretiva(self, i, fim, saida, topo, cor, dentro_de):
        m = self.m
        md = RX_DIRETIVA.match(m, i)
        if not md:
            return i + 1
        d = md.group(1)
        j = md.end()
        try:
            if d in ("declare", "local"):
                mn = re.match(r"\s*([A-Za-z_]\w*)\s*=\s*", m[j:fim])
                if not mn:
                    return j
                nome, k = mn.group(1), j + mn.end()
                mb = re.match(r"([A-Za-z_]\w*)\s*\{", m[k:fim])
                if mb and mb.group(1) not in ("rgb", "color"):
                    b = self.por_abre.get(k + mb.end() - 1)
                    if b is not None:
                        self.declarados[nome] = b
                        return (b.fecha or fim) + 1
                try:
                    v, p = sdl.avaliar(m, k, self.vs)
                    self.vs[nome] = v
                    return p
                except (sdl.Desconhecido, ValueError, ZeroDivisionError, OverflowError, TypeError):
                    fim_decl = m.find(";", k, fim)
                    return fim_decl + 1 if fim_decl >= 0 else fim
            if d == "for":
                a, b = self._parenteses(j)
                args = [x.strip() for x in m[a + 1:b - 1].split(",")]
                var = args[0]
                v0 = sdl.avaliar(args[1], 0, self.vs)[0]
                v1 = sdl.avaliar(args[2], 0, self.vs)[0]
                passo = sdl.avaliar(args[3], 0, self.vs)[0] if len(args) > 3 else 1.0
                ini_end, fim_end, _ = self._achar_fim(i, fim)
                v = v0
                while (v <= v1 + 1e-9 if passo > 0 else v >= v1 - 1e-9) and passo != 0:
                    self.iteracoes += 1
                    if self.iteracoes > LIMITE_ITERACOES:
                        self.cena.aviso = "laço grande demais para a prévia"
                        break
                    self.vs[var] = float(v)
                    self.executar(b, ini_end, saida, topo, cor, dentro_de)
                    v += passo
                return fim_end
            if d == "while":
                a, b = self._parenteses(j)
                ini_end, fim_end, _ = self._achar_fim(i, fim)
                while sdl.avaliar_condicao(m, a, b, self.vs):
                    self.iteracoes += 1
                    if self.iteracoes > LIMITE_ITERACOES:
                        self.cena.aviso = "laço grande demais para a prévia"
                        break
                    self.executar(b, ini_end, saida, topo, cor, dentro_de)
                return fim_end
            if d in ("if", "ifdef", "ifndef"):
                a, b = self._parenteses(j)
                ini_end, fim_end, meios = self._achar_fim(i, fim)
                if d == "if":
                    cond = sdl.avaliar_condicao(m, a, b, self.vs)
                else:
                    nome = m[a + 1:b - 1].strip()
                    existe = nome in self.vs or nome in self.declarados
                    cond = existe if d == "ifdef" else not existe
                trechos = [(b, meios[0][0] if meios else ini_end, cond)]
                for k, (s_ini, s_fim, tipo) in enumerate(meios):
                    prox = meios[k + 1][0] if k + 1 < len(meios) else ini_end
                    if tipo == "elseif":
                        a2, b2 = self._parenteses(s_fim)
                        trechos.append((b2, prox, None, (a2, b2)))
                    else:
                        trechos.append((s_fim, prox, True))
                for t in trechos:
                    ok = t[2] if t[2] is not None else sdl.avaliar_condicao(m, t[3][0], t[3][1], self.vs)
                    if ok:
                        self.executar(t[0], t[1], saida, topo, cor, dentro_de)
                        break
                return fim_end
            if d == "macro":
                mn = re.match(r"\s*([A-Za-z_]\w*)\s*\(([^)]*)\)", m[j:fim])
                ini_end, fim_end, _ = self._achar_fim(i, fim)
                if mn:
                    params = [x.strip() for x in mn.group(2).split(",") if x.strip()]
                    self.macros[mn.group(1)] = (params, j + mn.end(), ini_end)
                return fim_end
            if d == "switch":
                return self._achar_fim(i, fim)[1]
            if d == "include":
                mi = re.search(r'"([^"]+)"', self.texto[j:j + 300])
                if mi:
                    self._incluir(mi.group(1))
                    return j + mi.end()
                return j
        except (sdl.Desconhecido, ValueError, ZeroDivisionError, OverflowError, TypeError, IndexError):
            if d in ABRE:
                return self._achar_fim(i, fim)[1]
        # #version, #debug... : até o fim da linha
        k = m.find("\n", j)
        return fim if k < 0 or k > fim else k + 1

    def _chamar_macro(self, nome, abre_par, saida, topo, cor, dentro_de):
        """Executa o corpo da macro com os parâmetros ligados aos argumentos."""
        params, ini, fim = self.macros[nome]
        nivel, k = 0, abre_par
        while k < len(self.m):
            if self.m[k] == "(":
                nivel += 1
            elif self.m[k] == ")":
                nivel -= 1
                if nivel == 0:
                    break
            k += 1
        args = sdl._dividir_fora_de_parenteses(self.m[abre_par + 1:k], ",")
        antes = {p_: self.vs.get(p_) for p_ in params}
        try:
            for p_, a in zip(params, args):
                v = self.vs.get(a.strip()) if a.strip() in self.vs else sdl.avaliar(a, 0, self.vs)[0]
                self.vs[p_] = v
            self.iteracoes += 1
            if self.iteracoes <= LIMITE_ITERACOES:
                self.executar(ini, fim, saida, topo, cor, dentro_de)
        except (sdl.Desconhecido, ValueError, TypeError, ZeroDivisionError):
            pass
        finally:
            for p_, v in antes.items():
                if v is None:
                    self.vs.pop(p_, None)
                else:
                    self.vs[p_] = v
        return k + 1

    def _incluir(self, nome):
        """Declarações de .inc locais (cores, objetos simples) entram nas variáveis."""
        caminho = pov.achar_include(nome, self.pasta) if self.pasta else None
        if caminho in self.includes:
            texto = self.includes[caminho]
        elif caminho and not caminho.startswith(tuple(pov.BIBLIOTECA)):
            texto = open(caminho, encoding="utf-8", errors="replace").read()
        else:
            return
        self.vs.update(sdl.variaveis(texto, clock=self.vs.get("clock", 0.0)))

    # ----------------------------------------------------------------- blocos

    def _bloco(self, b, saida, topo, cor, dentro_de):
        kw = b.kw
        if kw == "light_source":
            if self.cena.luz is None:
                try:
                    v, _ = sdl.avaliar(self.m, b.abre + 1, self.vs)
                    if isinstance(v, tuple):
                        self.cena.luz = np.array(v)
                except (sdl.Desconhecido, ValueError, TypeError, ZeroDivisionError):
                    pass
            return
        if kw == "camera":
            self._camera(b)
            return
        if kw == "background":
            c = self._cor_em(b.abre + 1, b.fecha)
            if c is not None:
                self.cena.fundo = c
            return
        if kw in sdl.OBJETOS:
            self._objeto(b, saida, topo or b, cor)

    def _camera(self, b):
        """Câmera da cena (a última vale), com as transformações do próprio bloco."""
        m, corpo_ini, corpo_fim = self.m, b.abre + 1, b.fecha
        cam = {"location": np.zeros(3), "look_at": np.array([0, 0, 1.0]), "angle": None, "orto": None}
        sub = m[corpo_ini:corpo_fim]
        for chave in ("location", "look_at", "angle", "up", "right"):
            for mc in re.finditer(r"\b" + chave + r"\b", sub):
                try:
                    v, _ = sdl.avaliar(m, corpo_ini + mc.end(), self.vs)
                except (sdl.Desconhecido, ValueError, TypeError, ZeroDivisionError):
                    continue
                if chave == "angle" and not isinstance(v, tuple):
                    cam["angle"] = v
                elif chave == "up" and isinstance(v, tuple):
                    cam["up"] = np.linalg.norm(v)
                elif chave in ("location", "look_at"):
                    cam[chave] = np.array(v if isinstance(v, tuple) else (v, v, v), float)
        if re.search(r"\borthographic\b", sub):
            cam["orto"] = cam.get("up", 2 * np.linalg.norm(cam["look_at"] - cam["location"]) * 0.5) / 2
        M = self._matriz(b)
        if not np.allclose(M, np.eye(4)):
            for k in ("location", "look_at"):
                cam[k] = M[:3, :3] @ cam[k] + M[:3, 3]
        self.cena.camera = cam

    def _cores(self, ini, fim, maximo=2):
        """Cores do trecho, em ordem (rgb <...>, color Nome, Nome)."""
        m, cores, p = self.m, [], ini
        rx = re.compile(r"\b(?:rgb[ft]{0,2}|srgb|color|colour)\b|\b([A-Z]\w*)\b")
        while len(cores) < maximo:
            mc = rx.search(m, p, fim)
            if not mc:
                break
            p = mc.end()
            if mc.group(1):
                v = self.vs.get(mc.group(1))
                if isinstance(v, (int, float)):
                    v = (v, v, v)
                if isinstance(v, tuple):
                    cores.append(tuple(float(x) for x in v))
                continue
            try:
                e = sdl.Expressao(m, mc.start(), self.vs)
                v = e.expr()
                p = max(p, e.p)
            except (sdl.Desconhecido, ValueError, TypeError, ZeroDivisionError):
                continue
            if isinstance(v, (int, float)):
                v = (v, v, v)
            filtro = max(e.extras) if e.extras else 0.0
            cores.append(tuple(float(x) for x in v) + ((filtro,) if filtro else ()))
        return cores

    def _cor_em(self, ini, fim):
        c = self._cores(ini, fim, 1)
        return c[0] if c else None

    def _aparencia(self, b, cor_herdada):
        cor, cor2 = cor_herdada, None
        for f in b.filhos:
            if f.kw in ("pigment", "texture", "material"):
                pronta = _cor_de_textura_pronta(self.m[f.abre + 1:f.fecha])
                if pronta is not None:
                    cor = pronta
                    continue
                cs = self._cores(f.abre + 1, f.fecha)
                if cs:
                    cor = cs[0]
                    if re.search(r"\bchecker\b", self.m[f.abre + 1:f.fecha]) and len(cs) > 1:
                        cor2 = cs[1][:3]
        return cor, cor2

    def _args(self, b):
        """Argumentos iniciais separados por vírgula (centro, raio...)."""
        vals, p = [], b.abre + 1
        for _ in range(16):
            try:
                v, p2 = sdl.avaliar(self.m, p, self.vs)
            except (sdl.Desconhecido, ValueError, TypeError, ZeroDivisionError):
                break
            vals.append(v)
            mv = re.match(r"\s*,", self.m[p2:])
            if not mv:
                break
            p = p2 + mv.end()
        return vals

    def _matriz(self, b):
        total = matrizes.ident()
        for tipo, val, _orig, _pos, erro in sdl.transformacoes(self.texto, b, self.vs, self.m):
            if val is None:
                continue
            for _n, mat, _e in matrizes.passos_de(tipo, val, ""):
                total = matrizes.mul(mat, total)
        return np.array(total)

    def _objeto(self, b, saida, topo, cor_herdada):
        kw = b.kw
        cor, cor2 = self._aparencia(b, cor_herdada)
        locais = []
        try:
            locais = self._geometria(b, kw, cor, topo)
        except (sdl.Desconhecido, ValueError, TypeError, ZeroDivisionError, IndexError):
            locais = []
        if not locais and kw not in ("union", "merge", "difference", "intersection", "object", "blob"):
            return
        M = self._matriz(b)
        solidos = {}
        for p in locais:
            if p.solido is not None:
                if id(p.solido) not in solidos:
                    solidos[id(p.solido)] = p.solido.transformado(M)
                p.solido = solidos[id(p.solido)]
            if p.cor is None:
                p.cor = cor
            if cor2 is not None and p.xadrez is not None and p.cor2 is None:
                p.cor2 = cor2
            pts = p.tris.reshape(-1, 3)
            pts = pts @ M[:3, :3].T + M[:3, 3]
            p.tris = pts.reshape(-1, 3, 3)
            saida.append(p)
        if isinstance(saida, Operandos):
            saida.marcar()

    def _geometria(self, b, kw, cor, topo):
        a = self._args(b)
        corpo = self.m[b.abre + 1:b.fecha]
        aberto = bool(re.search(r"\bopen\b", corpo))
        v3 = lambda v: np.array(v if isinstance(v, tuple) else (v, v, v), float)
        if kw == "sphere":
            return [Peca(ESFERA * float(a[1]) + v3(a[0]), cor, topo, solido=csg.esfera(v3(a[0]), float(a[1])))]
        if kw == "box":
            return [Peca(caixa(v3(a[0]), v3(a[1])), cor, topo, solido=csg.caixa(v3(a[0]), v3(a[1])))]
        if kw == "cylinder":
            return [Peca(tronco(v3(a[0]), float(a[2]), v3(a[1]), float(a[2]), aberto), cor, topo,
                         solido=csg.tronco(v3(a[0]), float(a[2]), v3(a[1]), float(a[2])))]
        if kw == "cone":
            return [Peca(tronco(v3(a[0]), float(a[1]), v3(a[2]), float(a[3]), aberto), cor, topo,
                         solido=csg.tronco(v3(a[0]), float(a[1]), v3(a[2]), float(a[3])))]
        if kw == "torus":
            return [Peca(toro(float(a[0]), float(a[1])), cor, topo, solido=csg.toro(float(a[0]), float(a[1])))]
        if kw == "disc":
            return [Peca(disco(v3(a[0]), v3(a[1]), float(a[2]), float(a[3]) if len(a) > 3 else 0), cor, topo)]
        if kw == "plane":
            tris, par = chao(v3(a[0]), float(a[1]))
            return [Peca(tris, cor, topo, xadrez=par, solido=csg.plano(v3(a[0]), float(a[1])))]
        if kw in ("lathe", "sor"):
            mm = re.match(r"\s*(linear_spline|quadratic_spline|cubic_spline|bezier_spline)?", corpo)
            vals = self._args_a_partir(b.abre + 1 + mm.end())
            n = int(vals[0]) if vals and not isinstance(vals[0], tuple) else 0
            pts = [v[:2] for v in vals[1:1 + n] if isinstance(v, tuple)]
            if (kw == "sor" or (mm.group(1) or "").startswith(("cubic", "quadratic"))) and len(pts) > 3:
                pts = pts[1:-1]   # nesses tipos, o primeiro e o último ponto só controlam a curva
            return [Peca(revolucao(pts), cor, topo, solido=csg.revolucao(pts))] if len(pts) >= 2 else []
        if kw == "prism":
            mm = re.match(r"\s*(?:linear_sweep|conic_sweep|linear_spline|quadratic_spline|cubic_spline|bezier_spline|\s)*",
                          corpo)
            vals = self._args_a_partir(b.abre + 1 + mm.end())
            if len(vals) >= 4:
                y1, y2, n = float(vals[0]), float(vals[1]), int(vals[2])
                pts = [v[:2] for v in vals[3:3 + n] if isinstance(v, tuple)]
                return [Peca(prisma(y1, y2, pts), cor, topo, solido=csg.prisma(y1, y2, pts))]
            return []
        if kw == "superellipsoid":
            return [Peca(ESFERA.copy(), cor, topo, solido=csg.esfera((0, 0, 0), 1.0))]
        if kw == "blob":
            return self._blob(b, cor, topo)
        if kw in ("difference", "intersection"):
            chave = self._chave_csg(b, cor)
            guardado = _cache_csg.get(chave)
            if guardado is not None:
                pecas_g, solido = guardado
                return [Peca(t, c, topo, c2, x, al, solido) for t, c, c2, x, al in pecas_g]
            ops = Operandos()
            self.executar(b.abre + 1, b.fecha, ops, topo, cor, b)
            grupos = [g for g in ops.grupos() if g]
            if not grupos:
                return []
            pecas, solido = csg.combinar(grupos, kw)
            if len(_cache_csg) > 64:
                _cache_csg.pop(next(iter(_cache_csg)))
            _cache_csg[chave] = ([(p.tris, p.cor, p.cor2, p.xadrez, p.alfa) for p in pecas], solido)
            return pecas
        if kw in ("union", "merge"):
            filhos = []
            self.executar(b.abre + 1, b.fecha, filhos, topo, cor, b)
            return filhos
        if kw == "object":
            mn = re.match(r"\s*([A-Za-z_]\w*)\s*(\()?", corpo)
            if mn and mn.group(2) and mn.group(1) in self.macros:
                tmp = []
                self._chamar_macro(mn.group(1), b.abre + 1 + mn.end() - 1, tmp, topo, cor, b)
                return tmp
            if mn and mn.group(1) in self.declarados:
                d = self.declarados[mn.group(1)]
                tmp = []
                self._objeto(d, tmp, topo, cor)
                return tmp
            return []
        return []

    def _chave_csg(self, b, cor):
        """O que define o resultado de um CSG: o texto do bloco e o valor de cada nome que ele usa
        (variáveis, objetos declarados e macros, até 3 níveis). Assim, arrastar um número em outro
        objeto não refaz o recorte."""
        corpo = list(self.m[b.abre:b.fecha])
        for _t, _v, orig, pos, _e in sdl.transformacoes(self.texto, b, self.vs, self.m):
            for k in range(pos - b.abre, min(len(corpo), pos - b.abre + len(orig))):
                corpo[k] = " "      # as transformações do próprio bloco não mudam o recorte
        corpo = "".join(corpo)
        partes, vistos = [corpo, repr(cor)], set()
        trechos = [corpo]
        for _ in range(3):
            novos = []
            for t in trechos:
                for nome in set(re.findall(r"[A-Za-z_]\w*", t)) - vistos:
                    vistos.add(nome)
                    if nome in self.declarados:
                        d = self.declarados[nome]
                        novos.append(self.m[d.kw_ini:(d.fecha or d.abre) + 1])
                        partes.append(nome + "=" + novos[-1])
                    elif nome in self.macros:
                        _ps, ini, fim = self.macros[nome]
                        novos.append(self.m[ini:fim])
                        partes.append(nome + "=" + novos[-1])
                    elif nome in self.vs:
                        partes.append(f"{nome}={self.vs[nome]!r}")
            trechos = novos
        return "\x00".join(partes)

    def _args_a_partir(self, p):
        vals = []
        for _ in range(400):
            try:
                v, p2 = sdl.avaliar(self.m, p, self.vs)
            except (sdl.Desconhecido, ValueError, TypeError, ZeroDivisionError):
                break
            vals.append(v)
            mv = re.match(r"\s*,", self.m[p2:])
            if not mv:
                break
            p = p2 + mv.end()
        return vals

    def _blob(self, b, cor, topo):
        pecas = []
        for f in b.filhos:
            if f.kw in ("sphere", "cylinder"):
                a = self._args(f)
                try:
                    if f.kw == "sphere":
                        c, r = np.array(a[0], float), float(a[1]) * 0.75
                        pecas.append(Peca(ESFERA * r + c, cor, topo, solido=csg.esfera(c, r)))
                except (IndexError, TypeError, ValueError):
                    pass
        return pecas


def interpretar(texto, pasta="", clock=0.0, includes=None):
    it = Interpretador(texto, pasta, clock, includes)
    saida = []
    it.executar(0, len(it.m), saida)
    cena = it.cena
    cena.pecas = saida
    cena.gama = bool(re.search(r"assumed_gamma\s+1(\.0*)?\b", it.m))
    total = cena.n_triangulos()
    if total > LIMITE_TRIANGULOS:
        cena.aviso = "cena grande demais para a prévia"
        cena.pecas = []
    return cena


# ==================================================================== desenho (OpenGL)

def _sombreamento(tris, cor, luz):
    """Cor por triângulo: luz difusa simples dos dois lados + ambiente."""
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    centro = tris.mean(axis=1)
    L = luz[None, :] - centro
    L /= np.linalg.norm(L, axis=1, keepdims=True) + 1e-12
    k = 0.35 + 0.65 * np.abs((n * L).sum(1))
    return np.clip(np.asarray(cor[:3])[None, :] * k[:, None], 0, 1)


class Renderizador:
    """Desenha a Cena3D numa área invisível do OpenGL. disponivel=False se não houver OpenGL."""

    def __init__(self):
        self.disponivel = False
        self.ctx = None
        self.fbos = {}
        try:
            import OpenGL
            OpenGL.ERROR_CHECKING = False
            from OpenGL import GL  # noqa: F401
            from PyQt5.QtGui import QOpenGLContext, QOffscreenSurface
            self.ctx = QOpenGLContext()
            if not self.ctx.create():
                return
            self.sup = QOffscreenSurface()
            self.sup.setFormat(self.ctx.format())
            self.sup.create()
            if not self.sup.isValid() or not self.ctx.makeCurrent(self.sup):
                return
            self.GL = GL
            self.disponivel = True
            self.ctx.doneCurrent()
        except Exception:
            self.disponivel = False

    def _fbo(self, w, h):
        from PyQt5.QtGui import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat
        if (w, h) not in self.fbos:
            f = QOpenGLFramebufferObjectFormat()
            f.setAttachment(QOpenGLFramebufferObject.Depth)
            f.setSamples(4)
            self.fbos = {(w, h): QOpenGLFramebufferObject(w, h, f)}
        return self.fbos[(w, h)]

    def desenhar(self, cena, pos, alvo, fov, w, h, orto=None, linhas=()):
        """QImage w×h da cena vista da câmera. orto = metade da altura visível (câmera ortográfica)."""
        GL = self.GL
        self.ctx.makeCurrent(self.sup)
        fbo = self._fbo(w, h)
        fbo.bind()
        GL.glViewport(0, 0, w, h)
        self.gama = cena.gama
        fr, fg, fb = (c ** (1 / 2.2) if cena.gama else c for c in cena.fundo[:3])
        GL.glClearColor(fr, fg, fb, 1)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_CULL_FACE)

        pos, alvo = np.asarray(pos, float), np.asarray(alvo, float)
        f = alvo - pos
        f /= np.linalg.norm(f) or 1
        r = np.cross([0, 1, 0], f)
        if np.linalg.norm(r) < 1e-9:
            r = np.array([1.0, 0, 0])
        r /= np.linalg.norm(r)
        u = np.cross(f, r)
        V = np.eye(4)
        V[0, :3], V[1, :3], V[2, :3] = r, u, -f
        V[:3, 3] = -V[:3, :3] @ pos
        aspecto = w / h
        perto, longe = 0.05, 2000.0
        P = np.zeros((4, 4))
        if orto:
            P[0, 0], P[1, 1] = 1 / (orto * aspecto), 1 / orto
            P[2, 2], P[2, 3], P[3, 3] = -2 / (longe - perto), -(longe + perto) / (longe - perto), 1
        else:
            th = math.tan(fov / 2)
            P[0, 0], P[1, 1] = 1 / th, aspecto / th
            P[2, 2], P[2, 3] = -(longe + perto) / (longe - perto), -2 * longe * perto / (longe - perto)
            P[3, 2] = -1
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadMatrixf((P @ V).T.astype(np.float32))
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

        luz = cena.luz if cena.luz is not None else pos + np.array([3.0, 8.0, 0.0])
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glEnableClientState(GL.GL_COLOR_ARRAY)
        transparentes = []
        for p in cena.pecas:
            cor = p.cor if p.cor is not None else (0.7, 0.7, 0.7)
            alfa = 1.0 - 0.75 * (cor[3] if len(cor) > 3 else 0.0)
            if alfa < 0.99:
                transparentes.append((p, cor, alfa))
                continue
            self._desenhar_peca(p, cor, 1.0, luz)
        if transparentes:
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
            GL.glDepthMask(GL.GL_FALSE)
            for p, cor, alfa in transparentes:
                self._desenhar_peca(p, cor, alfa, luz)
            GL.glDepthMask(GL.GL_TRUE)
            GL.glDisable(GL.GL_BLEND)
        for a, b, cor in linhas:   # eixos
            GL.glLineWidth(2)
            GL.glBegin(GL.GL_LINES)
            GL.glColor3f(*cor)
            GL.glVertex3f(*a)
            GL.glVertex3f(*b)
            GL.glEnd()
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glDisableClientState(GL.GL_COLOR_ARRAY)
        GL.glFinish()
        img = fbo.toImage()
        fbo.release()
        self.ctx.doneCurrent()
        return img

    def _desenhar_peca(self, p, cor, alfa, luz):
        GL = self.GL
        tris = p.tris
        if not len(tris):
            return
        cores = _sombreamento(tris, cor, luz)
        if p.xadrez is not None:
            cor2 = np.asarray(p.cor2[:3] if p.cor2 is not None else np.asarray(cor[:3]) * 0.6)
            k = cores / (np.asarray(cor[:3])[None, :] + 1e-9)
            cores = np.where(p.xadrez[:, None], cores, np.clip(cor2[None, :] * k, 0, 1))
        if self.gama:
            cores = cores ** (1 / 2.2)
        cores4 = np.concatenate([cores, np.full((len(cores), 1), alfa)], 1)
        v = tris.reshape(-1, 3).astype(np.float32)
        c = np.repeat(cores4, 3, axis=0).astype(np.float32)
        GL.glVertexPointer(3, GL.GL_FLOAT, 0, v)
        GL.glColorPointer(4, GL.GL_FLOAT, 0, c)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(v))


def projetar(pontos, pos, alvo, fov, aspecto):
    """Pontos do mundo -> posição normalizada (0..1) na imagem, ou None se atrás da câmera."""
    pos, alvo = np.asarray(pos, float), np.asarray(alvo, float)
    f = alvo - pos
    f /= np.linalg.norm(f) or 1
    r = np.cross([0, 1, 0], f)
    r /= np.linalg.norm(r) or 1
    u = np.cross(f, r)
    th = math.tan(fov / 2)
    saida = []
    for p in pontos:
        d = np.asarray(p, float) - pos
        z = d @ f
        if z <= 1e-6:
            saida.append(None)
            continue
        x = (d @ r) / (z * th)
        y = (d @ u) / (z * th / aspecto)
        saida.append((0.5 + x / 2, 0.5 - y / 2))
    return saida
