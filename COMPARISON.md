# Using only the comparison tool

For people who want the **pixel comparison** — "does this build look like that
build?" — and nothing else. No functional automation, no test suite, no driving
the app.

If you want the full rig (functional tests, running the app on a phone), read
[SETUP.md](SETUP.md) instead. This is the short path.

---

## The good news: you need almost nothing

The comparison is pure image maths. It reads two PNGs and reports how many pixels
differ. It does **not** touch a phone.

So you can skip all of this:

| Not needed | Why |
|---|---|
| **Xcode** | nothing is built or launched |
| **WebDriverAgent** (`wda/`) | nothing is driven |
| **An iPhone** | you are comparing files, not devices |
| **Apple Developer account / signing** | nothing is installed on a device |
| **airtest, poco, tidevice** | none of them are imported by the comparison |
| **Homebrew tools** (`iproxy`, `idevice_id`) | no device to reach |

What you actually need: **Python, OpenCV, NumPy.** That is the whole list.

*(Verified: the comparison was run end to end in an environment containing only
those two packages.)*

---

## Install

```bash
git clone git@github.com:Shahab-N-PF/Spider-Solitaire-Automation.git
cd Spider-Solitaire-Automation

python3 -m venv .venv
./.venv/bin/pip install "opencv-contrib-python==4.6.0.66" "numpy==1.26.4"
```

Those versions are the ones this was tested against, on **Python 3.9.6**. Newer ones
will very likely work; pin these if you hit trouble.

> Running `./scripts/setup.sh` instead also works. It just installs more than you need.

**Disk:** the clone is about **800 MB** — 420 MB of screenshots plus 380 MB of git
data. Almost all of it is the committed baselines, and there is no way to trim it:
`git clone --depth 1` makes no difference (measured — still 803 MB), because the size
is the current screenshots themselves, not accumulated history.

---

## Try it in one command

The iPad comparison is the one that works immediately, because both sides of it are
committed. Nothing to capture, nothing to configure:

```bash
./.venv/bin/python tests/compare_unity_ipad.py
```

You should see a table of screens with a percentage each, and diff images written to
`log/`. That is the tool working. Open one:

```bash
open log/diff_ipad_MainMenu.png
```

---

## The idea in one paragraph

There are two sets of screenshots. **Baselines** are the reference — how it is
supposed to look. **Captures** are the build under test. The tool lines them up by
filename, compares them pixel by pixel, and reports the fraction that differ. Because
some pixels legitimately change every run (a clock, an advert, an animation), you can
mask regions out. What is left is real difference.

In this repo the baselines are the **Objective-C** build of Spider Solitaire, and the
captures are the **Unity** port. But nothing in the maths cares about that. It works
for any two sets of same-size screenshots.

---

## The five comparison tools

| Command | Compares | Works on a fresh clone? |
|---|---|---|
| `tests/compare_unity_ipad.py` | iPad, 1620×2160 | **Yes** — both sides committed |
| `tests/compare_unity_ip7.py` | iPhone 7 portrait, 750×1334 | No — needs captures in `log/ip7_unity/` |
| `tests/compare_unity_ip7_landscape.py` | iPhone 7 landscape, 1334×750 | No — needs `log/ip7_landscape_unity/` |
| `tests/compare_unity_ip14.py` | iPhone 14 Pro Max, 1290×2796 | No — needs `log/ip14_unity/` |
| `tests/compare_unity.py` | iPhone 11, 828×1792 | **No — this one drives a phone.** Not for you |

The first four are pure file comparison. **The last one is different**: it navigates the
app on a real device to take its own screenshots, so it needs the full setup. Ignore it.

The baselines for every device are committed. The captures mostly are not — they came
off a phone and live in git-ignored `log/`. Run a tool with nothing captured and it
tells you so and exits **2**, rather than pretending.

---

## Reading the output

```
  Play.png                    17.21% differ  <-- large
  StatsPage.png               10.32% differ  <-- large
  HelpPage.png                 0.12% differ
```

- **The percentage** is of *compared* pixels — masked-out areas are not counted.
- **`<-- large`** means that screen went over its own allowed threshold. Each screen
  has its own, because a busy screen and a plain one deserve different limits.
- **Exit code** is `0` when it ran, `2` when there was nothing to compare. It does
  **not** go non-zero just because diffs are large — read the table.

Every screen also writes `log/diff_<device>_<name>.png`, which is the useful part:

- **Left half** = the baseline. **Right half** = the capture.
- **Red pixels** = differ. **Yellow boxes** = grouped around each cluster, so you can
  find them at a glance.
- **Dimmed areas** = masked out and not counted.

---

## Using it on your own screenshots

Say you have two builds of something else entirely.

**1. Both sets must be the same pixel size.** A mismatched pair is reported as
`[size]` and not compared — screenshots are never rescaled to fit, because that would
invent differences that are not in the build. Same device, same orientation.

