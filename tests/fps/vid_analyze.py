#!/usr/bin/env python3
"""Frame-by-frame FPS analysis of a 60fps QuickTime screen recording of a move.

A 60Hz device screen recorded at 60fps yields one video frame per display
refresh. If the app renders a fresh frame every refresh -> consecutive video
frames differ (a "new" frame). If the app drops below 60 -> the frame is held
and consecutive video frames are identical ("duplicate"). So:
  effective fps of the animation = distinct frames / duration
  a hitch = a run of duplicate frames (frame held k refreshes -> 60/(k+1) fps)

A held-frame run is a *real app stall* (the app drew the same image N times); it
is NOT the same as a QuickTime capture-drop, which is a jump between *different*
frames (no duplicate run). Crucially, a fully-static gap *between* two eased
motion segments is a DESIGNED pause, not a stall — use --detail to tell them
apart (a stall cuts off at high motion and resumes at high motion; a designed
pause eases down to frac~0 and eases back up). See tests/fps/README.md.

Record clips TIGHT (one move only) or bursts blur together. Motion threshold
matters: a single-card move needs --motion ~0.002; deal/fly-off ~0.006-0.02.

Usage:
  vid_analyze.py "<video.mov>" [--win 0.5] [--motion 0.02] [--detail T0 T1]
"""
import argparse
import cv2
import numpy as np

PX_THRESH = 12       # per-pixel abs grayscale diff to count a pixel as changed
NEW_FRAC = 0.0008    # >this fraction of pixels changed => a "new" (non-duplicate) frame
DOWN_W = 160         # downscale width for speed/noise-robustness


def load(path):
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
        g = cv2.cvtColor(cv2.resize(fr, (DOWN_W, h)), cv2.COLOR_BGR2GRAY)
        frames.append(g)
    cap.release()
    # POS_MSEC is unreliable on a full sequential read for some codecs; the
    # capture is a constant-rate grid (verified), so synthesize if degenerate.
    if len(ts) < 2 or ts[-1] <= ts[0] or any(ts[i] <= ts[i - 1] for i in range(1, len(ts))):
        step = 1000.0 / nominal
        ts = [k * step for k in range(len(frames))]
    return frames, ts


def frac_series(frames):
    npix = frames[0].size
    frac = [0.0]
    for i in range(1, len(frames)):
        d = cv2.absdiff(frames[i], frames[i - 1])
        frac.append(float((d > PX_THRESH).sum()) / npix)
    return np.array(frac)


def hitch_analysis(frac, ts, base_ms, hitch_motion):
    """Apple-style hitch metrics. Between consecutive rendered ("new") frames:
    a gap longer than a refresh where motion is in progress on BOTH sides
    (max frac >= hitch_motion) is a HITCH (a frame frozen mid-motion); a gap
    where motion had eased to rest first is a DESIGNED pause, not a hitch.
    Reports frame-time percentiles + hitch-time ratio (ms hitch / s of motion)."""
    n = len(frac)
    new_idx = [i for i in range(n) if frac[i] > NEW_FRAC]
    print("\n=== hitch analysis (Apple-style: hitch time per second of motion) ===")
    if len(new_idx) < 3:
        print("  (not enough motion)")
        return
    thresh = 1.5 * base_ms
    MAX_HITCH_MS = 400.0   # longer static gaps are pauses/idle, not render hitches
    cont, hitches, pauses = [], [], []
    for k in range(len(new_idx) - 1):
        a, b = new_idx[k], new_idx[k + 1]
        gap = ts[b] - ts[a]
        if gap <= thresh:
            cont.append(gap)
            continue
        # HITCH only if motion was frozen *mid-flight*: the frame immediately
        # before AND after the gap were still moving (>= hitch_motion). An
        # eased-to-rest stop (low frac just before/after) is a DESIGNED pause.
        pre, post = float(frac[a]), float(frac[b])
        if gap <= MAX_HITCH_MS and min(pre, post) >= hitch_motion:
            hitches.append((gap, ts[a] / 1000.0))
        else:
            pauses.append((gap, ts[a] / 1000.0))
    frame_times = sorted(cont + [g for g, _ in hitches])

    def pctl(p):
        if not frame_times:
            return 0.0
        return frame_times[min(len(frame_times) - 1, int(round((len(frame_times) - 1) * p / 100.0)))]

    motion_span = (ts[new_idx[-1]] - ts[new_idx[0]]) / 1000.0
    pause_total = sum(g for g, _ in pauses) / 1000.0
    motion_time = max(1e-6, motion_span - pause_total)
    total_hitch = sum(g - base_ms for g, _ in hitches)  # ms beyond a refresh
    ratio = total_hitch / motion_time
    verdict = "GOOD" if ratio < 5 else ("CONCERN" if ratio < 10 else "BAD")
    print(f"  motion time {motion_time:5.2f}s   frame-time  p50 {pctl(50):3.0f}  "
          f"p95 {pctl(95):3.0f}  p99 {pctl(99):3.0f}  worst {frame_times[-1]:3.0f} ms")
    print(f"  hitches (frame frozen mid-motion): {len(hitches)}   "
          f"total hitch {total_hitch:4.0f} ms   -> ratio {ratio:4.1f} ms/s  [{verdict}]")
    for g, t in hitches:
        print(f"     hitch @ {t:5.2f}s: {g:.0f} ms held (~{1000/g:.0f} fps instant)")
    if pauses:
        ps = ", ".join(f"{g:.0f}ms@{t:.1f}s" for g, t in pauses)
        print(f"  designed pauses (eased stop, NOT counted as hitch): {len(pauses)}  [{ps}]")
    print("  ratio guide: <5 ms/s good · 5-10 concern · >10 bad (Apple hitch-ratio)")


