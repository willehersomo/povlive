#!/bin/bash
# Monta o PovLive-<versão>-x86_64.AppImage: um Python próprio (python-appimage), PyQt5/numpy/Pillow/
# PyOpenGL do pip, o app e o POV-Ray (compilado sem X/SDL) com as bibliotecas dele.
# Precisa de: curl, patchelf e o que o compilar_povray.sh pede (g++, autotools, boost, png, jpeg, tiff, zlib).
# Uso: empacotamento/appimage/montar.sh <pasta de saída>
set -euo pipefail
mkdir -p "${1:?informe a pasta de saída}"
SAIDA=$(realpath "$1")
RAIZ=$(cd "$(dirname "$0")/../.." && pwd)
VERSAO=$(cd "$RAIZ" && python3 -c "import povlive_app; print(povlive_app.__version__)")
PY=python3.12
TRAB=$(mktemp -d)
cd "$TRAB"

# 1. Python portátil
url=$(curl -sSL "https://api.github.com/repos/niess/python-appimage/releases/tags/$PY" | python3 -c \
  "import json,sys; print(next(a['browser_download_url'] for a in json.load(sys.stdin)['assets'] if a['name'].endswith('manylinux2014_x86_64.AppImage')))")
curl -sSL -o python.AppImage "$url"
chmod +x python.AppImage
./python.AppImage --appimage-extract > /dev/null
mv squashfs-root AppDir
PYBIN="AppDir/opt/$PY/bin/$PY"
"$PYBIN" -m pip install --quiet --no-cache-dir --no-warn-script-location PyQt5 numpy pillow PyOpenGL
# módulos do Qt que o app não usa (deixam o AppImage bem menor)
QT="AppDir/opt/$PY/lib/$PY/site-packages/PyQt5"
for m in Quick QuickWidgets QuickTest QuickParticles QuickShapes QuickTemplates2 QuickControls2 Qml QmlModels \
         QmlWorkerScript WebSockets Multimedia MultimediaWidgets MultimediaGstTools Bluetooth Nfc Sensors \
         SerialPort Positioning PositioningQuick Location RemoteObjects Designer Help Test XmlPatterns \
         WebChannel Sql 3DCore 3DRender 3DInput 3DLogic 3DAnimation 3DExtras 3DQuick 3DQuickScene2D \
         Gamepad TextToSpeech Bodymovin; do
  rm -f "$QT/Qt5/lib/libQt5$m.so"* "$QT/Qt$m."*.so "$QT/Qt$m.pyi"
done
rm -rf "$QT/Qt5/qml" "$QT/Qt5/plugins/"{sqldrivers,mediaservice,audio,playlistformats,sensors,geoservices,position,sceneparsers,renderers,texttospeech,gamepads,canbus,webview}
rm -f AppDir/AppRun AppDir/*.desktop AppDir/*.png AppDir/.DirIcon
rm -rf AppDir/usr/share/applications AppDir/usr/share/metainfo AppDir/usr/share/icons

# 2. o app
mkdir -p AppDir/opt/povlive/empacotamento
cp -r "$RAIZ/povlive.py" "$RAIZ/povlive_app" AppDir/opt/povlive/
cp "$RAIZ/empacotamento/povlive.svg" AppDir/opt/povlive/empacotamento/
find AppDir/opt/povlive -name __pycache__ -prune -exec rm -rf {} +

# 3. o POV-Ray e as bibliotecas dele (menos as do sistema base: glibc e libgcc)
bash "$RAIZ/empacotamento/windows/compilar_povray.sh" "$TRAB/povray"
cp -r "$TRAB/povray" AppDir/opt/povlive/povray
mkdir -p AppDir/opt/povlive/povray/lib
ldd AppDir/opt/povlive/povray/bin/povray | awk '$3 ~ /^\// {print $3}' | while read -r so; do
  case "$(basename "$so")" in
    libc.so*|libm.so*|libdl.so*|libpthread.so*|librt.so*|ld-linux*|libgcc_s.so*) ;;
    *) cp -L "$so" AppDir/opt/povlive/povray/lib/ ;;
  esac
done
patchelf --set-rpath '$ORIGIN/../lib' AppDir/opt/povlive/povray/bin/povray

# 4. AppRun, atalho e ícone
cat > AppDir/AppRun <<SH
#!/bin/sh
HERE="\$(dirname "\$(readlink -f "\$0")")"
export PYTHONNOUSERSITE=1
unset PYTHONHOME PYTHONPATH
exec "\$HERE/opt/$PY/bin/$PY" "\$HERE/opt/povlive/povlive.py" "\$@"
SH
chmod +x AppDir/AppRun
cp "$RAIZ/empacotamento/povlive.desktop" AppDir/povlive.desktop
cp "$RAIZ/empacotamento/povlive.svg" AppDir/povlive.svg
ln -sf povlive.svg AppDir/.DirIcon

# 5. AppImage
curl -sSL -o appimagetool \
  https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 ./appimagetool --no-appstream AppDir "$SAIDA/PovLive-$VERSAO-x86_64.AppImage"
ls -la "$SAIDA"
