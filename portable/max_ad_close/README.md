# Portable AppLovin pin + interstitial close

Copy this folder into another FingerArts / PeopleFun Unity Airtest project that
already has a Dev Panel and **Max Debugger**. It does not unlock that panel and
does not change Spider's live driver.

The robustness is not a lucky crop. It is a two-step journey:

1. Pin **AppLovin** as the MAX live network so the playable ad actually shows a
   closable X.
2. Close the **StoreKit product sheet first**, then the **ad's own X**.

Without the pin, a 5-minute watch produced one StoreKit X and the game never
came back.

```
online → Dev Panel → Max Debugger
     → scroll to Ads (visible "Select Live Network" or "Live Network")
     → open picker (navigation bar, not the static text)
     → AppLovin + checkmark → Back → Done → collapse panel
     → reach a table → wait ~30s → leave
     → wait_lost (still in-app, game UI gone)
     → tap_store_close (native Close)
     → tap_ad_close (native Close, then ad_close*.png near registered centre)
     → game UI recognizable again
```

## What transfers vs what you rewrite

**Copy as-is (AppLovin MAX native UI + close policy)**

- MAX Mediation Debugger is UIKit over Unity. Foreground stays the game.
  Title, Ads row, picker, and Close buttons are **text in WDA**.
- Interstitial chain: video ~15s **auto-opens** an in-app StoreKit sheet;
  closing it reveals the playable X. Never tap `▶▶` skip (it moves and scores
  ~0.656 on a plain menu).

**You must supply**

- How to unlock/open **that** game's Dev Panel and tap **Max Debugger**.
- `lost()` landmarks: unique crops of *that* game's screens so "ad is up"
  means none of your UI is visible, while `in_app()` is still true.
- Bundle id, WDA URL/session, screenshot + template-match helpers.
- How you trigger an interstitial (here: ~30s on the table, then Back;
  fallback is the next resume or new deal).

Do **not** cold-launch after pinning. A restart re-locks the Dev Panel and
drops AppLovin.

## Injection checklist

1. Copy `portable/max_ad_close/` into the other repo (keep the folder name or
   rename it; the package is the folder that contains `__init__.py`).
2. Copy `assets/ad_close.png`, `ad_close_creative_02.png`, and
   `ad_close_creative_03.png` into the directory your `find()` / `tap()`
   already search. The kit ships the PNGs; your matcher will not see them
   until they live on that search path.
3. Implement `Adapter` against that driver (see below).
4. After Max Debugger is on screen, call `pin_applovin(adapter)`.
5. Reach a table, dwell ~30s, leave (or next resume/deal), `wait_lost()`,
   then `close_interstitial_chain(adapter, where)`.
6. If the ad X is a new creative, follow
   [`skills/capture-ad-close/SKILL.md`](skills/capture-ad-close/SKILL.md):
   crop `54×54` RGB from `ad_unmatched.png`, save as the next
   `ad_close_creative_NN.png`, add its centre to `AD_CLOSE_COORDS`. Do not
   replace old crops. Copy that skill folder to the other project's
   `.cursor/skills/capture-ad-close/` so the workflow is available there.

`ad_free()` is for leftover/setup ads only. The assertion path that is
waiting for an interstitial must not call it.

There is no `ad_store_close.png` in this kit. StoreKit close is native
`Close` first; a crop is optional.

## Adapter

```python
from max_ad_close import (
    Adapter, pin_applovin, wait_lost, close_interstitial_chain, ad_free,
)

def reopen_debugger():
    # Game-specific: collapse leftover state, expand Dev Panel, tap Max Debugger.
    # Return True once MAX Mediation Debugger is up again.
    ...

adapter = Adapter(
    session=helpers.current_session,   # callable or current sid string
    wda_url=config.WDA_URL,            # e.g. http://127.0.0.1:8100
    bundle_id=config.BUNDLE_ID,
    find=ui.find,                      # name -> (x, y) capture pixels or None
    tap=ui.tap,                        # tap a template; accept reason= if you can
    tap_at=ui.tap_at,                  # capture-space coordinate tap
    lost=ui.lost,                      # True when no game landmark is visible
    in_app=ui.in_app,                  # foreground bundle == your game
    shoot=ui.shoot,                    # save log/<name>.png, return path
    screen_size=ui.screen_size,        # (w, h) capture pixels
    assets_dir=config.UNITY_ASSETS,    # where find() looks; copy the PNGs here
    active_app=ui.active_app,          # optional; used in failure messages
    have=ui.have,                      # optional; defaults to assets_dir/<name>.png
    seen=ui.seen,                      # optional; defaults to polling find()
    scroll=ui.scroll,                  # optional; else WDA swipe in point space
    expect=ui.expect,                  # optional; defaults to AssertionError
    network_online=lambda: True,       # optional; False disables dismiss_ad()
    reopen_max_debugger=reopen_debugger,
    close_dev_panel=ui.close_dev_panel,
    game_name="Your Game",
)

# After YOU opened Max Debugger:
pin_applovin(adapter)

# After YOU triggered the leave-game interstitial:
wait_lost(adapter, timeout=20)
close_interstitial_chain(adapter, "leaving the game",
                         store_timeout=90, ad_timeout=30)
```

