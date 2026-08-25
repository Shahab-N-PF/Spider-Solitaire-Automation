#!/usr/bin/env python3
"""Launch time over WDA — SECONDARY to the video method. [UNITY, iPhone 11 only]

`vid_launch.py` is the primary tool and the source of every quoted number. This
one exists for one job the video method is bad at: **unattended volume**. It taps
the icon and samples screenshots by itself, so it can repeat a subsequent/warm
launch 20 times while nobody watches, which is useful for spotting variance.

READ THIS BEFORE QUOTING ANYTHING FROM IT:

  * **Resolution is one screenshot round trip (~100-250 ms), not 17 ms.** Every
    result prints its own frame gap, and a run whose sampling stalled inside the
    measured window is flagged GAPPY. A build-vs-build difference smaller than
    that gap is not a finding here — take it to video.
  * **It cannot separate "looks ready" from "is ready" on a warm launch.** iOS's
    frozen snapshot can be shorter than one sample, so the liveness test that
    makes `vid_launch.py`'s warm number honest does not survive here. Warm results
    are reported as LOOKS-ready only, and labelled that way.
  * **iPhone 11 only.** The iPhone 7 has no working WDA at all.
  * **Not for fresh starts.** Those are one sample per install, where precision
    has to carry the result — video, always.

t0 is still taken FROM THE FRAMES (the first captured frame that is no longer the
still home screen), not from the tap request, so WDA's own latency is outside the
measurement even though WDA performs the tap.

Finding the icon: pass `--icon X,Y` in WDA points, measured once by hand — the
simple, reliable option. Without it this asks the springboard for an icon named
after the app, which is untested on this rig and will say so rather than guess.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set, device
OFFLINE (an interstitial covering the menu reads as a slow launch).
Run:  ./.venv/bin/python tests/launch/live_launch.py --icon 640,1200 --repeats 20
"""
import argparse
import base64
import http.client
import json
import os
import statistics
import sys
import threading
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import config  # noqa: E402
import helpers  # noqa: E402
import unity_ui as ui  # noqa: E402

REPEATS = 10
CAPTURE_WINDOW = 25.0       # seconds of frames per launch
SETTLE_BEFORE_TAP = 3.0     # let the home screen go still, so t0 is unambiguous
CHANGE_THRESH = 3.0         # mean abs grey diff that counts as "the screen changed"
SMALL_W = 240               # analysis downscale width


class Sampler(threading.Thread):
    """Grab screenshots as fast as WDA will serve them, timestamping each.

    Decodes nothing: any per-frame work here comes straight off the sampling rate,
    and the sampling rate is the precision of the whole measurement. One
    keep-alive connection for the same reason.
    """

    def __init__(self, host, port):
        super().__init__(daemon=True)
        self.host, self.port = host, port
        self.frames = []
        self._stop = threading.Event()

    def run(self):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=15)
        while not self._stop.is_set():
            t = time.time()
            try:
                conn.request("GET", "/screenshot")
                body = conn.getresponse().read()
            except Exception:  # noqa: BLE001 — reconnect, keep sampling
                try:
                    conn.close()
                except Exception:  # noqa: BLE001
                    pass
                conn = http.client.HTTPConnection(self.host, self.port, timeout=15)
                continue
            try:
                self.frames.append((t, base64.b64decode(json.loads(body)["value"])))
            except Exception:  # noqa: BLE001
                continue

    def stop(self):
        self._stop.set()
        self.join(timeout=20)


def _host_port():
    u = urllib.parse.urlparse(config.WDA_URL)
    return u.hostname, u.port or 80


def decode(png):
    import cv2
    import numpy as np
    return cv2.imdecode(np.frombuffer(png, "uint8"), cv2.IMREAD_COLOR)


def small_grey(img):
    import cv2
    h = max(1, int(img.shape[0] * SMALL_W / img.shape[1]))
    return cv2.cvtColor(cv2.resize(img, (SMALL_W, h), interpolation=cv2.INTER_AREA),
                        cv2.COLOR_BGR2GRAY)


