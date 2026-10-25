# Contributing to PovLive

Thanks for helping! Issues and pull requests are welcome in English or Portuguese.

## Running from source

```bash
sudo apt install povray povray-includes python3-pyqt5 python3-pil python3-numpy python3-opengl python3-pytest
python3 povlive.py scene.pov
```

On other systems, `pip install PyQt5 numpy pillow PyOpenGL pytest` works too. Set `POVLIVE_POVRAY` (the
`povray` program) and `POVLIVE_INCLUDE` (the folder with `colors.inc`) if they are not found automatically.

## Before a pull request

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest -q     # ~2.5 min; renders with the real POV-Ray
pipx run ruff check .                               # or: ruff check .
python3 povlive.py --autoteste                      # opens the app hidden, renders a scene, exits 0/1
```

CI runs the same on Linux and Windows, measures coverage (it must stay above 70%) and builds the `.deb`,
the AppImage and the Windows installer.

## Conventions

- **The code is in Portuguese** (names, comments, commit messages). It started as a study project for a
  Brazilian Computer Graphics course; keeping one language makes it easier to read. English is fine in
  issues and pull request descriptions.
- **Every text shown in the interface goes through `tr("...")`** (or `N_("...")` for tables defined at
  import time) with the Portuguese text, and gets an English version in `povlive_app/traducoes_en.py`.
  `tests/test_i18n.py` fails if a marked text has no translation, if a translation is left over, or if
  any Portuguese shows up in the English interface.
- **Guide examples and exercises exist in both languages**: `guia.py` / `guia_en.py` and
  `exercicios.py` (`EN`). Tests render every example and exercise in both languages and fail on any
  POV-Ray warning.
- **Matrices follow the course convention** in the matrix panel and the 2D practice (column points,
  `M = Mn···M1`, `M_r` is the *clockwise* rotation, `M_fx` flips the sign of x). It differs from most
  textbooks on purpose; see `matrizes.py`.
- Platform differences (Linux/Windows paths, the POV-Ray program, cache folders) live in
  `plataforma.py`. Start POV-Ray with `pov.iniciar(proc, args)` so paths and include folders are right.

## Where things are

| | |
|---|---|
| `janela.py` | main window, tabs, render engine |
| `editor.py` | code editor |
| `visor.py` | image viewer, four views, history |
| `previa3d.py`, `csg.py` | instant OpenGL preview and its CSG |
| `sdl.py`, `matrizes.py` | reading POV-Ray code, transformation matrices |
| `selecao.py`, `interacao.py` | clicking/dragging objects in the image |
| `texturas.py`, `biblioteca.py` | texture library |
| `arvore.py`, `navegar.py` | scene tree, go to definition, rename |
| `importar.py` | OBJ/STL import |
| `treino2d.py`, `treino2d_ui.py` | 2D transformations practice |
| `empacotamento/` | `.deb`, AppImage and Windows (Cygwin POV-Ray, PyInstaller, Inno Setup) |

## Packaging

- `.deb`: `./empacotamento/empacotar.sh dist`
- AppImage: `./empacotamento/appimage/montar.sh dist` (compiles POV-Ray; needs boost, png, jpeg, tiff, zlib)
- Windows: built by `.github/workflows/windows.yml`. POV-Ray's Unix (command-line) version is compiled
  with Cygwin by `empacotamento/windows/compilar_povray.sh` and shipped next to `PovLive.exe`.

A `v*` tag publishes everything in GitHub Releases.
