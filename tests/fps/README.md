# FPS / animation performance testing

Tools to compare **render frame-rate of in-game moves** between the Obj-C and
Unity Spider builds. This is a **different axis** from the pixel-fidelity
`compare_unity_*` suite (which asks "do the screens look right?") — here we ask
"do the moves *animate* at a smooth 60 fps, and did the Unity port introduce any
hitches?"

Measured on the **iPhone 7** ("Kaala", `385e82401ffb88ee946698f951ae9b991beba9da`,
iOS 15.7.5, 750×1334, 60 Hz). It's the weakest / slowest device and only 60 Hz,
so it exposes frame drops most clearly; and its old iOS is the one where the FPS
tooling works with **no** extra setup. No WDA on this device → moves are performed
**by hand** while FPS streams.

## Two methods (use the right one per move)

| | `fps_capture.py` (tidevice) | `vid_analyze.py` (video) |
|---|---|---|
| Source | `tidevice perf -o fps --json` (CoreAnimation FPS) | 60 fps QuickTime screen recording |
| Resolution | **~1 Hz** (one sample/sec) | **per-frame** (16.7 ms) |
| Good for | continuous moves (a sustained drag) | sub-second animations (deal, fly-off) |
| Blind spot | too coarse for <1 s events; reads ~0 when static | needs a tight hand-recorded clip |

