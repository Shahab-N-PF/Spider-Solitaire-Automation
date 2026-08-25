#!/usr/bin/env python3
"""Test: the Choose Look modal — tabs, selection, and closing.

Beyond opening the modal, this exercises what it's FOR: switching tabs and
actually applying a theme. Picking a surface swatch is verified by the screen
changing (the felt is repainted), which is the only observable proof available
without an accessibility tree.

The modal is also the one place where "the menu is visible" and "we are on the
menu" diverge — it overlays the menu, leaving the menu labels matchable behind
it (scripts/verify_unity_assets.py flagged this). ui.on_menu() rules the modal
out explicitly, and the close step below relies on that being correct.

Run:  ./.venv/bin/python tests/verifyChooseLook.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unity_ui as ui  # noqa: E402


def run():
    ui.expect(ui.launch_to_menu(), "could not reach the main menu")

    # 1. Open the modal. It reopens on whichever tab was last used, so normalise
    #    to Surface rather than assuming.
    ui.expect(ui.tap("choose_look", settle=3.0), "Choose Look control not found")
    ui.expect(ui.seen("look_close", timeout=8.0),
              "the Choose Look modal did not open (no close button)")
    if not ui.is_on("screen_surface"):
        ui.expect(ui.tap("look_surface_tab", settle=2.0), "Surface tab not found")
    ui.expect(ui.at_screen("surface"),
              "the Surface tab content ('Simulate Depth') is not showing")
    shot_s = ui.shoot("choose_look_surface")

    # 2. The menu must NOT count as reachable while the modal covers it.
    ui.expect(not ui.on_menu(timeout=1.0),
              "on_menu() returned True while the Choose Look modal was open — "
              "the modal leaves the menu labels visible behind it")

    # 3. Switch to Cards and back, proving both tabs work.
    ui.expect(ui.tap("look_cards_tab", settle=2.5), "Cards tab not found")
    ui.expect(ui.at_screen("cards"),
              "the Cards tab content ('Extra Large Card-Symbols') is not showing")
    shot_c = ui.shoot("choose_look_cards")

    ui.expect(ui.tap("look_surface_tab", settle=2.5), "Surface tab not found on the way back")
    ui.expect(ui.at_screen("surface"), "could not switch back to the Surface tab")

    # 4. Apply a different surface and require the screen to change.
    #
    #    Tapping the ALREADY-SELECTED swatch is a legitimate no-op, and the
    #    selection persists between runs — so a test that always taps the same
    #    swatch passes once and then fails forever after (which is exactly what
    #    happened). Trying two distinct swatches makes it order-independent:
    #    only one can be selected, so at least one must produce a change.
    #
    #    Positions are fractions of the screen (measured from the Unity layout)
    #    because the swatch grid has no per-swatch template.
    w, h = ui.screen_size()
    applied = False
    for i, fx in enumerate((0.164, 0.440, 0.713)):      # top row, left→right
        before = ui.shoot(f"_look_before{i}")
        ui.tap_at((int(w * fx), int(h * 0.368)), settle=2.5)
        if _differs(before, ui.shoot(f"_look_after{i}")):
            applied = True
            print(f"  applied a different surface (swatch {i + 1} of the top row)")
            break
    ui.expect(applied,
              "no swatch in the top row changed the surface — every tap was a "
              "no-op, so either the grid moved (adjust the fractions above) or "
              "selection is broken")

    # 5. Close via the x (the modal has no back button) and land on the menu.
    ui.expect(ui.tap("look_close", settle=2.0), "modal close (x) not found")
    ui.expect(ui.on_menu(timeout=6.0),
              "closing the Choose Look modal did not return to the main menu")

    print(f"PASS: Choose Look — Surface ({shot_s}) / Cards ({shot_c}) tabs switch, "
          "a surface applies, and x closes to the menu")


def _differs(a, b, min_frac=0.005):
    """True if two captures differ in more than `min_frac` of their pixels."""
    import numpy as np
    from PIL import Image
    ia = np.asarray(Image.open(a).convert("RGB"), dtype=np.int16)
    ib = np.asarray(Image.open(b).convert("RGB"), dtype=np.int16)
    if ia.shape != ib.shape:
        return True
    return float((np.abs(ia - ib).max(axis=2) > 12).mean()) > min_frac


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)
