"""Guia didático do POV-Ray (Ajuda > Guia do POV-Ray).

Cada tópico é uma lista de blocos:
  ("txt", "html")                 texto explicativo
  ("ex", "id", "trecho", opções)  exemplo: o trecho aparece no guia e "Abrir exemplo"
                                  abre uma cena completa (cenário padrão + trecho) numa aba nova
  ("dica", "html")                caixa de destaque
"""
import html, os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QTextDocument
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QListWidget, QTextBrowser, QSplitter

from . import exercicios
from .i18n import tr, idioma

CAMERA_PADRAO = "camera {\n    location <0, 3, -7>\n    look_at <0, 1, 0>\n}"
CHAO_PADRAO = "plane { y, 0 pigment { checker rgb 0.85, rgb 0.6 } }"


def cena_completa(trecho, camera=CAMERA_PADRAO, chao=CHAO_PADRAO, extra_inc=()):
    incs = "".join(f'#include "{i}"\n' for i in ("colors.inc",) + tuple(extra_inc))
    intro = (CABECALHO_EXEMPLO if idioma() == "pt" else CABECALHO_EXEMPLO_EN)
    return f"""{intro}
#version 3.7;
global_settings {{ assumed_gamma 1.0 }}
{incs}
{tr("// ---------- cenário ----------")}
{camera}

light_source {{ <4, 8, -6> rgb 1 }}
light_source {{ <-6, 5, -3> rgb 0.3 shadowless }}
background {{ rgb <0.55, 0.7, 0.9> }}
{chao}

{tr("// ---------- assunto do exemplo ----------")}
{trecho}
"""


CABECALHO_EXEMPLO = """// Exemplo do guia do PovLive.
// Mexa à vontade: dica, segure Ctrl e arraste um número para ver o efeito."""
CABECALHO_EXEMPLO_EN = """// Example from the PovLive guide.
// Play with it: tip, hold Ctrl and drag a number to see the effect."""


def topicos():
    """Tópicos do guia no idioma da interface."""
    if idioma() == "pt":
        return TOPICOS
    from .guia_en import TOPICOS as TOPICOS_EN
    return TOPICOS_EN


