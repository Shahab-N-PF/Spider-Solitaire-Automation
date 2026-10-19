import unittest
from unittest import mock

import max_test_mode as mtm
import unity_ui


class RelaunchHookTests(unittest.TestCase):
    def setUp(self):
        self.patch(unity_ui, "_RELAUNCH_HOOKS", [])
        self.patch(unity_ui, "on_menu", lambda timeout=0.0: True)
        self.patch(mtm, "_KEPT", None)
        self.patch(mtm, "_BUSY", False)

    def patch(self, target, name, value):
        patcher = mock.patch.object(target, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_cold_launch_runs_hooks_after_reaching_the_menu(self):
        ran = []
        self.patch(unity_ui, "_cold_launch", lambda: True)
        unity_ui.on_relaunch(lambda: ran.append(1))
        self.assertTrue(unity_ui.cold_launch())
        self.assertEqual(ran, [1])

    def test_failed_cold_launch_runs_no_hooks(self):
        self.patch(unity_ui, "_cold_launch", lambda: False)
        unity_ui.on_relaunch(lambda: self.fail("hook ran without a menu"))
        self.assertFalse(unity_ui.cold_launch())

    def test_hook_is_registered_once(self):
        def hook():
            pass
        unity_ui.on_relaunch(hook)
        unity_ui.on_relaunch(hook)
        self.assertEqual(unity_ui._RELAUNCH_HOOKS, [hook])

    def test_relaunch_re_enables_the_kept_network(self):
        calls = []
        self.patch(mtm, "ensure_network",
                   lambda network, capture=True, fresh=True:
                   calls.append((network, capture, fresh)))
        self.patch(unity_ui, "to_menu", lambda: True)
        self.patch(mtm, "_KEPT", "Pangle")
        mtm._after_relaunch()
        self.assertEqual(calls, [("Pangle", False, False)])
        self.assertFalse(mtm._BUSY)

    def test_no_re_enable_before_setup_or_while_busy(self):
        self.patch(mtm, "ensure_network",
                   lambda *a, **kw: self.fail("re-enabled when it should not"))
        mtm._after_relaunch()
        self.patch(mtm, "_KEPT", "Pangle")
        self.patch(mtm, "_BUSY", True)
        mtm._after_relaunch()

    def test_fresh_setup_relaunches_and_resets_a_stale_test_mode(self):
        steps = []
        self.patch(mtm, "_relaunch_to_menu", lambda why: steps.append("relaunch"))
        self.patch(mtm, "_open_debugger", lambda: None)
        self.patch(mtm, "_test_mode_state", lambda: (True, "reads true"))
        self.patch(mtm, "_disable_test_mode_and_relaunch",
                   lambda: steps.append("live"))
        self.patch(mtm, "_enable_test_mode_and_relaunch",
                   lambda: steps.append("test"))
        self.patch(mtm, "_select_test_network", lambda network: None)
        self.patch(mtm, "_back_out_of_subwindows", lambda why="": True)
        self.patch(unity_ui, "close_max_debugger", lambda: True)
        self.patch(unity_ui, "close_dev_panel", lambda: True)
        mtm.ensure_network("Pangle", capture=False)
        self.assertEqual(steps, ["relaunch", "live", "test"])

    def test_hook_does_not_relaunch_again(self):
        self.patch(mtm, "_relaunch_to_menu",
                   lambda why: self.fail("the hook runs right after a relaunch"))
        self.patch(mtm, "_open_debugger", lambda: None)
        self.patch(mtm, "_test_mode_state", lambda: (False, "reads false"))
        enabled = []
        self.patch(mtm, "_enable_test_mode_and_relaunch",
                   lambda: enabled.append(1))
        self.patch(mtm, "_select_test_network", lambda network: None)
        self.patch(mtm, "_back_out_of_subwindows", lambda why="": True)
        self.patch(unity_ui, "close_max_debugger", lambda: True)
        self.patch(unity_ui, "close_dev_panel", lambda: True)
        self.patch(unity_ui, "to_menu", lambda: True)
        self.patch(mtm, "_KEPT", "Pangle")
        mtm._after_relaunch()
        self.assertEqual(enabled, [1])

    def test_ensure_network_keeps_the_network_and_ignores_its_own_restart(self):
        self.patch(mtm, "_open_debugger", lambda: None)
        self.patch(mtm, "_test_mode_state", lambda: (False, "reads false"))
        self.patch(mtm, "_select_test_network", lambda network: None)
        self.patch(mtm, "_back_out_of_subwindows", lambda why="": True)
        self.patch(unity_ui, "close_max_debugger", lambda: True)
        self.patch(unity_ui, "close_dev_panel", lambda: True)
        self.patch(unity_ui, "_cold_launch", lambda: True)
        reentered = []
        real = mtm.ensure_network

        def enable_and_relaunch():
            # The Test Mode restart is a cold launch; its hook must not recurse.
            self.patch(mtm, "ensure_network",
                       lambda *a, **kw: reentered.append(1))
            unity_ui.on_relaunch(mtm._after_relaunch)
            unity_ui.cold_launch()
        self.patch(mtm, "_enable_test_mode_and_relaunch", enable_and_relaunch)
        real("Pangle", capture=False)
        self.assertEqual(reentered, [])
        self.assertEqual(mtm._KEPT, "Pangle")
        self.assertIn(mtm._after_relaunch, unity_ui._RELAUNCH_HOOKS)
        self.assertFalse(mtm._BUSY)


if __name__ == "__main__":
    unittest.main()