def mean_diff(a, b):
    import numpy as np
    if a is None or b is None or a.shape != b.shape:
        return 255.0
    return float(np.abs(a.astype("int16") - b.astype("int16")).mean())


def menu_drawn(img):
    """The suite's own idea of "the menu is up", applied to a captured frame.

    Deliberately reuses unity_ui.find() rather than a private matcher, so this
    and the functional tests cannot disagree about what counts as the menu.
    """
    return ui.find("menu_play", screen=img) is not None and \
        ui.find("menu_help", screen=img) is not None


def go_home():
    try:
        urllib.request.urlopen(config.WDA_URL + "/wda/homescreen", timeout=15)
        return True
    except Exception:  # noqa: BLE001
        return False


def icon_pos(explicit=None):
    """Where to tap for the app icon, in WDA points.

    --icon X,Y is the reliable path: measure it once by hand and pass it. The
    springboard query below is a convenience and is UNVERIFIED on this rig, so it
    reports failure plainly instead of returning a guess that would tap felt.
    """
    if explicit:
        x, y = explicit.split(",")
        return (float(x), float(y))
    try:
        sid = helpers.launch_app(bundle_id="com.apple.springboard", force=False)
        body = json.dumps({
            "using": "predicate string",
            "value": f"type == 'XCUIElementTypeIcon' AND name == '{config.GAME_NAME}'",
        }).encode()
        req = urllib.request.Request(
            config.WDA_URL + f"/session/{sid}/elements", data=body,
            headers={"Content-Type": "application/json"})
        found = json.load(urllib.request.urlopen(req, timeout=15))["value"]
        if not found:
            return None
        eid = list(found[0].values())[0]
        rect = json.load(urllib.request.urlopen(
            config.WDA_URL + f"/session/{sid}/element/{eid}/rect", timeout=15))["value"]
        return (rect["x"] + rect["width"] / 2.0, rect["y"] + rect["height"] / 2.0)
    except Exception:  # noqa: BLE001
        return None


def tap_point(pos):
    """Tap in WDA POINTS (not capture pixels) — the springboard is native UI."""
    sid = helpers.current_session()
    body = json.dumps({"x": pos[0], "y": pos[1]}).encode()
    req = urllib.request.Request(
        config.WDA_URL + f"/session/{sid}/wda/tap/0", data=body,
        headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=15)


def analyse(frames, ref_small, t_tap, tag):
    """Frames -> markers. t0 comes from the FRAMES, not from t_tap."""
    r = {"tag": tag, "frames": len(frames)}
    if len(frames) < 3:
        r["error"] = "too few frames to measure anything"
        return r
    g = [b[0] - a[0] for a, b in zip(frames, frames[1:])]
    r["gap_median"], r["gap_worst"] = statistics.median(g), max(g)

    i0 = None
    for i, (t, png) in enumerate(frames):
        if t < t_tap:
            continue
        if mean_diff(small_grey(decode(png)), ref_small) > CHANGE_THRESH:
            i0 = i
            break
    if i0 is None:
        r["error"] = "the home screen never changed — did the tap land on the icon?"
        return r

    i_menu = None
    for i in range(i0, len(frames)):
        if menu_drawn(decode(frames[i][1])):
            i_menu = i
            break
    if i_menu is None:
        r["error"] = "the menu never appeared inside the capture window"
        r["i0"] = i0
        return r

    r["to_menu"] = frames[i_menu][0] - frames[i0][0]
    r["i0"], r["i_menu"] = i0, i_menu
    window = [b[0] - a[0] for a, b in zip(frames[i0:i_menu], frames[i0 + 1:i_menu + 1])]
    r["gap_in_window"] = max(window) if window else 0.0
    # A stall inside the measured window means the true value could be anywhere in
    # that hole. Flag it rather than quote a tidy number.
    r["gappy"] = r["gap_in_window"] > 3 * r["gap_median"]
    return r


