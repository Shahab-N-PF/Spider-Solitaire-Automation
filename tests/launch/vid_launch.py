#!/usr/bin/env python3
"""Launch time from a 60 fps screen recording. [works on ANY build — Unity or Obj-C]

The third axis, beside pixel fidelity (`compare_unity*.py`) and function
(`verify*.py`): how long the user waits after tapping the icon. A port can be
pixel-perfect and still feel worse if the engine swap added seconds to startup,
and nothing else here would notice.

WHY VIDEO AND NOT THE WDA HARNESS
  * t0 is the ICON TAP. Nothing a harness can report gives you that — only frames
    can, whatever triggered the launch.
  * 16.7 ms resolution against ~150 ms for a screenshot round trip. Fresh start
    costs a reinstall per sample, so precision has to carry a low-N result.
  * The iPhone 7 has no working WDA at all, so video is the only option there —
    and one method on both devices keeps their numbers comparable.

THE FOUR MARKERS, all read off frames so no harness overhead is inside a number:

    t0 ─────────► t_first ────────► t_snapshot ──► t_ready
    tap: the      the app's own     the end screen  it is actually
    still home    launch screen     is DRAWN        running
    screen        fills the                         (see liveness)
    starts moving screen

  Headline per scenario:
    fresh       t0 → t_gate    (t_snapshot of a run that ends on a pop-up —
                                the run STOPS there, gates are not answered)
    subsequent  t0 → t_ready
    warm        t0 → t_ready
  `t0 → t_first` is reported for every run too: it stays comparable between two
  builds even when their pop-ups differ.

LIVENESS — WHY t_ready IS NOT JUST "THE MENU IS DRAWN"
On a warm launch iOS paints a frozen SNAPSHOT of the app during the open
animation, before the app is running. A drawn-only test matches that snapshot and
reports a fake-fast warm launch. So the settled screen being *visible* is
`t_snapshot` ("looks ready" — what the user perceives) and `t_ready` ("is ready")
is when the picture starts CHANGING again, which only the live app can do. The
menu animates — glow/sparkles, the reason `baselines/*.volatile.png` masks exist
— so a frozen run of frames at the start of the settled screen is the snapshot,
and its end is the resume. On a cold launch there is no frozen run and the two
markers coincide.

WHAT IT DETECTS BY, AND WHY NOT TEMPLATES
Reference-frame matching on downscaled greyscale, not `assets_unity/` templates.
The templates are Unity-only and 19.5:9-only, and this has to measure the **Obj-C**
build and run on the **iPhone 7's 16:9** layout where no Unity set exists. Screen
identity needs far less resolution than motion analysis, so frames are reduced to
DOWN_W px wide — that also keeps a 5-minute recording inside a few hundred MB.

The home-screen reference is taken FROM THE RECORDING (the still stretch before
the first tap), so nothing has to be cropped or committed per device or per build.

ONE RECORDING HOLDS MANY LAUNCHES. Runs are found automatically: a still home
screen, then movement, then a screen that settles. Trips to the app switcher to
kill the app are *also* home→something→home, so they are rejected by requiring a
run to settle on a screen that is NOT the home screen. Always eyeball `--list`
before trusting a batch.

Recording: QuickTime → File → New Movie Recording → Camera = the iPhone.
Full session protocol, and everything that must be held constant between blocks:
`tests/launch/README.md`.

Usage:
  vid_launch.py "<video.mov>" --list
  vid_launch.py "<video.mov>" --scenario subsequent --label "unity355 ip11 offline"
  vid_launch.py "<video.mov>" --scenario warm --report
"""
import argparse
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

# Analysis resolution. This tool only has to answer "which screen is this", and
# screen IDENTITY survives heavy downscaling. It is also what keeps a long
# recording in memory: 96px is ~20 KB/frame, so 5 minutes at 60 fps is ~350 MB
# rather than ~1 GB.
DOWN_W = 96
PX_THRESH = 12          # per-pixel abs greyscale diff before a pixel counts as changed

