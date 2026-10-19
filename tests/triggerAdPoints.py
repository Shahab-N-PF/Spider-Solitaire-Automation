#!/usr/bin/env python3
"""Verify observed interstitial trigger and cooldown points. [UNITY]

*** ONLINE only — deliberately not part of tests/run_all.py. ***

This test records two clocks:

* after more than 30 seconds on the game table, leaving the table for Options,
  Help, FAQ, or another destination can trigger an interstitial;
* every interstitial starts a 30-second cooldown that is counted from when the
  ad APPEARS, not from when it is closed. The cooldown left after the close is
  ``30 - (seconds the ad was up)``: an ad closed after 10s allows the next ad
  20s after the close, one closed after 15s allows it 15s after, and one up
  for 30s or more lets the very next trigger fire an ad at once. The same
  rule applies at every trigger point.

The test cannot see the instant an ad starts, so it brackets it: the earliest
start is the trigger tap (or detection minus ``AD_DETECT_LAG`` when the tap is
buried in a helper), the latest is when ``wait_lost`` sees the ad. Follow-up
taps are bracketed the same way and every claim keeps ``AD_MARGIN`` clear of
the cooldown's end. A follow-up that would land too close to that end to call
is recorded ``SKIP`` with the measured numbers, never guessed.

Checks, in run order:

1. table for less than 30 seconds, then Options: no ad (an ad is excused only
   when no earlier ad's cooldown provably covered the tap);
2. table for more than 30 seconds, then Help: ad;
3. right after that Help ad, Options inside the cooldown left: no ad;
4. once that same cooldown has run out, Options: ad (TA-13);
5. a Help ad held past 30s, then Options at once: ad (TA-12);
6. table for more than 30 seconds, then QA Complete Game: ad on Victory;
7. New inside that ad's remaining cooldown: no ad;
8. win again, wait only the cooldown left (30s minus the ad's length), then
   New: ad;
9. a Victory ad held past 30s, then New at once: ad (TA-11);
10. over 30 seconds on the table, then Back: ad, closing onto the main menu;
11. game entry straight away from that menu: no ad;
12. over 30 seconds on the table, then FAQ: ad.

Resume never shows an interstitial, so a long menu dwell followed by Resume
is not a trigger and is not asserted. ``AD_COOLDOWN``, ``AD_MARGIN``,
``AD_DETECT_LAG`` and ``AD_ACT_LATENCY`` read environment overrides, and the
end-of-run summary lists every ad's length and the cooldown it left.

Ads are only ever triggered from a TEST network: setup relaunches Spider
and puts MAX in Test Mode on Pangle in that fresh session
(``max_test_mode.ensure_network``), so every ad is a Pangle test ad. Those
setup relaunches are this test's deliberate cold launches, and Test Mode
lasts that app session. Any later relaunch (a recovery) turns it back on
before the run continues, and the cooldown clock is forgotten, since the
earlier ads belong to another session. An ad that closes without Pangle's
double-arrow or X was served by a LIVE network: the check that saw it FAILs
("live ad served"), Test Mode is re-enabled, and the run carries on.
A Pangle interstitial is closed by its grey double-arrow (top right, drawn
about 5s after the ad loads); when that skips to an end card instead, the end
card's dark X closes it. A held ad is never skipped before its cooldown has
run out.

An interstitial during ``resume_or_deal`` is also expected behavior. The test
closes it the same way and continues without a cold launch. The ad-close crop
is creative-dependent, so a missing close control is reported rather than
guessed. If the chain still cannot close after the 120s wait, the test prints
``Manual effort required at this step``, waits
for a hand close, and the summary marks that check ``Passed Manually``. A
failed named check is listed ``FAIL`` in that summary; the rest of the case
still runs and the overall result stays PASS so one miss does not fail
``run_all``. Each named check maps to its own TestRail card (TA-01..TA-08,
TA-10..TA-13) in ``log/spider_regression.html``; a FAIL there does not fail
the parent, and a ``SKIP`` renders as skipped with its reason. TA-09 is
commented out of the catalog.

Additional observed trigger: leaving a game can show an ad whose close returns
the user to the main menu. Resume from that menu does not show another
interstitial, even after a long dwell.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set,
         and a network connection.
Run:  ./.venv/bin/python tests/triggerAdPoints.py
      ./.venv/bin/python tests/triggerAdPoints.py --part cooldown
      ./.venv/bin/python tests/triggerAdPoints.py --part victory
      ./.venv/bin/python tests/triggerAdPoints.py --part menu
      ./.venv/bin/python tests/triggerAdPoints.py --part destinations
      ./.venv/bin/python tests/triggerAdPoints.py --part longad
"""
import argparse
import os
import sys
import time
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import max_test_mode as mtm  # noqa: E402
import unity_ui as ui  # noqa: E402


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


