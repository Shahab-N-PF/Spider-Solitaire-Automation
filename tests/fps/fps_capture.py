#!/usr/bin/env python3
"""Capture a CoreAnimation FPS timeseries from the iPhone 7 while a move plays.

Streams `tidevice perf -B <bundle> -o fps --json` (~1Hz) for a fixed window,
tags each sample with elapsed seconds, and writes JSONL to
<out-dir>/<label>__<move>.jsonl. FPS reads ~0 when the screen is static (the
counter counts *committed* frames), so keep the gesture going for the whole
window; analysis (fps_analyze.py) filters to active (fps>0) samples.

This is the iPhone-7 path (iOS 15.7.5): tidevice's classic-instruments perf
works there with no WDA/tunnel. ~1Hz is fine for a continuous move (a sustained
drag reads a clean 60) but too coarse for sub-second animations — use
vid_analyze.py on a 60fps QuickTime recording for those. See tests/fps/README.md.

Usage:
  fps_capture.py --label unity-8.0.0 --move drag --seconds 18
  fps_capture.py --label objc-7.42.5 --move deal --seconds 15 --no-launch

Env overrides: UDID, BUNDLE_ID, TIDEVICE_PY.
"""
import argparse
import json
import os
import re
import subprocess
import threading
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UDID = os.environ.get("UDID", "385e82401ffb88ee946698f951ae9b991beba9da")  # iPhone 7 "Kaala"
BUNDLE = os.environ.get("BUNDLE_ID", "com.fingerarts.Spider")
TID = os.environ.get("TIDEVICE_PY", os.path.expanduser("~/sudoku-automation/airtest/.venv/bin/python"))


def slug(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, help="build label, e.g. unity-8.0.0")
    ap.add_argument("--move", required=True, help="move type, e.g. drag/deal/suit/idle-menu")
    ap.add_argument("--seconds", type=float, default=15.0)
    ap.add_argument("--out-dir", default=os.path.join(REPO, "log", "fps"))
    ap.add_argument("--udid", default=UDID)
    ap.add_argument("--bundle", default=BUNDLE)
    ap.add_argument("--no-launch", action="store_true", help="don't foreground the app first")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    out_path = os.path.join(args.out_dir, f"{slug(args.label)}__{slug(args.move)}.jsonl")

    if not args.no_launch:
        print(f"launching {args.bundle} ...", flush=True)
        subprocess.run([TID, "-m", "tidevice", "-u", args.udid, "launch", args.bundle],
                       capture_output=True, text=True)
        time.sleep(3)

    cmd = [TID, "-m", "tidevice", "-u", args.udid, "perf", "-B", args.bundle,
           "-o", "fps", "--json"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1)
    samples = []
    t0 = time.time()

    def drain():
        for raw in iter(proc.stdout.readline, ""):
            line = raw.strip()
            if not line or "NotOpenSSL" in line or "warnings.warn" in line:
                continue
            try:
                d = json.loads(line)
                fps = float(d.get("fps", d.get("value", 0)))
            except (ValueError, AttributeError):
                continue
            t = time.time() - t0
            samples.append({"t": round(t, 3), "fps": fps})
            print(f"  +{t:5.2f}s  fps={fps:5.1f}", flush=True)

    th = threading.Thread(target=drain, daemon=True)
    th.start()

    print(f"\n>>> CAPTURING '{args.move}' on '{args.label}' for {args.seconds:.0f}s "
          f"— perform the move continuously NOW <<<\n", flush=True)
    time.sleep(args.seconds)
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()

    with open(out_path, "w") as f:
        f.write(json.dumps({"label": args.label, "move": args.move,
                            "seconds": args.seconds, "bundle": args.bundle}) + "\n")
        for s in samples:
            f.write(json.dumps(s) + "\n")

    active = [s["fps"] for s in samples if s["fps"] > 0]
    n = len(samples)
    print(f"\n----- wrote {n} samples ({len(active)} active) -> {out_path} -----")
    if active:
        active.sort()
        mean = sum(active) / len(active)
        print(f"      active fps: mean {mean:4.1f}  min {active[0]:.0f}  "
              f"max {active[-1]:.0f}")
    else:
        print("      WARNING: no active (fps>0) samples — was the move animating?")


if __name__ == "__main__":
    main()
