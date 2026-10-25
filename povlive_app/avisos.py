"""Avisos do POV-Ray (não impedem o render, mas costumam indicar um problema)."""
import re

from .i18n import N_, tr

INICIO = re.compile(r"^(?:File '([^']*)' line (\d+): )?(Parse Warning|Possible Parse Error|Warning|Render Warning): ?(.*)$")

TRADUCOES = [
    (r"assumed_gamma not specified",
     N_("Falta 'global_settings { assumed_gamma 1.0 }'. No POV-Ray 3.7 isso é recomendado para as cores "
     "ficarem corretas (as cores podem clarear um pouco ao corrigir)."), "gamma"),
    (r"other declarations preceding the first #version",
     N_("Falta '#version 3.7;' na primeira linha. Sem ele, o POV-Ray pode usar o comportamento de versões antigas."),
     "versao"),
    (r"More than one camera",
     N_("Há mais de uma câmera na cena: só a última vale."), None),
    (r"Scale (\w) by 0\.0",
     N_("Escala zero no eixo {0}: o POV-Ray trocou por 1. Escala 0 achataria o objeto."), None),
    (r"No objects in scene",
     N_("A cena não tem nenhum objeto."), None),
    (r"No pigment type given|No texture",
     N_("Objeto sem pigment: vai aparecer preto."), None),
    (r"Camera vectors are not perpendicular",
     N_("Os vetores da câmera (right, up, direction) não são perpendiculares: a imagem pode sair distorcida."), None),
    (r"Should have at least 1 light source|No light source",
     N_("A cena não tem luz: tudo vai sair escuro."), None),
    (r"Suspicious expression after rgb",
     N_("Expressão estranha depois de rgb: confira se o vetor da cor tem 3 componentes."), None),
]


def ler(saida, ignorar_cameras=False):
    """Lista de avisos: dicts com arquivo, linha, texto (traduzido), original e correção (ou None)."""
    avisos, atual = [], None
    for l in saida.splitlines():
        m = INICIO.match(l)
        if m:
            if atual:
                avisos.append(atual)
            atual = {"arquivo": m.group(1), "linha": int(m.group(2)) if m.group(2) else None,
                     "original": m.group(4).strip()}
        elif atual and l.startswith(" "):
            atual["original"] += " " + l.strip()
        elif atual:
            avisos.append(atual)
            atual = None
    if atual:
        avisos.append(atual)
    resultado, vistos = [], set()
    for a in avisos:
        a["texto"], a["correcao"] = a["original"], None
        for rx, trad, corr in TRADUCOES:
            mm = re.search(rx, a["original"])
            if mm:
                a["texto"] = tr(trad)
                for k, g in enumerate(mm.groups()):   # {0}, {1}... (sem usar format: o texto tem chaves)
                    a["texto"] = a["texto"].replace("{%d}" % k, g or "")
                a["correcao"] = corr
                break
        if ignorar_cameras and "More than one camera" in a["original"]:
            continue  # câmera livre/vistas do app acrescentam uma câmera
        chave = (a["arquivo"], a["linha"], a["texto"])
        if chave not in vistos:
            vistos.add(chave)
            resultado.append(a)
    return resultado


def corrigir(texto, tipo):
    """Aplica a correção rápida e devolve o novo texto."""
    linhas = texto.split("\n")
    if tipo == "versao" and not re.search(r"^\s*#version", texto, re.M):
        return "#version 3.7;\n" + texto
    if tipo == "gamma":
        m = re.search(r"global_settings\s*\{", texto)
        if m:
            return texto[:m.end()] + " assumed_gamma 1.0" + texto[m.end():]
        # depois do #version, se houver
        for i, l in enumerate(linhas):
            if l.strip().startswith("#version"):
                linhas.insert(i + 1, "global_settings { assumed_gamma 1.0 }")
                return "\n".join(linhas)
        return "global_settings { assumed_gamma 1.0 }\n" + texto
    return texto


# ---------------------------------------------------------------- erros (o render não acontece)

ERROS = [
    (r"No matching \} in '(\w+)'",
     N_("Falta fechar uma chave } do bloco {0}. O POV-Ray só percebe isso mais adiante (no próximo bloco "
     "ou no fim do arquivo), então a chave que falta costuma estar ANTES da linha indicada.")),
    (r"Undeclared identifier '(\w+)'",
     N_("O nome '{0}' não existe: confira se está escrito igual (maiúsculas contam) ou se falta o #include "
     "que o define (ex.: colors.inc para nomes de cores).")),
    (r"Cannot open include file (\S+)",
     N_("Não achei o arquivo {0}: confira o nome e se ele está na mesma pasta da cena.")),
    (r"Expected 'numeric expression'",
     N_("Faltou um número: confira vírgulas sobrando ou faltando, principalmente dentro de vetores < >.")),
    (r"Expected '(.)', (.+?) found instead",
     N_("Esperava '{0}' mas encontrou {1}: costuma ser vírgula, ponto e vírgula ou sinal de > faltando.")),
    (r"Expected '(\w+)'",
     N_("Esperava '{0}' aqui.")),
    (r"Float expected but vector or color",
     N_("Aqui vai um número, mas foi escrito um vetor ou cor (algo entre < >).")),
    (r"No objects in scene",
     N_("A cena não tem nenhum objeto para renderizar.")),
]


def explicar_erro(saida):
    """Explicação (no idioma da interface) do primeiro erro reconhecido (ou None)."""
    texto = " ".join(l.strip() for l in saida.splitlines())
    for rx, exp in ERROS:
        m = re.search(rx, texto)
        if m:
            exp = tr(exp)
            for k, g in enumerate(m.groups()):
                exp = exp.replace("{%d}" % k, g or "")
            return exp
    return None
