#!/bin/sh
if [ -z "$(find /app/parts -maxdepth 3 -name '*.stl' -print -quit 2>/dev/null)" ]; then
  echo "WARNING: no .stl files found in /app/parts. Mount your USSA parts folder there (see INSTALL.md)."
  echo "         The site will load, but Build will fail with 404 errors."
fi
echo "VaultBox listening on 0.0.0.0:8765"
exec python3 -m http.server 8765 --bind 0.0.0.0 --directory /app
