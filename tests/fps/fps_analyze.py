#!/usr/bin/env python3
"""Summarize + compare FPS capture JSONL files from fps_capture.py.

Reports stats over ACTIVE samples (fps>0, i.e. seconds the screen was actually
animating) plus raw counts. Pass any number of .jsonl files (or a dir).

Caveat: for a *continuous* move (drag) the active mean is meaningful. For a
*discrete* animation (deal, suit fly-off) the ~1Hz sampler averages the busy
sub-second with idle time, so the mean reads low even when the animation is
smooth — read `max` (peak), and confirm sub-second behaviour with vid_analyze.py.

Usage:
  fps_analyze.py log/fps/*.jsonl
  fps_analyze.py log/fps --target 60
"""
import argparse
import glob
import json
import os
import sys


def pct(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def load(path):
    meta, samples = {}, []
    with open(path) as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if i == 0 and "label" in d:
                meta = d
            elif "fps" in d:
                samples.append(d["fps"])
    if "label" not in meta:
        base = os.path.basename(path).rsplit(".", 1)[0]
        parts = base.split("__")
        meta = {"label": parts[0], "move": parts[1] if len(parts) > 1 else "?"}
    return meta, samples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--target", type=float, default=60.0)
    args = ap.parse_args()

    files = []
    for p in args.paths:
        if os.path.isdir(p):
            files += sorted(glob.glob(os.path.join(p, "*.jsonl")))
        else:
            files += sorted(glob.glob(p))
    if not files:
        sys.exit("no jsonl files found")

    tgt = args.target
    hdr = (f"{'label':<16} {'move':<11} {'n':>3} {'act':>3} {'mean':>5} "
           f"{'med':>4} {'min':>4} {'p05':>4} {'max':>4} {'<'+str(int(tgt)):>5} {'dips':>4}")
    print(hdr)
    print("-" * len(hdr))
    for path in files:
        meta, samples = load(path)
        active = sorted(s for s in samples if s > 0)
        if active:
            mean = sum(active) / len(active)
            med = pct(active, 50)
            p05 = pct(active, 5)
            below = 100.0 * sum(1 for s in active if s < tgt) / len(active)
            dips = sum(1 for s in active if s < 0.9 * tgt)
            print(f"{meta.get('label','?'):<16} {meta.get('move','?'):<11} "
                  f"{len(samples):>3} {len(active):>3} {mean:>5.1f} {med:>4.0f} "
                  f"{active[0]:>4.0f} {p05:>4.0f} {active[-1]:>4.0f} "
                  f"{below:>4.0f}% {dips:>4}")
        else:
            print(f"{meta.get('label','?'):<16} {meta.get('move','?'):<11} "
                  f"{len(samples):>3}   0  (no active samples)")
    print("\nactive = seconds with fps>0 (screen animating). mean/min over active only.")
    print(f"<{int(tgt)} = %% of active samples under target; dips = active samples < {0.9*tgt:.0f}.")


if __name__ == "__main__":
    main()