TOPICOS = [
    # ------------------------------------------------------------------
    ("1. Primeiros passos", [
        ("txt", """<p>Uma cena do POV-Ray é um arquivo de texto que descreve <b>o que existe</b> e
<b>de onde olhamos</b>. O POV-Ray então faz <i>ray tracing</i>: para cada pixel, lança um raio da câmera
e calcula a cor do que ele atinge.</p>
<p>Toda cena precisa de três coisas:</p>
<ol><li><b>câmera</b> – de onde olhamos e para onde;</li>
<li><b>luz</b> – sem luz, tudo fica preto;</li>
<li><b>objetos</b> – com algum <code>pigment</code> (cor), senão ficam pretos também.</li></ol>"""),
        ("ex", "inicio", """sphere {
    <0, 1, 0>, 1          // centro e raio
    pigment { color Red }  // cor (Red vem do colors.inc)
}""", {}),
        ("txt", """<p><b>Sintaxe básica:</b></p>
<ul><li>vetores são escritos entre <code>&lt; &gt;</code>: <code>&lt;x, y, z&gt;</code>;</li>
<li>blocos ficam entre chaves: <code>sphere { ... }</code>;</li>
<li><code>//</code> comenta até o fim da linha e <code>/* ... */</code> comenta um trecho;</li>
<li><code>#include "colors.inc"</code> traz nomes de cores prontos (Red, White, SkyBlue...);</li>
<li>uma cor é <code>rgb &lt;r, g, b&gt;</code> com valores de 0 a 1; <code>rgb 1</code> é branco.</li></ul>"""),
        ("txt", """<h3>Sistema de coordenadas</h3>
<p>O POV-Ray usa o sistema de <b>mão esquerda</b>: <b>x</b> para a direita, <b>y</b> para cima e
<b>z para dentro da tela</b> (se afastando de quem olha). Ligue os eixos com <b>Ctrl+E</b>:
x é vermelho, y é verde e z é azul.</p>"""),
        ("ex", "coords", """// Uma esfera na ponta de cada eixo positivo
sphere { <2, 0.3, 0>, 0.3 pigment { color Red } }    // +x (direita)
sphere { <0, 2, 0>, 0.3 pigment { color Green } }    // +y (cima)
sphere { <0, 0.3, 2>, 0.3 pigment { color Blue } }   // +z (para dentro)
sphere { <0, 0.3, 0>, 0.15 pigment { color White } } // origem""",
         {"camera": "camera {\n    location <2.5, 3, -4>\n    look_at <0.4, 0.6, 0.4>\n}"}),
        ("dica", "Erros comuns: esquecer uma chave <code>}</code>, esquecer a vírgula entre vetor e número "
                 "(<code>&lt;0,1,0&gt;, 1</code>) e escrever com acento ou maiúscula errada (<code>red</code> ≠ <code>Red</code>)."),
    ]),
    # ------------------------------------------------------------------
    ("2. Câmera", [
        ("txt", """<p><code>location</code> é onde a câmera está e <code>look_at</code> é o ponto para onde ela aponta.
<code>angle</code> define a abertura horizontal em graus (padrão ≈ 67°): menor é zoom/teleobjetiva, maior é grande-angular.</p>"""),
        ("ex", "cam_angle", """// Experimente angle 30 (zoom) e angle 100 (grande-angular)
camera {
    location <0, 3, -7>
    look_at <0, 1, 0>
    angle 50
}
sphere { <0, 1, 0>, 1 pigment { color Orange } }
box { <-3, 0, 2>, <-2, 2, 3> pigment { color SkyBlue } }
box { <2, 0, 2>, <3, 2, 3> pigment { color SkyBlue } }""", {"camera": "// (a câmera está no assunto do exemplo; a última câmera da cena é a que vale)"}),
        ("txt", """<p>A câmera <b>ortográfica</b> não tem perspectiva: objetos longe têm o mesmo tamanho dos perto.
É a projeção dos desenhos técnicos (vistas de frente, topo e lado). <code>right</code> e <code>up</code> dizem
quantas unidades cabem na largura e na altura.</p>"""),
        ("ex", "cam_orto", """camera {
    orthographic
    location <0, 1, -10>
    look_at <0, 1, 0>
    right x*8*image_width/image_height   // 8 unidades de altura, largura proporcional
    up y*8
}
// as duas caixas têm o mesmo tamanho, mas a de trás está muito mais longe
box { <-2.5, 0, 0>, <-0.5, 2, 1> pigment { color Red } }
box { <0.5, 0, 15>, <2.5, 2, 16> pigment { color Blue } }""", {"camera": ""}),
        ("dica", "No app: <b>F6</b> liga a câmera livre (arraste na imagem para girar) e <b>Shift+F6</b> copia a "
                 "posição escolhida para o código. <b>F7</b> mostra as vistas de frente, topo e lado."),
    ]),
    # ------------------------------------------------------------------
    ("3. Luzes", [
        ("txt", """<p><code>light_source { posição cor }</code> cria uma luz pontual, que ilumina em todas as direções
e gera sombras duras. A luz em si é invisível: só vemos o efeito dela.</p>"""),
        ("ex", "luz_ponto", """light_source { <-3, 4, -2> color rgb <1, 0.6, 0.3> }  // luz alaranjada extra
sphere { <0, 1, 0>, 1 pigment { color White } }""", {}),
        ("txt", """<p><b>area_light</b> é uma luz com área (um retângulo de luzes), que produz <b>sombras suaves</b>.
Os dois vetores são os lados do retângulo e os números dizem quantas luzes há em cada lado.</p>"""),
        ("ex", "luz_area", """light_source {
    <2, 6, -3> rgb 1
    area_light <3, 0, 0>, <0, 0, 3>, 6, 6   // retângulo 3x3 com 6x6 luzes
    adaptive 1 jitter                       // mais rápido e sem "degraus" na sombra
}
sphere { <0, 1, 0>, 1 pigment { color White } }""", {}),
        ("txt", """<p><b>spotlight</b> é uma lanterna: ilumina um cone. <code>radius</code> é o ângulo da parte
totalmente iluminada e <code>falloff</code> o ângulo onde a luz acaba.</p>"""),
        ("ex", "luz_spot", """light_source {
    <0, 6, 0> color rgb <1, 1, 0.8>
    spotlight
    point_at <0, 0, 0>
    radius 12
    falloff 20
}
sphere { <0, 1, 0>, 1 pigment { color White } }""", {}),
        ("dica", "<code>shadowless</code> faz uma luz que não gera sombra. É útil como luz de preenchimento "
                 "para clarear as partes escuras (o cenário dos exemplos usa uma)."),
    ]),
    # ------------------------------------------------------------------
    ("4. Sólidos básicos", [
        ("txt", """<p>As primitivas são definidas por poucos números. Passe o mouse sobre o nome de cada uma
no editor para ver a sintaxe.</p>
<table border=0 cellspacing=6>
<tr><td><code>sphere { centro, raio }</code></td><td>esfera</td></tr>
<tr><td><code>box { canto1, canto2 }</code></td><td>caixa alinhada aos eixos (dois cantos opostos)</td></tr>
<tr><td><code>cylinder { base, topo, raio }</code></td><td>cilindro entre dois pontos</td></tr>
<tr><td><code>cone { base, raio1, topo, raio2 }</code></td><td>cone ou tronco de cone</td></tr>
<tr><td><code>torus { raio_maior, raio_menor }</code></td><td>rosca deitada no plano XZ</td></tr>
<tr><td><code>plane { normal, distância }</code></td><td>plano infinito</td></tr>
<tr><td><code>disc { centro, normal, raio }</code></td><td>disco fino</td></tr></table>"""),
        ("ex", "solidos", """sphere   { <-3, 1, 0>, 1                      pigment { color Red } }
box      { <-1.5, 0, -0.5>, <-0.5, 1.5, 0.5>   pigment { color Orange } }
cylinder { <0.5, 0, 0>, <0.5, 2, 0>, 0.5        pigment { color Yellow } }
cone     { <2.2, 0, 0>, 0.7, <2.2, 2, 0>, 0     pigment { color Green } }
torus    { 0.8, 0.25 translate <4.2, 0.25, 0>   pigment { color Blue } }""",
         {"camera": "camera {\n    location <0.5, 4, -9>\n    look_at <0.5, 0.8, 0>\n}"}),
        ("txt", """<p>Um <b>cone</b> com os dois raios diferentes de zero vira um <b>tronco</b>. A palavra <code>open</code>
tira as tampas do cilindro e do cone, deixando só a parede.</p>"""),
        ("ex", "tronco", """cone { <-1.5, 0, 0>, 1, <-1.5, 1.5, 0>, 0.5 pigment { color Cyan } }        // tronco
cylinder { <1.5, 0, 0>, <1.5, 1.5, 0>, 0.8 open pigment { color Magenta } }  // sem tampas""", {}),
    ]),
    # ------------------------------------------------------------------
    ("5. Sólidos avançados", [
        ("txt", """<p><b>prism</b> extruda (estica) um polígono 2D na direção y. Os pontos são &lt;x, z&gt; e
o polígono precisa terminar no mesmo ponto em que começou.</p>"""),
        ("ex", "prisma", """prism {
    linear_sweep
    0, 1,          // de y=0 até y=1
    6,             // quantidade de pontos
    <-1, -1>, <1, -1>, <1.5, 0.5>, <0, 1.5>, <-1.5, 0.5>, <-1, -1>
    pigment { color Gold }
}""", {}),
        ("txt", """<p><b>lathe</b> é um sólido de revolução: você desenha um perfil &lt;raio, altura&gt; e ele gira em
torno do eixo y, como num torno mecânico. Ótimo para vasos, taças e peões.</p>"""),
        ("ex", "torno", """lathe {
    cubic_spline
    9,
    <0, 0>, <0.8, 0>, <1, 0.3>, <0.6, 1>, <0.4, 1.6>, <0.7, 2.2>, <0.75, 2.4>, <0.7, 2.4>, <0.6, 2.3>
    pigment { color rgb <0.3, 0.5, 0.9> }
    finish { phong 0.8 }
}""", {}),
        ("txt", """<p><b>text</b> cria texto 3D a partir de uma fonte TrueType. Os números são a espessura e um
deslocamento entre letras.</p>"""),
        ("ex", "texto", """text {
    ttf "timrom.ttf" "POV-Ray" 0.3, 0
    pigment { color Red }
    scale 1.2
    translate <-2.3, 0.2, 0>
}""", {}),
        ("txt", """<p><b>blob</b> são "metabolas": esferas que se fundem suavemente quando estão perto, como gotas.</p>"""),
        ("ex", "blob", """blob {
    threshold 0.6
    sphere { <-0.7, 1, 0>, 1.2, 1 }
    sphere { < 0.7, 1, 0>, 1.2, 1 }
    sphere { < 0, 1.8, 0>, 0.9, 1 }
    pigment { color rgb <0.2, 0.8, 0.4> }
    finish { phong 0.9 }
}""", {}),
    ]),
    # ------------------------------------------------------------------
    ("6. Transformações", [
        ("txt", """<p>Todo objeto aceita três transformações básicas. <b>Todas acontecem em relação à origem
&lt;0,0,0&gt; e aos eixos do mundo</b>, não ao centro do objeto:</p>
<ul><li><code>translate &lt;dx, dy, dz&gt;</code> move;</li>
<li><code>rotate &lt;ax, ay, az&gt;</code> gira em graus em torno de x, depois de y, depois de z;</li>
<li><code>scale &lt;sx, sy, sz&gt;</code> (ou <code>scale s</code>) estica ou encolhe a partir da origem.</li></ul>"""),
        ("ex", "translate", """// a mesma caixa, original e movida
box { <-0.5, 0, -0.5>, <0.5, 1, 0.5> pigment { color White } }
box { <-0.5, 0, -0.5>, <0.5, 1, 0.5> pigment { color Red } translate <2, 0, 1> }""", {}),
        ("txt", """<h3>Para que lado o rotate gira?</h3>
<p>Regra da <b>mão esquerda</b>: aponte o polegar esquerdo para o lado positivo do eixo; os dedos
dobrados mostram o sentido positivo. Na prática: <b>olhando da ponta positiva do eixo em direção à
origem, um ângulo positivo gira no sentido horário</b>.</p>
<p>Cuidado: a câmera de frente padrão fica em z negativo olhando para +z, ou seja, ela olha
<i>de trás</i> do eixo z. Por isso, para ela, <code>rotate &lt;0, 0, 45&gt;</code> parece
<b>anti-horário</b>. (Conferido no POV-Ray: <code>rotate &lt;0,0,90&gt;</code> leva o eixo x até o y.)</p>"""),
        ("ex", "rotate", """// ponteiro apontando para +x; mude o 45 arrastando com Ctrl
#declare Ponteiro = union {
    box { <0, -0.08, -0.08>, <2, 0.08, 0.08> }
    cone { <2, 0, 0>, 0.25, <2.5, 0, 0>, 0 }
}
object { Ponteiro pigment { color White } translate <0, 1.5, 0> }               // original
object { Ponteiro pigment { color Red } rotate <0, 0, 45> translate <0, 1.5, 0> } // girado""",
         {"camera": "camera {\n    location <0, 1.5, -7>\n    look_at <0, 1.5, 0>\n}", "chao": ""}),
        ("txt", """<p><code>scale</code> com valores diferentes em cada eixo deforma o objeto: uma esfera vira um
elipsoide. Um valor <b>negativo</b> espelha (reflete) o objeto naquele eixo.</p>"""),
        ("ex", "scale", """// esfera esticada em x e achatada em y: vira um elipsoide
sphere { <0, 0, 0>, 1 pigment { color Yellow } scale <1.5, 0.5, 1> translate <-4, 0.5, 0> }

// espelhamento: scale <-1, 1, 1> troca o sinal de x, refletindo no plano x = 0
#declare L = union { box { <0.5, 0, 0>, <0.8, 2, 0.3> } box { <0.5, 0, 0>, <1.6, 0.3, 0.3> } }
object { L pigment { color Blue } }                     // original (x positivo)
object { L pigment { color Cyan } scale <-1, 1, 1> }    // refletido (x negativo)
box { <-0.02, 0, -1>, <0.02, 2.4, 1> pigment { rgbt <1, 1, 1, 0.5> } } // o "espelho" em x = 0""",
         {"camera": "camera {\n    location <-1, 3, -7>\n    look_at <-1, 1, 0>\n}"}),
    ]),
    # ------------------------------------------------------------------
    ("7. Ordem das transformações", [
        ("txt", """<p>As transformações são aplicadas <b>na ordem em que aparecem</b>, e a ordem muda o resultado.
Como <code>rotate</code> e <code>scale</code> são feitos em torno da origem:</p>
<ul><li><b>rotate e depois translate</b>: o objeto gira em torno de si mesmo (estava na origem) e depois vai para o lugar;</li>
<li><b>translate e depois rotate</b>: o objeto já saiu da origem, então ele <b>orbita</b> em volta dela.</li></ul>"""),
        ("ex", "ordem", """#declare Caixa = box { <-0.5, 0, -0.5>, <0.5, 1, 0.5> }
// verde: gira no lugar, depois vai para x=2
object { Caixa pigment { color Green } rotate <0, 45, 0> translate <2, 0, 0> }
// vermelho: vai para x=2, depois gira em volta da ORIGEM
object { Caixa pigment { color Red }   translate <2, 0, 0> rotate <0, 45, 0> }
// referências: a origem e o círculo de raio 2
cylinder { <0, 0, 0>, <0, 1.5, 0>, 0.06 pigment { color White } }
torus { 2, 0.03 pigment { color Yellow } }""",
         {"camera": "camera {\n    location <1, 6, -5>\n    look_at <1, 0, 0>\n}"}),
        ("txt", """<h3>Girar em torno de um ponto qualquer</h3>
<p>Para girar em torno de um ponto P: leve P até a origem, gire e traga de volta.
É a mesma ideia das matrizes compostas da aula: <code>T(P) · R · T(−P)</code>.</p>"""),
        ("ex", "pivo", """// porta com dobradiça em x=1: gira em torno do ponto <1, 0, 0>
#declare Porta = box { <-1, 0, 0>, <1, 2.5, 0.1> }
object { Porta pigment { color rgb 0.6 } }   // fechada (referência)
object { Porta pigment { color Brown }
    translate <-1, 0, 0>   // dobradiça vai para a origem
    rotate <0, -60, 0>     // abre
    translate <1, 0, 0>    // volta para o lugar
}""", {"camera": "camera {\n    location <0, 4, -6>\n    look_at <0, 1, 0>\n}"}),
        ("txt", """<h3>matrix: qualquer transformação afim</h3>
<p><code>matrix &lt;a,b,c, d,e,f, g,h,i, tx,ty,tz&gt;</code> aplica uma matriz 3x3 mais translação.
O ponto (x, y, z) vira <code>(a·x + d·y + g·z + tx, b·x + e·y + h·z + ty, c·x + f·y + i·z + tz)</code>,
ou seja, cada linha de 3 números é para onde vai um eixo. Serve, por exemplo, para o
<b>cisalhamento</b>, que não dá para fazer com rotate/scale.</p>"""),
        ("ex", "matrix", """// cisalhamento: quanto mais alto, mais desloca em x (x' = x + 0.5*y)
box { <-0.5, 0, -0.5>, <0.5, 2, 0.5>
    pigment { color Violet }
    matrix < 1,   0, 0,     // para onde vai o eixo x
             0.5, 1, 0,     // para onde vai o eixo y (inclinado)
             0,   0, 1,     // para onde vai o eixo z
             0,   0, 0 >    // translação
}""", {}),
    ]),
    # ------------------------------------------------------------------
    ("8. Composição (CSG)", [
        ("txt", """<p>CSG (<i>Constructive Solid Geometry</i>) combina sólidos com operações de conjuntos:</p>
<table border=0 cellspacing=6>
<tr><td><code>union { A B }</code></td><td>A ∪ B: junta tudo num objeto só</td></tr>
<tr><td><code>difference { A B }</code></td><td>A − B: tira de A o que estiver em B</td></tr>
<tr><td><code>intersection { A B }</code></td><td>A ∩ B: só a parte que está nos dois</td></tr>
<tr><td><code>merge { A B }</code></td><td>como union, mas sem as paredes internas (melhor para vidro)</td></tr></table>
<p>Transformações e texturas colocadas no fim valem para o conjunto inteiro.</p>"""),
        ("ex", "csg3", """#declare A = box { <-0.8, -0.8, -0.8>, <0.8, 0.8, 0.8> }
#declare B = sphere { 0, 1.05 }
union        { object { A } object { B } pigment { color Red }   translate <-3, 1, 0> }
difference   { object { A } object { B } pigment { color Green } translate < 0, 1, 0> }
intersection { object { A } object { B } pigment { color Blue }  translate < 3, 1, 0> }""",
         {"camera": "camera {\n    location <0, 4, -8>\n    look_at <0, 0.9, 0>\n}"}),
        ("txt", """<p>Exemplo clássico: um <b>dado</b>. É a interseção de uma caixa com uma esfera (cantos
arredondados) menos esferas pequenas (os furos).</p>"""),
        ("ex", "dado", """difference {
    intersection {
        box { -1, 1 }        // -1 vira <-1,-1,-1>
        sphere { 0, 1.4 }
    }
    sphere { <0, 0, -1.15>, 0.3 }                                           // face da frente: 1
    sphere { <-0.45, 1.15, -0.45>, 0.25 } sphere { <0.45, 1.15, 0.45>, 0.25 } // topo: 2
    sphere { <-1.15, 0.45, -0.45>, 0.25 } sphere { <-1.15, 0, 0>, 0.25 }
    sphere { <-1.15, -0.45, 0.45>, 0.25 }                                   // lado: 3
    pigment { color White }
    finish { phong 0.5 }
    rotate <0, 30, 0>
    translate <0, 1, 0>
}""", {"camera": "camera {\n    location <-3, 4, -5>\n    look_at <0, 1, 0>\n}"}),
        ("txt", """<p>Para furar: <code>difference</code> com um cilindro mais comprido que a peça (assim ele
atravessa tudo e não sobra uma película fina).</p>"""),
        ("ex", "furo", """difference {
    cylinder { <0, 0, 0>, <0, 1, 0>, 1.5 }                // arruela
    cylinder { <0, -0.1, 0>, <0, 1.1, 0>, 0.7 }           // furo, um pouco mais alto
    pigment { color rgb <0.7, 0.7, 0.75> }
    finish { phong 0.7 reflection 0.15 }
}""", {}),
    ]),
    # ------------------------------------------------------------------
    ("9. Variáveis, laços e macros", [
        ("txt", """<p><code>#declare Nome = ...;</code> guarda um número, vetor, cor, textura ou objeto para usar depois.
Objetos declarados são usados com <code>object { Nome }</code>, e cada uso pode ter as próprias
transformações e cores.</p>"""),
        ("ex", "declare", """#declare Raio = 0.4;
#declare Boneco = union {
    sphere { <0, Raio, 0>, Raio }
    sphere { <0, Raio*2.5, 0>, Raio*0.7 }
}
object { Boneco pigment { color White } translate <-1.5, 0, 0> }
object { Boneco pigment { color Pink } }
object { Boneco pigment { color Cyan } scale 1.5 translate <1.8, 0, 0> }""", {}),
        ("txt", """<p><code>#for (i, início, fim)</code> repete um trecho. Com ele, padrões geométricos
ficam curtos: uma linha de esferas, um anel, uma escada em espiral.</p>"""),
        ("ex", "for_anel", """// 12 esferas em círculo: cada uma vai para x=2 e gira i*30° em y
#for (i, 0, 11)
    sphere { <2, 0.3, 0>, 0.3
        pigment { color rgb <i/11, 0.4, 1 - i/11> }
        rotate <0, i*30, 0>
    }
#end""", {}),
        ("ex", "for_escada", """// escada em espiral: cada degrau sobe e gira um pouco mais
#for (i, 0, 19)
    box { <0.3, 0, -0.25>, <1.8, 0.1, 0.25>
        pigment { color rgb <0.8, 0.6, 0.4> }
        rotate <0, i*20, 0>
        translate <0, i*0.2, 0>
    }
#end
cylinder { <0, 0, 0>, <0, 4.2, 0>, 0.3 pigment { color White } }""",
         {"camera": "camera {\n    location <0, 6, -7>\n    look_at <0, 1.8, 0>\n}"}),
        ("txt", """<p><code>#macro</code> é uma função que gera objetos a partir de parâmetros.</p>"""),
        ("ex", "macro", """#macro Arvore(Altura, Cor)
    union {
        cylinder { <0, 0, 0>, <0, Altura*0.4, 0>, 0.1 pigment { color Brown } }
        cone { <0, Altura*0.3, 0>, Altura*0.3, <0, Altura, 0>, 0 pigment { color Cor } }
    }
#end
object { Arvore(2, ForestGreen) translate <-2, 0, 0> }
object { Arvore(3, Green) }
object { Arvore(1.5, YellowGreen) translate <2, 0, 0.5> }""", {}),
    ]),
    # ------------------------------------------------------------------
    ("10. Cores e texturas", [
        ("txt", """<p>A aparência de um objeto tem quatro partes, que podem ir juntas dentro de <code>texture { }</code>:</p>
<ul><li><code>pigment</code> – a cor ou o padrão de cores;</li>
<li><code>finish</code> – como a superfície reage à luz (fosca, brilhante, espelhada);</li>
<li><code>normal</code> – relevo falso (amassados, ondas);</li>
<li><code>interior</code> – o que acontece dentro (refração, para vidro e água).</li></ul>
<p>Use <b>Ctrl+Shift+C</b> com o cursor num <code>rgb</code> para escolher a cor numa paleta.</p>"""),
        ("ex", "padroes", """// xadrez
sphere { <-3, 1, 0>, 0.9
    pigment { checker color Red, color White scale 0.3 }
}
// degradê ao longo de y
sphere { <-1, 1, 0>, 0.9
    pigment { gradient y color_map { [0 color Blue] [1 color Yellow] } }
}
// mármore (turbulence bagunça o padrão)
sphere { <1, 1, 0>, 0.9
    pigment { marble turbulence 0.8
              color_map { [0 color White] [1 color rgb 0.2] } }
}
// madeira (anéis em volta do eixo z)
sphere { <3, 1, 0>, 0.9
    pigment { wood scale 0.2
              color_map { [0 color rgb <0.6, 0.35, 0.15>] [1 color rgb <0.35, 0.18, 0.08>] } }
}""",
         {"camera": "camera {\n    location <0, 3, -8>\n    look_at <0, 1, 0>\n}"}),
        ("txt", """<p><b>finish</b>: <code>ambient</code> é a luz própria mínima, <code>diffuse</code> a luz espalhada,
<code>phong</code>/<code>specular</code> o brilho e <code>reflection</code> o espelhamento.</p>"""),
        ("ex", "finish", """sphere { <-3, 1, 0>, 0.9 pigment { color Red } }                                     // padrão
sphere { <-1, 1, 0>, 0.9 pigment { color Red } finish { phong 0.9 phong_size 60 } }  // plástico
sphere { < 1, 1, 0>, 0.9 pigment { color rgb 0.1 } finish { reflection 0.8 } }      // espelho
sphere { < 3, 1, 0>, 0.9 pigment { color Red } normal { bumps 0.6 scale 0.15 } }     // relevo""",
         {"camera": "camera {\n    location <0, 3, -8>\n    look_at <0, 1, 0>\n}"}),
        ("txt", """<p><b>Transparência</b>: <code>rgbf</code> tem um 4º valor, o <i>filter</i> (transparência que tinge a
luz), e <code>rgbt</code> tem o <i>transmit</i> (transparência que não tinge). Para vidro de verdade,
use <code>interior { ior 1.5 }</code>: o índice de refração entorta a luz.</p>"""),
        ("ex", "vidro", """sphere { <0, 1, 0>, 1
    pigment { rgbf <0.9, 1, 0.9, 0.95> }
    finish { specular 0.6 reflection 0.1 }
    interior { ior 1.5 }
}
box { <-0.3, 0, 2>, <0.3, 2.5, 2.3> pigment { color Red } }   // atrás, para ver a refração""", {}),
        ("txt", """<p>Os arquivos <code>textures.inc</code>, <code>metals.inc</code>, <code>stones.inc</code> e
<code>woods.inc</code> trazem texturas prontas. Inclua o arquivo e use o nome.</p>"""),
        ("ex", "prontas", """sphere { <-2.2, 1, 0>, 0.9 texture { T_Stone8 } }
sphere { < 0, 1, 0>, 0.9 texture { T_Gold_3C } }
sphere { < 2.2, 1, 0>, 0.9 texture { T_Wood10 } }""",
         {"extra_inc": ("textures.inc", "metals.inc", "stones.inc", "woods.inc"),
          "camera": "camera {\n    location <0, 3, -7>\n    look_at <0, 1, 0>\n}"}),
    ]),
    # ------------------------------------------------------------------
    ("11. Animação", [
        ("txt", """<p>A variável <code>clock</code> vai de 0 a 1 ao longo da animação. Use-a dentro de qualquer número:
<code>rotate &lt;0, clock*360, 0&gt;</code> dá uma volta completa.</p>
<p>No app: arraste a barra <b>clock</b>, aperte <b>▶</b> para tocar e use <b>Exportar GIF</b> (Ctrl+G)
para salvar a animação.</p>"""),
        ("ex", "anim_gira", """box { <-1, 0, -1>, <1, 1.5, 1>
    pigment { checker color Orange, color White scale 0.5 }
    rotate <0, clock*360, 0>
}""", {}),
        ("txt", """<p>Combinando: uma bola que <b>quica</b> (altura com <code>abs(sin(...))</code>) enquanto anda
de um lado para o outro.</p>"""),
        ("ex", "anim_quica", """#declare Altura = abs(sin(clock*2*pi*2)) * 2;    // 2 quiques por ciclo
sphere { <0, 0.5 + Altura, 0>, 0.5
    pigment { color Red }
    finish { phong 0.8 }
    translate <-3 + 6*clock, 0, 0>
}""", {}),
        ("txt", """<p>Também dá para animar a câmera: aqui ela dá uma volta em torno da cena.</p>"""),
        ("ex", "anim_camera", """camera {
    location <0, 3, -7>
    look_at <0, 1, 0>
    rotate <0, clock*360, 0>    // gira a câmera em volta do eixo y
}
box { <-0.5, 0, -0.5>, <0.5, 2, 0.5> pigment { color Blue } }
sphere { <1.5, 0.5, 0>, 0.5 pigment { color Red } }
cone { <-1.5, 0, 0>, 0.5, <-1.5, 1.5, 0>, 0 pigment { color Green } }""", {"camera": ""}),
    ]),
    # ------------------------------------------------------------------
    ("12. Dicas do app e erros comuns", [
        ("txt", """<h3>Trabalhando rápido</h3>
<ul><li><b>Ctrl + arrastar</b> sobre um número muda o valor ao vivo (Shift junto para ajuste fino);</li>
<li><b>Ctrl+E</b> liga os eixos e <b>F7</b> mostra as vistas de frente, topo e lado: ótimo para conferir posições;</li>
<li><b>Ctrl+P</b> fixa a imagem atual para comparar antes e depois; <b>F8</b> mostra o histórico de versões;</li>
<li>o menu <b>Inserir</b> tem modelos prontos de objetos, luzes e texturas;</li>
<li><b>Ctrl + clique</b> num <code>#include</code> abre o arquivo numa aba;</li>
<li>parar o mouse sobre uma palavra-chave mostra a sintaxe dela;</li>
<li><b>clicar num objeto na imagem</b> leva à linha dele no código e mostra <b>setas X/Y/Z</b> (mover num eixo) e um
<b>anel</b> (girar em y); <b>Ctrl + arrastar</b> na imagem move o objeto no plano da tela;</li>
<li>enquanto você arrasta alguma coisa, aparece uma <b>prévia rápida</b> em OpenGL (sem sombras nem texturas);
ao soltar, vem o render do POV-Ray;</li>
<li><b>F9</b> abre o painel de matrizes: as transformações do objeto sob o cursor como matrizes 4x4,
na convenção da aula ou na do POV-Ray;</li>
<li><b>Ctrl+Shift+F</b> formata o código e <b>Ctrl+Shift+X</b> exporta a entrega (.zip com cena, imagem e GIF);</li>
<li>avisos do POV-Ray aparecem em amarelo na barra de status (<b>⚠</b>), alguns com correção automática.</li></ul>
<h3>Mensagens de erro frequentes</h3>
<table border=0 cellspacing=6>
<tr><td><code>No matching } in ...</code></td><td>faltou fechar uma chave (veja o destaque vermelho do par)</td></tr>
<tr><td><code>Expected 'numeric expression'</code></td><td>número faltando, ou vírgula sobrando ou faltando num vetor</td></tr>
<tr><td><code>Undeclared identifier 'Xxx'</code></td><td>nome escrito errado, ou faltou o <code>#include</code> que o define</td></tr>
<tr><td><code>Cannot open include file</code></td><td>nome do arquivo errado ou ele está em outra pasta</td></tr>
<tr><td>imagem toda preta</td><td>sem luz, luz dentro de um objeto ou câmera dentro de um objeto</td></tr>
<tr><td>objeto não aparece</td><td>fora do campo da câmera, atrás dela, escondido no chão ou sem <code>pigment</code></td></tr></table>"""),
    ]),
]


