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
cd "povray-$VERSAO"
# o código recusa o Cygwin só por precaução ("not explicitly supported yet"): trata como o macOS,
# que também não tem lseek64 (no Cygwin de 64 bits o lseek já é de 64 bits)
sed -i 's|#error Cygwin detected, but not explicitly supported yet; proceed at your own risk.|#include <unistd.h>\n    #define lseek64(handle,offset,whence) lseek(handle,offset,whence)|' \
    vfe/unix/syspovconfig.h
grep -q "Cygwin detected, but not" vfe/unix/syspovconfig.h && { echo "o patch do Cygwin não entrou"; exit 1; }
cd unix
./prebuild.sh
cd ..
# --disable-optimiz: o configure ligaria -ffast-math, e com ele os GCC novos tratam "x != HUGE_VAL" como
# sempre verdadeiro; o POV-Ray usa isso para "ângulo da câmera não informado" e passa a recusar qualquer
# câmera ("Viewing angle has to be smaller than 180"). Também evita otimizar para o processador da máquina
# que compila (o binário roda em qualquer x86-64). As otimizações ficam por conta do -O2 do CXXFLAGS.
# No Windows, com a cygwin1.dll junto, a raiz "/" do Cygwin é a pasta acima de bin/. Por isso os caminhos
# são /bin, /share e /etc: o povray.exe acha sozinho os includes e o povray.ini dentro da pasta povray/.
./configure COMPILED_BY="PovLive <https://github.com/willehersomo/povlive>" --prefix=/opt/povray \
    --bindir=/bin --datadir=/share --sysconfdir=/etc --mandir=/share/man --docdir=/share/doc \
    --disable-optimiz --disable-io-restrictions --without-x --without-openexr --without-libsdl --with-boost-thread=boost_thread \
    CXXFLAGS="-O2 -std=gnu++11 -w" LIBS="-lboost_system"
make -j"$(nproc)"
make install DESTDIR="$TRAB/inst"

mkdir -p "$DESTINO/bin" "$DESTINO/share/povray-3.7" "$DESTINO/etc/povray/3.7" "$DESTINO/tmp" "$DESTINO/licencas"
EXE=povray; [ -f "$TRAB/inst/bin/povray.exe" ] && EXE=povray.exe     # .exe no Cygwin
cp "$TRAB/inst/bin/$EXE" "$DESTINO/bin/"
cp -r "$TRAB/inst/share/povray-3.7/include" "$DESTINO/share/povray-3.7/"
cp "$TRAB/inst/etc/povray/3.7/povray.conf" "$TRAB/inst/etc/povray/3.7/povray.ini" "$DESTINO/etc/povray/3.7/"
# DLLs do Cygwin que o povray.exe usa (cygwin1.dll, boost, png, jpeg, tiff, zlib...)
ldd "$DESTINO/bin/$EXE" | awk '$3 ~ /^\/usr\/bin\// {print $3}' | sort -u | while read -r dll; do
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
"$DESTINO/bin/$EXE" --version 2>&1 | head -3 || true
ls -la "$DESTINO/bin"
