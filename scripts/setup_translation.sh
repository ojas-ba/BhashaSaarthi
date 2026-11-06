#!/usr/bin/env bash
set -euo pipefail
# Standard authenticated HTTP downloads avoid a separate Xet/CAS transport path.
export HF_HUB_DISABLE_XET="${HF_HUB_DISABLE_XET:-1}"
TRANSLATION_ENV="${TRANSLATION_ENV:-/tmp/hinglish-translation}"
if [ ! -x "$TRANSLATION_ENV/bin/python" ]; then
  python3 -m venv --without-pip "$TRANSLATION_ENV"
  python3 -c 'import urllib.request,sys; urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py",sys.argv[1])' "$TRANSLATION_ENV/get-pip.py"
  "$TRANSLATION_ENV/bin/python" "$TRANSLATION_ENV/get-pip.py"
fi
"$TRANSLATION_ENV/bin/python" -m pip install --disable-pip-version-check --index-url https://download.pytorch.org/whl/cpu 'torch==2.5.1+cpu'
"$TRANSLATION_ENV/bin/python" -m pip install --disable-pip-version-check -r requirements-translation-worker.txt
"$TRANSLATION_ENV/bin/python" -m pip check
exec "$TRANSLATION_ENV/bin/python" -u scripts/translation_worker.py
