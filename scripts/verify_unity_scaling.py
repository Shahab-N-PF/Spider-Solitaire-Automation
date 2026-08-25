#!/usr/bin/env python3
"""Offline gate: does ONE Unity template set work on every device?

The functional suite keeps a single template set (assets_unity/) and rescales it
at match time instead of maintaining a crop set per phone — see the matching
section of unity_ui.py for why that is sound. This script is what keeps that
claim honest.

It drives the REAL unity_ui.find(), with the device's screenshot and screen size
swapped for a saved capture, so it tests the production matcher rather than a
reimplementation of it. For each device profile it reports:

  FOUND    the template was located on the screen it belongs to
  MISSED   it was not — this set does not work on that device
  GHOST    it was also found on a screen it does not belong to (an assertion
           could pass on the wrong screen)

Profiles come from real captures where they exist. `--synthetic` adds phones we
have no captures for by resampling a real capture to that device's width: that
exercises the scaling math end to end, but proves nothing about how the device
actually renders — it is labelled SYNTHETIC for exactly that reason.

Run:  ./.venv/bin/python scripts/verify_unity_scaling.py
      ./.venv/bin/python scripts/verify_unity_scaling.py --synthetic
      ./.venv/bin/python scripts/verify_unity_scaling.py --ghosts   # slower
"""
import os
import sys

import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import crop_unity_assets as C  # noqa: E402
import unity_ui as ui  # noqa: E402
# Reuse the curated "this element legitimately appears on more than one screen"
# knowledge rather than rebuilding it — the back controls are on every screen,
# the menu labels stay visible behind the Choose Look modal, and a scrolled page
# is still the same page. Without it this gate would report ~36 known-good
# matches as ghosts and bury any real one.
from verify_unity_assets import SHARED, UNIVERSAL  # noqa: E402

# Real capture sets: (label, directory, capture width, point scale).
#
# The point scale matters because the app draws in two regimes — Unity content
# scales by width, native iOS dialogs scale by point density (see NATIVE_UI in
# unity_ui). An @2x phone is 2.0, an @3x phone is 3.0. Getting this wrong makes
# the dialog templates miss, which is precisely the bug that broke every
# game-dealing test on the iPhone 16 Pro.
PROFILES = [
    ("iPhone 11      (828x1792, @2x)",
     os.path.join(ROOT, "log", "unity_screens"), 828, 2.0),
    ("iPhone 14 ProMax (1290x2796, @3x)",
     os.path.join(ROOT, "log", "ip14_unity_343"), 1290, 3.0),
    ("iPhone 16 Pro  (1206x2622, @3x)",
     os.path.join(ROOT, "log", "ip16_real"), 1206, 3.0),
]

# Phones we have no captures for. Resampled from a real capture — scaling math
# only, NOT evidence about the device's own rendering.
SYNTHETIC = []


def template_screens():
    """template name -> the capture filename it belongs to."""
    m = {n: src for n, (src, _b) in C.CROPS.items()}
    m.update({n: src for n, (src, _b) in C.CROPS_IP11.items()})
    return m


def load(path, width):
    if not os.path.exists(path):        # screen not captured for this device
        return None
    img = cv2.imread(path)
    if img is None:
        return None
    if img.shape[1] != width:                       # synthetic resample
        h = int(round(img.shape[0] * width / img.shape[1]))
        img = cv2.resize(img, (width, h), interpolation=cv2.INTER_AREA)
    return img


def check(label, srcdir, width, pscale, ghosts=False, synthetic=False):
    tag = "  [SYNTHETIC]" if synthetic else ""
    print(f"\n=== {label}{tag} ===")
    ui._SIZE = None
    ui._POINT_SCALE = pscale
    print(f"    authored at {ui.REF_WIDTH}px/@{ui.REF_POINT_SCALE:g}x  ->  "
          f"unity scale {width / ui.REF_WIDTH:.3f}, "
          f"native scale {pscale / ui.REF_POINT_SCALE:.3f}")

    screens = template_screens()
    # Only templates whose own screen was captured for this device can be judged.
    cache, found, missed = {}, [], []
    for name in sorted(screens):
        if not ui.have(name):
            continue
        src = screens[name]
        path = os.path.join(srcdir, src)
        if src not in cache:
            cache[src] = load(path, width)
        img = cache[src]
        if img is None:
            continue
        ui._SIZE = (img.shape[1], img.shape[0])
        (found if ui.find(name, screen=img) else missed).append(name)

    for n in missed:
        print(f"  MISSED  {n}")
    print(f"  {len(found)} found / {len(missed)} missed "
          f"({len(found) + len(missed)} judged)")

    ghost_hits = []
    if ghosts:
        for name in found:
            if name in UNIVERSAL:           # on every screen by design
                continue
            own = screens[name]
            allowed = SHARED.get(name, ())
            for src, img in cache.items():
                if src == own or img is None:
                    continue
                if any(a in src for a in allowed):
                    continue
                ui._SIZE = (img.shape[1], img.shape[0])
                if ui.find(name, screen=img):
                    ghost_hits.append((name, src))
        for n, s in ghost_hits:
            print(f"  GHOST   {n} also matches {s}")
        print(f"  {len(ghost_hits)} ghost match(es)")
    return len(missed), len(ghost_hits)


def main():
    ghosts = "--ghosts" in sys.argv
    profiles = list(PROFILES)
    if "--synthetic" in sys.argv:
        profiles += [(a, b, c, d, True) for a, b, c, d in SYNTHETIC]

    missed = ghosted = 0
    for p in profiles:
        label, srcdir, width, pscale = p[0], p[1], p[2], p[3]
        if not os.path.isdir(srcdir):
            print(f"\n=== {label} ===\n  no captures at {srcdir} — skipped")
            continue
        m, g = check(label, srcdir, width, pscale, ghosts=ghosts,
                     synthetic=len(p) > 4)
        missed += m
        ghosted += g

    # Reported separately: they are different failures. A MISS means the one-set
    # design does not reach that device. A GHOST means a crop is ambiguous — a
    # real problem, but not evidence about device coverage.
    print("\n" + "-" * 70)
    print("  device coverage: " + ("one template set covers every profile checked"
                                   if not missed else
                                   f"{missed} template(s) MISSED — the set does "
                                   "not cover every device"))
    if ghosts:
        print("  ambiguity:       " + ("no unexpected cross-screen matches"
                                       if not ghosted else
                                       f"{ghosted} ghost match(es) — a crop "
                                       "matches a screen it should not"))
    sys.exit(1 if (missed or ghosted) else 0)


if __name__ == "__main__":
    main()
