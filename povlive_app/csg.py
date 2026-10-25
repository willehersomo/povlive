"""CSG na prévia instantânea: difference e intersection com triângulos.

A ideia é a mesma do POV-Ray: a superfície de "A menos B" é a parte da superfície de A que fica fora
de B mais a parte da superfície de B que fica dentro de A. Então cada objeto ganha um teste exato de
"este ponto está dentro?" (Solido), e os triângulos de cada peça são:
  - subdivididos perto das outras peças (para os furos pequenos não passarem entre os vértices);
  - mantidos, descartados ou recortados na fronteira, que é achada por bisseção ao longo das arestas.
"""
import math

import numpy as np

MAX_TRIANGULOS_PECA = 120_000
PASSOS_BISSECAO = 11


class Solido:
    """dentro(P) -> bool por ponto, para P (n, 3) no mundo. caixa = (mín, máx) ou None (infinito)."""
    __slots__ = ("dentro", "caixa")

    def __init__(self, dentro, caixa=None):
        self.dentro = dentro
        self.caixa = caixa

    def transformado(self, M):
        if np.allclose(M, np.eye(4)):
            return self
        try:
            Mi = np.linalg.inv(M)
        except np.linalg.LinAlgError:
            return None
        R, t = Mi[:3, :3].T.copy(), Mi[:3, 3].copy()
        f = self.dentro
        caixa = None
        if self.caixa is not None:
            lo, hi = self.caixa
            cantos = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
            cantos = cantos @ M[:3, :3].T + M[:3, 3]
            caixa = (cantos.min(0), cantos.max(0))
        return Solido(lambda P: f(P @ R + t), caixa)


# ---------------------------------------------------------------- sólidos das formas (coordenadas locais)

def esfera(c, r):
    c = np.asarray(c, float)
    return Solido(lambda P: ((P - c) ** 2).sum(1) <= r * r, (c - abs(r), c + abs(r)))


def caixa(a, b):
    lo, hi = np.minimum(a, b).astype(float), np.maximum(a, b).astype(float)
    return Solido(lambda P: np.all((P >= lo) & (P <= hi), axis=1), (lo, hi))


def tronco(a, r1, b, r2):
    a, b = np.asarray(a, float), np.asarray(b, float)
    eixo = b - a
    L2 = float(eixo @ eixo)
    if L2 < 1e-18:
        return None

    def dentro(P):
        d = P - a
        t = d @ eixo / L2
        radial = d - t[:, None] * eixo
        r = r1 + (r2 - r1) * t
        return (t >= 0) & (t <= 1) & ((radial ** 2).sum(1) <= r * r)
    m = max(abs(r1), abs(r2))
    return Solido(dentro, (np.minimum(a, b) - m, np.maximum(a, b) + m))


def toro(R, r):
    def dentro(P):
        q = np.sqrt(P[:, 0] ** 2 + P[:, 2] ** 2) - R
        return q * q + P[:, 1] ** 2 <= r * r
    e = abs(R) + abs(r)
    return Solido(dentro, (np.array([-e, -abs(r), -e]), np.array([e, abs(r), e])))


def plano(normal, d):
    n = np.asarray(normal, float)
    n = n / (np.linalg.norm(n) or 1)
    return Solido(lambda P: P @ n <= d, None)


def _no_poligono(x, y, pts):
    """Par-ímpar: (x, y) dentro do polígono fechado pts (k, 2)?"""
    dentro = np.zeros(len(x), bool)
    xs, ys = pts[:, 0], pts[:, 1]
    xs2, ys2 = np.roll(xs, -1), np.roll(ys, -1)
    for x1, y1, x2, y2 in zip(xs, ys, xs2, ys2):
        if y1 == y2:
            continue
        cruza = (y1 > y) != (y2 > y)
        xc = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
        dentro ^= cruza & (x < xc)
    return dentro


def revolucao(perfil):
    pts = np.asarray(perfil, float)
    if len(pts) < 2:
        return None

    def dentro(P):
        return _no_poligono(np.sqrt(P[:, 0] ** 2 + P[:, 2] ** 2), P[:, 1], pts)
    rm = np.abs(pts[:, 0]).max()
    return Solido(dentro, (np.array([-rm, pts[:, 1].min(), -rm]), np.array([rm, pts[:, 1].max(), rm])))


