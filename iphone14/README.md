# iphone14/ — iPhone 14 Pro Max device set

Everything device-specific for the **iPhone 14 Pro Max** lives here, selected at
runtime with `DEVICE=iphone14` (see `config.py`):

```
iphone14/
├── assets/       # image-match templates for 1290×2796  (config.ASSETS)
└── baselines/    # visual-regression baselines for this device (config.BASELINES)
```

`DEVICE=iphone14` points **both** `config.ASSETS` and `config.BASELINES` here;
with `DEVICE` unset the suite uses the repo-root `assets/` + `baselines/` (the
iPhone 11 default — its `baselines/` are the Obj-C source of truth for the Unity
port and are never touched by an iPhone 14 run).

```bash
DEVICE=iphone14 ./.venv/bin/python tests/launch_and_shoot.py
SKIP_VISUAL=1 DEVICE=iphone14 ./.venv/bin/python tests/run_all.py   # functional only
```

> Was formerly the repo-root `assets_ip14/` set (assets only, no baselines);
> moved under `iphone14/` to match the per-device layout of `iphone7/` and
> `ipad/`. `DEVICE=iphone14` replaces the old `ASSETS=assets_ip14` override.

## Device on hand

**iPhone 14 Pro Max**, UDID `00008120-0001485A1E60201E` (ProductType
`iPhone15,3`), **iOS 26.5.2**. Runs WDA under Xcode 26.5 with **no special build**
— this UDID is already in the default signed WDA profile
(`../sudoku-automation/target/wda/derived`), so plain `scripts/wda.sh` drives it
(unlike the iPad, which needed its own device-registered WDA, and the iPhone 7,
which can't run WDA at all).

Because it's iOS 26, `tidevice screenshot` does **not** work here (DeveloperImage
won't mount) — capture over WDA + Airtest, same as the iPhone 11.

| | iPhone 11 (root, default) | iPhone 7 (`iphone7/`) | **iPhone 14 Pro Max (`iphone14/`)** |
|---|---|---|---|
| Pixels | 828×1792 | 750×1334 | **1290×2796** |
| Points (@scale) | 414×896 @2x | 375×667 @2x | **430×932 @3x** |
| Aspect | 19.5:9 | 16:9 | **19.5:9** |
| Notch / home button | notch | home button, no notch | **Dynamic Island, no home button** |

## assets/ — SEED, unverified

Every `.png` in `assets/` is a **copy of the iPhone 11 root `assets/` crop** (the
same 33 files) as a starting point. Because the iPhone 14 Pro Max shares the
iPhone 11's **19.5:9** aspect, the layout does **not** reflow — it is a uniform
scale-up — so the inherited crops match far more readily than the iPhone 7's do
(Airtest's SIFT matcher is scale-invariant). Still, **none has been re-verified
against a real iPhone 14 Pro Max screenshot yet**; re-crop any anchor that fails
to match from a real 1290×2796 screenshot, keeping the same file names so
`flows.py` picks them up. Per-template meaning is in
[`../assets/README.md`](../assets/README.md).

## baselines/ — captured (2026-07-31)

**17** Obj-C 7.42.5 reference screenshots (1290×2796) — the 16 that match the
iPhone 7 set plus `HelpPageBottom`. Captured over WDA + Airtest (this device runs
WDA, so no tidevice workaround). See [`baselines/README.md`](baselines/README.md)
for the list and per-screen state notes. As with every device, do **not** promote
another device's captures in here, and never re-baseline to the Unity build.

⚠️ Before `DEVICE=iphone14` **pixel comparison** is meaningful, `visual.py`'s
dimensions and ignore-regions (status bar, banner, table, stats) — currently
iPhone-11 828×1792 coordinates — need 1290×2796 values, plus volatile masks for
the animated menu screens (as for the iPhone 7 and iPad).