# ── thresholds ────────────────────────────────────────────────────
# All are exposed on the CLI: they are tuned once against a throwaway recording
# from the device in question (see README), never against the real session.
#
# Motion is the fraction of pixels that changed since the previous frame
# (`frac_series`). Distances are mean absolute greyscale difference,
# 0-255, between two frames.
TAP_MOTION = 0.0020     # the still home screen "started moving" -> the tap landed
FROZEN_MOTION = 0.0008  # at/below this a frame is a duplicate: nothing is rendering
HOME_TOL = 6.0          # this close to the home reference IS the home screen
GONE_TOL = 25.0         # this far from it, the home screen is off screen
SETTLE_TOL = 4.0        # consecutive frames this close are the same settled screen
MIN_HOME_S = 0.8        # the home screen must sit still this long before a tap counts
MIN_SETTLE_S = 0.40     # a settled screen must hold this long to be an end state
MAX_LAUNCH_S = 30.0     # beyond this a run is not a launch; report, do not measure


def read_video(path):
    """Every frame as a small greyscale image, plus its timestamp in ms."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise SystemExit(f"cannot open {path}")
    nominal = cap.get(cv2.CAP_PROP_FPS) or 60.0
    frames, ts = [], []
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        ts.append(cap.get(cv2.CAP_PROP_POS_MSEC))
        h = int(fr.shape[0] * DOWN_W / fr.shape[1])
        frames.append(cv2.cvtColor(cv2.resize(fr, (DOWN_W, h)), cv2.COLOR_BGR2GRAY))
    cap.release()
    # POS_MSEC is unreliable on a full sequential read for some codecs. The
    # capture is a constant-rate grid, so synthesize the grid if it looks wrong.
    if (len(ts) < 2 or ts[-1] <= ts[0]
            or any(ts[i] <= ts[i - 1] for i in range(1, len(ts)))):
        step = 1000.0 / nominal
        ts = [k * step for k in range(len(frames))]
    return frames, ts


def frac_series(frames):
    """Fraction of pixels that changed from each frame to the next."""
    npix = frames[0].size
    frac = [0.0]
    for i in range(1, len(frames)):
        d = cv2.absdiff(frames[i], frames[i - 1])
        frac.append(float((d > PX_THRESH).sum()) / npix)
    return np.array(frac)


def load(path):
    """Frames as small greyscale + timestamps (seconds) + motion series."""
    frames, ts_ms = read_video(path)
    if len(frames) < 30:
        raise SystemExit(f"{path}: only {len(frames)} frames — is this a real recording?")
    return frames, np.array(ts_ms) / 1000.0, frac_series(frames)


def mad(a, b):
    """Mean absolute difference between two greyscale frames (0-255)."""
    return float(np.abs(a.astype("int16") - b.astype("int16")).mean())


def runs_where(flags, min_len):
    """[(start, end)] inclusive index ranges of True runs at least min_len long."""
    out, start = [], None
    for i, f in enumerate(list(flags) + [False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            if i - start >= min_len:
                out.append((start, i - 1))
            start = None
    return out


def home_reference(frames, motion, fps):
    """The home screen, learned from the recording's own opening stillness.

    Taken from the video rather than a committed crop so the same analyser works
    on any device and any build with nothing to maintain. The protocol says the
    recording starts on a settled home screen; this takes the median of the first
    still stretch, so a stray sparkle or compression wobble cannot define it.
    """
    still = runs_where(motion <= FROZEN_MOTION, max(4, int(0.25 * fps)))
    if not still:
        raise SystemExit("no still stretch found at all — was the recording started "
                         "on a settled home screen?")
    lo, hi = still[0]
    return np.median(np.stack(frames[lo:hi + 1]), axis=0).astype("uint8")


def settled_run(frames, lo, hi, fps):
    """The LAST stretch in [lo, hi] where the picture stops changing SHAPE.

    Consecutive-frame distance, not motion: the menu never goes fully still (it
    glows and sparkles), but those pixels move a little while a screen transition
    moves a lot. So "the same screen, still animating" stays inside a stretch and
    a transition breaks it.

    LAST, not longest — this cost a bug. The launch/splash screen is a still image,
    so it is perfectly content-stable and on a slow launch it is stable for LONGER
    than the menu the operator then navigates away from. Taking the longest
    stretch therefore reported the splash appearing as "the launch finished". The
    screen a launch ENDS on is the one that matters, and that is the last one.
    """
    min_len = max(3, int(MIN_SETTLE_S * fps))
    same = [True] + [mad(frames[i], frames[i - 1]) < SETTLE_TOL
                     for i in range(lo + 1, hi + 1)]
    found = runs_where(same, min_len)
    if not found:
        return None
    a, b = found[-1]
    return (lo + a, lo + b)


def reject_odd_endings(runs, frames):
    """Flag runs that do not end on the same screen as the others.

    Every launch in a block ends on the same screen (the menu), so the odd one
    out is not a launch. This is what catches the trip to the app switcher to kill
    the app: that is also home -> something -> home, and the switcher IS a settled
    non-home screen, so it otherwise passes as a launch. It also catches a run an
    interstitial ad landed on, which is a real hazard in the online blocks.

    Needs a majority to compare against, so it only runs with 3+ candidates — a
    'fresh' recording holds exactly one launch and is left alone.
    """
    cands = [r for r in runs if "i_snap" in r and not r.get("skipped")]
    if len(cands) < 3:
        return
    refs = [frames[r["i_snap"]] for r in cands]
    groups = []
    for i, f in enumerate(refs):
        for g in groups:
            if mad(f, refs[g[0]]) < 2.5 * SETTLE_TOL:
                g.append(i)
                break
        else:
            groups.append([i])
    keep = set(max(groups, key=len))
    for i, r in enumerate(cands):
        if i not in keep:
            r["skipped"] = ("ends on a different screen from the other launches "
                            "(app-switcher trip, or an ad landed on it)")


def measure(frames, ts, motion, home, i_tap, i_end, fps):
    """The markers for one run, from the tap at i_tap to the run's end i_end."""
    r = {"t0": float(ts[i_tap]), "i_tap": i_tap}

    # t_first — the app's own launch screen fills the screen. During the open
    # animation the home screen is still there, scaling up, so this is the point
    # the home screen has effectively gone rather than the first pixel of change.
    i_first = None
    for i in range(i_tap, i_end + 1):
        if mad(frames[i], home) > GONE_TOL:
            i_first = i
            break
    r["to_first"] = None if i_first is None else float(ts[i_first] - ts[i_tap])

    settled = settled_run(frames, i_tap, i_end, fps)
    if settled is None:
        r["error"] = "the screen never settled — nothing to call the end of the launch"
        return r
    i_snap, i_settle_end = settled

    # A run that settles back on the home screen was never a launch: it is the
    # trip to the app switcher to kill the app. Caller drops these.
    r["ended_home"] = mad(frames[i_snap], home) < HOME_TOL
    r["to_snapshot"] = float(ts[i_snap] - ts[i_tap])

    # t_ready — liveness. A frozen stretch at the START of the settled screen is
    # iOS's snapshot, not the app; the app is running from the moment the picture
    # changes again. No frozen stretch (a cold launch) -> the two coincide.
    i_ready = i_snap
    while i_ready < i_settle_end and motion[i_ready] <= FROZEN_MOTION:
        i_ready += 1
    r["to_ready"] = float(ts[i_ready] - ts[i_tap])
    r["frozen_s"] = float(ts[i_ready] - ts[i_snap])
    r["i_snap"], r["i_ready"] = i_snap, i_ready
    return r


