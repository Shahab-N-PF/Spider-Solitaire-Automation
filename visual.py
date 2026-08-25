"""Exact-pixel baseline (visual-regression) comparison.

Each test writes a full-screen screenshot into log/<name>.png. This module
compares it pixel-for-pixel against baselines/<name>.png and highlights every
region that differs — position, size, font, and asset changes included (SSIM
was too tolerant: it ignores shifts, so a moved/resized icon slipped through).

Three things are excluded from the comparison so it doesn't fire on legitimate
run-to-run churn rather than real UI changes:
  1. COMMON_IGNORE — fixed volatile chrome (status bar, ad banner, this build's
     debug overlay / Test Banner).
  2. per-screen `ignore` in SPECS — e.g. the randomly-dealt card tableau, the
     changing Stats numbers.
  3. a learned VOLATILE mask (baselines/<name>.volatile.png) — pixels that
     flicker between multiple same-build captures (menu glow, sparkles). Built
     by scripts/update_baselines.py from shots taken with VIS_SHOTS>1. Without
     it, animated screens will show their animation as differences.

Everything else must match within _PIXEL_TOL per pixel or it is flagged.
"""
import os

import cv2
import numpy as np

import config

# Per-device (config.BASELINES): the default is <root>/baselines (iPhone 11 — the
# Obj-C source of truth); DEVICE=iphone7/portrait -> iphone7/portrait/baselines.
BASELINES = config.BASELINES

# NOTE: W/H and every ignore-region below are in iPhone 11 828×1792 pixel
# coordinates — correct for the default device only. A different-resolution device
# (e.g. DEVICE=iphone7/portrait, 750×1334) needs its own values here before the pixel
# comparison is meaningful. Capture + baseline promotion (update_baselines.py) is
# resolution-agnostic and works as-is, so iPhone 7 baselines can be recorded now.
W, H = 828, 1792

# Fixed volatile chrome to ignore everywhere (x0, y0, x1, y1):
STATUS_BAR = (0, 0, W, 100)
BOTTOM_BANNER = (0, 1590, W, H)
DEBUG_TL = (0, 150, 340, 500)
DEBUG_TR = (330, 150, W, 500)
TEST_BANNER = (560, 1470, W, 1590)
COMMON_IGNORE = [STATUS_BAR, BOTTOM_BANNER, DEBUG_TL, DEBUG_TR, TEST_BANNER]

# A pixel differs if |gray_cur - gray_base| exceeds this (0-255).
_PIXEL_TOL = 32
# When learning the volatile mask, a pixel is volatile if it varies this much
# across same-build captures (a bit looser, so we don't over-mask).
_VOLATILE_TOL = 22
# Ignore changed blobs smaller than this (anti-aliasing / 1px specks).
_MIN_REGION_AREA = 120

# Per-screen: extra regions to ignore + max fraction of compared pixels allowed
# to differ before it's a regression. Static screens are tight; screens whose
# animation isn't covered by a volatile mask get more slack.
GAME_TABLE_CARDS = (0, 520, W, 800)
STATS_VALUES = (420, 260, W, 900)

SPECS = {
    "MainMenu.png":            {"ignore": [], "max_diff": 0.010},
    "Play.png":                {"ignore": [GAME_TABLE_CARDS], "max_diff": 0.010},
    "DifficultyLevels.png":    {"ignore": [], "max_diff": 0.010},  # picker; menu glow + resume-game ghost vary
    "OptionsPage.png":         {"ignore": [], "max_diff": 0.005},
    "StatsPage.png":           {"ignore": [STATS_VALUES], "max_diff": 0.005},
    "HelpPage.png":            {"ignore": [], "max_diff": 0.005},
    "MoreGames.png":           {"ignore": [], "max_diff": 0.010},
    "SpiderAboutPage.png":     {"ignore": [], "max_diff": 0.005},
    "SpiderFAQ.png":           {"ignore": [], "max_diff": 0.005},  # static Q&A text screen (About -> FAQ)
    "choose_look_surface.png": {"ignore": [], "max_diff": 0.010},
    "choose_look_cards.png":   {"ignore": [], "max_diff": 0.010},
    "more_games_icons.png":    {"ignore": [], "max_diff": 0.010},
}