`tidevice dumpfps` returns nothing on this device — `perf --json` is the source.
On **iOS 17+** devices (iPhone 11 / 14) this classic-instruments path is dead
(tidevice can't even launch the app) — use the **xctrace** path instead, see
"iPhone 14 (120 Hz)" below. (`pymobiledevice3` is the other option but needs a sudo
tunnel + Python 3.10+, neither available here; xctrace needs neither.)

### Key gotcha — a low FPS number is not automatically a "hitch"

FPS reads **~0 when the screen is static** (the counter counts *committed* frames).
So a discrete animation like the suit fly-off, sampled at 1 Hz, averages its busy
sub-second with idle time and **reads low even when it's perfectly smooth**. And a
fully-static **pause between two eased animation segments is a *designed* pause,
not a stall**. Always confirm a suspected hitch with `vid_analyze.py --detail`:

- **Real stall/jank:** motion cuts off at high `frac` and resumes at high `frac`
  (a frame held mid-flight → a run of identical frames inside continuous motion).
- **Designed pause:** `frac` **eases down to ~0** and later **eases back up**
  (one animation segment finished, the next begins). Not a performance problem.

This distinction overturned an early wrong call — see `reports/CHANGELOG.md`
("FPS / animation performance") and the `no-fps-regression-iphone7` memory.

## Usage

```bash
# --- continuous move (drag), tidevice ~1Hz ---
# On the iPhone 7 (Obj-C or Unity build in a 1-suit game), drag a run in circles
# for the whole window while this streams:
./.venv/bin/python tests/fps/fps_capture.py --label unity-8.0.0 --move drag --seconds 18 --no-launch
./.venv/bin/python tests/fps/fps_capture.py --label objc-7.42.5 --move drag --seconds 18 --no-launch
./.venv/bin/python tests/fps/fps_analyze.py log/fps/*.jsonl      # compare (read mean for drag, max/peak for discrete)

# --- sub-second animation (deal, suit fly-off), 60fps video ---
# QuickTime Player -> File > New Movie Recording -> Camera = the iPhone.
# Record a TIGHT clip of ONE move (poise -> record -> single move -> stop). Then:
./.venv/bin/python tests/fps/vid_analyze.py "~/Documents/FPS Testing Videos/unity_suit.mov" --motion 0.006
./.venv/bin/python tests/fps/vid_analyze.py "~/Documents/FPS Testing Videos/unity_suit.mov" --motion 0.006 --detail 4.0 4.6
```

Captures land in `log/fps/<label>__<move>.jsonl` (git-ignored). Recordings live
wherever you save them (kept outside the repo, e.g. `~/Documents/FPS Testing Videos/`).

`vid_analyze.py` output: a per-window timeline (locate the animation), then a
**motion-burst table** — each row is one continuous motion (a card wave); `effFPS`
= distinct frames / burst duration, `worstHold` = longest single held frame inside
the burst. Tune `--motion` to the move (single card ~0.002; deal/fly-off ~0.006–0.02).

It then prints an **Apple-style hitch section**: frame-time p50/p95/p99 *within
motion*, and the **hitch-time ratio** — ms of hitch per second of animation
(`<5` good · `5–10` concern · `>10` bad). A hitch is a frame frozen **mid-motion**
(motion at speed on both sides of the gap); a static gap where motion **eased to
rest** first, or one longer than 400 ms, is reported as a **designed pause**, not a
hitch. Use `--detail T0 T1` to print the per-frame trace that adjudicates the two
(a real stall cuts off at high `frac`; a designed pause eases `frac`→0 and back).
Note: an earlier classifier that judged "was it moving?" by the *max of the last few
frames* over-flagged eased stops as hitches — judging by the **immediate** neighbor
frame is what makes it robust.

## iPhone 14 (120 Hz) — on-device Instruments via `xctrace`

The video method caps at 60 fps, so it can't measure a **120 Hz ProMotion** device.
There, use Xcode's Instruments CLI (`xctrace`) with the **Animation Hitches** template
and parse the per-frame timing with `trace_fps.py`.

**One-time setup:** iOS 17+ devices connect over Apple's CoreDevice stack, which
`xctrace` doesn't fully see — it lists the device **Offline** and hangs ("waiting for
device to boot"). Fix: open **Xcode → Window → Devices and Simulators**, select the
device, and let it finish *"Preparing device for development."* After that it shows
**online** to `xctrace`. (`devicectl` speaks CoreDevice directly — used to launch the app.)

```bash
IP14=00008120-0001485A1E60201E                       # iPhone 14 Pro Max
xcrun devicectl device process launch --device $IP14 --terminate-existing com.fingerarts.Spider
PID=$(xcrun devicectl device info processes --device $IP14 | awk '/Spider.app\/Spider/{print $1; exit}')
xcrun xctrace record --device $IP14 --template 'Animation Hitches' \
      --attach "$PID" --time-limit 12s --output move.trace      # drive the move by hand
./.venv/bin/python tests/fps/trace_fps.py move.trace [--window T0 T1] [--dump]
```

`trace_fps.py` reads the `hitches-frame-lifetimes` table (per-frame present times) and
reports the **present-rate mix** (120/60/30/irregular/idle) + interval percentiles.
ProMotion is adaptive, so 120/60/30 are all valid; only **irregular** intervals are
candidate hitches. Caveat: it's present *timing* only (no pixel data), so it can't tell
a designed pause from a stall and over-reports on near-static screens — window to the
move, and for pause-vs-stall use the 60 fps video method (valid since the app is 60-capped).

## Result (2026-08-06, Obj-C 7.42.5 vs Unity 8.0.0, iPhone 7)

**No FPS regression.** Every move that animates holds 60 fps on both builds: drag,
rapid 2-card move, deal-a-row (10 cards), and suit fly-off (13 cards). The fly-off
is, on **both** builds, two eased 60 fps card-waves separated by a designed static
pause (Unity ~133 ms, Obj-C ~180–240 ms) — not a mid-flight freeze. The Apple-style
hitch metrics confirm it: frame-time **p99 = 17 ms** (one refresh) and **hitch ratio
0.0 ms/s [GOOD]** on every move, both builds. Full write-up in `reports/CHANGELOG.md`.

**iPhone 14 Pro Max (120 Hz ProMotion), Unity 8.0.0 — via xctrace:** the app is
**locked to 60 fps** and does *not* use the 120 Hz display (drag: 749/749 frames at
60 fps, p99 16.8 ms, 0 hitches — flawless at 60). Open question: whether the old
Obj-C build drove 120 Hz (needs a TestFlight swap, and a 7.x build may not run on
iOS 26). The fly-off shows 60 fps card-motion with static gaps that `xctrace` alone
can't classify as pause-vs-stall — a 60 fps screen recording + `vid_analyze.py` would
settle that.

> The builds share bundle id `com.fingerarts.Spider`, so installing one replaces
> the other — swap between Obj-C 7.x and Unity 8.x via **TestFlight**, measure one
> at a time. Reinstall Unity afterward to restore the normal test setup.
