#!/usr/bin/env python3
"""Parse an Xcode Instruments 'Animation Hitches' .trace -> present-frame cadence.

For iOS 17+ devices (e.g. the 120 Hz iPhone 14) where the video method can't reach
120 fps and tidevice's classic-instruments perf is dead. Runs `xctrace export` on
the trace's `hitches-frame-lifetimes` table and analyzes the per-frame present
timeline. ProMotion is adaptive, so 120/60/30 are all VALID rates: each present
interval is classified to the nearest standard rate (±30%); only intervals near no
standard rate are "irregular" (a candidate hitch), and >400 ms are idle gaps.

Caveat: this is present *timing* only — it knows WHEN frames were shown, not WHAT
was on them, so on a near-static screen a long gap looks like a hitch but is just
idle, and it cannot tell a designed pause from a stall (use the 60 fps video +
vid_analyze.py for that, valid whenever the app is 60 fps-capped). Meaningful
during a continuous move; window to the move with --window.

Record first (see tests/fps/README.md):
  xcrun devicectl device process launch --device <udid> com.fingerarts.Spider
  xcrun xctrace record --device <udid> --template 'Animation Hitches' \
        --attach <pid> --time-limit 12s --output move.trace

Usage: trace_fps.py <trace> [--window T0 T1] [--dump]   (T0,T1 = s from trace start)
"""
import argparse
import subprocess
import sys
import xml.etree.ElementTree as ET

XPATH = '/trace-toc/run[@number="1"]/data/table[@schema="hitches-frame-lifetimes"]'


def export_rows(trace):
    r = subprocess.run(["xcrun", "xctrace", "export", "--input", trace, "--xpath", XPATH],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("xctrace export failed:\n" + r.stderr[-800:])
    return r.stdout


def parse(xml):
    root = ET.fromstring(xml)
    idmap, starts, durs = {}, [], []
    for row in root.iter('row'):
        s = d = None
        for ch in row:
            a = ch.attrib
            if 'id' in a:
                idmap[a['id']] = ch.text
                v = ch.text
            elif 'ref' in a:
                v = idmap.get(a['ref'])
            else:
                v = ch.text
            if ch.tag == 'start-time' and s is None:
                s = v
            elif ch.tag == 'duration' and d is None:
                d = v
        if s is not None:
            starts.append(int(s))
            durs.append(int(d) if d else 0)
    return starts, durs


def pctl(vals, p):
    if not vals:
        return 0.0
    v = sorted(vals)
    return v[min(len(v) - 1, int(round((len(v) - 1) * p / 100.0)))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace")
    ap.add_argument("--window", type=float, nargs=2, metavar=("T0", "T1"),
                    help="analyze only frames in [T0,T1] seconds from trace start")
    ap.add_argument("--dump", action="store_true",
                    help="print each present time + interval in the window")
    args = ap.parse_args()

    starts, durs = parse(export_rows(args.trace))
    if len(starts) < 3:
        sys.exit("not enough frames in trace")
    t0 = starts[0]
    t = [(s - t0) / 1e6 for s in starts]  # ms from start

    lo, hi = (args.window if args.window else (t[0] / 1000.0, t[-1] / 1000.0))
    idx = [i for i in range(len(t)) if lo * 1000 <= t[i] <= hi * 1000]
    if len(idx) < 3:
        sys.exit("not enough frames in window")
    tw = [t[i] for i in idx]
    intervals = [tw[i + 1] - tw[i] for i in range(len(tw) - 1)]  # ms between presents

    if args.dump:
        print("  t(s)   interval(ms)")
        for i in range(len(intervals)):
            mark = "  <<<" if intervals[i] > 25 else ""
            print(f"  {tw[i]/1000:6.2f}   {intervals[i]:6.1f}{mark}")

    span = (tw[-1] - tw[0]) / 1000.0
    n = len(tw)
    from collections import Counter

    # ProMotion is adaptive: 120/60/30 are all VALID rates. Classify each present
    # interval to the nearest standard rate (±30%); only intervals near no standard
    # rate are "irregular" (a real hitch), and >400ms are idle gaps (not a hitch).
    STD = [(120, 1000 / 120.0), (60, 1000 / 60.0), (30, 1000 / 30.0)]
    CAP_MS = 400.0

    def classify(iv):
        for r, p in STD:
            if abs(iv - p) <= 0.30 * p:
                return r
        return 'idle' if iv > CAP_MS else 'irregular'

    cls = [classify(iv) for iv in intervals]
    cnt = Counter(cls)
    std_counts = {r: cnt.get(r, 0) for r, _ in STD}
    dom = max(std_counts, key=std_counts.get)
    domp = 1000.0 / dom
    irregular = [(tw[i], intervals[i]) for i in range(len(intervals)) if cls[i] == 'irregular']
    idle = [(tw[i], intervals[i]) for i in range(len(intervals)) if cls[i] == 'idle']
    total_hitch = sum(iv - domp for _, iv in irregular if iv > domp)
    eff_fps = (n - 1) / span if span else 0
    ratio = total_hitch / span if span else 0
    verdict = "GOOD" if ratio < 5 else ("CONCERN" if ratio < 10 else "BAD")

    print(f"trace: {args.trace}")
    print(f"window {lo:.2f}-{hi:.2f}s   frames {n}   span {span:.2f}s")
    hist = "  ".join(f"{r}fps:{cnt.get(r,0)}" for r, _ in STD) + \
           f"  irregular:{cnt.get('irregular',0)}  idle:{cnt.get('idle',0)}"
    print(f"present-rate mix   {hist}")
    print(f"dominant rate: {dom} fps ({domp:.1f} ms)   effective {eff_fps:4.1f} fps")
    print(f"present interval  p50 {pctl(intervals,50):.1f}  p95 {pctl(intervals,95):.1f}  "
          f"p99 {pctl(intervals,99):.1f}  worst {max(intervals):.1f} ms")
    print(f"hitches (irregular intervals): {len(irregular)}   total hitch {total_hitch:.0f} ms   "
          f"-> ratio {ratio:.1f} ms/s [{verdict}]")
    for tt, g in irregular[:8]:
        print(f"   hitch @ {tt/1000:6.2f}s: interval {g:.0f} ms (~{1000/g:.0f} fps)")
    if idle:
        gs = ", ".join(f"{g:.0f}ms@{tt/1000:.1f}s" for tt, g in idle[:6])
        print(f"idle gaps (>{CAP_MS:.0f}ms, not hitches): {len(idle)} [{gs}]")


if __name__ == "__main__":
    main()