def _gray(path):
    img = cv2.imread(path)
    return None if img is None else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def _mask(shape, ignore):
    m = np.ones(shape[:2], dtype=bool)
    h, w = shape[:2]
    for (x0, y0, x1, y1) in ignore:
        m[max(0, y0):min(h, y1), max(0, x0):min(w, x1)] = False
    return m


def _volatile_path(name):
    return os.path.join(BASELINES, name.replace(".png", ".volatile.png"))


def _load_volatile(name, shape):
    """Boolean mask of learned volatile (animated) pixels, or all-False if none."""
    p = _volatile_path(name)
    if not os.path.exists(p):
        return np.zeros(shape[:2], dtype=bool)
    v = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
    if v is None:
        return np.zeros(shape[:2], dtype=bool)
    if v.shape != shape[:2]:
        v = cv2.resize(v, (shape[1], shape[0]))
    return v > 127


def build_volatile_mask(shots):
    """From same-build captures of one screen, return the volatile-pixel mask.

    A pixel is volatile if its grayscale value ranges more than _VOLATILE_TOL
    across the shots (animation/sparkle). Dilated so flickering edges are fully
    covered. `shots` is a list of image paths (>= 2).
    """
    grays = [g for g in (_gray(s) for s in shots) if g is not None]
    if len(grays) < 2:
        return None
    stack = np.stack(grays).astype("int16")
    span = (stack.max(axis=0) - stack.min(axis=0)).astype("uint8")
    vol = (span > _VOLATILE_TOL).astype("uint8") * 255
    vol = cv2.dilate(vol, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)))
    return vol


def _changed(cur, base, mask):
    """Binary map of pixels that differ by more than _PIXEL_TOL, within mask."""
    diff = cv2.absdiff(cur, base)
    changed = ((diff > _PIXEL_TOL) & mask).astype("uint8") * 255
    # drop single-pixel specks, then reconnect nearby real differences
    changed = cv2.morphologyEx(changed, cv2.MORPH_OPEN,
                               cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    changed = cv2.morphologyEx(changed, cv2.MORPH_CLOSE,
                               cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)))
    return changed


