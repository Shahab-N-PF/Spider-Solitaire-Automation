#!/usr/bin/env bash
# wda.sh — start WebDriverAgent for this Airtest project.
#
# REUSES the already-signed WDA build from the sudoku-automation repo (team
# 4528523FZZ) — no new signing, no new build. It just launches that signed
# test bundle on the device and forwards port 8100, then waits until WDA is
# healthy. Leave this running while you author/run scripts; Ctrl-C stops it.
#
# Usage:
#   ./scripts/wda.sh                 # auto-detect device, port 8100
#   ./scripts/wda.sh <UDID>          # explicit device
#   SUDOKU_REPO=~/path WDA_PORT=8200 ./scripts/wda.sh
#
# Prereqs: iPhone connected + UNLOCKED. The sudoku-automation repo must have a
# built WDA (any prior `mvn test` or `airtest-wda.sh` run produces it).

set -u

# Where the already-signed WDA build lives (override if your repo is elsewhere).
SUDOKU_REPO="${SUDOKU_REPO:-$HOME/sudoku-automation}"
DERIVED="${WDA_DERIVED:-$SUDOKU_REPO/target/wda/derived}"
PRODUCTS="$DERIVED/Build/Products"
PORT="${WDA_PORT:-8100}"
IPROXY_BIN="${IPROXY_BIN:-$(command -v iproxy || echo /opt/homebrew/bin/iproxy)}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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
    echo "       Build it once in the sudoku-automation repo, e.g.:" >&2
    echo "         (cd \"$SUDOKU_REPO\" && ./scripts/airtest-wda.sh)   # then Ctrl-C" >&2
    echo "       or set SUDOKU_REPO / WDA_DERIVED to the correct path." >&2
    exit 2
fi
echo ">>> [wda] reusing signed build: $XCTESTRUN"

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
SERVE_LOG="$ROOT/log/wda-serve.log"; mkdir -p "$(dirname "$SERVE_LOG")"
echo ">>> [wda] launching (log: $SERVE_LOG)..."
xcodebuild -xctestrun "$XCTESTRUN" -destination "id=$UDID" \
    -derivedDataPath "$DERIVED" -disable-concurrent-destination-testing \
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