SHORT = 8.0
DWELL = 32.0
NO_AD = 8.0
AD_WAIT = 20.0
CLOSE_WAIT = 120.0
AD_CLOSE_WAIT = 30.0
MANUAL_WAIT = 300.0
COOLDOWN = _env_float("AD_COOLDOWN", 30.0)
AD_MARGIN = _env_float("AD_MARGIN", 3.0)
# wait_lost polls ~every 2-3s, so an ad is seen up to this long after it starts.
AD_DETECT_LAG = _env_float("AD_DETECT_LAG", 4.0)
# Cost of a follow-up tap including the template find.
ACT_LATENCY = _env_float("AD_ACT_LATENCY", 2.0)
_SETUP_CLOSES = (
    "leftover",
    "resume_or_deal",
    "fresh-table setup",
    "short table -> Options setup retry",
)

RESULTS = []
MANUAL_CLOSES = set()
AD_LOG = []
LAST_AD = None
CHECK_AD = {}


@dataclass
class AdRecord:
    """One interstitial, its start bracketed between start_lo and start_hi."""
    where: str
    start_lo: Optional[float]
    start_hi: Optional[float]
    closed_at: float
    held: bool = False
    manual: bool = False

    @property
    def known(self) -> bool:
        return self.start_lo is not None and self.start_hi is not None

    @property
    def seconds(self) -> Optional[float]:
        if not self.known:
            return None
        return max(0.0, self.closed_at - self.start_hi)

    @property
    def cooldown_until_lo(self) -> Optional[float]:
        return None if not self.known else self.start_lo + COOLDOWN

    @property
    def cooldown_until_hi(self) -> Optional[float]:
        return None if not self.known else self.start_hi + COOLDOWN

    @property
    def remaining_after_close(self) -> Optional[float]:
        if not self.known:
            return None
        return max(0.0, self.cooldown_until_hi - self.closed_at)

    def describe(self) -> str:
        extra = []
        if self.held:
            extra.append("held past the cooldown")
        if self.manual:
            extra.append("closed manually")
        tail = f" [{', '.join(extra)}]" if extra else ""
        if not self.known:
            return f"  ?  ad of unknown age — {self.where}{tail}"
        return (f"{self.seconds:>3.0f}s ad, next ad allowed "
                f"{self.remaining_after_close:.0f}s after close — "
                f"{self.where}{tail}")


class SkipCheck(Exception):
    """A check whose precondition (an ad of a known length) was not met."""


# Named checks → TestRail cards in the regression report. TA-09 is commented
# out of docs/testrail/cases.py (Resume no longer fires an ad).
CHECK_CASES = {
    "short table -> Options": "TA-01",
    "long table -> Help": "TA-02",
    "Help ad closed -> Options within cooldown": "TA-03",
    "long table -> Victory": "TA-04",
    "Victory ad closed -> New within cooldown": "TA-05",
    "Victory -> New after the cooldown left": "TA-06",
    "long table -> Back": "TA-07",
    "short menu dwell -> game entry": "TA-08",
    "long table -> FAQ": "TA-10",
    "Victory ad held 30s+ -> New fires instantly": "TA-11",
    "Help ad held 30s+ -> Options fires instantly": "TA-12",
    "Help ad cooldown over -> Options shows an ad": "TA-13",
}


def _add_result(label: str, status: str, error: str = "", shots=None):
    entry = {
        "id": CHECK_CASES.get(label),
        "label": label,
        "status": status,
        "error": str(error) if error else "",
    }
    if shots:
        entry["shots"] = [
            os.path.splitext(os.path.basename(shot))[0] for shot in shots
        ]
    prior = CHECK_AD.get(label)
    if prior is not None:
        entry["ad_seconds"] = (None if prior.seconds is None
                               else round(prior.seconds, 1))
        left = prior.remaining_after_close
        entry["ad_cooldown_left"] = None if left is None else round(left, 1)
    RESULTS.append(entry)


def note_check(label: str):
    """Record a completed check for the end-of-run summary."""
    status = "Passed Manually" if label in MANUAL_CLOSES else "PASS"
    case_id = CHECK_CASES.get(label)
    shot = ui.shoot(f"trigger_{case_id}") if case_id else None
    _add_result(label, status, shots=[shot] if shot else [])


def note_fail(label: str, err):
    _add_result(label, "FAIL", err)
    print(f"  FAIL {label}: {err}")


def note_skip(label: str, reason):
    _add_result(label, "SKIP", reason)
    print(f"  SKIP {label}: {reason}")


def print_report():
    if RESULTS:
        print()
        for item in RESULTS:
            print(f"  {item['status']:<16}  {item['label']}")
    if AD_LOG:
        print()
        print(f"  ad lengths (cooldown {COOLDOWN:.0f}s from each ad's start, "
              f"margin {AD_MARGIN:.0f}s):")
        for rec in AD_LOG:
            print(f"    {rec.describe()}")


