# iPad device set

Per-device assets + baselines for the **iPad**, selected with `DEVICE=ipad`
(`config.py` points `ASSETS` → `ipad/assets` and `BASELINES` → `ipad/baselines`).
Same idea as `iphone7/` — a dedicated set so this device's Obj-C baselines are
stored separately and never mixed with the iPhone 11 root or the iPhone 7 set.

```bash
DEVICE=ipad ./.venv/bin/python tests/<something>.py
```

## Device

- **Hamza's iPad**, **iPad (9th generation)**, iOS **26.3.1**
- UDID `00008030-00162C1A0E50202E` (USB)
- Resolution: **1620×2160** (portrait). Spider runs portrait on this iPad.

## Capture method — WDA (tidevice does NOT work on iOS 26)

`tidevice` / `idevicescreenshot` **cannot** screenshot this iPad: both fail with
*"DeveloperImage not found"* — the iOS 26 personalized Developer Disk Image won't
mount for them. (This is the opposite of the iPhone 7, where tidevice works
*because* it's iOS 15.) So the iPad uses **WDA + Airtest**, like the iPhone 11.

The iPad was **not** in the existing signed WDA's provisioning profile (that
build targets the iPhone 11 + others), so a **separate WDA build** was made,
registering the iPad, into its own derived dir — leaving the iPhone 11 build
untouched. iPad is iOS 26.3.1, fully compatible with the Xcode 26.5 WDA (no
iOS-15 incompatibility like the iPhone 7).

```bash
# 1. one-time: build+sign WDA for the iPad (registers the device)
cd ~/sudoku-automation
xcodebuild -project "$HOME/.appium/node_modules/appium-xcuitest-driver/node_modules/appium-webdriveragent/WebDriverAgent.xcodeproj" \
  -scheme WebDriverAgentRunner -destination "id=00008030-00162C1A0E50202E" \
  -derivedDataPath target/wda/derived-ipad DEVELOPMENT_TEAM=4528523FZZ \
  "CODE_SIGN_IDENTITY=Apple Development" CODE_SIGNING_REQUIRED=YES CODE_SIGNING_ALLOWED=YES \
  -allowProvisioningUpdates -allowProvisioningDeviceRegistration build-for-testing

# 2. each session: launch WDA against the iPad (iPad UNLOCKED), leave running
cd ~/spider-solitaire-airtest
WDA_DERIVED=~/sudoku-automation/target/wda/derived-ipad ./scripts/wda.sh 00008030-00162C1A0E50202E

# 3. capture over WDA/Airtest (iOS:///http://127.0.0.1:8100)
```

`com.fingerarts.Spider` (Obj-C **7.42.5**) is installed on the iPad.

## Captures

- `ipad/baselines/` — 15 Obj-C **7.42.5** screens (the reference).
- `ipad/unity/` — 15 Unity **8.0.0** screens, same names, for comparison.

Both sets captured at 1620×2160 via WDA/Airtest. A masked pixel comparison still
needs an iPad (1620×2160) variant of `tests/compare_unity_ip7.py` — its mask
regions are 750×1334 (iPhone 7).

## Assets

`ipad/assets/` holds **62 placeholder templates copied from the iPhone 11 root
`assets/`** (mirroring how `iphone7/portrait/assets` was seeded). They are the WRONG
resolution for iPad and are **unverified** — re-crop from real iPad `log/*.png`
captures before using any of them for image matching. Not needed for the
pixel-diff baseline comparison, which is coordinate/manual-nav based.

## Baselines

`ipad/baselines/` is empty — capture the **Obj-C** Spider screens here once a
build is installed and a working iOS-26 screenshot method is chosen. Never
promote another device's captures into this folder. `visual.py`'s ignore-regions
are 828×1792 (iPhone 11) specific; the iPad will need its own region values
before any masked pixel comparison is meaningful.
