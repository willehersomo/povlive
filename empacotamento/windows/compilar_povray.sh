#!/bin/bash
# Compila o POV-Ray 3.7 de linha de comando (a versão Unix) no Cygwin e junta numa pasta o que o PovLive
# precisa no Windows: bin/povray.exe com as DLLs do Cygwin, os includes padrão e as licenças.
# Uso (dentro do Cygwin):  bash compilar_povray.sh /cygdrive/c/caminho/da/saida
set -euo pipefail
VERSAO=3.7.0.10
DESTINO=${1:?informe a pasta de saída}
TRAB=$(mktemp -d)
cd "$TRAB"
curl -sSL "https://github.com/POV-Ray/povray/archive/refs/tags/v$VERSAO.tar.gz" | tar xz
cd "povray-$VERSAO/unix"
./prebuild.sh
cd ..
./configure COMPILED_BY="PovLive <https://github.com/willehersomo/povlive>" --prefix=/opt/povray \
    --disable-io-restrictions --without-x --without-openexr --with-boost-thread=boost_thread \
    CXXFLAGS="-O2 -std=gnu++11 -w" LIBS="-lboost_system"
make -j"$(nproc)"
make install

mkdir -p "$DESTINO/bin" "$DESTINO/share/povray-3.7" "$DESTINO/licencas"
cp /opt/povray/bin/povray.exe "$DESTINO/bin/"
cp -r /opt/povray/share/povray-3.7/include "$DESTINO/share/povray-3.7/"
# DLLs do Cygwin que o povray.exe usa (cygwin1.dll, boost, png, jpeg, tiff, zlib...)
ldd /opt/povray/bin/povray.exe | awk '$3 ~ /^\/usr\/bin\// {print $3}' | sort -u | while read -r dll; do
    cp "$dll" "$DESTINO/bin/"
done
cp LICENSE "$DESTINO/licencas/POV-Ray-AGPL-3.0.txt"
cp /usr/share/doc/cygwin/COPYING "$DESTINO/licencas/Cygwin-COPYING.txt" 2>/dev/null || true
cat > "$DESTINO/LEIAME.txt" <<TXT
POV-Ray $VERSAO (versão de linha de comando) compilado com o Cygwin para o PovLive.

POV-Ray: AGPL-3.0, código-fonte em https://github.com/POV-Ray/povray/tree/v$VERSAO
Cygwin (cygwin1.dll): LGPL-3.0, código-fonte em https://cygwin.com/
As outras DLLs vêm dos pacotes do Cygwin (boost, libpng, libjpeg, libtiff, zlib), com o código em
https://cygwin.com/packages/. O script que gera esta pasta está em
https://github.com/willehersomo/povlive/blob/main/empacotamento/windows/compilar_povray.sh
TXT
"$DESTINO/bin/povray.exe" --version 2>&1 | head -3 || true
ls -la "$DESTINO/bin"
