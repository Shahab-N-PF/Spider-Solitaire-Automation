#!/usr/bin/env python3
"""Test: Options -> "Contact Us" opens the Helpshift support flow. [UNITY]

The Options screen's top-right "Contact Us" button opens FingerArts' Helpshift
support page. That page is fetched over the NETWORK, so it needs the device
online — which is the opposite of how the rest of the suite runs (Airplane Mode,
to keep cross-promo interstitials from interrupting screen transitions).

For that reason this is intentionally NOT in tests/run_all.py: it would either
fail offline or drag the whole suite online. Run it deliberately, with the device
connected:

    ./.venv/bin/python tests/verifyHelpShift.py

Because the loaded page renders unpredictably (network content), the assertion is
deliberately weak: tapping Contact Us must LEAVE the Options screen. That is the
part the app controls; what Helpshift then renders is not ours to pin down.

Captures log/HelpShift.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set, device
ONLINE.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402


def run():
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")
    ui.expect(ui.tap("menu_options", settle=2.5), "Options control not found on the menu")
    ui.expect(ui.at_screen("options"), "the Options screen did not open")
    ui.expect(ui.is_on("contact_us"), "the 'Contact Us' button is missing from Options")

    ui.expect(ui.tap("contact_us", settle=4.0), "'Contact Us' could not be tapped")
    ui.sleep(4)                                  # let the support page load
    shot = ui.shoot("HelpShift")
    ui.expect(not ui.is_on("screen_options"),
              "tapping 'Contact Us' did not leave the Options screen — the "
              "support flow may not have opened (is the device online?). "
              f"See {shot}")
    print(f"PASS: 'Contact Us' opened the support flow (left the Options screen) "
          f"— see {shot}")

    ui.expect(ui.to_menu(), "could not return to the main menu from the support flow")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
