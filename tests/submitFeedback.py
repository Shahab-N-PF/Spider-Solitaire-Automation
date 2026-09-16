#!/usr/bin/env python3
"""Test: About's "submit feedback" opens a mail draft naming the build. [UNITY]

**Standalone, NOT in tests/run_all.py** — composing mail needs a Mail account
configured on the device. Without one iOS raises "No Mail Accounts" instead of a
composer, and the suite would fail for an environment reason rather than a build
one. See run_all's "Not in the suite, on purpose" block.

"submit feedback" was the last untested link on About. verifySpiderLogo asserts
it is present but never taps it, because it leaves the app — the objection
verifyAdFreeVersion has since answered for the ad-free link.

The flow, measured on an iPhone 11, build 363:

  1. the link raises a real iOS ALERT — "We appreciate your feedback … Tap
     'Write Email' to launch the Mail app to send us a feedback" — with
     Cancel / Write Email;
  2. Write Email leaves the app entirely and opens MAIL (com.apple.mobilemail),
     not an in-app compose sheet. Coming back is done the way a PERSON does it —
     tapping the "◀ Spider" crumb iOS draws in the status bar (proved in
     isolation: Mail, tap (45, 75), Spider). Unlike the App Store, which Spider
     survives underneath, coming back from Mail lands on the MAIN MENU rather
     than the About screen it left. That is CONFIRMED EXPECTED BEHAVIOUR, not a
     defect — do not file it as one, and do not tighten this test to demand
     About the way verifyAdFreeVersion does;
  3. the draft's subject reads
       Spider 8.0.0 feedback (iPhone12,1, iOS 26.5 al/al) us

THE SUBJECT IS THE POINT. It is the app telling support which build and which
hardware a complaint came from, so a stale or wrong value there is a real defect
that no screenshot comparison could ever catch — the subject is different on
every device by design, so there is nothing to diff it against.

Which is why every expected value is READ FROM THE DEVICE in the same run
(helpers.os_version / device_model / app_info) rather than written in as a
constant. A test carrying "26.5" works on one phone until the next iOS update;
this one runs unchanged on the iPhone 14 Pro Max and 16 Pro.

Two spellings matter and are easy to get backwards:
  * the app writes "Spider" (its display name), NOT config.GAME_NAME's
    "Spider Solitaire";
  * it writes "iPhone12,1" (the model identifier), NOT the marketing name
    "iPhone 11".
Both are taken from the device rather than assumed.

This test NEVER SENDS. The compose sheet's X and its blue send arrow are
addressed by NAME (Mail.cancelSendButton / Mail.sendButton) so a coordinate slip
cannot hit the wrong one, and the draft is deleted from a `finally` so a failed
assertion still leaves nothing behind in the user's Mail app.

Two oddities in the draft were REVIEWED AND ACCEPTED — they are printed each run
for visibility, deliberately not asserted, and should not be re-raised as bugs:
  * the recipient is cardgames@peoplefun.com, from the SPIDER app;
  * the subject's locale field reads "al/al) us" on a device set to English.
If either is ever made to matter, add it to expected_fields() rather than
turning the printed line into an assertion by hand.

Captures log/SubmitFeedback.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set,
         a Mail account configured on the device.
Run:  ./.venv/bin/python tests/submitFeedback.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import helpers  # noqa: E402
import unity_ui as ui  # noqa: E402

LINK = "about_feedback"


def expected_fields():
    """The four things the subject must name, read off THIS device, this run."""
    name, version = helpers.app_info()
    return [
        ("game name",    name),
        ("app version",  version),
        ("device model", helpers.device_model()),
        ("iOS version",  helpers.os_version()),
    ]


def run():
    # The network is already on (HelpShiftOnline / Ad-free / any prior online
    # case). Do not call ui.online() — that opens Settings and can take 75s
    # for a radio state this test does not own.
    # 1-3. Reach About and prove the link is there before tapping it, so "the
    #      link is missing" and "the link goes nowhere" stay separate failures.
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.tap("menu_about", settle=2.5), "About control not found on the menu")
    ui.expect(ui.at_screen("about"),
              "tapping About did not open the About screen (copyright line not found)")
    ui.expect(ui.is_on(LINK), "the 'submit feedback' link is not on the About screen")

    # 4-5. Tap it. The prompt is a REAL alert, so identify it by its TEXT — the
    #      house rule for look-alike dialogs, and stronger than counting buttons.
    ui.expect(ui.tap(LINK, settle=3.0), "the 'submit feedback' link could not be tapped")
    prompt = ui.alert_now()
    ui.expect("feedback" in prompt.lower(),
              f"tapping 'submit feedback' did not raise the feedback prompt — the "
              f"alert on screen reads {prompt!r}. An empty string means no alert "
              f"came up at all, so the link did nothing.")

    # 6. Press Write Email — the RIGHT-hand button. Index 0 is Cancel, and the
    #    count is asserted first so a different dialog cannot be answered blind.
    buttons = ui.card_buttons()
    ui.expect(len(buttons) == 2,
              f"the feedback prompt should offer two buttons (Cancel, Write "
              f"Email) but {len(buttons)} were found at {buttons}")
    ui.expect(ui.answer_card(1, settle=5.0), "could not press 'Write Email'")
    print("  the link raises the feedback prompt; answered 'Write Email'")

    # 7. It must reach Mail. A missing mail account shows an alert instead, and
    #    that is an environment problem, so it gets its own message.
    went_to = ui.left_app()
    ui.expect(went_to == ui.MAIL,
              f"'Write Email' did not open Mail — the foreground app is "
              f"{went_to or 'unknown'}. If this is still the game, check the "
              f"device has a MAIL ACCOUNT set up: without one iOS shows a 'No "
              f"Mail Accounts' alert rather than a composer, which is an "
              f"environment problem and not a build defect.")

    # 8-11. Read the draft, assert the subject, and ALWAYS throw it away.
    shot = ui.shoot("SubmitFeedback")
    discarded = False
    try:
        draft = ui.mail_draft()
        subject = draft["subject"]
        ui.expect(subject,
                  f"Mail opened but the draft has no readable subject — the "
                  f"composer may not have finished appearing (see {shot})")
        print(f"  subject: {subject!r}")
        print(f"  to     : {draft['to']!r}")

        unreadable = [label for label, value in expected_fields() if not value]
        ui.expect(not unreadable,
                  f"could not read {unreadable} FROM THE DEVICE, so the subject "
                  f"cannot be checked against them. This is a harness problem "
                  f"(is ideviceinfo on PATH? is DEVICE_UDID right?), not a "
                  f"failure of the app.")

        missing = [f"{label} ({value!r})" for label, value in expected_fields()
                   if value.lower() not in subject.lower()]
        ui.expect(not missing,
                  f"the feedback subject does not name {', '.join(missing)}. "
                  f"The subject is {subject!r}. Support uses this line to know "
                  f"which build and which handset a report came from.")
        for label, value in expected_fields():
            print(f"    {label:13} {value!r} — present")
    finally:
        discarded = ui.mail_discard()
        if not discarded:
            print("  WARNING: the draft could not be deleted — check the Mail app; "
                  "nothing was sent, but a draft may be left on the device")

    ui.expect(discarded,
              "the subject was correct but the draft could NOT be thrown away, so "
              "this run left a half-written mail on the device. Delete it by hand.")

    # 12-13. Back to the game the way a PERSON does it: tap the "◀ Spider"
    #        breadcrumb iOS puts in the status bar, not a programmatic resume().
    #        The two are different acts — resume() asks WDA to foreground the
    #        app and can relaunch it, the crumb is iOS's own task switch — and
    #        the crumb is what a player actually taps, so it is what gets tested.
    #
    # Which screen comes back is REPORTED, not demanded. verifyAdFreeVersion can
    # insist on About because the App Store is an overlay Spider survives
    # underneath; Mail is a whole second app and, measured on build 363, coming
    # back from it lands on the MAIN MENU. Requiring About here would fail a
    # build that is behaving perfectly well.
    ui.expect(ui.tap_back_to_app(),
              "tapping the '◀ Spider' breadcrumb in the status bar did not bring "
              "the game back. That crumb is drawn by iOS, not by Mail, so it is "
              "the only control here with no accessibility entry to fall back on "
              "— check the top-left of log/SubmitFeedback.png for it.")
    landed = ("the About screen" if ui.at_screen("about", timeout=6.0)
              else "the main menu" if ui.on_menu(timeout=6.0) else "")
    ui.expect(landed,
              "came back to Spider from Mail but not to any recognised screen — "
              "neither About nor the main menu")
    print(f"  switching back returns to the game, on {landed}")
    ui.expect(ui.to_menu(), "could not reach the main menu after coming back")
    print(f"PASS: 'submit feedback' opens a mail draft whose subject names the "
          f"game, version, device model and iOS version; draft discarded, "
          f"nothing sent (see {shot})")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
