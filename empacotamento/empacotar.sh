#!/bin/bash
# Gera o pacote .deb do PovLive.  Uso: ./empacotar.sh [pasta de saída]
# Instalar:  sudo apt install ./povlive_<versão>_all.deb   (o apt baixa povray, PyQt5 e Pillow se faltar)
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(dirname "$AQUI")"
VERSAO=$(python3 -c "import sys; sys.path.insert(0,'$RAIZ'); import povlive_app; print(povlive_app.__version__)")
SAIDA="${1:-$AQUI}"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
P="$TMP/povlive_${VERSAO}_all"

mkdir -p "$P/DEBIAN" "$P/usr/lib/povlive/povlive_app" "$P/usr/bin" \
         "$P/usr/share/applications" "$P/usr/share/icons/hicolor/scalable/apps"
cp "$RAIZ"/povlive_app/*.py "$P/usr/lib/povlive/povlive_app/"
cp "$RAIZ/povlive.py" "$P/usr/lib/povlive/povlive.py"
sed -i '1s|.*|#!/usr/bin/python3|' "$P/usr/lib/povlive/povlive.py"   # Python do sistema, não o do usuário
chmod 755 "$P/usr/lib/povlive/povlive.py"
ln -s ../lib/povlive/povlive.py "$P/usr/bin/povlive"
cp "$AQUI/povlive.desktop" "$P/usr/share/applications/"
cp "$AQUI/povlive.svg" "$P/usr/share/icons/hicolor/scalable/apps/"

cat > "$P/DEBIAN/control" <<CTRL
Package: povlive
Version: $VERSAO
Architecture: all
Maintainer: Breno Wille <brenowille23@gmail.com>
Depends: python3 (>= 3.8), python3-pyqt5, povray, povray-includes, python3-pil, python3-numpy, python3-opengl
Recommends: qttranslations5-l10n
Section: graphics
Priority: optional
Homepage: https://github.com/willehersomo/povlive
Description: POV-Ray scene editor with live preview
 Code on one side and the image on the other, rendered as you type.
 Instant OpenGL preview while dragging, move/rotate arrows on objects,
 free camera, four views, transformation matrices, a guide with 33
 examples and auto-graded exercises. Interface in English and Portuguese.
CTRL

find "$P" -type d -exec chmod 755 {} +
find "$P" -type f ! -name povlive.py -exec chmod 644 {} +
fakeroot dpkg-deb --build "$P" "$SAIDA/" >/dev/null
echo "Gerado: $SAIDA/povlive_${VERSAO}_all.deb"