Each screen ends up with one of four outcomes: `ok` (compared), `no-capture` (the
build-under-test image is missing), `no-baseline` (the reference is missing), or
`size`. If *nothing* was compared the tool exits **2** and names which of those three
problems it was.

**2. Filenames must match exactly.** `MainMenu.png` is compared with `MainMenu.png`.
The names are how the pairing happens.

**3. Put them where a tool expects them.** Easiest is to copy an existing tool and
change two lines at the top:

```python
UNITY_DIR = os.path.join(config.LOG, "my_captures")   # the build under test
BASE_DIR  = os.path.join(config.ROOT, "my_baselines") # the reference
```

**4. List your screens.** Further down is a `SPECS` block — one entry per screen:

```python
SPECS = {
    "MainMenu.png":  {"ignore": [],                "max_diff": 0.010},
    "StatsPage.png": {"ignore": [STATS_VALUES],    "max_diff": 0.005},
}
```

`max_diff` is the fraction allowed before it is flagged — `0.010` is 1%.

**5. Delete the `META` block** or empty it. That is curated commentary about *this*
project's findings and will be nonsense for yours.

[tests/compare_unity_ipad.py](tests/compare_unity_ipad.py) is the cleanest one to copy
— **188 lines, of which the first 111 are just this configuration**. The actual
comparison underneath is short, because the work happens in `visual.py`.

---

## Making the numbers mean something

**Your first run will over-report.** Everyone's does. A clock, a rotating advert or a
sparkle animation will show as differences, and a screen can read 20% when nothing is
actually wrong. Three ways to exclude them, in order of preference:

**1. Fixed chrome — `COMMON_IGNORE`.** Regions excluded on *every* screen, given as
`(x0, y0, x1, y1)` in pixels. Status bar, advert banner, debug overlays:

```python
STATUS_BAR    = (0, 0, W, 44)
BOTTOM_BANNER = (0, 1160, W, H)
COMMON_IGNORE = [STATUS_BAR, BOTTOM_BANNER]
```

**2. Per-screen regions — the `ignore` list.** For things that change on one screen
only: a randomly dealt card layout, changing statistics numbers.

**3. A learned volatile mask — for animation.** When something flickers and you cannot
draw a neat box around it, let the tool find it. Take **two or more screenshots of the
same screen from the same build**, then:

```python
import cv2, visual
mask = visual.build_volatile_mask(["shot1.png", "shot2.png", "shot3.png"])
cv2.imwrite("my_baselines/MainMenu.volatile.png", mask)
```

Any pixel that moved between those shots is excluded from then on. Three shots is
usually enough.

> **Volatile masks are not wired into every tool.** `visual.py` (the iPhone 11 path)
> and `compare_unity_ip14.py` load them. The iPhone 7 and iPad tools do not — they
> just note animated areas in their commentary. If you copy one of those and want
> volatile masks, copy `_load_volatile()` from `compare_unity_ip14.py`.

**Tune until a screen you believe is unchanged reads near zero.** Then the numbers on
the other screens mean something.

---

## The one rule

**Never make a big difference go away by re-capturing the baselines.**

The baselines are the reference. A large difference is the **finding** — it is the
tool doing its job. If you overwrite the baselines with the new build, both sides
become the new build, everything reads 0%, and you have destroyed the only copy of
what you were measuring against.

When a number looks wrong, the fix is a mask, a threshold, or a real bug in the build.
Never the baselines.

---

## The HTML report (optional)

Add `--report` and you get a single self-contained page — every screen side by side,
a slider to wipe between them, and a build switcher:

```bash
./.venv/bin/python tests/compare_unity_ipad.py --report
```

It writes into `reports/`. Be aware it **overwrites the committed report** for that
device, and the written findings in it are specific to this project.

Existing reports are already in [reports/](reports/) if you just want to see what the
output looks like — open one in a browser, no setup at all.

---

## When you would need a phone after all

Only for one thing: **taking the screenshots of the build under test**. The comparison
never needs a device; getting the captures does.

If someone hands you the screenshots, you never need a phone. If you must take them
yourself, that is the full setup — see [SETUP.md](SETUP.md), and the *Capturing the
Unity screenshots* section for how each device is handled.

---

## What to look at, and what to ignore

**Worth reading:**

| File | What it is |
|---|---|
| [visual.py](visual.py) | the comparison engine — masking, diffing, volatile masks, diff images |
| [tests/compare_unity_ipad.py](tests/compare_unity_ipad.py) | the clearest example to copy |
| [config.py](config.py) | paths only; everything is overridable by environment variable |
| [scripts/gen_versioned_report.py](scripts/gen_versioned_report.py) | the HTML report builder |

**Safe to ignore completely** — this is the functional automation:
`unity_ui.py`, `flows.py`, `helpers.py`, `driver.py`, `tests/verify*.py`,
`tests/run_all.py`, `wda/`, `scripts/wda.sh`, `assets/`, `assets_unity/`.