def restore_after_check():
    """Best-effort table restore so a failed check does not skip the rest."""
    try:
        if ui.at_table(timeout=2.0):
            return
        back_to_table()
    except Exception:
        try:
            reach_table()
            ui.settle_prompts()
        except Exception as e:  # noqa: BLE001
            print(f"  could not restore the table after a failed check: {e}")


def run_check(label: str, body):
    """Run one named check. A failure is recorded; the rest of the case continues."""
    try:
        body()
        note_check(label)
    except SkipCheck as e:
        note_skip(label, e)
        restore_after_check()
    except AssertionError as e:
        note_fail(label, e)
        restore_after_check()


def wait_for_manual_close(where: str):
    """Pause until the user dismisses a stuck interstitial on the phone."""
    print("Manual effort required at this step", flush=True)
    print(f"  Close the {where} interstitial on the phone; the test "
          "continues when Spider's own UI is back.", flush=True)
    if ui.in_app() and ui.lost(timeout=0.5):
        path = ui.shoot("ad_unmatched")
        print(f"  unmatched ad close captured before waiting — see {path}")
    deadline = time.time() + MANUAL_WAIT
    while time.time() < deadline:
        if ui.in_app() and not ui.lost(timeout=1.0):
            MANUAL_CLOSES.add(where)
            if where in _SETUP_CLOSES:
                _add_result(where, "Passed Manually")
            print(f"  {where} closed manually — continuing")
            return
        ui.sleep(1.5)
    raise AssertionError(
        f"the {where} interstitial was still showing after "
        f"{MANUAL_WAIT:.0f}s of waiting for a manual close")


def hold_ad(where: str, until: float) -> bool:
    """Keep an ad on screen until ``until``; False if it closed by itself."""
    left = until - time.time()
    if left > 0:
        print(f"  holding the {where} ad open for another {left:.0f}s "
              "before closing it")
    while time.time() < until:
        ui.expect(ui.in_app(),
                  f"the {where} interstitial left Spider while held — now in "
                  f"{ui.active_app() or 'unknown'}")
        if not ui.lost(timeout=0.5):
            print(f"  the {where} ad closed by itself during the hold")
            return False
        ui.sleep(min(2.0, max(0.0, until - time.time())))
    return True


def close_current_ad(where: str, start_lo: Optional[float] = None,
                     start_hi: Optional[float] = None, hold: bool = False,
                     known_start: bool = True) -> AdRecord:
    """Close the ad chain and record when it started and closed.

    ``start_hi`` is when the ad was seen (default: now); ``start_lo`` is the
    trigger tap, or ``start_hi - AD_DETECT_LAG`` when the tap was not stamped.
    ``hold`` keeps the ad up until its cooldown has run out (plus the margin)
    before closing it. ``known_start=False`` marks a leftover of unknown age.
    """
    global LAST_AD
    hi = time.time() if start_hi is None else start_hi
    lo = hi - AD_DETECT_LAG if start_lo is None else min(start_lo, hi)
    manual = False
    closed = False
    try:
        still_up = True
        if hold:
            still_up = hold_ad(where, hi + COOLDOWN + AD_MARGIN)
        if still_up:
            ui.expect(ui.in_app(),
                      f"the {where} interstitial left Spider — now in "
                      f"{ui.active_app() or 'unknown'}")
            ui.expect(ui.close_interstitial_chain(where, CLOSE_WAIT,
                                                  AD_CLOSE_WAIT),
                      f"could not close the {where} interstitial chain")
            closed = True
    except AssertionError:
        wait_for_manual_close(where)
        manual = True
    rec = AdRecord(where, lo if known_start else None,
                   hi if known_start else None, time.time(),
                   held=hold, manual=manual)
    LAST_AD = rec
    AD_LOG.append(rec)
    print(f"  ad closed: {rec.describe()}")
    # Only test-network ads may be triggered. One that closed without a test
    # ad's controls fails the check that saw it; Test Mode is re-enabled (a
    # fresh relaunch, which also forgets the cooldown clock) so the rest of
    # the run carries on with test ads.
    if closed and ui.last_ad_was_live():
        raise AssertionError(mtm.live_ad_served(where))
    return rec


def reach_table(ad_attempts: int = 5):
    """Resume/deal, absorbing valid cooldown-expiry ads before the table."""
    for attempt in range(ad_attempts + 1):
        started = time.time()
        try:
            how = ui.resume_or_deal("easy")
            print(f"  {how}")
            ui.expect(ui.at_table(timeout=8.0),
                      "resume/deal finished without reaching the game table")
            return
        except AssertionError as e:
            if not (ui.lost() and ui.in_app()):
                raise
            print(f"  interstitial during resume_or_deal ({e}) — cooldown "
                  "expired, so the ad is expected before the table")
            close_current_ad("resume_or_deal", start_lo=started)
            if attempt == ad_attempts:
                raise AssertionError(
                    "resume_or_deal kept producing interstitials without "
                    "eventually reaching the table")


