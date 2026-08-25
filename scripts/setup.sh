#!/usr/bin/env bash
# setup.sh — create the Python venv for this Airtest project.
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo ">>> creating venv at .venv ..."
python3 -m venv .venv
./.venv/bin/pip install -q --upgrade pip
echo ">>> installing requirements ..."
./.venv/bin/pip install -q -r requirements.txt
echo ">>> done. Verify:"
./.venv/bin/python -c "import airtest, poco; print('airtest', airtest.__version__, '| poco OK')"
echo ""
echo "Next:"
echo "  1) set BUNDLE_ID in config.py (or export BUNDLE_ID=...)"
echo "  2) start WDA:  ./scripts/wda.sh   (iPhone unlocked)"
echo "  3) run:        ./.venv/bin/python tests/connect_check.py"
