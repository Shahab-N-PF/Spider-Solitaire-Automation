#!/usr/bin/env python3
"""Derive one device's Unity templates from another's, by multi-scale matching.

Cropping anchors by hand for every device is slow and error-prone. But Spider's
Unity UI is the same design at a different scale across the 19.5:9 devices, so a
template cropped on the iPhone 14 (1290x2796) can be *found* on an iPhone 11
capture (828x1792) by trying a range of scales and keeping the best match.

For each source template we rescale it over a range, run normalised-correlation
matching against the target device's capture of the SAME screen, take the best
(score, scale, location), and cut the matched region out of the target capture.
The result is a genuine crop of the target device's own pixels — not a resized
image — so it matches at full fidelity at run time.

Two useful self-checks fall out of this: the best scale should cluster tightly
around the resolution ratio (~0.64 for ip14 -> ip11), and a low best-score means
that element genuinely differs between devices (a reflow, not just a scale) and
needs a hand crop.

Run:  ./.venv/bin/python scripts/derive_unity_assets.py \
          [--src iphone14/assets_unity] [--shots log/unity_screens] [--out assets_unity]
"""
import argparse
import os
import sys

import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from scripts.crop_unity_assets import CROPS  # noqa: E402

SCALES = [0.50 + i * 0.005 for i in range(int((0.85 - 0.50) / 0.005) + 1)]


def best_match(shot, tpl):
    """Best (score, scale, x, y, w, h) of `tpl` in `shot` over SCALES."""
    best = (-1.0, None, 0, 0, 0, 0)
    sh, sw = shot.shape[:2]
    for s in SCALES:
        w, h = int(round(tpl.shape[1] * s)), int(round(tpl.shape[0] * s))
        if w < 8 or h < 8 or w > sw or h > sh:
            continue
        r = cv2.resize(tpl, (w, h), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(shot, r, cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(res)
        if score > best[0]:
            best = (float(score), s, loc[0], loc[1], w, h)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join(ROOT, "iphone14", "assets_unity"))
    ap.add_argument("--shots", default=os.path.join(ROOT, "log", "unity_screens"))
    ap.add_argument("--out", default=os.path.join(ROOT, "assets_unity"))
    # Genuine cross-resolution matches score ~0.87-1.00; a template whose source
    # screen is wrong tops out around 0.78 while still "finding" something. The
    # bar sits in that gap so a bad capture is rejected rather than silently
    # producing a template cut from the wrong pixels.
    ap.add_argument("--min-score", type=float, default=0.80)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    shots = {}
    for fn in os.listdir(args.shots):
        if fn.endswith(".png"):
            im = cv2.imread(os.path.join(args.shots, fn))
            if im is not None:
                shots[fn] = im

    ok, weak, missing = 0, [], []
    print(f"{'template':22} {'score':>6} {'scale':>6}  box")
    print("-" * 66)
    for name in sorted(CROPS):
        src_shot = CROPS[name][0]
        tpl_path = os.path.join(args.src, name + ".png")
        if not os.path.exists(tpl_path):
            continue
        if src_shot not in shots:
            missing.append(f"{name} (needs {src_shot})")
            continue
        tpl = cv2.imread(tpl_path)
        score, scale, x, y, w, h = best_match(shots[src_shot], tpl)
        if score < args.min_score:
            weak.append(f"{name}={score:.2f}")
            print(f"{name:22} {score:6.3f} {scale or 0:6.3f}  WEAK - skipped")
            continue
        cv2.imwrite(os.path.join(args.out, name + ".png"),
                    shots[src_shot][y:y + h, x:x + w])
        ok += 1
        print(f"{name:22} {score:6.3f} {scale:6.3f}  ({x},{y},{x+w},{y+h})")

    print("-" * 66)
    print(f"  {ok} templates -> {args.out}")
    if weak:
        print(f"  WEAK ({len(weak)}): {', '.join(weak)}")
        print("    -> element differs beyond a uniform scale; crop it by hand.")
    if missing:
        print(f"  no target capture for {len(missing)}: {', '.join(missing)}")


if __name__ == "__main__":
    main()
