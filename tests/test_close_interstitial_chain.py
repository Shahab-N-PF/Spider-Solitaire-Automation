import types
import unittest
from unittest import mock

import unity_ui


class CloseChainTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.up = True
        clock = types.SimpleNamespace(time=lambda: self.now,
                                      sleep=self.advance)
        self.patch(unity_ui, "time", clock)
        self.patch(unity_ui, "in_app", lambda: True)
        self.patch(unity_ui, "lost", lambda timeout=0.0: self.up)
        self.patch(unity_ui, "_tap_ad_skip", lambda: False)

    def advance(self, seconds):
        self.now += seconds

    def patch(self, target, name, value):
        patcher = mock.patch.object(target, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def close(self):
        return unity_ui._close_interstitial_chain("test", 90.0, 30.0)

    def closes_after(self, n):
        taps = []

        def tap(*a, **kw):
            taps.append(1)
            self.up = len(taps) < n
            return True
        return tap, taps

    def test_ad_closes_on_its_own_x(self):
        tap, taps = self.closes_after(1)
        self.patch(unity_ui, "_tap_ax_close", lambda: False)
        self.patch(unity_ui, "_tap_ad_close_crop", tap)
        self.assertTrue(self.close())
        self.assertEqual(len(taps), 1)

    def test_native_close_then_ad_x_in_any_order(self):
        ax_tap, ax = self.closes_after(99)
        crop_tap, crops = self.closes_after(1)
        self.patch(unity_ui, "_tap_ax_close",
                   lambda: not ax and ax_tap())
        self.patch(unity_ui, "_tap_ad_close_crop", crop_tap)
        self.assertTrue(self.close())
        self.assertEqual((len(ax), len(crops)), (1, 1))

    def test_pangle_skip_closes_the_ad(self):
        skip, skips = self.closes_after(1)
        self.patch(unity_ui, "_tap_ax_close", lambda: False)
        self.patch(unity_ui, "_tap_ad_skip", skip)
        self.patch(unity_ui, "_tap_ad_close_crop",
                   lambda: self.fail("no X once the skip closed the ad"))
        self.assertTrue(self.close())
        self.assertEqual(len(skips), 1)

    def test_skip_to_end_card_then_its_x(self):
        skip, skips = self.closes_after(99)
        crop, crops = self.closes_after(1)
        self.patch(unity_ui, "_tap_ax_close", lambda: False)
        self.patch(unity_ui, "_tap_ad_skip", lambda: not skips and skip())
        self.patch(unity_ui, "_tap_ad_close_crop", crop)
        self.assertTrue(self.close())
        self.assertEqual((len(skips), len(crops)), (1, 1))

    def test_nothing_is_tapped_once_spider_is_back(self):
        self.up = False
        for name in ("_tap_ax_close", "_tap_ad_skip", "_tap_ad_close_crop"):
            self.patch(unity_ui, name, lambda: self.fail("tapped with no ad"))
        self.assertTrue(self.close())

    def test_skip_close_proves_a_test_ad(self):
        skip, _ = self.closes_after(1)

        def tap():
            unity_ui._note_close("ad_skip_pangle")
            return skip()
        self.patch(unity_ui, "_tap_ax_close", lambda: False)
        self.patch(unity_ui, "_tap_ad_skip", tap)
        self.assertTrue(unity_ui.close_interstitial_chain("test", 90.0, 30.0))
        self.assertTrue(unity_ui.LAST_AD_CLOSE["test"])
        self.assertFalse(unity_ui.last_ad_was_live())

    def test_native_close_alone_marks_a_live_ad(self):
        native, _ = self.closes_after(1)

        def tap():
            unity_ui._note_close("native:close")
            return native()
        self.patch(unity_ui, "_tap_ax_close", tap)
        self.assertTrue(unity_ui.close_interstitial_chain("test", 90.0, 30.0))
        self.assertTrue(unity_ui.last_ad_was_live())

    def test_nothing_closes_falls_back_to_tap_ad_close_and_fails(self):
        self.patch(unity_ui, "_tap_ax_close", lambda: False)
        self.patch(unity_ui, "_tap_ad_close_crop", lambda: False)
        fallback = []
        self.patch(unity_ui, "tap_ad_close",
                   lambda timeout: fallback.append(self.now) or False)
        with self.assertRaises(AssertionError):
            self.close()
        self.assertGreaterEqual(fallback[0], 90.0)


if __name__ == "__main__":
    unittest.main()
