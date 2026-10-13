#!/usr/bin/env bash
# Compila Kenti Limnología (Windows .exe y Linux).
# Requiere Go (>=1.21) y Python 3 con Pillow. Uso: ./build.sh
set -euo pipefail
cd "$(dirname "$0")"
VER=0.6.1
L=launcher; APPID=kenti-limnologia; NAME="Kenti Limnología"; EXE="Kenti Limnologia"; FOLDER="Kenti Limnologia"; PORT=47860
rm -rf "$L/web"
python3 prep.py base
cp -r src/web/. "$L/web/"
python3 scripts/icono.py src/web/icono.png "$L/rsrc_windows_amd64.syso"
mkdir -p "out/$NAME"
LD="-s -w -X 'main.appID=$APPID' -X 'main.appName=$NAME' -X 'main.folderName=$FOLDER' -X 'main.portText=$PORT' -X 'main.version=$VER'"
( cd "$L"
  CGO_ENABLED=0 GOOS=windows GOARCH=amd64 eval go build -trimpath -ldflags "\"-H windowsgui $LD\"" -o "\"../out/$NAME/$EXE.exe\"" .
  CGO_ENABLED=0 eval go build -ldflags "\"$LD\"" -o "\"../out/$NAME/kenti-linux\"" . )
ls -la out/*