def measure(kind, pos, window, tag):
    host, port = _host_port()
    sid = helpers.launch_app()
    time.sleep(1.0)
    if kind == "cold":
        ui.terminate(sid)
    go_home()
    time.sleep(SETTLE_BEFORE_TAP)

    sampler = Sampler(host, port)
    sampler.start()
    time.sleep(1.2)                      # reference frames of a still home screen
    if not sampler.frames:
        sampler.stop()
        return {"tag": tag, "error": "no frames — is WDA up?"}
    ref = small_grey(decode(sampler.frames[-1][1]))

    t_tap = time.time()
    try:
        tap_point(pos)
    except Exception as e:  # noqa: BLE001
        sampler.stop()
        return {"tag": tag, "error": f"could not tap the icon: {e}"}
    time.sleep(window)
    sampler.stop()

    r = analyse(list(sampler.frames), ref, t_tap, tag)
    r["kind"] = kind
    return r


def summarise(results, kind, label):
    rows = [r for r in results if r.get("kind") == kind and "to_menu" in r]
    bad = [r for r in results if r.get("kind") == kind and "to_menu" not in r]
    print(f"\n  {label}  ({len(rows)} of {len(rows) + len(bad)} measured)")
    for r in bad:
        print(f"    ! {r['tag']}: {r.get('error', 'no result')}")
    if not rows:
        return None
    for r in rows:
        flag = "   << GAPPY, indicative only" if r.get("gappy") else ""
        print(f"    {r['tag']}: {r['to_menu']:.2f}s   "
              f"(frame gap ~{r['gap_median'] * 1000:.0f}ms){flag}")
    vals = [r["to_menu"] for r in rows]
    res = statistics.median([r["gap_median"] for r in rows])
    print(f"    MEDIAN {statistics.median(vals):.2f}s   "
          f"(range {min(vals):.2f}-{max(vals):.2f}s, +/- ~{res * 1000:.0f}ms resolution)")
    return statistics.median(vals)


def run(a):
    helpers.wda_status()
    ui.connect()
    ui.screen_size()

    pos = icon_pos(a.icon)
    if pos is None:
        print("FAIL: could not locate the app icon on the home screen.\n"
              "      The springboard query is unverified on this rig. Measure the\n"
              "      icon centre once by hand and pass it in WDA POINTS, e.g.:\n"
              "        ./.venv/bin/python tests/launch/live_launch.py --icon 320,600")
        return 1
    print(f"tapping the icon at {pos[0]:.0f},{pos[1]:.0f} (WDA points)")

    results = []
    for i in range(1, a.repeats + 1):
        print(f"  cold {i}/{a.repeats} ...", flush=True)
        results.append(measure("cold", pos, a.window, f"cold{i}"))
        ui.clear_overlays()
    if not a.no_warm:
        for i in range(1, a.repeats + 1):
            print(f"  warm {i}/{a.repeats} ...", flush=True)
            results.append(measure("warm", pos, a.window, f"warm{i}"))
            ui.clear_overlays()

    cold = summarise(results, "cold", "SUBSEQUENT (cold) — tap to menu drawn")
    warm = None
    if not a.no_warm:
        warm = summarise(results, "warm",
                         "WARM — tap to menu LOOKS drawn (see the caveat below)")
        print("    NOTE: this warm number cannot tell iOS's frozen snapshot from the "
              "app actually resuming.\n          Use vid_launch.py for a warm number "
              "you can quote.")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join(config.LOG, "launch", "live", stamp)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "results.json"), "w") as f:
        json.dump({"bundle": config.BUNDLE_ID, "when": stamp, "icon": pos,
                   "cold_median": cold, "warm_looks_median": warm,
                   "results": results}, f, indent=2)
    print(f"\n  raw timings -> {out_dir}/results.json")
    return 0 if cold is not None else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--icon", help="icon centre in WDA points, e.g. 640,1200")
    p.add_argument("--repeats", type=int, default=REPEATS)
    p.add_argument("--window", type=float, default=CAPTURE_WINDOW)
    p.add_argument("--no-warm", action="store_true")
    args = p.parse_args()
    try:
        sys.exit(run(args))
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
