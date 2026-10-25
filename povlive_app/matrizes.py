"""Painel de matrizes: mostra as transformações do objeto sob o cursor como matrizes 4x4.

Duas convenções:
  - "aula": ponto em coluna [x y z 1]ᵀ, p' = M·p, a última transformação fica à ESQUERDA
            (M = Mn ··· M2·M1). Nomes da disciplina (CGRA): M_r é a rotação HORÁRIA
            [[cos, sen], [-sen, cos]] e M_rah a anti-horária; M_fx troca o sinal de x.
  - "pov":  ponto em linha [x y z 1], p' = p·M, a primeira transformação fica à esquerda
            (M = M1·M2···Mn). É como o POV-Ray guarda a matriz (palavra-chave matrix).

O POV-Ray gira com a regra da mão esquerda: rotate <0,0,θ> leva o eixo x em direção ao y
(no plano xy isso é a anti-horária da aula: M_rah(θ) = M_r(−θ)).
"""
import math

from . import sdl


# ---------------------------------------------------------------- álgebra 4x4 (convenção coluna)

def ident():
    return [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def transp(a):
    return [[a[j][i] for j in range(4)] for i in range(4)]


def aplicar(m, p):
    v = [p[0], p[1], p[2], 1.0]
    return tuple(sum(m[i][k] * v[k] for k in range(4)) for i in range(3))


def T(t):
    m = ident()
    m[0][3], m[1][3], m[2][3] = t
    return m


def S(s):
    m = ident()
    m[0][0], m[1][1], m[2][2] = s
    return m


def R(eixo, graus):
    """Rotação do POV-Ray em torno de um eixo, em forma de coluna (mesmos números do vrotate)."""
    c, s = math.cos(math.radians(graus)), math.sin(math.radians(graus))
    m = ident()
    if eixo == "x":      # y -> z
        m[1][1], m[1][2], m[2][1], m[2][2] = c, -s, s, c
    elif eixo == "y":    # z -> x
        m[0][0], m[0][2], m[2][0], m[2][2] = c, s, -s, c
    else:                # x -> y
        m[0][0], m[0][1], m[1][0], m[1][1] = c, -s, s, c
    return m


def M_pov(v):
    """matrix <a,b,c, d,e,f, g,h,i, tx,ty,tz> do POV-Ray (linhas) -> forma de coluna."""
    linhas = [list(v[0:3]) + [0.0], list(v[3:6]) + [0.0], list(v[6:9]) + [0.0], list(v[9:12]) + [1.0]]
    return transp(linhas)


# ---------------------------------------------------------------- passos

PLANO = {"x": ("yz", "y → z"), "y": ("zx", "z → x"), "z": ("xy", "x → y")}


def vetor3(v):
    return v if isinstance(v, tuple) else (v, v, v)


def passos_de(tipo, val, original):
    """Uma transformação do código -> lista de passos (nome, matriz coluna, explicação)."""
    if tipo == "translate":
        t = vetor3(val)
        return [(f"T({fn(t[0])}, {fn(t[1])}, {fn(t[2])})", T(t), "translação: soma o vetor à posição")]
    if tipo == "scale":
        s = vetor3(val)
        notas = []
        for nome, k in zip("xyz", s):
            if k < 0:
                notas.append(f"<b>reflexão</b>: troca o sinal de {nome} (na aula: M_f{nome})")
            if k == 0:
                notas.append(f"<b>atenção</b>: escala 0 em {nome} achata o objeto (o POV-Ray avisa e troca por 1)")
        expl = "escala a partir da origem" + ("; " + "; ".join(notas) if notas else "")
        return [(f"S({fn(s[0])}, {fn(s[1])}, {fn(s[2])})", S(s), expl)]
    if tipo == "rotate":
        a = vetor3(val)
        lista = []
        for eixo, g in zip("xyz", a):  # o POV-Ray aplica x, depois y, depois z
            if abs(g) < 1e-12:
                continue
            plano, sentido = PLANO[eixo]
            aula = f"M_rah({fn(g)}°) = M_r({fn(-g)}°)" if g > 0 else f"M_r({fn(-g)}°)"
            lista.append((f"R<sub>{eixo}</sub>({fn(g)}°)", R(eixo, g),
                          f"gira {fn(g)}° em torno de {eixo} (no plano {plano}, {sentido}); "
                          f"na notação da aula, nesse plano: <b>{aula}</b>"))
        if not lista:
            lista.append(("R(0°)", ident(), "rotação nula"))
        return lista
    if tipo == "matrix":
        return [("matrix", M_pov(val), "matriz escrita direto (o POV-Ray lista as linhas da forma ponto-em-linha)")]
    return []


def fn(x):
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ---------------------------------------------------------------- análise do objeto sob o cursor

def analisar(texto, pos, clock=0.0):
    """Dados para o painel: objeto, cadeia de transformações (do objeto até os pais) e totais."""
    m = sdl.mascarar(texto)
    todos = sdl.blocos(texto, m)
    alvo = None
    for b in todos:
        if b.kw in sdl.COM_TRANSFORMACAO and b.contem(pos):
            if alvo is None or b.abre > alvo.abre:
                alvo = b
    if alvo is None:
        return None
    vs = sdl.variaveis(texto, ate=alvo.kw_ini, clock=clock)
    decl = sdl.declarados(texto, todos)

    grupos = []   # (rótulo, bloco, transformações)

    def adicionar(rotulo, b):
        grupos.append((rotulo, b, sdl.transformacoes(texto, b, vs, m)))

    # object { Nome ... }: as transformações de dentro da declaração vêm primeiro
    if alvo.kw == "object":
        import re
        mn = re.match(r"\s*([A-Za-z_]\w*)", m[alvo.abre + 1:])
        if mn and mn.group(1) in decl:
            adicionar(f"dentro de #declare {mn.group(1)}", decl[mn.group(1)])
    adicionar(f"{alvo.kw} (linha {sdl.linha_de(texto, alvo.kw_ini)})", alvo)
    p = alvo.pai
    while p is not None:
        if p.kw in sdl.OBJETOS:
            adicionar(f"{p.kw} que contém (linha {sdl.linha_de(texto, p.kw_ini)})", p)
        p = p.pai

    passos, problemas = [], []
    for rotulo, b, ts in grupos:
        for tipo, val, original, _pos, erro in ts:
            if val is None:
                problemas.append((original, erro))
                passos.append({"grupo": rotulo, "original": original, "nome": "?", "matriz": None,
                               "expl": f"não dá para calcular aqui: depende de <code>{erro}</code>"})
                continue
            for nome, mat, expl in passos_de(tipo, val, original):
                passos.append({"grupo": rotulo, "original": original, "nome": nome, "matriz": mat, "expl": expl})

    total = None
    if passos and not problemas:
        total = ident()
        for p in passos:
            total = mul(p["matriz"], total)   # coluna: a nova fica à esquerda
    ponto = sdl.primeiro_ponto(texto, alvo, vs, m)
    return {"objeto": alvo.kw, "linha": sdl.linha_de(texto, alvo.kw_ini), "passos": passos,
            "total": total, "ponto": ponto, "declarado": alvo.declarado}


# ---------------------------------------------------------------- HTML

def _mat_html(mat, conv):
    if mat is None:
        return ""
    mm = mat if conv == "aula" else transp(mat)
    esq, dir_ = "⎡⎢⎢⎣", "⎤⎥⎥⎦"
    linhas = "".join(
        f"<tr><td style='color:#888'>{esq[i]}</td>"
        + "".join(f"<td align=right style='padding:0 6px'>{fn(v)}</td>" for v in row)
        + f"<td style='color:#888'>{dir_[i]}</td></tr>" for i, row in enumerate(mm))
    return f"<table cellspacing=0 style='font-family:monospace'>{linhas}</table>"


def html(dados, conv="aula"):
    estilo = ("<style>body{font-size:10pt} code{color:#e6db74} .g{color:#a6e22e;font-weight:bold}"
              " .n{color:#66d9ef;font-weight:bold} .e{color:#bbb} .aviso{color:#ffb86c}</style>")
    if not dados:
        return estilo + ("<p class=e>Coloque o cursor dentro de um objeto (sphere, box, union, object...) "
                         "para ver as matrizes das transformações dele.</p>")
    d = dados
    if conv == "aula":
        cab = ("Convenção <b>da aula</b>: ponto em coluna <code>[x y z 1]ᵀ</code>, <code>p' = M·p</code>; "
               "a última transformação fica à esquerda: <code>M = Mₙ···M₂·M₁</code>. "
               "<code>M_r</code> = rotação horária, <code>M_rah</code> = anti-horária.")
    else:
        cab = ("Convenção <b>do POV-Ray</b>: ponto em linha <code>[x y z 1]</code>, <code>p' = p·M</code>; "
               "a primeira transformação fica à esquerda: <code>M = M₁·M₂···Mₙ</code> "
               "(é a ordem dos números da palavra-chave <code>matrix</code>).")
    partes = [estilo, f"<p><span class=n>{d['objeto']}</span> na linha {d['linha']}"
              + (f" (declarado como <code>{d['declarado']}</code>)" if d["declarado"] else "") + "</p>",
              f"<p class=e>{cab}</p>"]
    if not d["passos"]:
        partes.append("<p class=e>Este objeto não tem transformações: a matriz é a identidade.</p>")
    grupo = None
    for i, p in enumerate(d["passos"], 1):
        if p["grupo"] != grupo:
            grupo = p["grupo"]
            partes.append(f"<p class=g>{grupo}</p>")
        partes.append(f"<p><b>M{i}</b> = <span class=n>{p['nome']}</span> &nbsp; <code>{escape(p['original'])}</code>"
                      f"<br><span class=e>{p['expl']}</span></p>{_mat_html(p['matriz'], conv)}")
    if d["total"] is not None and len(d["passos"]) > 0:
        n = len(d["passos"])
        ordem = "·".join(f"M{i}" for i in (range(n, 0, -1) if conv == "aula" else range(1, n + 1)))
        partes.append(f"<p class=g>Matriz final M = {ordem}</p>{_mat_html(d['total'], conv)}")
        o = aplicar(d["total"], (0, 0, 0))
        partes.append(f"<p>Origem &lt;0, 0, 0&gt; vai para <code>&lt;{fn(o[0])}, {fn(o[1])}, {fn(o[2])}&gt;</code>")
        if d["ponto"]:
            q = aplicar(d["total"], d["ponto"])
            pt = d["ponto"]
            partes.append(f"<br>Primeiro ponto do objeto <code>&lt;{fn(pt[0])}, {fn(pt[1])}, {fn(pt[2])}&gt;</code> "
                          f"vai para <code>&lt;{fn(q[0])}, {fn(q[1])}, {fn(q[2])}&gt;</code>")
        partes.append("</p>")
    elif any(p["matriz"] is None for p in d["passos"]):
        partes.append("<p class=aviso>A matriz final não foi calculada porque algum passo depende de valores "
                      "que só existem quando o POV-Ray roda (por exemplo, a variável de um #for).</p>")
    return "".join(partes)


def escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