Spider wiring (this repo) looks the same, with `unity_ui` as `ui` and
`reopen` as `ui.is_on("dev_max_debugger") or (ui.open_dev_panel() and
ui.tap("dev_max_debugger", settle=4.0))`.

## Pin AppLovin

`pin_applovin()` assumes the debugger is already open.

1. Confirm title `MAX Mediation Debugger` with a **predicate** query
   (`name == '…'`). Do not enumerate StaticTexts by class — that table timed
   out at 15s and looked empty.
2. Scroll **down** until a **visible** row is either `Select Live Network`
   (empty) or `Live Network` (already persisted). Off-screen rows stay in the
   tree with garbage rects (`y=102`, AppLovin `y=-409`). If 8 down-swipes
   miss, **Done + reopen** via `adapter.reopen_max_debugger` — the list is
   one-direction; a leftover scroll puts Ads above the viewport.
3. Tap that row. Confirm the **navigation bar** `Select Live Network` before
   looking for AppLovin. The name also lives under *Completed SDK
   Integrations* on the previous page; both screens also have a static text
   "Select Live Network."
4. Tap `AppLovin` only if the Live Network row does not already show it.
   Proof is a **checkmark button** that does not exist until a network is
   selected. Row text does not change.
5. BackButton on the picker, **Done** on the debugger (not Share), then
   `close_dev_panel` if you supplied it.

`close_debugger_overlays(adapter)` unwinds a leftover picker / debugger /
panel without restarting.

## Close the interstitial

```python
# after wait_lost() and in_app()
close_interstitial_chain(adapter, where, store_timeout=90, ad_timeout=30)
#   1. tap_store_close: native button Close, then optional ad_store_close crop
#   2. tap_ad_close:    native Close, then every ad_close*.png near its
#                       registered centre, then scaled AD_CLOSE_COORDS
#   3. success = still in_app() AND not lost()
```

Why this is not flaky on AppLovin:

- **Wait, do not skip.** Video ~15s then StoreKit opens itself.
- **Native Close before pixels.** StoreKit X is a real
  `XCUIElementTypeButton` named `Close`.
- **Crop match is rejected unless it is near the registered centre**
  (`AD_CLOSE_COORDS`, 80px). `ad_close` once hit `(111, 1730)` on first-launch
  chrome and opened the real App Store.
- **Coords are last**, scaled from 828×1792, and only while `in_app()` and
  `lost()`. A tap that leaves the game is a failure, not a close.
- **Unmatched frame is saved first** (`ad_unmatched.png`) so a new creative
  can be cropped without guessing. The full register-a-new-X procedure is
  [`skills/capture-ad-close/SKILL.md`](skills/capture-ad-close/SKILL.md).

Known centres (iPhone 11 capture space):

```python
AD_CLOSE_COORDS = {
    "ad_close": (50, 136),
    "ad_close_creative_02": (55, 139),
    "ad_close_creative_03": (57, 145),
}
AD_CLOSE_REF_SIZE = (828, 1792)
```

## Two silent bugs this kit keeps

- **WDA points vs capture pixels.** Debugger rects are points (414×896 on
  iPhone 11). Template taps are capture pixels (828×1792). `WdaAx.tap_point`
  uses W3C actions in point space. Mixing them lands at half position and
  "succeeds."
- **`kind` on `WdaAx.first` is load-bearing.** Same name exists as StaticText
  and NavigationBar. Ignoring class made `on_window()` pass while still on
  the debugger.

## Files

| Path | Role |
|---|---|
| `adapter.py` | Protocol the other project implements |
| `wda_ax.py` | Predicate lookups, visible-only rects, named taps in point space |
| `pin_applovin.py` | Ads scroll → picker → AppLovin + checkmark → Back/Done |
| `closer.py` | `wait_lost`, store X, ad X, `ad_free` |
| `assets/ad_close*.png` | Known playable-ad X creatives |
| `skills/capture-ad-close/SKILL.md` | Register a new X from `ad_unmatched.png` |
