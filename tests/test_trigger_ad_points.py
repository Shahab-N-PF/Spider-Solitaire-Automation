import types
import unittest
from unittest import mock

from tests import triggerAdPoints as tap


class Clock:
    def __init__(self, now=1000.0):
        self.now = now

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += max(0.0, seconds)


def _expect(cond, msg):
    if not cond:
        raise AssertionError(msg)


def fake_ui(clock, lost=lambda: False, screen=True):
    calls = {"chain_at": None}

    def close_chain(where, store, ad, **kw):
        calls["chain_at"] = clock.now
        return True

    ui = types.SimpleNamespace(
        in_app=lambda: True,
        lost=lambda timeout=0.0: lost(),
        sleep=clock.sleep,
        active_app=lambda: "com.fingerarts.Spider",
        expect=_expect,
        close_interstitial_chain=close_chain,
        last_ad_was_live=lambda: calls.get("live", False),
        at_table=lambda timeout=0.0: screen,
        at_screen=lambda name, timeout=0.0: screen,
    )
    return ui, calls


def ad(seconds, start=0.0, where="prior"):
    """An ad that appeared at ``start`` and closed ``seconds`` later."""
    return tap.AdRecord(where, start, start, start + seconds)


class TriggerAdPointsTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        tap.AD_LOG.clear()
        tap.CHECK_AD.clear()
        tap.LAST_AD = None
        for name, value in (("COOLDOWN", 30.0), ("AD_MARGIN", 3.0),
                            ("AD_DETECT_LAG", 4.0), ("ACT_LATENCY", 2.0)):
            patcher = mock.patch.object(tap, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(
            tap, "time", types.SimpleNamespace(time=self.clock.time))
        patcher.start()
        self.addCleanup(patcher.stop)

    def use_ui(self, **kw):
        ui, calls = fake_ui(self.clock, **kw)
        patcher = mock.patch.object(tap, "ui", ui)
        patcher.start()
        self.addCleanup(patcher.stop)
        return calls

    def act(self, cost=0.5):
        """A follow-up tap that takes ``cost`` seconds; returns its bracket."""
        def run():
            before = self.clock.now
            self.clock.sleep(cost)
            return before, self.clock.now
        return run

    def test_cooldown_left_is_thirty_minus_the_ad_length(self):
        for seconds, left in ((10, 20), (15, 15), (20, 10), (30, 0), (45, 0)):
            self.assertEqual(ad(seconds).remaining_after_close, left)
        self.assertEqual(ad(15, start=100).cooldown_until_lo, 130)

    def test_unstamped_start_is_bracketed_by_the_detection_lag(self):
        self.use_ui(lost=lambda: True)
        seen = self.clock.now
        rec = tap.close_current_ad("ad", start_hi=seen)
        self.assertEqual(rec.start_lo, seen - 4.0)
        self.assertEqual(rec.start_hi, seen)

    def test_inside_cooldown_keeps_the_margin_clear(self):
        prior = ad(10, start=0.0)
        self.assertTrue(tap.inside_cooldown(prior, 26.9))
        self.assertFalse(tap.inside_cooldown(prior, 27.0))
        self.assertTrue(tap.usable_window(prior, 24.9))
        self.assertFalse(tap.usable_window(prior, 25.0))
        self.assertFalse(tap.inside_cooldown(None, 0.0))

    def test_no_ad_inside_the_window_passes(self):
        self.use_ui(screen=True)
        prior = ad(10, start=self.clock.now - 10)
        tap.expect_no_ad_inside("TA-05", prior, self.act(), lambda: True,
                                lambda: self.fail("no restore"))
        self.assertIs(tap.CHECK_AD["TA-05"], prior)

    def test_no_usable_window_runs_the_action_then_skips(self):
        self.use_ui(screen=True)
        prior = ad(26, start=self.clock.now - 26)
        acted, restored = [], []

        def act():
            acted.append(1)
            return self.clock.now, self.clock.now

        with self.assertRaises(tap.SkipCheck) as ctx:
            tap.expect_no_ad_inside("TA-05", prior, act, lambda: True,
                                    lambda: restored.append(1))
        self.assertEqual((acted, restored), ([1], [1]))
        self.assertIn("no usable cooldown window", str(ctx.exception))
        self.assertIn("leaving 4s of cooldown", str(ctx.exception))

    def test_late_tap_is_downgraded_to_skip(self):
        self.use_ui(screen=True)
        prior = ad(20, start=self.clock.now - 20)
        with self.assertRaises(tap.SkipCheck) as ctx:
            tap.expect_no_ad_inside("TA-03", prior, self.act(cost=8.0),
                                    lambda: True, lambda: None)
        self.assertIn("too close to the cooldown's end", str(ctx.exception))

    def test_ad_inside_the_window_fails_and_is_closed(self):
        self.use_ui(lost=lambda: True, screen=False)
        prior = ad(10, start=self.clock.now - 10)
        closed = []
        with mock.patch.object(tap, "close_current_ad",
                               lambda where, **kw: closed.append(where)):
            with self.assertRaises(AssertionError) as ctx:
                tap.expect_no_ad_inside("TA-05", prior, self.act(),
                                        lambda: False, lambda: None)
        self.assertEqual(closed, ["TA-05 (unexpected)"])
        self.assertIn("no-ad window", str(ctx.exception))

    def test_expiry_check_taps_only_after_the_cooldown_and_margin(self):
        self.use_ui()
        prior = ad(10, start=self.clock.now - 10)
        tapped = []

        def act():
            tapped.append(self.clock.now)
            return self.clock.now, self.clock.now

        with mock.patch.object(tap, "expect_ad",
                               lambda label, triggered_at=None: triggered_at):
            got = tap.expect_ad_after_expiry("TA-06", prior, act)
        self.assertGreaterEqual(tapped[0], prior.cooldown_until_hi + 3.0)
        self.assertLess(tapped[0] - prior.closed_at, 30.0)
        self.assertEqual(got, tapped[0])

    def test_options_ad_is_excused_only_outside_a_known_cooldown(self):
        prior = ad(10, start=0.0)
        self.assertTrue(tap.options_ad_excused(0, None, 5.0))
        self.assertFalse(tap.options_ad_excused(1, None, 5.0))
        self.assertFalse(tap.options_ad_excused(0, prior, 15.0))
        self.assertTrue(tap.options_ad_excused(1, prior, 40.0))
        unknown = tap.AdRecord("leftover", None, None, 0.0)
        self.assertTrue(tap.options_ad_excused(1, unknown, 5.0))

    def test_held_ad_closes_only_after_the_cooldown(self):
        calls = self.use_ui(lost=lambda: True)
        start = self.clock.now
        rec = tap.close_current_ad("held", start_lo=start, start_hi=start,
                                   hold=True)
        self.assertGreaterEqual(calls["chain_at"], start + 33.0)
        self.assertEqual(rec.remaining_after_close, 0.0)
        tap.require_ran_past_cooldown(rec, "TA-11")
        self.assertIs(tap.LAST_AD, rec)
        self.assertEqual(tap.AD_LOG, [rec])

    def test_live_ad_fails_its_check_and_re_enables_test_mode(self):
        calls = self.use_ui(lost=lambda: True)
        calls["live"] = True
        served = []
        with mock.patch.object(tap.mtm, "live_ad_served",
                               lambda where: served.append(where) or "live"):
            with self.assertRaises(AssertionError):
                tap.close_current_ad("long table -> Help")
        self.assertEqual(served, ["long table -> Help"])
        self.assertEqual(len(tap.AD_LOG), 1)

    def test_held_ad_that_closes_itself_early_is_skipped(self):
        start = self.clock.now
        calls = self.use_ui(lost=lambda: self.clock.now < start + 20.0)
        rec = tap.close_current_ad("held", start_lo=start, start_hi=start,
                                   hold=True)
        self.assertIsNone(calls["chain_at"])
        self.assertLess(rec.seconds, 30.0)
        with self.assertRaises(tap.SkipCheck):
            tap.require_ran_past_cooldown(rec, "TA-11")

    def test_leftover_ad_has_unknown_age(self):
        self.use_ui(lost=lambda: True)
        rec = tap.close_current_ad("leftover", known_start=False)
        self.assertFalse(rec.known)
        self.assertIsNone(rec.remaining_after_close)
        self.assertFalse(tap.inside_cooldown(rec, self.clock.now))
        self.assertIn("unknown age", rec.describe())


if __name__ == "__main__":
    unittest.main()