def exemplos():
    """{id: cena completa} de todos os exemplos (usado também nos testes)."""
    r = {}
    for _, blocos in topicos():
        for b in blocos:
            if b[0] == "ex":
                _, id_, trecho, op = b
                r[id_] = cena_completa(trecho, op.get("camera", CAMERA_PADRAO), op.get("chao", CHAO_PADRAO),
                                       op.get("extra_inc", ()))
    return r


ESTILO = """<style>
body { font-size: 11pt; }
h2 { color: #66d9ef; } h3 { color: #a6e22e; margin-bottom: 2px; }
code { background: #333; color: #e6db74; }
pre { background: #272822; color: #f8f8f2; padding: 8px; font-family: monospace; }
a { color: #6fa8ff; }
</style>"""


def html_topico(i):
    titulo, blocos = topicos()[i]
    partes = [ESTILO, f"<h2>{titulo}</h2>"]
    for b in blocos:
        if b[0] == "txt":
            partes.append(b[1])
        elif b[0] == "dica":
            partes.append("<table width='100%' cellpadding=8 style='background:#2d3a2d'><tr><td>💡 "
                          + b[1] + "</td></tr></table><br>")
        else:
            _, id_, trecho, _op = b
            partes.append(f"<pre>{html.escape(trecho)}</pre>"
                          f"<p><a href='exemplo:{id_}'>▶ " + tr("Abrir exemplo numa aba nova") + "</a></p>")
    return "\n".join(partes)


