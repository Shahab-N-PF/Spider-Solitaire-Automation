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

Before the five trigger rules begin, the Dev Panel must be available:

- If the panel is already open (`dev_complete_game` is visible), leave it open
  until the prerequisite closes it for the test.
- If the panel is closed but its button (`dev_panel`) is visible, skip the
  unlock gesture and expand it from the current screen.
- If neither is visible, enable it first with `ui.open_dev_panel()`. That
  helper walks to About and performs the rapid emblem taps only when needed.

After confirming the panel is available, collapse it with
`ui.close_dev_panel()` so it does not cover the table or menu controls.

## Procedure

1. Trigger this workflow when `tests/triggerAdPoints.py` or the shared closer
   used by `tests/verifyAds.py` reports:

   `the interstitial's own X never appeared after the StoreKit sheet closed`

   Do not cold-launch or call `recover()`: both can destroy the current ad
   state and reset the Dev Panel.

2. Confirm the correct layer before capturing:
   - Spider is still foregrounded (`ui.in_app()`).
   - The StoreKit product sheet is closed.
   - The playable interstitial is still present (`ui.lost()`).
   - The target is the ad's circular close X, never the moving `▶▶` skip glyph
     and never the StoreKit product-sheet X.

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
   - Crop a `54×54` RGB PNG centred on the X.
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
       "ad_close": (50, 136),
       "ad_close_creative_02": (55, 139),
       "ad_close_creative_03": (57, 145),
   }
   AD_CLOSE_REF_SIZE = (828, 1792)
   ```

7. Stop after registering the new crop and coordinate. Report the asset path
   and measured coordinate. Do not rerun `triggerAdPoints` unless the user
   explicitly asks.
