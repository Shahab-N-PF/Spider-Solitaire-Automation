#!/usr/bin/env python3
"""Test: the difficulty picker's "Last Score" opens the ranking view. [UNITY]

Steps, as specified:
  1. reach the difficulty picker (menu -> Play)
  2. tap "LAST SCORE", bottom-left of the picker
  3. assert the header reads "Last Won Game Score"
  4. tap the forward arrow 4 times, 2 seconds apart
  5. tap "leaderboards". The first tap can raise a Game Center notice card
     ("previous Scores and Achievements may take a little time to upload")
     instead of Apple's sheet — OK that card, and the Leaderboards page
     opens directly (do not tap the link again)
  6. Apple's Game Center sheet opens, headed "Leaderboards"
  7. tap that sheet's back arrow (top-left circle)
  8. tap the empty space at the bottom to dismiss it, back on Last Score
  9. the same steps again for "achievements", headed "Achievements"

ONLINE, OPT-IN — deliberately NOT in tests/run_all.py, alongside verifyAds.
Steps 5-9 need the device on the network AND a signed-in Apple
account: Game Center simply does not open in Airplane Mode, which is how the
rest of the suite runs. The first half would run offline happily, but a case
that is only half-checked in the offline suite is worse than one run
deliberately with the network on.

So take the device OFF Airplane Mode before running this. Failing to open Game
Center is a real failure here and the message says to check the network first —
there is no silent skip, because there is no longer an offline suite to protect.

About step 3. Unity draws its whole UI into one opaque view and publishes no
accessibility text, so there is no API that can return the header string — the
only way to assert what it says is to match the pixels of the words themselves.
The screen_last_score template IS a picture of "Last Won Game Score", cut from
this build's own rendering, and it scores 1.000 here against 0.448 for the
next-best screen in the capture set: the words are what is matched, not the red
bar behind them.

That template is also the only safe way to identify this screen at all. Its
ranking body is the SAME view the victory screen draws, so screen_victory,
victory_ranking, victory_leaderboards and victory_achieve all match here too
(measured). Anything anchoring on those cannot tell the two screens apart.

About step 4. The forward arrow cycles the ranking period rather than paging
forward without end:

    Week of <date>  ->  <month>  ->  Overall  ->  <date>  ->  Week of <date>

so four taps are a full round trip and the screen is left on the period it was
found on. The test prints whether the period line actually changed after each
tap, but does NOT fail on "unchanged" — the spec for this case is to tap four
times, and a dead arrow is a finding to raise rather than a pass/fail the case
was asked to own. Turn the printed line into an assertion if that changes.

Captures log/unity_last_score.png, log/unity_last_score_tap<N>.png,
log/unity_game_center_notice_<link>.png (only if the notice card appeared)
and log/unity_game_center_<link>.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set, and the
device ONLINE with an Apple account signed in to Game Center.
Run:  ./.venv/bin/python tests/visitLastScore.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402

TAPS = 4
TAP_DELAY = 2.0          # seconds between taps, per the spec

# The two Game Center links at the foot of the Last Score screen. Both open the
# SAME sheet chrome — same back arrow in the same place, same dismiss — so one
# routine drives both and only the header tells them apart.
#
#   link text  ->  the control template on Last Score, the sheet's spoken title,
#                  and the template for that title
#
# The control crops are the victory_* ones on purpose, not copies: the victory
# screen draws the same ranking body this screen does, so they are one element.
GAME_CENTER = (
    ("leaderboards", "victory_leaderboards", "Leaderboards", "gc_leaderboards"),
    ("achievements", "victory_achieve",      "Achievements", "gc_achievements"),
)


def run():
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.open_picker(), "the difficulty picker did not open")

    ui.expect(ui.tap("last_score", settle=2.5),
              "the picker has no 'LAST SCORE' label to tap")

    # The header IS the assertion: this template is the words "Last Won Game
    # Score" and nothing else. See the module docstring for why a pixel match is
    # the only form this assertion can take on Unity.
    ui.expect(ui.at_screen("last_score", timeout=6.0),
              "tapping 'LAST SCORE' did not open a screen headed 'Last Won Game "
              "Score' — either it opened nothing, or the header text changed")
    shot = ui.shoot("unity_last_score")
    print(f"  header reads 'Last Won Game Score' — {shot}")

    step_period(shot)
    for entry in GAME_CENTER:
        visit_game_center(*entry)

    # Leave the screen as we found it, so a suite run continues from the menu.
    ui.expect(ui.back(settle=2.0), "the Last Score screen's 'back' was not found")
    ui.expect(ui.to_menu(), "could not get back to the main menu afterwards")

    links = " and ".join(f"'{link}'" for link, _, _, _ in GAME_CENTER)
    print(f"PASS: 'Last Score' opens the 'Last Won Game Score' ranking view, its "
          f"forward arrow takes {TAPS} taps, and {links} each open and close "
          f"Game Center (see {shot})")


def step_period(before_shot: str):
    """Tap the forward arrow TAPS times, TAP_DELAY apart, capturing each state."""
    pos = ui.find("last_score_next")
    ui.expect(pos, "the Last Score screen has no forward arrow beside the "
                   "'ranking for' line, so the period cannot be stepped")

    box = period_box(pos)
    prev = ui.region(before_shot, box)
    for i in range(1, TAPS + 1):
        ui.tap_at(pos, settle=TAP_DELAY)
        shot = ui.shoot(f"unity_last_score_tap{i}")
        now = ui.region(shot, box)
        # Informational, not an assertion — see the module docstring.
        state = "period changed" if ui.changed(prev, now) else "period UNCHANGED"
        print(f"  tap {i}/{TAPS}: {state} — {shot}")
        prev = now

    # The taps must not have navigated off the screen. This one IS a failure:
    # taps 2..4 land on a remembered coordinate, so if tap 1 had carried us
    # somewhere else the rest would be blind taps on an unknown screen.
    ui.expect(ui.at_screen("last_score", timeout=4.0),
              f"{TAPS} taps on the forward arrow left the 'Last Won Game Score' "
              f"screen — the arrow navigated instead of cycling the period")


def visit_game_center(link: str, control: str, header: str, header_tpl: str):
    """Open Game Center from `link`, back out of that page, and dismiss it."""
    tap_game_center_link(link, control)
    # The first Game Center open (leaderboards or achievements) can raise a
    # one-button notice card on Last Score instead of Apple's sheet. That is
    # the same Unity widget as the table tip / reset prompt — WDA cannot see
    # it — so it is found by shape and answered OK. After OK the sheet opens
    # on its own; do not tap the link again. Skip this if Last Score is
    # already covered: that is the sheet.
    if ui.is_on("screen_last_score") and ui.card_up(timeout=1.5):
        dismiss_game_center_notice(link)

    # Two different failures, told apart by whether the Last Score header is
    # still uncovered, because they have completely different causes: nothing
    # was presented at all (almost always the network), or something was
    # presented and it is not the sheet we asked for (a real port defect).
    ui.expect(not ui.is_on("screen_last_score"),
              f"tapping '{link}' presented nothing — the 'Last Won Game Score' "
              f"header is still on screen. Check the device is OFF Airplane Mode "
              f"and signed in to Game Center; that is what usually causes this")
    ui.expect(ui.seen(header_tpl, timeout=10.0),
              f"tapping '{link}' covered the screen with something that is NOT "
              f"Game Center's '{header}' sheet")
    shot = ui.shoot(f"unity_game_center_{link}")
    print(f"  Game Center opened, headed '{header}' — {shot}")

    # One crop covers both sheets: gc_back scores 1.000 on each, at the same
    # point, because they share Apple's chrome.
    ui.expect(ui.tap("gc_back", settle=3.0),
              f"Game Center's '{header}' sheet has no back arrow (top-left)")
    ui.expect(not ui.is_on(header_tpl),
              f"the back arrow did not leave the '{header}' page")

    # Deliberately a raw coordinate: the target is EMPTY SPACE below Game
    # Center's last row, not a control, so there is nothing to match. The rows
    # end around 75% of the height on this screen; 95% is clear of them and
    # clear of the home indicator.
    w, h = ui.screen_size()
    ui.tap_at((w // 2, int(h * 0.95)), settle=3.0)
    ui.expect(ui.at_screen("last_score", timeout=8.0),
              f"after '{link}', tapping the bottom did not dismiss Game Center "
              f"back to the 'Last Won Game Score' screen")
    print(f"  {link}: back arrow, then a tap at the bottom, returned to Last Score")


def tap_game_center_link(link: str, control: str):
    ui.expect(ui.tap(control, settle=4.5),
              f"the Last Score screen has no '{link}' text to tap")


def dismiss_game_center_notice(link: str):
    """OK the first-time Game Center notice; the sheet opens from that tap."""
    shot = ui.shoot(f"unity_game_center_notice_{link}")
    ui.expect(ui.answer_card(0, settle=2.0),
              f"tapping '{link}' raised a card, but its OK button could not "
              f"be pressed — {shot}")
    ui.expect(not ui.card_up(timeout=2.0),
              f"OK did not dismiss the Game Center notice after '{link}' — {shot}")
    print(f"  dismissed Game Center notice after '{link}', sheet should open — {shot}")


def period_box(arrow_pos):
    """Crop box over the 'ranking for / <period> / won N' block.

    Anchored on the arrow rather than on fixed pixels so it survives the other
    phones in the family, where the same layout is drawn at a different scale.
    """
    w, h = ui.screen_size()
    _, ay = arrow_pos
    return (int(0.15 * w), int(ay - 0.035 * h),
            int(0.85 * w), int(ay + 0.045 * h))


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