def titulo_exercicios():
    return tr("13. Exercícios")


def html_exercicios():
    partes = [ESTILO, f"<h2>{titulo_exercicios()}</h2>",
              "<p>" + tr("Cada exercício abre numa aba nova com a câmera e as luzes prontas. Escreva sua resposta "
                         "e use <b>Ajuda &gt; Verificar exercício</b> (<b>Ctrl+Shift+V</b>): o app renderiza a sua "
                         "cena e o gabarito e compara as duas imagens. A dica aparece se não estiver certo.") + "</p>"]
    for e in exercicios.EXERCICIOS:
        titulo, enunciado = exercicios.campo(e, "titulo"), exercicios.campo(e, "enunciado")
        partes.append(f"<h3>{html.escape(titulo)}</h3><p>{html.escape(enunciado)}</p>"
                      f"<p><img src='gabarito:{e['id']}' width=320 height=240></p>"
                      f"<p><a href='exercicio:{e['id']}'>▶ " + tr("Começar este exercício") + "</a></p>")
    return "\n".join(partes)


class Navegador(QTextBrowser):
    """QTextBrowser que mostra as imagens dos gabaritos (do cache)."""

    def loadResource(self, tipo, url):
        if tipo == QTextDocument.ImageResource and url.scheme() == "gabarito":
            ex = exercicios.POR_ID.get(url.path())
            if ex:
                w, h = exercicios.TAMANHO
                arq = exercicios.arquivo_cache(exercicios.texto_gabarito(ex), w, h)
                if os.path.exists(arq):
                    return QImage(arq)
                img = QImage(w, h, QImage.Format_RGB32)
                img.fill(0x333333)
                return img
        return super().loadResource(tipo, url)