def prisma(y1, y2, pontos):
    pts = np.asarray(pontos, float)
    if len(pts) < 3:
        return None
    lo_y, hi_y = min(y1, y2), max(y1, y2)

    def dentro(P):
        return (P[:, 1] >= lo_y) & (P[:, 1] <= hi_y) & _no_poligono(P[:, 0], P[:, 2], pts)
    return Solido(dentro, (np.array([pts[:, 0].min(), lo_y, pts[:, 1].min()]),
                           np.array([pts[:, 0].max(), hi_y, pts[:, 1].max()])))


# ---------------------------------------------------------------- combinações

def _caixa_uniao(caixas):
    if not caixas or any(c is None for c in caixas):
        return None
    return np.min([c[0] for c in caixas], 0), np.max([c[1] for c in caixas], 0)


def uniao(solidos):
    solidos = [s for s in solidos if s is not None]
    if not solidos:
        return None
    if len(solidos) == 1:
        return solidos[0]

    def dentro(P):
        r = solidos[0].dentro(P)
        for s in solidos[1:]:
            falta = ~r
            if falta.any():
                r[falta] = s.dentro(P[falta])
        return r
    return Solido(dentro, _caixa_uniao([s.caixa for s in solidos]))


def intersecao(solidos):
    if not solidos or any(s is None for s in solidos):
        return None

    def dentro(P):
        r = solidos[0].dentro(P)
        for s in solidos[1:]:
            if r.any():
                r[r] = s.dentro(P[r])
        return r
    caixas = [s.caixa for s in solidos if s.caixa is not None]
    caixa_ = None
    if caixas:
        caixa_ = (np.max([c[0] for c in caixas], 0), np.min([c[1] for c in caixas], 0))
    return Solido(dentro, caixa_)


def diferenca(a, outros):
    if a is None:
        return None
    outros = [s for s in outros if s is not None]

    def dentro(P):
        r = a.dentro(P)
        for s in outros:
            if r.any():
                r[r] = ~s.dentro(P[r])
        return r
    return Solido(dentro, a.caixa)


def solido_do_grupo(pecas):
    """Sólido de um operando: a união dos sólidos (distintos) das peças dele."""
    vistos, lista = set(), []
    for p in pecas:
        s = p.solido
        if s is not None and id(s) not in vistos:
            vistos.add(id(s))
            lista.append(s)
    return uniao(lista)


# ---------------------------------------------------------------- triângulos

def _sobrepoe(tris, caixa, folga):
    lo, hi = caixa
    tlo, thi = tris.min(1), tris.max(1)
    return np.all((thi >= lo - folga) & (tlo <= hi + folga), axis=1)


def subdividir(tris, attr, niveis):
    """Divide cada triângulo em 4 (pelos pontos médios), 'niveis' vezes. attr acompanha cada triângulo."""
    for _ in range(niveis):
        a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
        ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
        tris = np.concatenate([np.stack(t, 1) for t in ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca))])
        if attr is not None:
            attr = np.concatenate([attr] * 4)
    return tris, attr


def _fronteira(p_dentro, p_fora, manter):
    """Ponto da fronteira entre um ponto mantido e um descartado (bisseção)."""
    lo, hi = p_dentro.copy(), p_fora.copy()
    for _ in range(PASSOS_BISSECAO):
        meio = (lo + hi) / 2
        k = manter(meio)
        lo[k] = meio[k]
        hi[~k] = meio[~k]
    return (lo + hi) / 2


def recortar(tris, attr, manter):
    """Fica só com a parte dos triângulos onde manter(P) é verdadeiro (recortando na fronteira)."""
    if not len(tris):
        return tris, attr
    k = manter(tris.reshape(-1, 3)).reshape(-1, 3)
    n = k.sum(1)
    saida, saida_attr = [tris[n == 3]], [attr[n == 3]] if attr is not None else None
    for qtd in (1, 2):
        sel = n == qtd
        if not sel.any():
            continue
        T, K = tris[sel], k[sel]
        # gira os vértices para o diferente ficar na posição 0, mantendo a orientação
        alvo = K if qtd == 1 else ~K
        i0 = np.argmax(alvo, axis=1)
        idx = (i0[:, None] + np.arange(3)[None, :]) % 3
        V = np.take_along_axis(T, idx[:, :, None], 1)
        a, b, c = V[:, 0], V[:, 1], V[:, 2]
        if qtd == 1:          # só a fica: triângulo a, a→b, a→c
            pab = _fronteira(a, b, manter)
            pac = _fronteira(a, c, manter)
            novos = [np.stack([a, pab, pac], 1)]
        else:                 # a sai: quadrilátero b, c, c→a, a→b
            pba = _fronteira(b, a, manter)
            pca = _fronteira(c, a, manter)
            novos = [np.stack([b, c, pca], 1), np.stack([b, pca, pba], 1)]
        saida += novos
        if attr is not None:
            saida_attr += [attr[sel]] * len(novos)
    tris = np.concatenate(saida)
    attr = np.concatenate(saida_attr) if attr is not None else None
    return tris, attr