def find_runs(frames, ts, motion, home, fps):
    """Every launch in the recording, in order. See the module docstring."""
    is_home = np.array([mad(f, home) < HOME_TOL for f in frames])
    quiet_home = is_home & (motion <= FROZEN_MOTION)
    home_runs = runs_where(quiet_home, max(3, int(MIN_HOME_S * fps)))
    if not home_runs:
        raise SystemExit("never found the home screen sitting still — check --home-tol")

    out = []
    for k, (_, hi) in enumerate(home_runs):
        # The tap: the first movement after the home screen has sat still.
        i_tap = None
        for i in range(hi + 1, len(frames)):
            if motion[i] > TAP_MOTION:
                i_tap = i
                break
        if i_tap is None:
            continue
        # The run ends where the home screen next sits still (the operator going
        # back to kill or background the app), or at the end of the recording.
        i_end = len(frames) - 1
        for lo2, _ in home_runs[k + 1:]:
            if lo2 > i_tap:
                i_end = lo2 - 1
                break
        if ts[i_end] - ts[i_tap] > MAX_LAUNCH_S:
            i_end = int(np.searchsorted(ts, ts[i_tap] + MAX_LAUNCH_S))
            i_end = min(i_end, len(frames) - 1)
        if i_end - i_tap < int(0.15 * fps):
            continue
        m = measure(frames, ts, motion, home, i_tap, i_end, fps)
        if m.get("ended_home"):
            m["skipped"] = "ends back on the home screen, so nothing was launched"
        out.append(m)
    # Deduplicate: two home runs separated by a blink can point at the same tap.
    seen, uniq = set(), []
    for m in out:
        if m["i_tap"] in seen:
            continue
        seen.add(m["i_tap"])
        uniq.append(m)
    reject_odd_endings(uniq, frames)
    return uniq