class Guia(QDialog):
    def __init__(self, janela):
        super().__init__(janela)
        self.janela = janela
        self.setWindowTitle(tr("Guia do POV-Ray"))
        self.resize(1000, 720)
        self.cenas = exemplos()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        sp = QSplitter()
        self.lista = QListWidget()
        self.lista.addItems([t for t, _ in topicos()] + [titulo_exercicios()])
        self.lista.setMinimumWidth(250)
        self.lista.setMaximumWidth(320)
        self.texto = Navegador()
        self.texto.setOpenLinks(False)
        self.texto.anchorClicked.connect(self._link)
        sp.addWidget(self.lista)
        sp.addWidget(self.texto)
        sp.setSizes([260, 740])
        lay.addWidget(sp)
        self.lista.currentRowChanged.connect(self._mostrar)
        self.lista.setCurrentRow(0)

    def _mostrar(self, i):
        if i == len(topicos()):
            self.texto.setHtml(html_exercicios())
            self._gerar_gabaritos()
        else:
            self.texto.setHtml(html_topico(i))

    def ir_para_exercicios(self):
        self.lista.setCurrentRow(len(topicos()))

    def _gerar_gabaritos(self):
        """Renderiza (uma vez) as imagens dos gabaritos que ainda não estão no cache."""
        w, h = exercicios.TAMANHO
        for e in exercicios.EXERCICIOS:
            texto = exercicios.texto_gabarito(e)
            arq = exercicios.arquivo_cache(texto, w, h)
            if not os.path.exists(arq) and arq not in getattr(self, "_pedidos", set()):
                self._pedidos = getattr(self, "_pedidos", set()) | {arq}
                self.janela.fila.adicionar(texto, arq, [f"+W{w}", f"+H{h}"] + exercicios.ARGS,
                                           lambda ok, log: self._recarregar())

    def _recarregar(self):
        if self.lista.currentRow() == len(topicos()):
            barra = self.texto.verticalScrollBar().value()
            self.texto.document().clear()
            self.texto.setHtml(html_exercicios())
            self.texto.verticalScrollBar().setValue(barra)

    def _link(self, url):
        s = url.toString()
        if s.startswith("exemplo:"):
            id_ = s.split(":", 1)[1]
            self.janela.abrir_exemplo(id_, self.cenas[id_])
        elif s.startswith("exercicio:"):
            self.janela.comecar_exercicio(s.split(":", 1)[1])