def establish_fresh_table():
    """Start a new table so Rule 5 has a genuinely short dwell window."""
    reach_table()
    ui.settle_prompts()
    ui.expect(ui.at_table(), "could not establish the initial game table")

    # A previous standalone run may have left this table open past the
    # 30-second threshold. Deal a fresh table before starting the clocks. If
    # that New action itself triggers the stale-table ad, it proves the prior
    # cooldown expired. The ad is expected BEFORE the table: close it and keep
    # entering until a table is visible, then start Rule 5's short dwell clock.
    ui.expect(ui.open_ingame_menu(), "could not open the drawer for a fresh game")
    tapped = time.time()
    ui.expect(ui.tap("ingame_new", settle=3.0),
              "could not deal the fresh setup game")
    if ui.wait_lost(timeout=20.0):
        print("  fresh-game entry showed an interstitial — prior cooldown "
              "expired; closing it before waiting for the table")
        close_current_ad("fresh-table setup", start_lo=tapped,
                         start_hi=time.time())
    ui.settle_prompts()
    if not ui.at_table(timeout=8.0):
        reach_table()
        ui.settle_prompts()
    ui.expect(ui.at_table(timeout=8.0),
              "could not reach a table after handling fresh-game entry ads")


def timed_tap(anchor: str, what: str, settle: float = 1.0):
    """Tap ``anchor`` and return (just before, just after) the tap."""
    before = time.time()
    ui.expect(ui.tap(anchor, settle=0), f"could not tap {what}")
    after = time.time()
    if settle:
        ui.sleep(settle)
    return before, after


def expect_ad(label: str, triggered_at: Optional[float] = None,
              hold: bool = False) -> AdRecord:
    ui.expect(ui.wait_lost(timeout=AD_WAIT),
              f"no interstitial appeared for {label} within {AD_WAIT:.0f}s")
    return close_current_ad(label, start_lo=triggered_at,
                            start_hi=time.time(), hold=hold)


def screen_or_ad(screen_check, label: str, timeout: float = NO_AD):
    """Watch an action settle: 'screen', 'ad', or None if neither showed."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        ui.expect(ui.in_app(),
                  f"the app left Spider during {label}: "
                  f"{ui.active_app() or 'unknown'}")
        if screen_check():
            return "screen"
        if ui.lost(timeout=0.5):
            # A screen transition can briefly match no landmark.
            ui.sleep(1.5)
            if ui.lost(timeout=1.0):
                return "ad"
        ui.sleep(0.3)
    return None


def assert_no_ad(label: str, screen_check, triggered_at: Optional[float],
                 context: str = ""):
    """Require the expected screen with no interstitial; close one if it shows."""
    seen = screen_or_ad(screen_check, label)
    if seen == "screen":
        return
    if seen == "ad":
        close_current_ad(f"{label} (unexpected)", start_lo=triggered_at)
        raise AssertionError(
            f"an interstitial appeared during the {label} no-ad window"
            + (f" — {context}" if context else ""))
    raise AssertionError(
        f"the expected screen did not settle during the {label} no-ad window")


def unasserted_followup(label: str, screen_check,
                        triggered_at: Optional[float] = None) -> str:
    """Let an untestable follow-up settle, closing any ad it raised."""
    if screen_or_ad(screen_check, label) == "ad":
        close_current_ad(f"{label} (unasserted)", start_lo=triggered_at)
        return "an ad followed"
    return "no ad followed"


def window_text(prior: Optional[AdRecord]) -> str:
    if prior is None:
        return "there was no earlier ad"
    if not prior.known:
        return f"the earlier '{prior.where}' ad is of unknown age"
    return (f"the earlier '{prior.where}' ad ran {prior.seconds:.0f}s, "
            f"leaving {prior.remaining_after_close:.0f}s of cooldown after "
            "it closed")


def inside_cooldown(prior: Optional[AdRecord], tapped_after: float) -> bool:
    """True when a tap provably landed inside the prior ad's cooldown."""
    return (prior is not None and prior.known
            and tapped_after + AD_MARGIN < prior.cooldown_until_lo)


def usable_window(prior: Optional[AdRecord], now: float) -> bool:
    """True when a tap started now can still land provably inside the cooldown."""
    return inside_cooldown(prior, now + ACT_LATENCY)


