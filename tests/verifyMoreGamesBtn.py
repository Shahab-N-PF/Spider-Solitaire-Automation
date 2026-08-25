#!/usr/bin/env python3
"""Test: the "More Games" button opens the in-app cross-promo page. [UNITY]

"More Games" (gift icon, left of the main menu) opens FingerArts' in-app
cross-promo page ("Tap any game to download it!" over red curtains) — it stays
in the app rather than jumping to the App Store. Tapping a game there WOULD open
the App Store, so this only verifies the page opened (via its instruction text)
and walks back.

Captures log/MoreGames.png.

Prereqs: WDA up via scripts/wda.sh, iPhone unlocked, DEVICE_UDID set.
Run:  ./.venv/bin/python tests/verifyMoreGamesBtn.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402


def run():
    shot = ui.visit_sub_screen("more_games", "more_games", "MoreGames")
    print(f"PASS: More Games opened (verified 'Tap any game to download it!') "
          f"and returned to the main menu (see {shot})")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
