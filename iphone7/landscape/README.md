# iphone7/landscape/ — iPhone 7 **landscape** device set

Landscape-orientation assets + baselines for the **iPhone 7**, kept separate from
the portrait set in `../portrait/` (`iphone7/portrait/{baselines,assets}`). Spider's
landscape UI is a genuinely different layout (the tableau spreads horizontally and
the menu/chrome reposition) — **not** a rotation of portrait — so it needs its own
baselines, mask regions, compare tool, and report.

```
iphone7/landscape/
├── assets/       # image-match templates for 1334×750 landscape (future functional tests)
└── baselines/    # Obj-C 7.42.5 landscape reference screenshots (the source of truth)
```

## Device + orientation

**"iPhone 7 Kaala"**, UDID `385e82401ffb88ee946698f951ae9b991beba9da`, iOS 15.7.5.
Landscape resolution: **1334×750** (portrait 750×1334 with dimensions swapped).

Captured **manually-assisted via tidevice** `screenshot` (WDA can't run on this
device — see `../README.md`), with the phone **rotated to landscape** and the game
showing its landscape layout:

```bash
./.venv/bin/python -m tidevice -u <udid> \
    screenshot iphone7/landscape/baselines/<Name>.png    # image is 1334×750
```

## Comparison

- **Diff tool:** `tests/compare_unity_ip7_landscape.py` — diffs
  `log/ip7_landscape_unity/` (Unity) vs `iphone7/landscape/baselines/` (Obj-C) with
  **1334×750** mask regions (re-measured for landscape, not scaled from portrait).
- **Report:** `reports/iPhone7_Landscape_Unity_Report.html` via
  `scripts/gen_versioned_report.py ip7-landscape`.

## Rules
- Obj-C landscape captures are the **reference**; never re-baseline to Unity.
- Do **not** mix with the portrait set — landscape layout ≠ rotated portrait, and the
  mask regions differ entirely.
- Never promote another device's or orientation's captures in here.
