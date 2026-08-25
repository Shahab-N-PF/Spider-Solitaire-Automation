# Spider Solitaire — Airtest + WDA automation

> Game: **Spider Solitaire** (`com.fingerarts.Spider`, listed as "Spider")

A standalone iOS UI-automation project driven by **Airtest** (image recognition)
and **Poco** (accessibility hierarchy) over **WebDriverAgent**. It **reuses the
already-signed WDA** from the neighbouring `sudoku-automation` repo (team
`4528523FZZ`) — no new signing or WDA build required.

> **Cloned from `../solitaire-airtest`.** The `assets/` menu templates are
> inherited from that project (FingerArts games share menu chrome) — re-verify
> them against the live device (`tests/launch_and_shoot.py`) before trusting the
> suite.

```
game-airtest/
├── config.py            # game name, BUNDLE_ID, WDA URL  ← fill this in
├── requirements.txt     # airtest, pocoui, tidevice
├── scripts/
│   ├── setup.sh         # create .venv + install deps
│   └── wda.sh           # start/forward WDA (reuses the signed build)
├── tests/
│   ├── connect_check.py # connect + screenshot (smoke test)
│   └── launch_and_shoot.py  # open the game + screenshot (start of real flows)
└── assets/              # template images for image matching
```

## Prerequisites (already true on this Mac)

- The `sudoku-automation` repo is at `~/sudoku-automation` with a built, signed
  WDA (any prior run produced `target/wda/derived/...`). Override the location
  with `SUDOKU_REPO=/path ./scripts/wda.sh` if different.
- Xcode 26.5 + iOS 26.5 platform, valid `4528523FZZ` signing identity, device
  registered + developer-trusted on the iPhone (all done during Sudoku setup).
- `iproxy` + `idevice_id` (libimobiledevice) on PATH.

## 1. One-time setup

```bash
cd ~/game-airtest
./scripts/setup.sh          # creates .venv and installs airtest/poco/tidevice
```

## 2. Point it at your game

Find the bundle ID (any Python venv with tidevice works):

```bash
~/sudoku-automation/airtest/.venv/bin/python -m tidevice applist
```

Then edit **`config.py`** — set `GAME_NAME` and `BUNDLE_ID`
(or export them: `export BUNDLE_ID=com.yourco.yourgame`).

## 3. Start WDA (keep it running)

Unlock the iPhone, then:

```bash
./scripts/wda.sh
```

Wait for `WDA is UP`. Leave this terminal open; Ctrl-C to stop.

## 4. Run

```bash
./.venv/bin/python tests/connect_check.py     # smoke test: connect + screenshot
./.venv/bin/python tests/launch_and_shoot.py  # open the game + screenshot
```

### Test suite / regression run

The functional tests live in `tests/` (`verify*.py`) and target the **Unity**
build via `unity_ui.py` — the Obj-C build is no longer functionally tested.
Templates are in `assets_unity/`; the Obj-C `assets/` do not match Unity.

**Full regression, from a clean terminal** (in `~/spider-solitaire-airtest`):

```bash
./scripts/setup.sh                          # 1. one-time: build .venv (skip if it exists)
./scripts/wda.sh <UDID>                     # 2. start WDA — own tab; iPhone UNLOCKED
export DEVICE_UDID=<UDID>                   # 3. pin Airtest to the same phone
#                                             then enable Airplane Mode on the device
./.venv/bin/python tests/run_all.py         # 4. run every test, print PASS/FAIL
```

`run_all.py` preflights the rig (templates present, WDA reachable, `DEVICE_UDID`
set), runs the tests, and prints a PASS/FAIL summary. Two failures are **expected**
— they are known Unity port gaps and are labelled as such, so they don't mask a
broken rig. Full detail: `tests/README.md`.

> **WDA must be running** (`./scripts/wda.sh`, own tab) and the **iPhone
> unlocked** for any of this to work — WDA listens on `http://127.0.0.1:8100`.
> Always use the project venv (`./.venv/bin/python`), never system `python`.

Run a subset, or a single test standalone:

```bash
./.venv/bin/python tests/run_all.py verifyPlay verifyGamePlay
./.venv/bin/python tests/verifyMainMenu.py     # menu shows all its controls
./.venv/bin/python tests/verifyGamePlay.py     # the table plays (deal/undo, drawer)
./.venv/bin/python tests/verifyOptions.py      # Options: sections, scroll, live toggle
```

Opt-in, deliberately out of the suite:

```bash
./.venv/bin/python tests/resetStats.py         # DESTRUCTIVE: wipes local statistics
./.venv/bin/python tests/verifyHelpShift.py    # needs the device ONLINE
./.venv/bin/python tests/preflight_offline.py  # assert Airplane Mode before a run
```

Refresh the Unity templates after a build that restyles a control (this is **not**
re-baselining — `baselines/` stay Obj-C):

```bash
./.venv/bin/python scripts/capture_unity_screens.py
./.venv/bin/python scripts/crop_unity_assets.py --device iphone11
./.venv/bin/python scripts/verify_unity_assets.py   # offline gate before trusting
```

If WDA fails to start it's usually a locked/disconnected device — or an offline
one: WDA re-verifies its developer certificate over the network at launch, so
start it *before* enabling Airplane Mode.

Then crop buttons/cells from `log/launch.png` into `assets/` and build real
flows:

```python
import config, helpers
from airtest.core.api import connect_device, touch, exists, sleep
from airtest.core.cv import Template

helpers.launch_app()                          # foreground the game via WDA session
sleep(3)
connect_device(config.DEVICE_URI)             # Airtest drives what's on screen
touch(Template("assets/play_button.png"))     # image-based tap
assert exists(Template("assets/game_board.png"))
```

> **Launching:** use `helpers.launch_app()` (WDA session), **not** Airtest's
> `start_app()` — the latter doesn't reliably foreground iOS apps on this device.

### How the Unity suite works

Unity has **no accessibility tree**, so the suite drives it with templates
cropped from Unity's own rendering (`assets_unity/`, via `unity_ui.py`) — which
makes "the control is on screen" a genuine assertion, and absorbs the layout
shifts between builds that leave hardcoded coordinates stale. (The pixel suite,
`compare_unity*.py`, deliberately does the opposite and uses fixed coordinates: a
comparison must not locate its targets using the pixels it is measuring.)
Templates are gated offline by `scripts/verify_unity_assets.py` before use.

Because there's no state to read, "did the control do anything?" is answered by
comparing captures before/after — including a real game-logic check: deal a row
from the stock, the board must change; undo, the board must come back. Full
doc: `tests/README.md`.

## FPS / animation performance testing

A separate axis from the pixel checks above: do in-game *moves* animate at a
smooth 60 fps, and did the Unity port add hitches? Tools live in `tests/fps/`
(see `tests/fps/README.md`). Run on the **iPhone 7** (no WDA there — moves are
performed by hand while FPS streams):

```bash
# continuous move (drag) — tidevice ~1Hz sampler:
./.venv/bin/python tests/fps/fps_capture.py --label unity-8.0.0 --move drag --seconds 18 --no-launch
./.venv/bin/python tests/fps/fps_analyze.py log/fps/*.jsonl

# sub-second animation (deal, suit fly-off) — per-frame from a 60fps QuickTime clip:
./.venv/bin/python tests/fps/vid_analyze.py "~/Documents/FPS Testing Videos/unity_suit.mov" --motion 0.006
```

Latest result (Obj-C 7.42.5 vs Unity 8.0.0, iPhone 7): **no FPS regression** —
drag, rapid 2-card, deal and suit fly-off all hold 60 on both builds. Details in
`reports/CHANGELOG.md`.

## Authoring tips

- **Poco** for menus/buttons with stable names; **image templates** for the
  playfield (cards/piles) where there are no accessibility IDs — the same
  mix that makes the Sudoku grid reliable.
- Prefer `exists(Template(...))` for assertions, `touch(Template(...))` for taps.
- Screenshots land in `log/` (git-ignored); commit your `assets/` templates.

## Connection reference

| | Value |
|---|---|
| WDA URL | `http://127.0.0.1:8100` |
| Airtest device URI | `iOS:///http://127.0.0.1:8100` |
| Wi-Fi (optional) | `iOS:///http://<device-ip>:8100` (from WDA's `ServerURLHere` log) |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `no signed WDA build found` | Build once in the Sudoku repo: `(cd ~/sudoku-automation && ./scripts/airtest-wda.sh)` then Ctrl-C; or set `SUDOKU_REPO` |
| `may need to be unlocked` / timed out | Unlock the iPhone and keep it awake |
| `xcodebuild exited before WDA came up` | Stale runner — `~/sudoku-automation/scripts/reset-wda.sh`, then re-run |
| Port 8100 busy | `WDA_PORT=8200 ./scripts/wda.sh` and set `WDA_URL` to match |
