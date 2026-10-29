#!/bin/sh
# Serves the VaultBox site (needed so the page can fetch STL files).
cd "$(dirname "$0")" && echo "VaultBox on http://localhost:8765/" && exec python3 -m http.server 8765 --bind 127.0.0.1
