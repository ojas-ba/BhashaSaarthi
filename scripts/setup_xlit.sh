#!/usr/bin/env bash
# Local-only legacy runtime. No system package changes. Keep this process alive
# when using /tmp on a WSL distro that clears temporary files on shutdown.
set -euo pipefail
XLIT_ENV="${XLIT_ENV:-/tmp/hinglish-xlit}"
python3.10 -m venv --without-pip "$XLIT_ENV"
python3.10 -c 'import urllib.request,sys; urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py",sys.argv[1])' "$XLIT_ENV/get-pip.py"
"$XLIT_ENV/bin/python" "$XLIT_ENV/get-pip.py" 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
"$XLIT_ENV/bin/python" -m pip install --extra-index-url https://download.pytorch.org/whl/cpu 'torch==1.13.1+cpu' 'torchaudio==0.13.1+cpu' 'numpy==1.23.5' 'fairseq==0.12.2'
"$XLIT_ENV/bin/python" -m pip install --no-deps 'ai4bharat-transliteration==1.1.3'
# Upstream package metadata lists unused web/other-language dependencies.
# Their absence is intentional for the direct official Fairseq class below.
exec "$XLIT_ENV/bin/python" -u scripts/xlit_worker.py
