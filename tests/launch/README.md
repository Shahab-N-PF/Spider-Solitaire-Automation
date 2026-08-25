# Launch time — Unity vs Obj-C

The **third axis**, beside pixel fidelity (`compare_unity*.py`) and function
(`verify*.py`): **how long the user waits after tapping the icon.** A build can
be pixel-perfect and still feel worse if the engine swap added seconds to
startup, and nothing else in this repo would notice.

Unity is a specific risk here: engine init, asset bundles and first-run shader warm-up are
startup work the Obj-C build never did.

## Three scenarios, three different questions

| Scenario | What it is | Headline number |
|---|---|---|
| **Fresh start** | the very first launch after installing | **tap → pop-up.** Stops at the ATT prompt; the gates are *not* answered |
| **Subsequent** | app killed from the switcher, then launched | tap → ready |
| **Warm** | app backgrounded, then brought forward | tap → ready |

The ATT prompt only appears on a fresh launch, so a fresh start ends where the user is
first *blocked* — that is the wait that matters, and it is where the run stops.

## The four markers

All read off video frames, so no harness overhead sits inside any number.

```
t0 ──────────► t_first ────────► t_snapshot ─────► t_ready
tap: the       the app's own     the end screen    it is actually
still home     launch screen     is DRAWN          running
starts moving  fills the screen                    (liveness, below)
```

`t0 → t_first` is reported for every run as well. It stays comparable between two builds
**even when their pop-ups differ** — which matters, because the Obj-C build may not show an
ATT prompt at all.

We cannot see the finger in a screen recording, so **t0 lags the real touch by up to one
frame (≤17 ms)**. Same bias on both builds, so it cancels in the comparison. Markers land
on the first frame that can be *confirmed*, so they are late by ≤1 frame, never early.

### Liveness — why `t_ready` is not just "the menu is drawn"

On a warm launch **iOS paints a frozen snapshot of the app during the open animation,
before the app is running.** A drawn-only test matches that snapshot and reports a
fake-fast warm launch. So:

- **`t_snapshot`** — when it *looks* ready. What the user perceives.
- **`t_ready`** — when it *is* ready: when the picture starts changing again, which only the
  live app can do.

The menu animates (glow/sparkles — the reason `baselines/*.volatile.png` masks exist), so a
frozen run of frames at the start of the settled screen *is* the snapshot, and its end is
the resume. On a cold launch there is no frozen run and the two markers coincide.

Both are reported for warm launches. The gap between them is iOS's, not the app's.

## Why video, not the WDA harness

`vid_launch.py` (60 fps QuickTime recording) is **primary** and the source of every quoted
number:

- **t0 is the icon tap.** No harness can report that — only frames can.
- **16.7 ms** resolution against ~150 ms for a screenshot round trip. Fresh start costs a
  reinstall per sample, so per-sample precision has to carry a low-N result.
- The **iPhone 7 has no working WDA**, so video is the only option there — and one method on
  both devices keeps their numbers comparable.

`live_launch.py` exists only for **unattended volume** on subsequent/warm, iPhone 11 only.
It taps the icon itself and samples screenshots, and it is honest about its limits: it
prints its own frame gap, flags a run whose sampling stalled inside the measured window as
`GAPPY`, and **cannot** separate "looks ready" from "is ready" (iOS's snapshot can be
shorter than one sample), so its warm number is labelled LOOKS-ready.

## Running

```bash
# see what was detected before trusting a batch — ALWAYS do this first
./.venv/bin/python tests/launch/vid_launch.py "~/Movies/unity_ip11_offline_sub.mov" --list

# then measure
./.venv/bin/python tests/launch/vid_launch.py "<video.mov>" \
    --scenario subsequent --label "unity355 ip11 offline" --report
./.venv/bin/python tests/launch/vid_launch.py "<video.mov>" --scenario warm --report
./.venv/bin/python tests/launch/vid_launch.py "<video.mov>" --scenario fresh --report

# optional, iPhone 11 only, unattended volume
./.venv/bin/python tests/launch/live_launch.py --icon 640,1200 --repeats 20
```

`--report` writes a filmstrip per launch to `log/launch/<video stem>/`, labelled in seconds
from the tap. **Every quoted number must be checkable on a filmstrip.**

## Session protocol

Both builds install **from TestFlight**, so the install path is identical on both sides and
cannot confound the comparison. Per (device × build):

1. Install the build. Record **`CFBundleVersion`** — the marketing version reads `8.0.0` on
   every Unity build and cannot tell them apart.
2. **Reboot the phone**, wait 60 s. No discard launch: the first launch after install *is*
   the fresh-start sample.
3. Set the network state for the block (Airplane Mode on / off).
4. Start QuickTime → File → New Movie Recording → Camera = the iPhone. **Start the
   recording on a settled home screen** — that is where the analyser learns what the home
   screen looks like.
