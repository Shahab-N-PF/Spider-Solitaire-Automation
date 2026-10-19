---
name: capture-ad-close
description: Captures and registers a new interstitial ad close-button creative when triggerAdPoints or the shared ad closer cannot match the ad's own X. Use during triggerAdPoints, verifyAds, tap_ad_close, or ad-close matching failures.
---

# Ad-X Capture

Use this workflow whenever the ad's own X is not matched while verifying
`triggerAdPoints`.

> whenever ad's own X is not matched while verifying triggerAdPoints . First
> take the screenshot of the ad that is showing on the screen. Create and save
> a new image of that Ad's own X and also save the co-ordinates if the X that
> is showing is new and not already saved in the assets or memory.

## triggerAdPoints prerequisite

`prepare()` puts MAX in Test Mode on Pangle with
`max_test_mode.ensure_network("Pangle", capture=False)` — the same steps as
`verifyAds`: relaunch Spider into a fresh session, enable Test Mode (another
relaunch), tick Pangle. That also re-unlocks the Dev Panel, which both
synthetic wins need. An ad that closes without Pangle's skip or X is a live
ad: its check fails as "live ad served" and Test Mode is re-enabled — do NOT
register a live ad's X.

## Procedure

1. Trigger this workflow when `tests/triggerAdPoints.py` or the shared closer
   used by `tests/verifyAds.py` reports:

   `the interstitial after <where> was still up after <N>s and no native
   Close, skip or ad X closed it`

   Do not cold-launch or call `recover()`: both can destroy the current ad
   state and reset the Dev Panel.

2. Confirm the correct layer before capturing:
   - Spider is still foregrounded (`ui.in_app()`).
   - MAX is in Test Mode (ads only ever come from a test network; a live
     ad means Test Mode was lost — fix that, do not register its X).
   - The playable interstitial is still present (`ui.lost()`).
   - The target is the ad's circular close X. A FIXED skip glyph (like
     Pangle's double-arrow) is registered separately — see *Registering a
     skip glyph* below.

3. Open `log/ad_unmatched.png` first. `ui.tap_ad_close()` writes this full
   frame while the playable ad is still present, immediately before it reports
   an unmatched X. Do not take a second live screenshot: by then the ad may
   already have dismissed itself.

   If the in-run capture is unexpectedly absent while the ad is still live,
   capture it without restarting the app:

   ```python
   ui.launch(settle=1.0)
   ad_screen = ui.shoot("ad_unmatched")
   ```

   The full ad screenshot stays under `log/`; it is git-ignored. Only after
   inspecting this capture should the close-button crop be created.

4. Measure the X in capture-pixel coordinates. The iPhone 11 reference space
   is `828×1792`. Record the centre of the circular X in `ad_screen`, not the
   top-left of the crop.

5. Check whether the creative is already known:
   - Compare the live frame against every `assets_unity/ad_close*.png`.
   - Also compare the measured centre with every existing
     `AD_CLOSE_COORDS` entry.
   - If an existing crop matches or the centre is within a few pixels of a
     known coordinate, do not add a duplicate. Report that it is already
     registered.

6. If it is genuinely new:
   - Crop a `54×54` RGB PNG centred on the X. If the X is an opaque circle
     that can sit on different backgrounds, crop from inside the circle
     instead (`ad_close_creative_04` is 36×36) so the corners carry no
     background.
   - Save it as the next unused
     `assets_unity/ad_close_creative_NN.png`; never replace an existing
     creative.
   - Add the measured centre under the same name in `AD_CLOSE_COORDS` in
     `unity_ui.py`.
   - `tap_ad_close()` already iterates every `ad_close*.png`, so do not add a
     one-off lookup branch.

   Existing reference coordinates are:

   ```python
   AD_CLOSE_COORDS = {
       "ad_close_creative_04": (768, 156),   # Pangle test video end card
   }
   AD_CLOSE_REF_SIZE = (828, 1792)
   ```

7. Stop after registering the new crop and coordinate. Report the asset path
   and measured coordinate. Do not rerun `triggerAdPoints` unless the user
   explicitly asks.

## Registering a skip glyph

Some networks close (or skip to an end card) from a skip glyph that never
moves — Pangle's grey double-arrow at (767, 171), about 5 s into the ad. Only
a glyph seen at the SAME spot on at least three ads qualifies; one that
moves between creatives (like the old live ads' `▶▶`) must stay unregistered.

1. Sample frames of a live ad without touching it, and confirm the glyph's
   centre is identical across creatives.
2. Crop 36×36 from INSIDE the glyph's circle (no background in the corners)
   and save it as `assets_unity/ad_skip_<network>.png`.
3. Add the centre to `AD_SKIP_COORDS` in `unity_ui.py` and a `THRESH` entry
   of 0.9. Check the crop against every saved Spider capture in `log/` (best
   score must stay well under 0.9) and against the network's end-card X,
   which may sit only a few pixels away.
4. `_tap_ad_skip()` iterates `AD_SKIP_COORDS`, and the closer loop tries it
   after native Close and before the X crops, so no new branch is needed.

Existing skip coordinates:

```python
AD_SKIP_COORDS = {"ad_skip_pangle": (767, 171)}
_AD_SKIP_POS_TOL = 40
```
