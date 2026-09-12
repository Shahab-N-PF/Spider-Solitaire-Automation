"""Test: install the newest odd Spider build from TestFlight.

This is the first test in the full regression run.  It deliberately leaves
TestFlight in front after the download; ``verifyFirstLaunch`` launches Spider
next and owns the fresh-install Terms & Conditions and ATT flow.

The newest Previous Builds row is selected first.  An even build is a hard
failure, but the existing Spider installation is left untouched so a mistaken
TestFlight release cannot strand the device without the app.

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
    network = ui.online()
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

    marketing, build = tf.tap_newest_build()
    ui.expect(
        build is not None,
        "TestFlight did not show a versioned build row at the top of "
        f"Previous Builds (see {previous_shot})",
    )
    build_shot = ui.shoot("TestFlightBuild")
    print(f"  newest TestFlight build: {marketing} ({build}) — {build_shot}")

    if build % 2 == 0:
        raise AssertionError(
            f"the newest TestFlight build is even: {marketing} ({build}); "
            "Spider was not uninstalled or changed"
        )

    ui.expect(
        tf.uninstall_spider(),
        "Spider did not uninstall before the TestFlight download",
    )
    ui.expect(
        tf.install_current_build(marketing, build),
        f"TestFlight did not install {marketing} ({build}) within 10 minutes",
    )
    installed = tf.app_installed()
    ui.expect(
        installed is not None and installed[1] == build,
        f"the installed Spider build was {installed}, expected "
        f"{marketing} ({build})",
    )
    print(
        f"PASS: TestFlight installed newest odd Spider build "
        f"{marketing} ({build}); Spider was left unopened"
    )


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        sys.exit(1)