5. **Fresh** — tap the icon, wait for the pop-up, **stop there.** Note which gate it is.
6. Answer the gates, reach the menu, then **subsequent ×10**: kill from the app switcher,
   **wait on the home screen** (≥2 s, still), tap the icon, wait for the menu.
7. **Warm ×10**: from the menu press Home, wait 5 s, tap the icon.
8. Stop recording. Analyse, `--list` first, then eyeball one filmstrip.
9. Repeat 3–8 for the other network state. For a further fresh sample: delete the app,
   reinstall from TestFlight, and repeat from 2.

**Pause on a still home screen between launches.** The analyser finds runs by looking for a
settled home screen followed by movement; without the pause, two launches merge into one.

### Held constant across every block

A difference in any of these lands straight in the numbers:

- **Reduce Motion off** — it changes the open animation that t0 is read from.
- **Low Power Mode off.**
- Brightness and auto-lock fixed; **battery >50 % and not charging while recording**
  (charging changes thermals); no other apps running.
- Icon in the **same home-screen position**.

### Controls

- **Drift:** run the subsequent block as Unity → Obj-C → Unity on one device. If the two
  Unity blocks disagree by more than their spread, the session drifted (thermal, iOS
  background work) and the A/B is not trustworthy.
- **Fresh start is N=2** — each sample costs a TestFlight reinstall. Reported as two values,
  never as a median. Enough to catch a large regression (the kind shader warm-up causes),
  not enough to resolve a small one.

## Tuning the thresholds

Defaults are in `vid_launch.py` and every one is a CLI flag. Tune them **once against a
throwaway recording** from the device in question — never against the real session. A single
launch is enough:

```bash
./.venv/bin/python tests/launch/vid_launch.py "throwaway.mov" --list
```

If `--list` finds nothing, `--home-tol` is usually the one to move (it decides what counts
as the home screen). If two launches merge, the pause between them was too short.

## Gotchas

- **The splash screen is also perfectly static, and can be stable for LONGER than the
  menu.** So the end of a launch is the *last* settled stretch in a run, not the longest.
  Taking the longest reported the splash appearing as "the launch finished" — this cost a
  real bug and is why `settled_run()` scans backwards.
- **A trip to the app switcher looks like a launch.** Killing the app is
  home → something → home, and the switcher *is* a settled non-home screen, so it passes
  every other test. It is rejected by requiring a run to end on the **same screen as the
  other launches** — which also catches a run an interstitial ad landed on. Needs 3+
  candidates to have a majority, so a `fresh` recording (exactly one launch) is left alone.
- **iOS app prewarming** means a "cold" launch may not be fully cold, and it cannot be
  disabled. Mitigated by the reboot and the fixed wait; a caveat, not something solved.
- **Run offline for the controlled A/B.** Online, ad-SDK fetches ride along with startup and
  an interstitial can cover the menu, which reads as a slow launch. Online numbers are worth
  having as the real-user figure — just do not mix the two sets.
- **Never quote a `live_launch.py` warm number.** It cannot see iOS's frozen snapshot.

## Status

**Tooling verified offline; no device measurements yet.** The analyser was checked against
synthetic frame streams with injected ground truth and recovers them exactly:

| Check | Result |
|---|---|
| subsequent launch, splash held **longer** than the menu | 3/3 launches, markers within 1 frame |
| app-switcher trips mixed in | 3 launches found, **both** switcher trips rejected |
| warm launch, 0.45 s frozen snapshot | drawn 0.100 s, ready 0.550 s, frozen 0.45 s — exact |
| frozen length, injected 0.30 s | 0.30 s — exact |
| full pipeline on a **compressed** 60 fps video at device resolution | drawn 0.10 s, ready 0.55 s, frozen 0.45 s — exact, so codec noise does not break liveness |
| `live_launch.py`: t0 from frames, stall flagged, honest errors | 4/4 paths, and the 0.30 s of WDA tap latency correctly excluded |

`live_launch.py`'s **springboard icon lookup is untested on a device** — pass `--icon X,Y`
(measured once by hand) and it says so plainly rather than guessing.

## Results

_To fill in after the first session._ Table shape: 3 scenarios × 2 builds (Unity vs Obj-C
7.42.5) × 2 devices (iPhone 7, iPhone 11) × 2 network states — median, range, N.

Open question this session also settles: **the first-launch gate order.** CLAUDE.md says ATT
first with Terms & Conditions on the *next* launch; `tests/verifyFirstLaunch.py` says T&C
then ATT on the *same* launch, and claims WDA can read ATT's buttons — which `helpers.py`
and `unity_ui.clear_overlays()` both record as false. The fresh-start recording shows which
gate comes first, and launch #2 shows whether the other one follows.