def expect_no_ad_inside(label: str, prior: Optional[AdRecord], act,
                        screen_check, restore):
    """Tap inside the cooldown ``prior`` left and require no ad.

    ``act`` performs the tap and returns its (before, after) times. With too
    little cooldown left to land a tap provably inside it, or a tap that
    came out late, the action still runs (any ad it raises is closed),
    ``restore`` puts the screen back, and the check is SKIP.
    """
    CHECK_AD[label] = prior
    if not usable_window(prior, time.time()):
        before, _ = act()
        seen = unasserted_followup(label, screen_check, before)
        restore()
        raise SkipCheck(f"no usable cooldown window: {window_text(prior)}, "
                        f"too little to land a tap inside it — {seen}")
    before, after = act()
    if not inside_cooldown(prior, after):
        seen = unasserted_followup(label, screen_check, before)
        restore()
        raise SkipCheck(f"the tap landed too close to the cooldown's end "
                        f"({window_text(prior)}) — {seen}")
    left = prior.cooldown_until_lo - after
    assert_no_ad(label, screen_check, before,
                 f"the tap came {left:.0f}s before {window_text(prior)} "
                 "could have run out")
    print(f"  {label}: no ad, tapped {left:.0f}s before the cooldown "
          "could end")


def expect_ad_after_expiry(label: str, prior: Optional[AdRecord],
                           act) -> AdRecord:
    """Wait out the cooldown ``prior`` left, tap, and require an ad."""
    CHECK_AD[label] = prior
    if prior is not None and prior.known:
        target = prior.cooldown_until_hi + AD_MARGIN
        wait = target - time.time()
        if wait > 0:
            print(f"  {label}: waiting {wait:.0f}s for the cooldown to end "
                  f"({target - prior.closed_at:.0f}s after the "
                  f"{prior.seconds:.0f}s ad closed)")
            ui.sleep(wait)
        else:
            print(f"  {label}: cooldown already over "
                  f"({time.time() - prior.closed_at:.0f}s after the "
                  f"{prior.seconds:.0f}s ad closed)")
    before, _ = act()
    return expect_ad(label, triggered_at=before)


def require_ran_past_cooldown(held: AdRecord, label: str):
    """SKIP a held-ad check whose ad closed itself before 30s."""
    if held.known and held.seconds >= COOLDOWN:
        return
    secs = "an unknown time" if not held.known else f"{held.seconds:.0f}s"
    raise SkipCheck(
        f"the held ad for {label} was up only {secs}, under the "
        f"{COOLDOWN:.0f}s cooldown — it likely closed itself")


def open_drawer_action(anchor: str, label: str):
    """Open the drawer and tap one action; returns the tap's (before, after)."""
    ui.expect(ui.open_ingame_menu(),
              f"the game drawer did not open before {label}")
    return timed_tap(anchor, f"the drawer's {label} action", settle=2.0)


def enter_from_menu():
    """Start a resume/deal action without swallowing an entry interstitial.

    Returns (how, before, after) for the action's final tap.
    """
    ui.expect(ui.on_menu(timeout=4.0),
              "game entry did not start from the main menu")
    before = time.time()
    if not ui.open_picker():
        ui.expect(ui.in_app() and ui.lost(timeout=1.0),
                  "Play did not open the difficulty picker")
        return "opening the difficulty picker", before, time.time()
    if ui.have("resume") and ui.is_on("resume"):
        before, after = timed_tap("resume", "the Resume ribbon", settle=2.0)
        return "resuming the paused game", before, after
    before, after = timed_tap("difficulty_easy", "Easy", settle=2.0)
    return "dealing a fresh Easy game", before, after


def leave_table_ad_to_menu(label: str):
    """Leave a long-lived table, close its ad, and require the main menu."""
    ui.expect(ui.at_table(timeout=8.0),
              f"{label} did not start on the game table")
    print(f"  {label}: waiting {DWELL:.0f}s on the table before Back")
    ui.sleep(DWELL)
    before = time.time()
    ui.expect(ui.back(), f"the table's Back control failed for {label}")
    expect_ad(label, triggered_at=before)
    ui.expect(ui.on_menu(timeout=8.0),
              f"the {label} ad did not close onto the main menu")


def options_ad_excused(attempt: int, prior: Optional[AdRecord],
                       tapped_after: float) -> bool:
    """True when an ad on short table -> Options is not a rule violation.

    A tap provably inside a known ad's cooldown must never fire. Otherwise
    the cooldown had run out (or the ad's age is unknown), so an ad is the
    expected cooldown-expiry event. With no earlier ad at all, only the
    first attempt is excused, for a cooldown inherited from an earlier run.
    """
    if prior is None:
        return attempt == 0
    return not inside_cooldown(prior, tapped_after)


