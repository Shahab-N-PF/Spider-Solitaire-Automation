#!/usr/bin/env bash
# wda.sh — start WebDriverAgent for this Airtest project.
#
# Launches an already-signed WDA test bundle on the device, forwards port 8100
# and waits until WDA is healthy. NO signing and NO build happen here.
#
# The signed build is COMMITTED to this repo at wda/ (see wda/README.md), so a
# fresh clone needs nothing else. It only installs on the 9 devices baked into
# its provisioning profile, and it expires around 2027-07-02 — wda/README.md
# lists both, and SETUP.md covers rebuilding.
#
# If wda/ is absent (e.g. a partial checkout) it falls back to the old source:
# the sudoku-automation repo this build originally came from.
#
# Usage:
#   ./scripts/wda.sh                 # auto-detect device, port 8100
#   ./scripts/wda.sh <UDID>          # explicit device
#   WDA_PORT=8200 ./scripts/wda.sh
#   WDA_PRODUCTS=/path ./scripts/wda.sh    # override which build to launch
#   SUDOKU_REPO=~/path ./scripts/wda.sh    # point the fallback elsewhere
#
# Prereqs: iPhone connected + UNLOCKED, Xcode installed, and the developer
# certificate trusted on the phone.

set -u

PORT="${WDA_PORT:-8100}"
IPROXY_BIN="${IPROXY_BIN:-$(command -v iproxy || echo /opt/homebrew/bin/iproxy)}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── which signed build to launch ──────────────────────────────────
# In-repo first (the committed one), then the sudoku-automation repo this build
# originally came from. WDA_PRODUCTS overrides both.
SUDOKU_REPO="${SUDOKU_REPO:-$HOME/sudoku-automation}"
DERIVED="${WDA_DERIVED:-$SUDOKU_REPO/target/wda/derived}"
if [ -n "${WDA_PRODUCTS:-}" ]; then
    PRODUCTS="$WDA_PRODUCTS"; SOURCE="WDA_PRODUCTS override"
elif ls "$ROOT/wda"/WebDriverAgentRunner_*.xctestrun >/dev/null 2>&1; then
    PRODUCTS="$ROOT/wda"; SOURCE="in-repo (wda/)"
else
    PRODUCTS="$DERIVED/Build/Products"; SOURCE="fallback: $SUDOKU_REPO"
fi

# xcodebuild writes results/logs here, so it must be writable and must NOT be the
# committed wda/ tree. log/ is git-ignored.
DERIVED_OUT="${WDA_DERIVED_OUT:-$ROOT/log/wda-derived}"

# ── device UDID ───────────────────────────────────────────────────
UDID="${1:-}"
if [ -z "$UDID" ] && command -v idevice_id >/dev/null 2>&1; then
    UDID="$(idevice_id -l | head -n1)"
fi
[ -z "$UDID" ] && { echo "ERROR: no device. Plug in an iPhone: idevice_id -l" >&2; exit 1; }
echo ">>> [wda] device: $UDID   port: $PORT"

# ── locate the signed WDA test bundle ─────────────────────────────
XCTESTRUN="$(find "$PRODUCTS" -maxdepth 1 -name "WebDriverAgentRunner_*.xctestrun" 2>/dev/null | head -n1)"
if [ -z "$XCTESTRUN" ]; then
    echo "ERROR: no signed WDA build found under $PRODUCTS" >&2
    echo "       The signed build ships with this repo at wda/ — if that folder is" >&2
    echo "       missing or empty, your checkout is incomplete: re-clone or run" >&2
    echo "         git checkout -- wda" >&2
    echo "       To point at a different build instead:" >&2
    echo "         WDA_PRODUCTS=/path/to/Build/Products ./scripts/wda.sh" >&2
    echo "       See wda/README.md and SETUP.md." >&2
    exit 2
fi
echo ">>> [wda] signed build [$SOURCE]: $XCTESTRUN"

# ── cleanup on exit ───────────────────────────────────────────────
WDA_PID=""; IPROXY_PID=""
cleanup() {
    echo ""; echo ">>> [wda] stopping..."
    [ -n "$IPROXY_PID" ] && kill "$IPROXY_PID" 2>/dev/null
    [ -n "$WDA_PID" ] && kill "$WDA_PID" 2>/dev/null
    wait 2>/dev/null; echo ">>> [wda] stopped."
}
trap cleanup INT TERM EXIT

# ── launch WDA + forward the port ─────────────────────────────────
SERVE_LOG="$ROOT/log/wda-serve.log"; mkdir -p "$(dirname "$SERVE_LOG")" "$DERIVED_OUT"
echo ">>> [wda] launching (log: $SERVE_LOG)..."
xcodebuild -xctestrun "$XCTESTRUN" -destination "id=$UDID" \
    -derivedDataPath "$DERIVED_OUT" -disable-concurrent-destination-testing \
    test-without-building > "$SERVE_LOG" 2>&1 &
WDA_PID=$!

echo ">>> [wda] forwarding $PORT -> device:8100..."
"$IPROXY_BIN" "$PORT:8100" -u "$UDID" >/dev/null 2>&1 &
IPROXY_PID=$!

# ── wait for WDA ──────────────────────────────────────────────────
URL="http://127.0.0.1:$PORT"
for i in $(seq 1 60); do
    if ! kill -0 "$WDA_PID" 2>/dev/null; then
        echo "ERROR: xcodebuild exited before WDA came up. Tail of $SERVE_LOG:" >&2
        tail -n 25 "$SERVE_LOG" >&2
        grep -qi "unlock" "$SERVE_LOG" && echo ">>> HINT: UNLOCK the iPhone and re-run." >&2
        exit 5
    fi
    if curl -fsS "$URL/status" >/dev/null 2>&1; then
        echo ""
        echo "==================================================================="
        echo "  WDA is UP.  Device URI for Airtest:"
        echo "      iOS:///$URL"
        echo "  Leave this open; Ctrl-C to stop."
        echo "==================================================================="
        break
    fi
    sleep 2
    [ "$i" = "60" ] && { echo "ERROR: WDA didn't answer $URL/status in 120s." >&2; tail -n 25 "$SERVE_LOG" >&2; exit 6; }
done

wait "$WDA_PID"