def filmstrip(path, run, ts, out_png, cols=16):
    """Contact sheet across one launch, labelled in seconds from the tap."""
    i0, i1 = run["i_tap"], run.get("i_ready", run["i_tap"])
    span = max(1, i1 - i0)
    idx = [max(0, i0 - 2)] + [i0 + int(round(span * k / (cols - 2)))
                              for k in range(cols - 1)]
    cap = cv2.VideoCapture(path)
    thumbs = []
    for i in idx:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, fr = cap.read()
        if not ok:
            continue
        h = int(fr.shape[0] * 150 / fr.shape[1])
        strip = np.full((h + 22, 150, 3), 20, "uint8")
        strip[22:] = cv2.resize(fr, (150, h), interpolation=cv2.INTER_AREA)
        cv2.putText(strip, f"{ts[i] - run['t0']:+.2f}s", (3, 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 255), 1)
        thumbs.append(strip)
    cap.release()
    if thumbs:
        cv2.imwrite(out_png, np.hstack(thumbs))
        return out_png
    return None


def main():
    global TAP_MOTION, HOME_TOL, SETTLE_TOL, FROZEN_MOTION
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("video")
    p.add_argument("--scenario", choices=("fresh", "subsequent", "warm"),
                   default="subsequent",
                   help="fresh quotes t0->gate; subsequent/warm quote t0->ready")
    p.add_argument("--label", default="", help="build/device/network, for the results file")
    p.add_argument("--list", action="store_true", help="just show what was detected")
    p.add_argument("--report", action="store_true", help="write a filmstrip per launch")
    p.add_argument("--tap-motion", type=float, default=TAP_MOTION)
    p.add_argument("--home-tol", type=float, default=HOME_TOL)
    p.add_argument("--settle-tol", type=float, default=SETTLE_TOL)
    p.add_argument("--frozen-motion", type=float, default=FROZEN_MOTION)
    a = p.parse_args()

    TAP_MOTION, HOME_TOL = a.tap_motion, a.home_tol
    SETTLE_TOL, FROZEN_MOTION = a.settle_tol, a.frozen_motion

    frames, ts, motion = load(a.video)
    fps = (len(frames) - 1) / max(1e-6, ts[-1] - ts[0])
    print(f"{os.path.basename(a.video)}: {len(frames)} frames, {ts[-1] - ts[0]:.1f}s, "
          f"{fps:.1f} fps")
    if fps < 45:
        print(f"  WARNING: {fps:.0f} fps capture — every marker is only good to "
              f"{1000 / fps:.0f} ms. Record at 60.")

    home = home_reference(frames, motion, fps)
    runs = find_runs(frames, ts, motion, home, fps)
    good = [r for r in runs if "error" not in r and "skipped" not in r]

    print(f"\n  {len(runs)} candidate run(s), {len(good)} launch(es):")
    for n, r in enumerate(runs, 1):
        if r.get("skipped"):
            print(f"    {n:2d}. t={r['t0']:6.2f}s  skipped — {r['skipped']}")
        elif "error" in r:
            print(f"    {n:2d}. t={r['t0']:6.2f}s  ! {r['error']}")
        else:
            first = "  n/a" if r["to_first"] is None else f"{r['to_first']:5.2f}"
            froze = f"   (snapshot held {r['frozen_s']:.2f}s)" if r["frozen_s"] > 0.05 else ""
            print(f"    {n:2d}. t={r['t0']:6.2f}s  first {first}s  "
                  f"drawn {r['to_snapshot']:5.2f}s  ready {r['to_ready']:5.2f}s{froze}")

    if a.list or not good:
        if not good:
            print("\n  nothing measurable. Check --list output and the thresholds "
                  "(README: tuning), then re-run.")
        return 0 if good else 1

    end_key = "to_snapshot" if a.scenario == "fresh" else "to_ready"
    end_name = "tap -> pop-up" if a.scenario == "fresh" else "tap -> ready"
    vals = [r[end_key] for r in good]
    firsts = [r["to_first"] for r in good if r["to_first"] is not None]

    print(f"\n  SCENARIO: {a.scenario}    {a.label}")
    if a.scenario == "fresh" and len(vals) > 2:
        print(f"    NOTE: {len(vals)} runs in a 'fresh' recording — a fresh start "
              f"happens ONCE per install. Check --list; the later runs are not fresh.")
    if len(vals) < 3:
        # Too few to median honestly — show them all instead of implying volume.
        print(f"    {end_name}: " + ", ".join(f"{v:.2f}s" for v in vals) + f"   (N={len(vals)})")
    else:
        print(f"    {end_name}: median {statistics.median(vals):.2f}s   "
              f"(range {min(vals):.2f}-{max(vals):.2f}s, N={len(vals)})")
    if firsts:
        print(f"    tap -> first frame: median {statistics.median(firsts):.2f}s "
              f"(comparable between builds whatever their pop-ups do)")
    if a.scenario == "warm":
        held = [r["frozen_s"] for r in good]
        print(f"    of which iOS's frozen snapshot: median {statistics.median(held):.2f}s "
              f"— the gap between LOOKING ready and BEING ready")
    print(f"    resolution: +/- {1000 / fps:.0f} ms (one video frame)")

    stem = os.path.splitext(os.path.basename(a.video))[0]
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "..", "log", "launch", stem)
    out_dir = os.path.normpath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    if a.report:
        for n, r in enumerate(good, 1):
            filmstrip(a.video, r, ts, os.path.join(out_dir, f"{a.scenario}_{n}.png"))
        print(f"    filmstrips -> {out_dir}")
    with open(os.path.join(out_dir, f"{a.scenario}.json"), "w") as f:
        json.dump({"video": a.video, "label": a.label, "scenario": a.scenario,
                   "fps": fps, "runs": runs}, f, indent=2)
    print(f"    raw markers -> {os.path.join(out_dir, a.scenario + '.json')}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
