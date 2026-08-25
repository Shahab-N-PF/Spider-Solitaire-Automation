#!/usr/bin/env python3
"""Refresh visual-regression baselines (and learn volatile-pixel masks).

Copies each screenshot the suite captures (log/<name>.png) into baselines/, and
— if the suite was run with VIS_SHOTS>1 so extra log/<name>.<i>.volshot.png
frames exist — builds baselines/<name>.volatile.png, the mask of pixels that
flicker between same-build captures (menu glow, sparkles). The exact-pixel
comparison excludes those, so it flags real changes (placement/size/font/asset)
without firing on animation.

Usage:
    ./scripts/wda.sh
    VIS_SHOTS=3 ./.venv/bin/python tests/run_all.py    # capture + volatile frames
    ./.venv/bin/python scripts/update_baselines.py      # promote + learn masks

(Run without VIS_SHOTS to refresh baselines only, keeping existing masks.)
"""
import glob
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import visual  # noqa: E402


def main():
    os.makedirs(visual.BASELINES, exist_ok=True)
    updated, masks, missing = [], [], []
    for name in visual.SPECS:
        src = os.path.join(config.LOG, name)
        if not os.path.exists(src):
            missing.append(name)
            continue
        shutil.copyfile(src, os.path.join(visual.BASELINES, name))
        updated.append(name)

        shots = [src] + sorted(glob.glob(
            os.path.join(config.LOG, name[:-4] + ".*.volshot.png")))
        if len(shots) >= 2:
            vol = visual.build_volatile_mask(shots)
            if vol is not None:
                import cv2
                cv2.imwrite(visual._volatile_path(name), vol)
                pct = 100.0 * (vol > 127).sum() / vol.size
                masks.append((name, len(shots), pct))

    for name in updated:
        print(f"  updated  baselines/{name}")
    for name, n, pct in masks:
        print(f"  learned  baselines/{name.replace('.png', '.volatile.png')} "
              f"from {n} shots ({pct:.1f}% volatile)")
    for name in missing:
        print(f"  MISSING  log/{name} (not captured — run tests/run_all.py first)")
    print(f"\n{len(updated)}/{len(visual.SPECS)} baselines updated"
          + (f", {len(masks)} volatile masks learned" if masks else "")
          + (f", {len(missing)} missing" if missing else ""))


if __name__ == "__main__":
    main()
