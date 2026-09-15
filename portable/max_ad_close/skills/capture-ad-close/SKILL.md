---
name: capture-ad-close
description: Captures and registers a new interstitial ad close-button creative when the shared ad closer cannot match the ad's own X. Use during tap_ad_close, close_interstitial_chain, or ad-close matching failures.
---

# Ad-X Capture

Use this workflow whenever the ad's own X is not matched after the StoreKit
sheet closed.

> whenever ad's own X is not matched. First take the screenshot of the ad
> that is showing on the screen. Create and save a new image of that Ad's
> own X and also save the co-ordinates if the X that is showing is new and
> not already saved in the assets or memory.

This skill travels with the portable AppLovin pin + close kit. In Spider it
lived at `.cursor/skills/capture-ad-close/SKILL.md` and was aimed at
`triggerAdPoints` / `verifyAds`. Copy this folder to the other project's
`.cursor/skills/capture-ad-close/` so the same workflow is available there.

## Dev Panel prerequisite

AppLovin must stay pinned. Before the closer runs, the Dev Panel must be
available, then collapsed so it does not cover table or menu controls:

- If the panel is already open, leave it open until setup closes it.
- If the panel button is visible, skip the unlock gesture and expand from
  the current screen.
- If neither is visible, unlock it with that game's Dev Panel gesture.

After confirming the panel is available, collapse it. Do not cold-launch:
that re-locks the panel and drops the AppLovin selection.

## Procedure

1. Trigger this workflow when `tap_ad_close` / `close_interstitial_chain`
   reports:

   `the interstitial's own X never appeared after the StoreKit sheet closed`

   Do not cold-launch or call `recover()`: both can destroy the current ad
   state and reset the Dev Panel.

2. Confirm the correct layer before capturing:
   - The game is still foregrounded (`adapter.in_app()`).
   - The StoreKit product sheet is closed.
   - The playable interstitial is still present (`adapter.lost()`).
   - The target is the ad's circular close X, never the moving `▶▶` skip
     glyph and never the StoreKit product-sheet X.

3. Open `log/ad_unmatched.png` first. `tap_ad_close()` writes this full
   frame while the playable ad is still present, immediately before it
   reports an unmatched X. Do not take a second live screenshot: by then
   the ad may already have dismissed itself.

   If the in-run capture is unexpectedly absent while the ad is still live,
   capture it without restarting the app:

   ```python
   ad_screen = adapter.shoot("ad_unmatched")
   ```

   The full ad screenshot stays under `log/`; it is git-ignored. Only after
   inspecting this capture should the close-button crop be created.

4. Measure the X in capture-pixel coordinates. The iPhone 11 reference space
   is `828×1792`. Record the centre of the circular X in `ad_screen`, not the
   top-left of the crop.

5. Check whether the creative is already known:
   - Compare the live frame against every `assets/ad_close*.png` in this kit
     and against the same names in the game's template directory.
   - Also compare the measured centre with every existing
     `AD_CLOSE_COORDS` entry in `closer.py`.
   - If an existing crop matches or the centre is within a few pixels of a
     known coordinate, do not add a duplicate. Report that it is already
     registered.

6. If it is genuinely new:
   - Crop a `54×54` RGB PNG centred on the X.
   - Save it as the next unused `ad_close_creative_NN.png` in **both**
     this kit's `assets/` and the directory the game's `find()` / `tap()`
     already search. Never replace an existing creative.
   - Add the measured centre under the same name in `AD_CLOSE_COORDS` in
     `closer.py`.
   - `tap_ad_close()` already iterates every `ad_close*.png`, so do not add
     a one-off lookup branch.

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
   and measured coordinate. Do not rerun the ad test unless the user
   explicitly asks.
