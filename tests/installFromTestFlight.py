"""Test: install the greatest odd Spider build from TestFlight.

This is the first test in the full regression run.  It deliberately leaves
TestFlight in front after the download; ``verifyFirstLaunch`` launches Spider
next and owns the fresh-install Terms & Conditions and ATT flow.

The Previous Builds list is scanned completely. The greatest odd build is
selected regardless of where it appears in the list; an all-even list fails
without changing the existing installation.

A missing Spider install is not a reason to stop: going online does not
restore the game, and TestFlight still installs the greatest odd build.

Prereqs: WDA up while the phone is online, TestFlight installed and signed in,
the Spider TestFlight invite accepted, and DEVICE_UDID set.
Run: ./.venv/bin/python tests/installFromTestFlight.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import testflight_ui as tf  # noqa: E402
import unity_ui as ui  # noqa: E402


def run():
    installed = tf.app_installed()
    if installed is None:
        print("  could not read whether Spider is installed; continuing to TestFlight")
    elif installed == ("", None):
        print("  Spider is not installed; TestFlight will install the greatest odd build")
    else:
        print(f"  Spider already installed: {installed[0]} ({installed[1]})")

    # Do not restore Spider after Settings: it may not be on the device yet,
    # and launching a missing bundle 500s WDA. TestFlight is opened next.
    try:
        network = ui.online(restore=False)
    except Exception as exc:  # noqa: BLE001
        print(f"  WARNING: going online raised {exc}; retrying without restoring Spider")
        network = ui.online(restore=False)
    ui.expect(network, "the phone did not reconnect to Wi-Fi for TestFlight")

    tf.open_testflight()
    list_shot = ui.shoot("TestFlightList")
    app_name = tf.open_spider()
    ui.expect(
        app_name,
        "Spider Solitaire was not found in TestFlight's Apps list "
        f"(see {list_shot})",
    )

    ui.expect(
        tf.open_previous_builds(),
        "TestFlight did not show a Previous Builds link",
    )
    previous_shot = ui.shoot("TestFlightPreviousBuilds")

    marketing, build, seen, row = tf.tap_latest_odd_build()
    ui.expect(
        build is not None,
        "TestFlight showed no odd build in Previous Builds; seen builds: "
        f"{[build for build, _marketing in seen]} "
        f"(see {previous_shot})",
    )
    build_shot = ui.shoot("TestFlightBuild")
    print(f"  greatest odd TestFlight build: {marketing} ({build}) — "
          f"{build_shot}")

    ui.expect(
        tf.uninstall_spider(),
        "Spider did not uninstall before the TestFlight download",
    )
    ui.expect(
        tf.install_current_build(marketing, build, row=row),
        f"TestFlight did not install {marketing} ({build}) within 10 minutes",
    )
    installed = tf.app_installed()
    ui.expect(
        installed is not None and installed[1] == build,
        f"the installed Spider build was {installed}, expected "
        f"{marketing} ({build})",
    )
    print(
        f"PASS: TestFlight installed greatest odd Spider build "
        f"{marketing} ({build}); Spider was left unopened"
    )


def selftest():
    """Exercise greatest-odd selection without a device."""
    builds = [
        ("8.0.2", 382), ("8.0.2", 380), ("8.0.2", 379),
        ("8.0.2", 377), ("8.0.2", 375), ("8.0.2", 373),
        ("8.0.2", 371),
    ]
    chosen = tf.latest_odd_build(builds)
    if chosen != ("8.0.2", 379):
        print(f"SELFTEST FAIL: expected (8.0.2, 379), got {chosen}")
        return False
    if tf.latest_odd_build([("8.0.2", 382), ("8.0.2", 380)]) != ("", None):
        print("SELFTEST FAIL: all-even builds produced a selection")
        return False
    print("SELFTEST PASS: selected 8.0.2 (379) from the mixed list")
    return True


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        sys.exit(1)
