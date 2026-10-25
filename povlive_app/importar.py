"""Importar modelos 3D (OBJ e STL) como mesh2 do POV-Ray.

Os eixos mudam: o POV-Ray usa a mão esquerda com y para cima. O OBJ costuma ser mão direita com y
para cima (então o z troca de sinal) e o STL, mão direita com z para cima (então y e z trocam de
lugar). Nos dois casos a ordem dos vértices de cada face também é invertida, para as normais
continuarem para fora.
"""
import os, re, struct

import numpy as np


class ModeloInvalido(ValueError):
    pass


def ler_obj(texto):
    """(vértices (n,3), faces (m,3)) de um OBJ; polígonos viram leques de triângulos."""
    vs, faces = [], []
    for linha in texto.splitlines():
        partes = linha.split()
        if not partes:
            continue
        if partes[0] == "v" and len(partes) >= 4:
            vs.append([float(x) for x in partes[1:4]])
        elif partes[0] == "f" and len(partes) >= 4:
            idx = []
            for p in partes[1:]:
                i = int(p.split("/")[0])
                idx.append(i - 1 if i > 0 else len(vs) + i)
            for k in range(1, len(idx) - 1):
                faces.append([idx[0], idx[k], idx[k + 1]])
    if not vs or not faces:
        raise ModeloInvalido("obj vazio")
    V, F = np.array(vs, float), np.array(faces, np.int64)
    if F.min() < 0 or F.max() >= len(V):
        raise ModeloInvalido("índice de vértice fora do intervalo")
    V[:, 2] *= -1               # mão direita -> esquerda
    return V, F[:, ::-1]


def ler_stl(dados):
    """(vértices, faces) de um STL binário ou texto; vértices repetidos são unidos."""
    tris = None
    if len(dados) >= 84:
        n = struct.unpack("<I", dados[80:84])[0]
        if 84 + 50 * n == len(dados):
            reg = np.frombuffer(dados, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]),
                                count=n, offset=84)
            tris = reg["v"].astype(float)
    if tris is None:
        texto = dados.decode("latin-1")
        if "vertex" not in texto:
            raise ModeloInvalido("stl sem vértices")
        nums = re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", texto)
        tris = np.array(nums, float).reshape(-1, 3, 3)
    if not len(tris):
        raise ModeloInvalido("stl vazio")
    pts = tris.reshape(-1, 3)
    V, inv = np.unique(np.round(pts, 6), axis=0, return_inverse=True)
    F = inv.reshape(-1, 3)
    V = V[:, [0, 2, 1]]          # z para cima (mão direita) -> y para cima (mão esquerda)
    return V, F[:, ::-1]


def ler(caminho):
    with open(caminho, "rb") as f:
        dados = f.read()
    ext = os.path.splitext(caminho)[1].lower()
    if ext == ".obj":
        return ler_obj(dados.decode("utf-8", errors="replace"))
    if ext == ".stl":
        return ler_stl(dados)
    raise ModeloInvalido("formato")


def ajustar(V, tamanho=2.0):
    """Centraliza em x e z, apoia em y = 0 e escala para a maior medida ser 'tamanho'."""
    lo, hi = V.min(0), V.max(0)
    maior = float((hi - lo).max()) or 1.0
    k = tamanho / maior
    centro = (lo + hi) / 2
    W = (V - [centro[0], lo[1], centro[2]]) * k
    return W


def nome_pov(caminho):
    """Nome de #declare a partir do nome do arquivo: 'meu bule.obj' -> Meu_bule."""
    base = re.sub(r"\W+", "_", os.path.splitext(os.path.basename(caminho))[0]).strip("_") or "Modelo"
    if base[0].isdigit():
        base = "M_" + base
    return base[0].upper() + base[1:]


def mesh2(nome, V, F, origem=""):
    def fmt(x):
        s = f"{x:.5f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    linhas = [f"// {origem}: {len(V)} vértices, {len(F)} triângulos (importado pelo PovLive)"] if origem else []
    linhas += [f"#declare {nome} = mesh2 {{", f"    vertex_vectors {{ {len(V)},"]
    linhas += ["        " + ", ".join(f"<{fmt(a)}, {fmt(b)}, {fmt(c)}>" for a, b, c in V[i:i + 4])
               + ("," if i + 4 < len(V) else "") for i in range(0, len(V), 4)]
    linhas += ["    }", f"    face_indices {{ {len(F)},"]
    linhas += ["        " + ", ".join(f"<{a}, {b}, {c}>" for a, b, c in F[i:i + 6])
               + ("," if i + 6 < len(F) else "") for i in range(0, len(F), 6)]
    linhas += ["    }", "}", ""]
    return "\n".join(linhas)


def importar(caminho, pasta_destino, tamanho=2.0):
    """Cria <nome>.inc na pasta da cena. Devolve (caminho do .inc, nome declarado, nº de triângulos)."""
    V, F = ler(caminho)
    if tamanho:
        V = ajustar(V, tamanho)
    nome = nome_pov(caminho)
    destino = os.path.join(pasta_destino, nome.lower() + ".inc")
    with open(destino, "w", encoding="utf-8") as f:
        f.write(mesh2(nome, V, F, os.path.basename(caminho)))
    return destino, nome, len(F)
