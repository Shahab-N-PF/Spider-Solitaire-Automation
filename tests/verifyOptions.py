#!/usr/bin/env python3
"""Test: four named Options controls actually work, and end at fixed values. [UNITY]

Options carries two kinds of control, and this drives two of each:

    Applause Volume    slider   Sounds       a track whose knob is dragged
    Auto Mute Sounds   toggle   Sounds       a pill whose knob sits left/right
    Card Lowering      slider   Interface
    Use Hearts         toggle   Interface

Unity publishes no accessibility state, so a control's setting cannot be read as
a boolean or a number. It can be read off the screen: the knob's position IS the
setting (unity_ui.opt_knob). That turns the assertion from the weak "something
changed after I tapped" into the real "it was ON, I tapped it, it is now OFF,
I tapped again and it is ON" — which a dead control, a passing animation or an
interstitial ad cannot satisfy.

Both toggle directions are covered by driving one row that ships ON (Auto Mute
Sounds) and one that ships OFF (Use Hearts). Each slider is driven to both ends
and to mid-track.

**The test always leaves these four at the values in TARGETS** — including when
it fails partway, which is when it matters: every check ends in an assertion
that raises, and without the reset a failed run would strand a toggle flipped or
a slider at maximum, for the next test and the next run to inherit. Fixed
targets rather than "put back what was there" also means every run *starts* from
a known state.

Note the "-" and "+" beside a slider are LABELS marking the ends of the track,
not buttons — see unity_ui's Options section for the measurement behind that.
The row's own caption agrees: "Move slider to change the volume".

Captures log/OptionsPage.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/verifyOptions.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402

MID = 0.5           # "~mid" for both sliders
# How close to a fixed slider target counts as arrived. It is 0.08 rather than
# something tighter because that is the resolution a synthetic swipe HAS on
# these sliders: a drag asking for less than ~0.06 of the track does not
# register as a drag at all, so the knob can be left up to about one such step
# from any target and no further gesture can close the gap. See
# unity_ui.SLIDER_MIN_DRAG for the measurement. The ends are exempt from this —
# both sliders hit 0.00 and 1.00 exactly, which is what check_slider asserts.
MID_TOL = 0.08

# The rows this test drives, and the value each is left at. Listed in PAGE
# ORDER, which is what keeps the run cheap: ui.opt_row() has to rewind to the
# top of the page whenever a row has already scrolled past, so working downwards
# means one sweep and no rewinds.
TARGETS = (
    ("opt_applause",      "slider", "Applause Volume",  MID),
    ("opt_auto_mute",     "toggle", "Auto Mute Sounds", True),     # ON
    ("opt_card_lowering", "slider", "Card Lowering",    MID),
    ("opt_use_hearts",    "toggle", "Use Hearts",       False),    # OFF
)


def run():
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    open_options("tapping Options did not open the Options screen "
                 "('options' title not found)")
    ui.expect(not ui.on_menu(timeout=1.0), "tapping Options did not leave the main menu")
    shot = ui.shoot("OptionsPage")

    # The support entry point lives in this screen's top bar.
    ui.expect(ui.is_on("contact_us"), "the 'Contact Us' button is missing from Options")

    ok = False
    try:
        # Applause Volume first, and its persistence check with it: both want the
        # page at the top, and reopening Options lands there anyway.
        check_slider("opt_applause", "Applause Volume")
        check_persists("opt_applause", "Applause Volume")
        check_toggle("opt_auto_mute", "Auto Mute Sounds")
        check_slider("opt_card_lowering", "Card Lowering")
        check_toggle("opt_use_hearts", "Use Hearts")
        ok = True
    finally:
        stuck = reset()

    # Only reached when the checks passed — if one raised, the exception is
    # already on its way out of the finally above and reset()'s warning stands on
    # its own rather than replacing the real failure.
    ui.expect(not stuck,
              "these Options controls could not be set to their end value: "
              + ", ".join(stuck))
    ui.expect(ok, "the Options checks did not complete")

    ui.expect(ui.to_menu(), "could not return to the main menu after Options")
    print(f"PASS: Options opened; both toggles flip and report their state, both "
          f"sliders drive end to end, the value survives leaving the screen, and "
          f"all four were left at {_targets_text()} (see {shot})")


def open_options(why: str):
    """Menu -> Options, asserting it landed. Used on entry and by reset()."""
    ui.expect(ui.tap("menu_options", settle=2.5), "Options control not found on the menu")
    ui.expect(ui.at_screen("options"), why)


def check_toggle(label, human):
    """Flip a toggle, read the new state, flip it back."""
    before = ui.toggle_state(label)
    ui.expect(before is not None,
              f"could not read the '{human}' toggle — its knob was not found")

    after = ui.tap_toggle(label)
    ui.expect(after is not None, f"the '{human}' toggle vanished after being tapped")
    ui.expect(after != before,
              f"tapping the '{human}' toggle left it {_s(before)} — the control is dead")

    back = ui.tap_toggle(label)
    ui.expect(back == before,
              f"the '{human}' toggle would not go back to {_s(before)} "
              f"(it is {_s(back)}) — it flips one way only")
    print(f"  toggle '{human}': {_s(before)} -> {_s(after)} -> {_s(back)}")


def check_slider(label, human):
    """Drive a slider to both ends and then to mid-track.

    It deliberately does NOT put the value back where it was found — the run
    ends with reset(), which drives it to a fixed target instead. Ending on
    mid-track means that reset is usually already satisfied.
    """
    start = ui.slider_value(label)
    ui.expect(start is not None,
              f"could not read the '{human}' slider — its knob was not found")

    lo = ui.slider_drag(label, 0.0)
    ui.expect(lo is not None and lo <= 0.02,
              f"dragging the '{human}' slider to the left end left it at {lo} — "
              f"it does not reach its minimum")

    hi = ui.slider_drag(label, 1.0)
    ui.expect(hi is not None and hi >= 0.98,
              f"dragging the '{human}' slider to the right end left it at {hi} — "
              f"it does not reach its maximum")

    mid = ui.slider_set(label, MID)
    ui.expect(mid is not None and 0.2 < mid < 0.8,
              f"dragging the '{human}' slider to mid-track left it at {mid} — "
              f"it only snaps to the ends")
    print(f"  slider '{human}': {start:.2f} -> min {lo:.2f} -> max {hi:.2f} "
          f"-> mid {mid:.2f}")


def check_persists(label, human):
    """A changed value survives leaving Options and coming back.

    Cheap, and it is the check that says the setting was actually *applied*
    rather than only drawn: a knob that moves but writes nothing would pass
    every assertion above and fail this one.

    Scope note — this is persistence WITHIN a session. Whether a setting
    survives the app being killed is a separate question with a trap in it; see
    unity_ui's Options section, which records the measurement.
    """
    start = ui.slider_value(label)
    target = 0.20 if start > 0.5 else 0.80
    ui.slider_set(label, target)
    was = ui.slider_value(label)

    ui.expect(ui.to_menu(), "could not leave Options to check the setting stuck")
    open_options("reopening Options did not land on Options")
    ui.opt_top()

    now = ui.slider_value(label)
    ui.expect(now is not None and abs(now - was) <= 0.05,
              f"the '{human}' slider was left at {was:.2f} but reads {now} after "
              f"leaving Options and coming back — the setting is not being kept")
    print(f"  '{human}' kept {was:.2f} across leaving and reopening Options")


def reset():
    """Put all four controls at their TARGETS value. Returns the ones that stuck.

    Runs from a `finally`, so it must not raise: on a failed run the exception
    already travelling outwards is the useful one, and a reset that blew up
    would replace it with something unrelated. Anything it cannot do it names on
    stdout and returns; the caller decides whether that matters.

    Because the targets are constants rather than values captured earlier, this
    works even when the run died before a control was ever read.
    """
    try:
        if not ui.at_screen("options", timeout=2.0):
            # A run can fail anywhere, including back on the menu. Getting to
            # Options is worth one try — the whole point is that the settings
            # are normalised however the run ended.
            if not (ui.to_menu() and ui.tap("menu_options", settle=2.5)
                    and ui.at_screen("options", timeout=2.0)):
                print("  WARNING: could not reach Options to reset the controls — "
                      "they are left as the run ended")
                return [t[2] for t in TARGETS]
        ui.opt_top()
    except Exception as e:  # noqa: BLE001
        print(f"  WARNING: could not reach Options to reset the controls ({e})")
        return [t[2] for t in TARGETS]

    stuck, left = [], []
    for label, kind, human, want in TARGETS:
        try:
            now = ui.opt_get(label, kind)
            if not _at(kind, now, want):
                now = ui.opt_put(label, kind, want)
            if _at(kind, now, want):
                left.append(f"{human}={_v(kind, now)}")
            else:
                stuck.append(f"{human} (wanted {_v(kind, want)}, reads {_v(kind, now)})")
        except Exception as e:  # noqa: BLE001
            stuck.append(f"{human} ({e})")
    if left:
        print(f"  reset: {', '.join(left)}")
    for s in stuck:
        print(f"  WARNING: could not reset {s}")
    return stuck


def _at(kind, now, want) -> bool:
    """Is `now` at `want`? Exact for a toggle, within tolerance for a slider."""
    if now is None:
        return False
    return now == want if kind == "toggle" else abs(now - want) <= MID_TOL


def _v(kind, value) -> str:
    if value is None:
        return "unreadable"
    return _s(value) if kind == "toggle" else f"{value:.2f}"


def _targets_text() -> str:
    return ", ".join(f"{human} {_v(kind, want)}"
                     for _l, kind, human, want in TARGETS)


def _s(state):
    return {True: "ON", False: "OFF"}.get(state, str(state))


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