def _regions(changed, min_area):
    cnts, _ = cv2.findContours(changed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [(cv2.contourArea(c), cv2.boundingRect(c)) for c in cnts]
    return sorted([(a, b) for a, b in boxes if a >= min_area],
                  key=lambda ab: ab[0], reverse=True)


def compare(name, ignore=None, max_diff=0.005):
    """Exact-pixel compare of log/<name> to baselines/<name>.

    Returns a result dict. status: pass | fail | no-baseline | no-capture | size.
    Fails when the fraction of compared pixels that differ exceeds `max_diff`.
    Writes log/diff_<name> highlighting exactly what differs on a fail.
    """
    cur = _gray(os.path.join(config.LOG, name))
    base = _gray(os.path.join(BASELINES, name))
    if cur is None:
        return {"name": name, "status": "no-capture", "diff_pct": None}
    if base is None:
        return {"name": name, "status": "no-baseline", "diff_pct": None}
    if cur.shape != base.shape:
        return {"name": name, "status": "size", "diff_pct": None}

    mask = _mask(cur.shape, COMMON_IGNORE + list(ignore or []))
    mask &= ~_load_volatile(name, cur.shape)     # exclude learned animated pixels
    changed = _changed(cur, base, mask)

    compared = int(mask.sum())
    changed_px = int((changed > 0).sum())
    frac = (changed_px / compared) if compared else 0.0
    has_volatile = os.path.exists(_volatile_path(name))
    status = "fail" if frac > max_diff else "pass"

    diff_path = _write_diff(name, changed, mask, frac) if status == "fail" else None
    return {"name": name, "status": status, "diff_pct": frac * 100,
            "max_diff_pct": max_diff * 100, "has_volatile": has_volatile,
            "diff": diff_path}


def _label(img, line1, line2=""):
    bar = np.full((92, img.shape[1], 3), 30, dtype="uint8")
    cv2.putText(bar, line1, (24, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.95,
                (255, 255, 255), 2, cv2.LINE_AA)
    if line2:
        cv2.putText(bar, line2, (24, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (120, 220, 255), 2, cv2.LINE_AA)
    return np.vstack([bar, img])


def _write_diff(name, changed, mask, frac):
    """log/diff_<name>: baseline | captured with every differing pixel in red.

    The red is the exact per-pixel difference (dilated slightly for visibility),
    so moved/resized/re-fonted elements are outlined precisely. Boxes ring the
    largest changed regions. Masked (not-compared) areas are lightly dimmed.
    """
    cur = cv2.imread(os.path.join(config.LOG, name))
    base = cv2.imread(os.path.join(BASELINES, name))
    if cur is None or base is None:
        return None
    if base.shape != cur.shape:
        base = cv2.resize(base, (cur.shape[1], cur.shape[0]))

    vis = cv2.dilate(changed, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    annotated = cur.copy()
    red = annotated.copy()
    red[vis > 0] = (0, 0, 255)
    annotated = cv2.addWeighted(red, 0.55, annotated, 0.45, 0)
    for _area, (x, y, w, h) in _regions(changed, _MIN_REGION_AREA):
        cv2.rectangle(annotated, (x - 3, y - 3), (x + w + 3, y + h + 3),
                      (0, 255, 255), 3)
    annotated[~mask] = (annotated[~mask] * 0.6).astype("uint8")

    combo = np.hstack([
        _label(base, "BASELINE (previous build)", "exact-pixel compare"),
        _label(annotated, "CAPTURED (this run)",
               f"{frac * 100:.1f}% of pixels differ (red)"),
    ])
    out = os.path.join(config.LOG, "diff_" + name)
    cv2.imwrite(out, combo)
    return out


def compare_all():
    return [compare(name, spec["ignore"], spec["max_diff"])
            for name, spec in SPECS.items()]


def exit_if_nothing_compared(results, unity_dir, device, how):
    """Fail loudly when a comparison compared nothing — and say which reason.

    The per-device comparison tools only READ their captures; they do not shoot
    them. Those captures live under log/, which is git-ignored, so on a fresh
    clone every screen comes back [no-capture] — and the run still printed a tidy
    summary and exited 0, which reads as "compared, all good" to a person and to
    CI alike.

    Nothing being compared has three different causes and they need three
    different answers, so this reports the one that actually applies rather than
    always blaming missing captures. A partial set is left alone — the per-screen
    status lines already show what is missing.

    Returns nothing; exits the process when there is nothing to compare.
    """
    import sys
    if any(r.get("status") == "ok" for r in results):
        return

    counts = {}
    for r in results:
        counts[r.get("status")] = counts.get(r.get("status"), 0) + 1
    reason = max(counts, key=counts.get) if counts else "no-capture"

    print("\n  NOTHING WAS COMPARED — this run proved nothing.\n")

    if reason == "size":
        print(f"  Every capture in\n      {unity_dir}\n"
              "  is a DIFFERENT PIXEL SIZE from its baseline, so no pair could be\n"
              "  compared. This tool is fixed to one resolution: the captures must\n"
              "  come from the same device model and the same orientation as the\n"
              "  baselines. Screenshots are never rescaled to fit — that would\n"
              "  invent differences that are not in the build.")
    elif reason == "no-baseline":
        print("  The BASELINES are missing — the reference side of the comparison.\n"
              "  Baselines are committed to this repo, so an empty set means your\n"
              "  checkout is incomplete, or the tool is pointed at the wrong folder\n"
              "  (see BASE_DIR at the top of this tool).")
    else:
        print(f"  No captures were found in:\n      {unity_dir}\n")
        print("  The Obj-C baselines ship with this repo and are the reference. The")
        print("  build under test does NOT: those captures are shot from the app on")
        print("  the device and land under log/, which is git-ignored.\n")
        print(f"  To make them for the {device}:\n      {how}")

    print("\n  See SETUP.md -> 'Capturing the Unity screenshots', or COMPARISON.md")
    print("  if you only want the comparison tool.")
    sys.exit(2)