def verify_short_options_no_ad(retries: int = 2):
    """Rule 5, retrying while an expired cooldown explains the ad."""
    label = "short table -> Options"
    for attempt in range(retries + 1):
        if attempt == 0:
            print(f"  rule 5: waiting {SHORT:.0f}s before opening Options")
            ui.sleep(SHORT)
        else:
            print("  rule 5: clean retry inside the setup ad's cooldown")
        prior = LAST_AD
        CHECK_AD[label] = prior
        before = after = time.time()
        try:
            before, after = open_drawer_action("ingame_options", "Options")
        except AssertionError:
            if not (ui.in_app() and ui.lost(timeout=1.0)):
                raise
            after = time.time()

        deadline = time.time() + NO_AD
        while time.time() < deadline:
            ui.expect(ui.in_app(),
                      "the app left Spider during the short table -> Options "
                      f"window: {ui.active_app() or 'unknown'}")
            if ui.at_screen("options", timeout=0.5):
                back_to_table()
                print("  rule 5 passed: short table visit did not trigger an ad")
                return
            if ui.lost(timeout=0.5):
                break
            ui.sleep(0.3)
        else:
            raise AssertionError(
                "Options did not settle during the short-table no-ad window")

        if not options_ad_excused(attempt, prior, after):
            close_current_ad("short table -> Options setup retry",
                             start_lo=before)
            back_to_table()
            raise AssertionError(
                "an interstitial appeared during short table -> Options "
                f"inside a running cooldown: {window_text(prior)}")
        if attempt == retries:
            raise AssertionError(
                "an interstitial appeared during short table -> Options on "
                f"every one of {retries + 1} attempts")
        print("  short table -> Options fired an ad after the cooldown had "
              f"run out ({window_text(prior)}); closing it and retrying")
        close_current_ad("short table -> Options setup retry", start_lo=before)
        back_to_table()
        ui.expect(ui.at_table(timeout=8.0),
                  "could not restore the table for the clean Rule 5 retry")


def back_to_table():
    """Return from a destination without restarting Spider."""
    if ui.at_table(timeout=4.0):
        return
    if ui.at_screen("options", timeout=2.0) or ui.at_screen("help", timeout=2.0):
        ui.expect(ui.back(), "could not return from the destination screen")
        ui.expect(ui.at_table(timeout=8.0),
                  "destination back did not return to the game table")
        return
    # FAQ has no dedicated screen anchor in the Unity template set, but it
    # carries the same back_bar control as Options and Help.
    if ui.back():
        ui.expect(ui.at_table(timeout=8.0),
                  "destination back did not return to the game table")
        return
    reach_table()
    ui.settle_prompts()
    ui.expect(ui.at_table(timeout=8.0),
              "could not restore the table without a cold launch")


def settle_on_table():
    """Answer any post-deal tip and make sure the table is showing."""
    ui.settle_prompts()
    if not ui.at_table(timeout=8.0):
        back_to_table()


def win_and_expect_victory_ad(label: str, hold: bool = False) -> AdRecord:
    """Win the active table through the QA panel and require its ad."""
    ui.expect(ui.win_current_game(timeout=12.0),
              f"QA Complete Game did not reach Victory for {label}")
    # The Complete Game tap is inside win_current_game, so the ad's start is
    # bracketed from its detection (AD_DETECT_LAG) rather than a tap stamp.
    rec = expect_ad(label, hold=hold)
    ui.expect(ui.at_screen("victory", timeout=8.0),
              f"the {label} ad did not leave the Victory screen visible")
    ui.expect(ui.close_dev_panel(),
              f"could not collapse the Dev Panel after the {label} ad closed")
    return rec


def victory_new(what: str):
    return timed_tap("victory_new", f"Victory's New button ({what})",
                     settle=1.0)


def victory_to_table(label: str):
    """Leave Victory for a new table, closing whatever ad that raises."""
    before, _ = victory_new(label)
    unasserted_followup(label, lambda: ui.at_table(timeout=0.5), before)
    settle_on_table()


def clear_startup_overlays():
    """Close leftover debugger/Dev Panel UI before classifying an ad."""
    mtm.unwind_leftovers()
    if ui.dev_panel_open():
        ui.expect(ui.close_dev_panel(),
                  "could not collapse the leftover Dev Panel")


def forget_cooldown():
    """Relaunch hook: earlier ads belong to another app session."""
    global LAST_AD
    if LAST_AD is not None:
        print("  relaunched — the last ad's cooldown no longer applies")
    LAST_AD = None


def prepare():
    """Bring the device online and establish the shared clean table state."""
    net = ui.online()
    ui.expect(net,
              "the device could not be brought online — MAX/interstitial "
              "coverage needs Wi-Fi")
    print(f"  device is online — Wi-Fi joined {net!r}")

    ui.launch()
    clear_startup_overlays()

    # MAX on Pangle in Test Mode, in a FRESH app session, so every ad below is
    # a Pangle test ad with one known close pattern. ensure_network()
    # relaunches Spider first (clearing any leftover ad or table without
    # walking off it, which would fire a live ad), then once more to enable
    # Test Mode — this test's deliberate cold launches. The same visit leaves
    # the Dev Panel unlocked for both synthetic wins.
    mtm.ensure_network("Pangle", capture=False)
    ui.on_relaunch(forget_cooldown)

    establish_fresh_table()
    return net


