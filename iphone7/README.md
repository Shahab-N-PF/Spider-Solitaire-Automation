# iphone7/ — iPhone 7 device set

Everything device-specific for the **iPhone 7**, split by orientation into two
parallel sets (Spider's landscape layout is a genuine reflow, not a rotation):

```
iphone7/
├── portrait/          # 750×1334  (the original set)
│   ├── assets/        #   image-match templates       (config.ASSETS)
│   └── baselines/     #   Obj-C visual baselines       (config.BASELINES)
└── landscape/         # 1334×750
    ├── assets/
    └── baselines/
```

Selected at runtime with `DEVICE=iphone7/portrait` (or `iphone7/landscape`) — the
`DEVICE` env is path-joined under the repo root, so any `<device>/<orientation>`
works (see `config.py`). With `DEVICE` unset the suite uses the repo-root `assets/`
+ `baselines/` (the iPhone 11 default — its `baselines/` are the Obj-C source of
truth for the Unity port and are never touched by an iPhone 7 run).

```bash
DEVICE=iphone7/portrait ./.venv/bin/python tests/launch_and_shoot.py
SKIP_VISUAL=1 DEVICE=iphone7/portrait ./.venv/bin/python tests/run_all.py   # functional only
```

**Unity-port comparison** (the active work) reads the baselines directly:
`tests/compare_unity_ip7.py` (portrait) and `tests/compare_unity_ip7_landscape.py`
(landscape) — see [`landscape/README.md`](landscape/README.md).

## Device on hand

**"iPhone 7 Kaala"**, UDID `385e82401ffb88ee946698f951ae9b991beba9da`, **iOS
15.7.5**.

| | iPhone 11 (root, default) | iPhone 14 Pro Max (`iphone14/`) | **iPhone 7 (`iphone7/`)** |
|---|---|---|---|
| Pixels | 828×1792 | 1290×2796 | **750×1334** |
| Points (@scale) | 414×896 @2x | 430×932 @3x | **375×667 @2x** |
| Aspect | 19.5:9 | 19.5:9 | **16:9** |
| Notch / home button | notch | notch | **home button, no notch** |

## portrait/assets/ — SEED, unverified

Every `.png` in `portrait/assets/` is a **copy of the iPhone 11 root `assets/` crop**
(the same 33 files the `iphone14/assets/` set carries) as a starting point. **None has
been verified against a real iPhone 7 screenshot yet.**

Because the iPhone 7 is **16:9** (vs the iPhone 11 / 14 Pro Max at 19.5:9) the
layout *reflows* — a uniform scale does not reproduce it (that shortcut only
worked for the iPhone 14). Element art is unchanged and Airtest's SIFT matcher is
scale-invariant, so many inherited crops still match, but each anchor must be
**re-verified and re-cropped** from a real 750×1334 screenshot where it doesn't.
Keep the same file names so `flows.py` picks them up; per-template meaning is in
[`../assets/README.md`](../assets/README.md).

## portrait/baselines/ — captured

17 screens captured (Obj-C 7.42.5, 750×1334) — see
[`portrait/baselines/README.md`](portrait/baselines/README.md). Captured
**manually-assisted via tidevice** (`launch` + `screenshot`), because WDA can't run
here (see below); the normal `wda.sh` / `run_all.py` / `update_baselines.py` flow
does **not** work on the iPhone 7.

The Unity-port **pixel comparison** uses `tests/compare_unity_ip7.py`, which has its
own 750×1334 mask regions + learned volatile masks. (The legacy `visual.py`/`run_all`
flow still uses iPhone-11 828×1792 ignore-regions, so use the compare tool instead.)

## landscape/

Landscape set (1334×750) lives at [`landscape/`](landscape/) — its own baselines,
masks, compare tool, and report. Same tidevice capture method, phone rotated.

## WDA does NOT run on this device (confirmed 2026-07-26)

WDA cannot run on the iPhone 7 under the only installed Xcode (26.5): `scripts/wda.sh`
(xcodebuild) can't resolve the iOS-15 device, and a purpose-built + signed WDA
dyld-crashes then won't hold an XCTest session on iOS 15.7.5 (Xcode-26 Swift Testing
+ XCTest-vs-iOS-15 incompatibility). Use **tidevice** (`launch` + `screenshot`) for
no-WDA capture; full hands-free automation would need WDA built with an older Xcode.
`scripts/wda.sh` auto-detects the connected device, so plug in **only** the
iPhone 7 (unplug the iPhone 11) so it resolves to the right UDID.