def detail(frac, ts, t0, t1):
    """Per-frame trace over [t0, t1]: frac, new?, and gap since the last new frame
    (reveals whether a hold is mid-motion jank or a static pause between waves)."""
    print(f"\n=== frame-level {t0:.2f}-{t1:.2f}s ===")
    prev_new_t = None
    for i in range(1, len(frac)):
        t = ts[i] / 1000.0
        if t < t0 or t > t1:
            continue
        new = frac[i] > NEW_FRAC
        g = ""
        if new:
            if prev_new_t is not None:
                gap = (t - prev_new_t) * 1000
                if gap > 25:
                    g = f"  <-- {gap:.0f}ms gap (~{1000/gap:.0f}fps)"
            prev_new_t = t
        print(f"{t:5.2f} {frac[i]:6.4f} {'NEW' if new else ' . '}{g}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--win", type=float, default=0.5, help="timeline window (s)")
    ap.add_argument("--motion", type=float, default=0.02,
                    help="changed-fraction above which a frame counts as animation")
    ap.add_argument("--detail", type=float, nargs=2, metavar=("T0", "T1"),
                    help="also print a per-frame trace over [T0,T1] seconds")
    ap.add_argument("--hitch-motion", type=float, default=0.008,
                    help="frac level that counts as 'mid-motion' when classifying a "
                         "still-gap as a hitch vs a designed (eased) pause")
    args = ap.parse_args()

    frames, ts = load(args.video)
    n = len(frames)
    dur = (ts[-1] - ts[0]) / 1000.0 if n > 1 else 0
    base_ms = float(np.median(np.diff(ts))) if n > 1 else 16.7  # refresh period
    print(f"{args.video}")
    print(f"{n} frames, {dur:.2f}s, capture ~{(n-1)/dur:.1f} fps "
          f"(refresh {base_ms:.1f} ms)\n")

    frac = frac_series(frames)
    is_new = frac > NEW_FRAC
    is_moving = frac > args.motion

    # ---- timeline per window ----
    print(f"{'t(s)':>6} {'frms':>4} {'new':>4} {'effFPS':>6} {'peakΔ':>6}  motion")
    t0 = ts[0]
    w = args.win * 1000
    # bucket frames into fixed time windows
    buckets = {}
    for i in range(n):
        k = int((ts[i] - t0) // w)
        buckets.setdefault(k, []).append(i)
    for k in sorted(buckets):
        idx = buckets[k]
        seg_new = sum(1 for i in idx if is_new[i])
        seg_dur = (ts[idx[-1]] - ts[idx[0]]) / 1000.0 or (args.win)
        eff = seg_new / seg_dur if seg_dur else 0
        peak = frac[idx].max()
        bar = "#" * int(min(eff, 60) / 3)
        print(f"{k*args.win:6.1f} {len(idx):4d} {seg_new:4d} {eff:6.1f} {peak:6.3f}  {bar}")

    # ---- segment into discrete motion bursts ----
    # A burst = consecutive moving frames; small non-moving gaps (< MERGE_GAP,
    # e.g. an in-animation hitch) are bridged, but larger idle gaps (between
    # separate actions) split bursts. Each burst is scored independently so the
    # real fly-off isn't diluted by idle time or by other moves in the clip.
    MERGE_GAP = 200.0   # ms of stillness bridged inside one burst
    MIN_BURST = 0.12    # s; ignore blips shorter than this
    bursts = []
    i = 0
    while i < n:
        if not is_moving[i]:
            i += 1
            continue
        start = last = i
        j = i + 1
        while j < n:
            if is_moving[j]:
                last = j
            elif ts[j] - ts[last] > MERGE_GAP:
                break
            j += 1
        bursts.append((start, last))
        i = j

    print(f"\n{'#':>2} {'start':>6} {'end':>6} {'dur':>5} {'dist':>4} "
          f"{'effFPS':>6} {'minInst':>7} {'worstHold':>9}")
    kept = []
    for bi, (a, z) in enumerate(bursts):
        seg_dur = (ts[z] - ts[a]) / 1000.0
        if seg_dur < MIN_BURST:
            continue
        nt = [ts[k] for k in range(a, z + 1) if is_new[k]]
        dist = len(nt)
        eff = dist / seg_dur if seg_dur else 0
        if len(nt) > 1:
            gaps = np.diff(nt)
            worst = gaps.max()
            mininst = 1000.0 / worst
        else:
            worst, mininst = 0.0, 0.0
        kept.append((a, z, seg_dur, dist, eff, mininst, worst))
        print(f"{len(kept):>2} {ts[a]/1000:6.2f} {ts[z]/1000:6.2f} {seg_dur:5.2f} "
              f"{dist:4d} {eff:6.1f} {mininst:7.0f} {worst:8.0f}ms")

    print("\nEach row = one continuous motion burst (a drag, a deal, or the fly-off).")
    print("effFPS = distinct frames / burst duration;  worstHold = longest single")
    print("held frame inside the burst (an in-animation hitch).")

    hitch_analysis(frac, ts, base_ms, args.hitch_motion)

    if args.detail:
        detail(frac, ts, args.detail[0], args.detail[1])


if __name__ == "__main__":
    main()
