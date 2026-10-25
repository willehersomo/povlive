# POV-Ray ao vivo

[![CI](https://github.com/willehersomo/povlive/actions/workflows/ci.yml/badge.svg)](https://github.com/willehersomo/povlive/actions/workflows/ci.yml)

Editor de cenas [POV-Ray](https://www.povray.org/) para Linux, com o código de um lado e a imagem do outro,
renderizada enquanto você digita. Foi feito para estudar Computação Gráfica: além do preview ao vivo, ele
mostra as **matrizes das transformações**, deixa **clicar e arrastar objetos na imagem**, tem **câmera livre
com o mouse**, **quatro vistas**, um **guia com 33 exemplos** e **exercícios corrigidos automaticamente**.

![Janela principal](docs/img/janela.png)

## Recursos

**Preview ao vivo**
- A cena renderiza de novo meio segundo depois que você para de digitar (primeiro uma prévia pequena, depois a completa).
- **Ctrl + arrastar um número** no código muda o valor e a imagem acompanha.
- Erros marcam a linha em vermelho e vêm explicados em português; avisos aparecem em amarelo, alguns com correção automática.
- Os `.inc` abertos em abas entram no render mesmo sem salvar.

**Interagir com a imagem**
- **Clique num objeto** e o cursor vai para a linha dele no código.
- **Ctrl + arrastar um objeto** move ele; o `translate` no código é atualizado sozinho.
- **Câmera livre (F6)**: girar, mover e aproximar com o mouse, sem travar (veja [como](#como-a-câmera-livre-fica-fluida)). **Shift+F6** copia a câmera escolhida para o código.
- **Quatro vistas (F7)**: perspectiva, frente, topo e lado, com câmeras ortográficas.
- Eixos X/Y/Z, comparação antes/depois, histórico de versões salvo em disco e zoom com leitura do pixel.

<p align="center"><img src="docs/img/camera_livre.gif" width="480" alt="Câmera livre girando em volta da cena"></p>

**Estudo**
- **Painel de matrizes (F9)**: as transformações do objeto sob o cursor como matrizes 4×4, passo a passo, na convenção
  da aula (ponto em coluna, `M = Mₙ···M₁`, `M_r` horária) ou na do POV-Ray (ponto em linha). As contas são conferidas
  contra o `vtransform` do próprio POV-Ray nos testes.
- **Guia (F1)** com 12 tópicos — sólidos, transformações, ordem das transformações, CSG, laços, texturas, animação —
  e 33 exemplos que abrem numa aba com um clique.
- **Exercícios** com gabarito: o app renderiza a sua resposta e o gabarito, compara as imagens e mostra a diferença.

| Quatro vistas | Matrizes | Exercício |
|---|---|---|
| ![](docs/img/quatro_vistas.png) | ![](docs/img/matrizes.png) | ![](docs/img/exercicio.png) |

**Editor**: destaque de sintaxe, autocompletar (inclusive nomes dos `#include`), ajuda ao passar o mouse, fechamento
automático de `{ ( [ < "`, par de chaves destacado, comentar com Ctrl+/, buscar e substituir, formatar (Ctrl+Shift+F),
seletor de cor ao vivo, modelos prontos (menu Inserir) e abas.

**Saída**: PNG, GIF da animação (variável `clock`) e **exportar entrega** — um `.zip` com a cena, os `.inc`, a imagem
em alta, o GIF e um LEIAME com o comando para renderizar.

## Instalar

**Pacote .deb** (Ubuntu, Debian, Pop!_OS, Mint) — baixe em [Releases](https://github.com/willehersomo/povlive/releases):

```bash
sudo apt install ./povlive_3.0.0_all.deb    # instala também povray, PyQt5 e Pillow
povlive cena.pov
```

**Direto do código**:

```bash
sudo apt install povray python3-pyqt5 python3-pil python3-numpy
git clone https://github.com/willehersomo/povlive.git
python3 povlive/povlive.py cena.pov
```

Funciona offline. **F1** abre o guia e **Shift+F1** a lista de atalhos.

## Como funciona

O app chama o próprio `povray` para renderizar; o resultado é idêntico ao da linha de comando. Algumas partes
interessantes:

### Como a câmera livre fica fluida
Medindo, todo render do POV-Ray 3.7 leva ~0,75 s **mesmo para uma cena vazia em 160×120** — é um custo fixo de
inicialização. Diminuir a imagem não ajuda. Então, com a câmera livre ligada e o mouse parado, o app pré-renderiza
a cena em 36 ângulos × 7 alturas (252 imagens) usando o modo de animação do POV-Ray: 12 processos em prioridade baixa,
cada um com uma faixa de quadros (`+SF`/`+EF`), e a cena calcula a câmera de cada quadro a partir de `frame_number`.
A ordem dos quadros é intercalada para os ângulos mais próximos da vista atual ficarem prontos primeiro.
Ao arrastar, aparece o quadro mais próximo, e até 4 renders da posição exata rodam em paralelo.
No zoom e no mover, a imagem atual é deformada na hora até o render exato chegar.

| | sem cache | com cache |
|---|---|---|
| primeira resposta ao arrastar | 0,8 s | 0,02 s |
| imagens novas por segundo | 4 | 12,5 |
| atraso médio em relação ao mouse | > 100° | 2,5° |

### Como o clique acha o objeto
O app renderiza (em segundo plano) uma cópia da cena em que cada objeto ganha uma cor única e chapada:
as aparências originais são apagadas, e cada bloco recebe `texture { pigment { rgb <id> } finish { emission 1 ... } }`,
com `File_Gamma=1.0`, `ambient_light 0` e sem antialiasing, para a cor no PNG ser exata. A cor do pixel clicado diz
qual bloco do código o gerou. Objetos dentro de `#declare` não são marcados, para cada `object { Nome }` ter a
própria cor.

### Estrutura

```
povlive.py              lançador
povlive_app/
  janela.py             janela principal, abas e motor de render (prévia → final, 4 vistas)
  recursos.py           matrizes, avisos, seleção/arraste na imagem, exercícios, entrega
  editor.py             editor de código (sintaxe, pares, autocompletar, busca)
  visor.py              visor de imagem (zoom, câmera livre, destaque), 4 vistas, histórico
  cache_orbita.py       cache de órbita da câmera livre
  sdl.py                leitura do código POV-Ray: blocos, expressões, transformações
  matrizes.py           matrizes 4×4 nas duas convenções
  selecao.py            cores únicas por objeto (clique/arraste)
  pov.py, guia.py, exercicios.py, avisos.py, formatador.py, entrega.py, fila.py
tests/                  testes (pytest, Qt sem janela)
empacotamento/          script do .deb, ícone e atalho
docs/                   prints e o script que gera eles
extras/povlive_web.py   primeira versão (editor no navegador)
```

## Testes

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest -q
```

São 83 testes: leitura do código, matrizes comparadas com o POV-Ray, formatador (a imagem antes e depois de formatar
tem que ser idêntica), seleção por cor, avisos, os 33 exemplos do guia (nenhum pode dar erro ou aviso), os 7
exercícios (o gabarito passa e o código inicial não) e testes de integração que abrem o app, digitam, clicam e
arrastam na imagem, exportam a entrega e conferem o histórico. O CI roda tudo em cada push e gera o `.deb`;
numa tag `v*`, o `.deb` é publicado em Releases.

Para regerar os prints: `python3 docs/gerar_imagens.py`.

## Licença

MIT — veja [LICENSE](LICENSE).