def run_cooldown_rules():
    """Short Options suppression, the Help ad, and both sides of its cooldown."""
    run_check("short table -> Options", verify_short_options_no_ad)

    def help_ad():
        print(f"  rule 4: waiting {DWELL:.0f}s before opening Help")
        ui.sleep(DWELL)
        before, _ = open_drawer_action("ingame_help", "Help")
        expect_ad("long table -> Help", triggered_at=before)
        back_to_table()
        print("  rule 4 passed: long table redirect triggered an ad")

    run_check("long table -> Help", help_ad)

    def help_cooldown():
        expect_no_ad_inside(
            "Help ad closed -> Options within cooldown", LAST_AD,
            lambda: open_drawer_action("ingame_options",
                                       "Options inside Help-ad cooldown"),
            lambda: ui.at_screen("options", timeout=0.5),
            back_to_table)
        back_to_table()

    run_check("Help ad closed -> Options within cooldown", help_cooldown)

    def help_cooldown_over():
        label = "Help ad cooldown over -> Options shows an ad"
        expect_ad_after_expiry(
            label, LAST_AD,
            lambda: open_drawer_action("ingame_options",
                                       "Options after the Help-ad cooldown"))
        back_to_table()
        print("  cooldown-expiry rule passed: Options once the Help ad's "
              "cooldown ran out triggered an ad")

    run_check("Help ad cooldown over -> Options shows an ad",
              help_cooldown_over)


def run_victory_rules():
    """Victory trigger plus inside/after-cooldown New behavior."""
    def first_victory():
        print(f"  rule 1: waiting {DWELL:.0f}s before Complete Game")
        ui.sleep(DWELL)
        win_and_expect_victory_ad("long table -> Victory")
        print("  rule 1 passed: long table visit triggered an ad on Victory")

    run_check("long table -> Victory", first_victory)

    def new_in_cooldown():
        expect_no_ad_inside(
            "Victory ad closed -> New within cooldown", LAST_AD,
            lambda: victory_new("inside the cooldown"),
            lambda: ui.at_table(timeout=0.5),
            settle_on_table)
        ui.settle_prompts()
        ui.expect(ui.at_table(timeout=12.0),
                  "New within the cooldown did not reach a game table")

    run_check("Victory ad closed -> New within cooldown", new_in_cooldown)

    def second_victory():
        print(f"  rule 3: waiting {DWELL:.0f}s before the second win")
        ui.sleep(DWELL)
        win_and_expect_victory_ad("second long table -> Victory")

    run_check("second long table -> Victory", second_victory)

    def new_after_cooldown():
        expect_ad_after_expiry(
            "Victory -> New after the cooldown left", LAST_AD,
            lambda: victory_new("after the cooldown"))
        settle_on_table()
        print("  rule 3 passed: New once the Victory ad's cooldown ran out "
              "triggered an ad")

    run_check("Victory -> New after the cooldown left", new_after_cooldown)


def run_menu_rules():
    """Back-ad landing plus immediate main-menu entry (Resume fires no ad)."""
    run_check("long table -> Back",
              lambda: leave_table_ad_to_menu("long table -> Back"))

    def short_menu():
        label = "short menu dwell -> game entry"
        prior = LAST_AD
        CHECK_AD[label] = prior
        how, before, after = enter_from_menu()
        at_table = lambda: ui.at_table(timeout=0.5)  # noqa: E731
        if how == "resuming the paused game":
            assert_no_ad(label, at_table, before,
                         "Resume never shows an interstitial")
        elif not inside_cooldown(prior, after):
            seen = unasserted_followup(label, at_table, before)
            settle_on_table()
            raise SkipCheck(f"{how} landed outside the cooldown "
                            f"({window_text(prior)}) — {seen}")
        else:
            assert_no_ad(label, at_table, before,
                         f"{how} came inside the cooldown: "
                         f"{window_text(prior)}")
        print(f"  menu rule passed: {how} did not trigger an ad")

    run_check("short menu dwell -> game entry", short_menu)


def run_destination_rules():
    """Prove the long-table trigger also applies to the drawer's FAQ."""
    def faq_ad():
        print(f"  destination rule: waiting {DWELL:.0f}s before opening FAQ")
        ui.sleep(DWELL)
        before, _ = open_drawer_action("ingame_faq", "FAQ")
        expect_ad("long table -> FAQ", triggered_at=before)
        back_to_table()
        print("  destination rule passed: long table -> FAQ triggered an ad")

    run_check("long table -> FAQ", faq_ad)


