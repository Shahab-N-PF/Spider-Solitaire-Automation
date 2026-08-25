"""Per-game configuration — fill these in for your game.

Everything the scripts need to know about the target game and how to reach the
device lives here. Values can be overridden with environment variables so the
same code runs in CI without editing this file.

Find your bundle ID with:
    ./.venv/bin/python -m tidevice applist
"""
import os

# ── the game under test ───────────────────────────────────────────
# Confirmed via `tidevice applist` on the device: the app is listed as
# "Spider" with bundle id com.fingerarts.Spider.
GAME_NAME = os.environ.get("GAME_NAME", "Spider Solitaire")
BUNDLE_ID = os.environ.get("BUNDLE_ID", "com.fingerarts.Spider")

# ── how to reach WebDriverAgent (reused, already signed, on :8100) ─
WDA_URL = os.environ.get("WDA_URL", "http://127.0.0.1:8100")

# Which device Airtest should drive. Without this, Airtest picks the FIRST
# device it can see — and that list includes WiFi-paired devices that aren't
# even plugged in, so an unrelated phone can win (the iPhone 7 pairs over WiFi
# and sorts ahead of the USB-connected iPhone 11). Pinning the UDID makes the
# target explicit instead of order-dependent. WDA itself is aimed with
# `scripts/wda.sh <UDID>`; this aims Airtest at the same device.
DEVICE_UDID = os.environ.get("DEVICE_UDID", "").strip()
_uri = f"iOS:///{WDA_URL}" + (f"/?udid={DEVICE_UDID}" if DEVICE_UDID else "")
DEVICE_URI = os.environ.get("DEVICE_URI", _uri)

# ── local paths ───────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "log")         # screenshots / run logs (git-ignored)

# Per-device template + baseline sets. Image matching (ASSETS) and visual-
# regression baselines (BASELINES) each live in a per-device directory. The
# default — no DEVICE — is the iPhone 11 at the repo root: assets/ + baselines/
# (the baselines are the Obj-C source of truth for the Unity port; see CLAUDE.md).
#
#   DEVICE=iphone7/portrait   ->  iphone7/portrait/{assets,baselines}  (iPhone 7,
#                        750×1334, 16:9 — a different aspect, so templates are
#                        re-cropped, not scaled; baselines captured separately from
#                        the iPhone 11's). Landscape lives beside it at
#                        iphone7/landscape/ (DEVICE=iphone7/landscape, 1334×750).
#                        DEVICE accepts a path, so any <device>/<orientation> works.
#   DEVICE=iphone14  ->  iphone14/assets + iphone14/baselines  (iPhone 14 Pro Max,
#                        1290×2796, 19.5:9 — same aspect as the iPhone 11, so the
#                        templates are a uniform scale-up; baselines TBD).
#
# ASSETS / BASELINES may also be set directly to override either path on its own.
DEVICE = os.environ.get("DEVICE", "").strip()
_dev_root = os.path.join(ROOT, DEVICE) if DEVICE else ROOT
ASSETS = os.environ.get("ASSETS", os.path.join(_dev_root, "assets"))
BASELINES = os.environ.get("BASELINES", os.path.join(_dev_root, "baselines"))

# Unity-build templates, cropped from the UNITY renderer's own screenshots
# (scripts/crop_unity_assets.py) rather than inherited from Obj-C. The Unity
# functional suite matches against these; the Obj-C templates in ASSETS do NOT
# match the Unity build.
#
# Deliberately NOT per-device, unlike ASSETS/BASELINES. Unity scales its whole UI
# by width, so ONE set serves every phone in the 19.5:9 family — iPhone 11
# (828x1792), iPhone 14 Pro Max (1290x2796), iPhone 16 Pro (1206x2622).
# unity_ui.find() resizes each template by (device width / unity_ui.REF_WIDTH)
# before matching; scripts/verify_unity_scaling.py is the gate that proves it,
# and the measurements behind it are in unity_ui's matching section.
#
# A 16:9 device (the iPhone 7) is a different layout rather than a different
# scale, so it would need its own set — point UNITY_ASSETS at it explicitly.
UNITY_ASSETS = os.environ.get("UNITY_ASSETS", os.path.join(ROOT, "assets_unity"))


def bundle_id_is_set() -> bool:
    return BUNDLE_ID and BUNDLE_ID != "com.example.yourgame"