def _tamanho(caixa):
    return float(np.linalg.norm(caixa[1] - caixa[0])) if caixa is not None else math.inf


def aplicar(tris, attr, manter, relevantes):
    """Recorta os triângulos de uma peça. relevantes = sólidos de que manter() depende: só a região
    perto deles é subdividida; o resto é mantido ou descartado inteiro."""
    if not len(tris):
        return tris, attr
    caixas = [s.caixa for s in relevantes]
    perto = np.ones(len(tris), bool)
    if all(c is not None for c in caixas):
        perto = np.zeros(len(tris), bool)
        for c in caixas:
            perto |= _sobrepoe(tris, c, 1e-6 + 0.01 * _tamanho(c))
    partes, partes_attr = [], []
    longe = ~perto
    if longe.any():
        T = tris[longe]
        k = manter(T.mean(1))
        partes.append(T[k])
        if attr is not None:
            partes_attr.append(attr[longe][k])
    if perto.any():
        T = tris[perto]
        A = attr[perto] if attr is not None else None
        tam = min([_tamanho(c) for c in caixas if c is not None] + [_tamanho((T.reshape(-1, 3).min(0),
                                                                              T.reshape(-1, 3).max(0)))])
        h = max(tam / 14, 1e-6)
        aresta = max(np.linalg.norm(T[:, 1] - T[:, 0], axis=1).max(), np.linalg.norm(T[:, 2] - T[:, 1], axis=1).max(),
                     np.linalg.norm(T[:, 0] - T[:, 2], axis=1).max())
        niveis = max(0, math.ceil(math.log2(aresta / h))) if aresta > h else 0
        while niveis and len(T) * 4 ** niveis > MAX_TRIANGULOS_PECA:
            niveis -= 1
        T, A = subdividir(T, A, niveis)
        T, A = recortar(T, A, manter)
        partes.append(T)
        if attr is not None:
            partes_attr.append(A)
    tris = np.concatenate(partes) if partes else tris[:0]
    attr = np.concatenate(partes_attr) if attr is not None and partes_attr else (attr[:0] if attr is not None else None)
    return tris, attr


def combinar(operandos, tipo):
    """operandos: lista de listas de Peca (já no sistema do bloco CSG). Recorta as peças no lugar e
    devolve (peças resultantes, sólido do resultado)."""
    solidos = [solido_do_grupo(g) for g in operandos]
    saida = []
    for i, grupo in enumerate(operandos):
        outros = [s for j, s in enumerate(solidos) if j != i and s is not None]
        if tipo == "difference":
            if i == 0:
                fora = [s for s in solidos[1:] if s is not None]
                u = uniao(fora)
                manter = (lambda P, u=u: ~u.dentro(P)) if u is not None else None
                relevantes = fora
            else:
                a = solidos[0]
                if a is None:
                    continue          # sem o sólido de A, as peças de B não aparecem (como se fossem furos)
                resto = [s for j, s in enumerate(solidos[1:], 1) if j != i and s is not None]
                d = diferenca(a, resto)
                manter = d.dentro
                relevantes = [a] + resto
        else:  # intersection
            if not outros:
                manter, relevantes = None, []
            else:
                inter = intersecao(outros)
                manter = inter.dentro
                relevantes = outros
        for p in grupo:
            if p.cor2 is None:
                p.xadrez = None       # plano sem checker: dentro do CSG é uma cor só (não o chão quadriculado)
            if manter is not None:
                p.tris, p.xadrez = aplicar(p.tris, p.xadrez, manter, relevantes)
            if len(p.tris):
                saida.append(p)
    if tipo == "difference":
        resultado = diferenca(solidos[0], solidos[1:]) if solidos else None
    else:
        resultado = intersecao(solidos) if solidos else None
    for p in saida:
        p.solido = resultado
    return saida, resultado