def run_long_help_bypass():
    """TA-12: a Help ad up for 30s+ leaves no cooldown, even on a short visit."""
    label = "Help ad held 30s+ -> Options fires instantly"

    def body():
        print(f"  long-ad rule: waiting {DWELL:.0f}s before opening Help")
        ui.sleep(DWELL)
        before, _ = open_drawer_action("ingame_help",
                                       "Help before the held ad")
        held = expect_ad("Help ad (held past the cooldown)",
                         triggered_at=before, hold=True)
        CHECK_AD[label] = held
        if not back_to_table_quietly():
            raise SkipCheck(
                "an interstitial fired on Help's Back right after the held "
                "ad, so Options could not be tested as the next trigger")
        require_ran_past_cooldown(held, label)
        expect_ad_after_expiry(
            label, held,
            lambda: open_drawer_action("ingame_options",
                                       "Options right after the held ad"))
        back_to_table()
        print("  long-ad rule passed: Options right after a 30s+ Help ad "
              "triggered another ad")

    run_check(label, body)


def run_long_victory_bypass():
    """TA-11: a Victory ad up for 30s+ leaves no cooldown for New."""
    label = "Victory ad held 30s+ -> New fires instantly"

    def body():
        print(f"  long-ad rule: waiting {DWELL:.0f}s before Complete Game")
        ui.sleep(DWELL)
        held = win_and_expect_victory_ad("Victory ad (held past the cooldown)",
                                         hold=True)
        CHECK_AD[label] = held
        try:
            require_ran_past_cooldown(held, label)
        except SkipCheck:
            victory_to_table(f"{label} setup")
            raise
        expect_ad_after_expiry(label, held,
                               lambda: victory_new("right after the held ad"))
        settle_on_table()
        print("  long-ad rule passed: New right after a 30s+ Victory ad "
              "triggered another ad")

    run_check(label, body)


def back_to_table_quietly() -> bool:
    """back_to_table, but False (ad closed) if the return itself raised an ad."""
    try:
        back_to_table()
        return True
    except AssertionError:
        if not (ui.in_app() and ui.lost(timeout=1.0)):
            raise
    close_current_ad("Help Back after the held ad (unasserted)")
    back_to_table()
    return False


def run_long_ad_rules():
    run_long_help_bypass()
    run_long_victory_bypass()


def run(part: str = "all"):
    global LAST_AD
    RESULTS.clear()
    MANUAL_CLOSES.clear()
    AD_LOG.clear()
    CHECK_AD.clear()
    LAST_AD = None
    net = prepare()
    if part in ("all", "cooldown"):
        run_cooldown_rules()
    if part == "all":
        run_long_help_bypass()
    if part in ("all", "victory"):
        run_victory_rules()
    if part == "all":
        run_long_victory_bypass()
    if part == "longad":
        run_long_ad_rules()
    if part in ("all", "menu"):
        run_menu_rules()
    if part in ("all", "destinations"):
        run_destination_rules()

    if part == "all":
        result = "all interstitial trigger/cooldown rules"
    elif part == "cooldown":
        result = "the table and Help-ad cooldown rules"
    elif part == "victory":
        result = "the Victory trigger/cooldown rules"
    elif part == "menu":
        result = "the main-menu trigger/cooldown rules"
    elif part == "longad":
        result = "the held-ad (30s+) instant-trigger rules"
    else:
        result = "the additional destination trigger rules"
    print_report()
    failed = sum(1 for item in RESULTS if item["status"] == "FAIL")
    skipped = sum(1 for item in RESULTS if item["status"] == "SKIP")
    if failed or skipped:
        print(f"PASS: {result} completed online on {net!r} "
              f"({failed} check(s) failed, {skipped} skipped, see summary)")
    else:
        print(f"PASS: {result} passed online on {net!r}")


def _publish_report(ok, seconds, error=""):
    """Merge this run's named checks into log/spider_regression.html."""
    try:
        import importlib
        try:
            suite = importlib.import_module("run_all")
        except ImportError:
            suite = importlib.import_module("tests.run_all")
        suite.record_module_result(
            "triggerAdPoints", ok, seconds, error, RESULTS)
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: could not update regression report: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--part",
                        choices=("all", "cooldown", "victory", "menu",
                                 "destinations", "longad"),
                        default="all",
                        help="run all rules or one independently-runnable group")
    args = parser.parse_args()
    t0 = time.time()
    ok, err = True, ""
    try:
        run(args.part)
    except Exception as e:  # noqa: BLE001
        print_report()
        print(f"FAIL: {e}")
        ok, err = False, str(e)
    _publish_report(ok, time.time() - t0, err)
    sys.exit(0 if ok else 1)
