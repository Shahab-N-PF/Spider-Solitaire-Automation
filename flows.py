"""Reusable driver helpers shared by the test scripts.

Keeps each test in tests/ small: they describe *what* to verify, while the
mechanics of launching, connecting, matching templates, tapping and
screenshotting live here.

Convention (see CLAUDE.md):
  - Launch/foreground the game with helpers.launch_app() (WDA session), never
    airtest start_app().
  - Drive the menu with image Template(...) matches — this game renders its menu
    as stylised graphics with no accessibility IDs, so Poco names are unreliable.
  - Prefer exists() for assertions and touch() for taps.

Templates live in assets/ (committed) and are cropped from log/*.png.
"""
import logging
import os
import time

import config
import helpers
from airtest.core.api import connect_device, exists, snapshot, swipe, text, touch, sleep
from airtest.core.cv import Template
from airtest.core.settings import Settings as ST

logging.getLogger("airtest").setLevel(logging.WARNING)

# Every template here is cropped from THIS device's own screenshots, so it always
# appears at the same scale/rotation — plain template matching finds it. Airtest's
# default strategy also runs a keypoint matcher (SIFT + homography) as a fallback,
# which never helps at matching resolution but dominates the cost of every
# "element absent" check (a full, failing SIFT pass per call — the source of the
# `findHomography` warnings). Restricting to template matching makes negative
# matches ~5-10x cheaper, which is where these UI flows spend most of their time.
ST.CVSTRATEGY = ["tpl"]

# exists() is used here as an INSTANT "is it on screen right now?" check — the
# waiting/polling is done by seen(). But airtest's exists() defaults to looping
# for FIND_TIMEOUT_TMP (3s) before giving up, so every "element absent" check
# (and there are many, especially in back_to_menu) burned ~3s. Shrink it to a
# single-shot check; seen() still governs real waits via its own poll loop.
ST.FIND_TIMEOUT_TMP = 0.5

# ── template registry ─────────────────────────────────────────────
# Threshold is deliberately a touch below airtest's 0.7 default: the menu
# labels sit on a subtly textured background, so we allow a little slack while
# still requiring a confident match.
_THRESH = 0.7


def T(name: str, threshold: float = _THRESH) -> Template:
    """Template for assets/<name>.png (extension optional)."""
    fn = name if name.endswith(".png") else name + ".png"
    return Template(os.path.join(config.ASSETS, fn), threshold=threshold)


# Named main-menu anchors (see assets/).
#
# Spider's main menu is Play / Stats / Options / Help / About (+ More Games and
# Choose Look down the left). Most of these templates are INHERITED from the
# sibling Solitaire project — FingerArts games share the menu chrome — but note
# Spider has NO "Daily" button (that's a Solitaire item). `menu_daily` is kept
# only for reference; do not assert it. `menu_about` was cropped from a real
# Spider screenshot. There is intentionally no game-title anchor — the title
# text differs per game, so the menu checks below key off the Play/Options
# labels instead.
PLAY, DAILY, STATS, OPTIONS, HELP, ABOUT = (
    "menu_play", "menu_daily", "menu_stats", "menu_options", "menu_help",
    "menu_about",
)
MORE_GAMES, CHOOSE_LOOK = "more_games", "choose_look"
# The Spider emblem/logo at the top of the menu is itself tappable — it opens
# the same About screen as the About button.
LOGO = "menu_logo"

# The promo-icon strip on the left of the home screen: 5 FingerArts game icons
# (above More Games) that animate in a few seconds after the menu appears.
# Cropped from a real Spider screenshot (log/diag_home_2s.png).
PROMO_ICONS = (
    "promo_solitaire",   # green, playing cards
    "promo_sudoku2",     # brown, "S²"
    "promo_cardgames",   # brown, four card suits
    "promo_freecell",    # blue, crown
    "promo_spiderette",  # orange, spider
)

# Positive per-screen anchors: the title/heading unique to each sub-screen, so
# tests can assert they opened the RIGHT screen — not merely that the menu
# closed. Cropped from log/OptionsPage.png / StatsPage.png / HelpPage.png.
# (Help has no title word in its bar, so its anchor is the "Introduction"
# section heading.)
SCREEN_OPTIONS, SCREEN_STATS, SCREEN_HELP = (
    "screen_options", "screen_stats", "screen_help",
)
# The gold, underlined "Reset Statistics" link at the very bottom of the Stats
# page (below the fold — scroll to it). Tapping it pops TWO sequential confirm
# dialogs ("reset local scores?" then "just to be on the safe side..."), both of
# whose "Yes" buttons match CONFIRM_YES. Used by tests/resetStats.py.
RESET_STATS = "reset_stats"
# The Options screen has a "Contact Us" button in its top-right (red) bar that
# opens the Helpshift support flow. CONTACT_US anchors the button; SCREEN_CONTACT
# anchors the screen it opens (used by verifyHelpShift to prove the tap landed).
CONTACT_US = "contact_us"
SCREEN_CONTACT = "screen_contact"
# The × close button in the Helpshift header (left of "PeopleFun Support"). Tapping
# it dismisses the support screen and returns to the Options screen.
HELPSHIFT_CLOSE = "helpshift_close"
# The About screen (Play/logo/version/copyright + help/FAQ/feedback links),
# opened by BOTH the About button and the menu logo. Anchor = the copyright
# line (stable across app versions, unlike the version number).
SCREEN_ABOUT = "screen_about"
# The "frequently asked questions" link on the About screen — opens the FAQ
# screen (same one the in-game menu's FAQ opens; anchored by SCREEN_FAQ below).
ABOUT_FAQ = "about_faq"
# The About screen's "Version X.Y.Z" line is a hidden toggle: tapping it swaps
# the marketing version for the internal debug build id ("<n> build <hash>").
# ABOUT_VERSION anchors the "Version" word to tap; DEBUG_BUILD anchors the
# "build" text that then appears (proof the debug/build info was revealed). Both
# crop the label word only, so they survive version/build-number changes.
ABOUT_VERSION = "about_version"
DEBUG_BUILD = "debug_build"
# After tapping the logo 10x on the (build-info) About screen, a numeric keypad
# appears to enter the QA/debug passcode (QA_CODE). Entering it TOGGLES QA mode;
# the prompt then reads "Enabling QA" or "Disabling QA" depending on which way it
# flipped (ENABLING_QA / DISABLING_QA). ABOUT_LOGO_XY is the Spider-emblem centre
# on the About screen (capture px), tapped by coordinate so the 10 taps fire as a
# fast burst. See enter_qa_code() / set_qa() and tests/openDebugTools.py.
ABOUT_LOGO_XY = (414, 430)
QA_CODE = "943010"
ENABLING_QA = "enabling_qa"
DISABLING_QA = "disabling_qa"
# The "CONFIDENTIAL / <build> / <ver>" debug watermark this internal build paints
# on the top-left of the HOME SCREEN — present ONLY while QA debug mode is ON, so
# it is the reliable QA-state signal (far better than the brief, ambiguous
# Enabling/Disabling prompt). See qa_enabled() / set_qa().
QA_WATERMARK = "qa_watermark"

# The Choose Look window (a modal with "Surface" and "Cards" tabs + a × close
# button, opened by the menu "Choose Look"). Each tab has a distinctive toggle
# used as its anchor. Not a full-screen sub-screen — it overlays the menu.
SCREEN_SURFACE = "screen_surface"   # "Simulate Depth" — the Surface tab is showing
SCREEN_CARDS = "screen_cards"       # "Extra Large Card-Symbols" — the Cards tab is showing
LOOK_SURFACE_TAB = "look_surface_tab"  # the "Surface" tab button
LOOK_CARDS_TAB = "look_cards_tab"   # the "Cards" tab button
LOOK_CLOSE = "look_close"           # the × close button (both tabs)
# "More Games" opens an in-app cross-promo page ("Tap any game to download it!",
# red curtains) — NOT the App Store. Tapping a game there would open the App
# Store, so tests only verify the page opened and go back. Its own "◄ back"
# button is matched by the existing BACK_* templates.
SCREEN_MORE_GAMES = "screen_more_games"

# Difficulty picker + in-game anchors (Spider-specific — NOT inherited).
#
# Unlike regular Solitaire, Spider's "Play" does not deal immediately: it opens
# a difficulty picker (Easy / Medium / Hard / Bold / Expert, plus Resume). You
# must choose a difficulty before the table appears, and if a game is already
# paused, choosing one prompts "abandon the currently paused game?" (Yes/No).
# IN_GAME is the top-bar "menu" button, present for the whole game — a durable
# positive proof that a game was actually dealt. All cropped from real Spider
# screenshots (log/diag_after_play.png, log/diag_after_easy.png, log/diag_table.png).
EASY = "difficulty_easy"
MEDIUM = "difficulty_medium"    # picker labels below Easy — each deals a harder game
HARD = "difficulty_hard"
BOLD = "difficulty_bold"
EXPERT = "difficulty_expert"
# All five difficulty labels on the Play picker, easiest→hardest. verifyPlay
# exercises Easy; verifyDifficultyLevels covers Medium/Hard/Bold/Expert.
DIFFICULTIES = (EASY, MEDIUM, HARD, BOLD, EXPERT)
# "Resume" — the red banner on the Play picker, shown only when a game is paused;
# tapping it returns to that game instead of dealing a new one.
RESUME = "resume"
CONFIRM_YES = "confirm_yes"     # "Yes" on the abandon-paused-game dialog
IN_GAME = "in_game_menu"        # top-bar "menu" button, shown on the table
HINTS = "hints"                 # "tap for hints" control on the game table
QA_BADGE = "qa_badge"           # "QA" badge (bottom-right), shown when QA mode is on
SYNTHETIC_WIN = "synthetic_win"  # "Synthetic Win" heading of the QA panel the badge opens
QA_90_99 = "qa_90_99"           # the "90% - 99%" completion option in the QA panel
QA_WIN = "qa_win"               # the "WIN" action in the QA panel (forces a synthetic win)

# The in-game menu bar (opened by tapping the top-bar IN_GAME "menu" button): a
# grid of red buttons — replay / abandon / options / new / help / faq. Named
# ingame_* so they don't collide with the main-menu labels (menu_options, etc.).
# Replay pops an in-app "play this game again?" Yes/No (positive = CONFIRM_YES).
# Options/Help/FAQ open full screens (backed by BACK_BAR); New deals a fresh game.
INGAME_REPLAY = "ingame_replay"
INGAME_ABANDON = "ingame_abandon"
INGAME_OPTIONS = "ingame_options"
INGAME_NEW = "ingame_new"
INGAME_HELP = "ingame_help"
INGAME_FAQ = "ingame_faq"
SCREEN_FAQ = "screen_faq"       # the "FAQ" title header of the in-game FAQ screen
SCREEN_VICTORY = "screen_victory"  # "leaderboards" — anchor of the post-win results/victory screen

# Navigation chrome. Sub-screens (Options/Stats/Help) and the game table each
# have a top-left "◄ back" button, but in DIFFERENT fonts (serif on the red
# sub-screen bar, monospace on the green game bar), so they need separate
# templates. Leaving the game table can also pop a cross-promo interstitial ad
# over the menu; AD_CLOSE is its "×" close button. Used to walk back to the menu
# without killing/relaunching the app.
BACK_BAR = "back_bar"           # "◄ back" on sub-screens (red bar)
BACK_GAME = "back_game"         # "◄ back" on the game table (green bar)
AD_CLOSE = "ad_close"           # "×" on a cross-promo interstitial ad

# First-launch pop-ups (only on a fresh install / after resetting App Tracking).
# Verified against a real reinstall: launch -> Terms & Conditions ("Continue")
# -> App Tracking Transparency ("Allow") -> main menu. Both are dismissed by
# IMAGE MATCHING: the T&C pop-up is in-app, and although the ATT prompt is a
# system alert, WDA's app.alerts API does NOT see it (it's a separate process) —
# but its buttons are on screen, and WDA taps hit them, so we match+tap.
TC_ACCEPT = "tc_accept"         # "Continue" on the Terms & Conditions pop-up
ATT_ALLOW = "att_allow"         # "Allow" on the App Tracking Transparency prompt
ATT_NOTRACK = "att_notrack"     # "Ask App Not to Track" (alternative to ATT_ALLOW)

# Offline preflight anchor. Airplane Mode is the recommended way to take this
# rig offline (WDA keeps working over the USB cable via iproxy), and it puts an
# airplane glyph in the status bar — the most direct "device is offline" signal
# we can observe. Crop it once, in Airplane Mode, into assets/status_airplane.png
# (resolution-specific, like every template — so on the iPhone 14 Pro Max it goes
# in iphone14/assets/). See assert_offline() and tests/preflight_offline.py.
STATUS_AIRPLANE = "status_airplane"


# ── lifecycle ─────────────────────────────────────────────────────
def launch_to_menu(settle: float = 3.0):
    """Ensure the game is foregrounded on the main menu; connect Airtest.

    Prefers navigating back to the menu with the on-screen back buttons over
    killing and relaunching the app, so the app stays alive across tests (a
    previous test can leave us on the table or a sub-screen). Only (re)launches
    as a bootstrap when we're not in a state we can walk back from — e.g. the
    app isn't running yet at the very start of a run. That bootstrap goes through
    handle_first_launch, so a FIRST launch after install (with its T&C -> ATT
    pop-up sequence) is cleared to the menu before returning, not just a warm
    relaunch.

    Raises if BUNDLE_ID is unset so tests fail loudly rather than driving
    whatever app happens to be foregrounded.
    """
    if not config.bundle_id_is_set():
        raise RuntimeError(
            "BUNDLE_ID is not set — edit config.py or export BUNDLE_ID=..."
        )
    os.makedirs(config.LOG, exist_ok=True)
    connect_device(config.DEVICE_URI)
    dismiss_popups()                    # auto-handle any native alert on entry
    if back_to_menu():                  # already on / can walk back to the menu
        return
    # Bootstrap: the app isn't in a state we can walk back from (not running at
    # the start of a run, or a FIRST launch after install where the T&C -> ATT
    # prompts still have to be cleared before the menu appears). Delegate to
    # handle_first_launch, which launches and then WAITS-and-RETRIES — polling for
    # the menu and clearing each pop-up as it shows — rather than a single fixed
    # sleep + one dismiss_popups pass, which races the delayed, sequential
    # first-launch prompts (and the splash / Game Center toast) and can return
    # with a prompt still covering the menu.
    handle_first_launch(settle=settle)
    return helpers.current_session()


def handle_first_launch(settle: float = 3.0, max_rounds: int = 12) -> bool:
    """Launch the game and clear the first-launch pop-up sequence to the menu.

    On a fresh install the game shows, in order: a Terms & Conditions pop-up
    (in-app, "Continue") and the iOS App Tracking Transparency prompt ("Allow"),
    then the menu. This launches and repeatedly runs dismiss_popups() (the
    generic "tap the positive option" sweep) until the menu shows. Idempotent:
    on a non-first launch there are no pop-ups. Returns True at the menu.
    """
    sid = helpers.launch_app()
    sleep(settle)                       # let the splash + first prompt appear
    connect_device(config.DEVICE_URI)
    for _ in range(max_rounds):
        if on_main_menu(timeout=1.5):
            return True
        if dismiss_popups(sid, rounds=1) == 0:
            sleep(1.0)                  # nothing actionable yet — let it settle
    return on_main_menu(timeout=2.0)


def dismiss_popups(sid: str = None, rounds: int = 8) -> int:
    """Generic pop-up handler: clear native alerts + known launch pop-ups by
    tapping the POSITIVE option, until none remain (or `rounds` reached).

    Each pass dismisses one of, in order:
      1. an iOS system alert WDA can see — read its buttons and tap the
         affirmative one (helpers.positive_button: Allow / OK / Yes / Continue …,
         never Don't Allow / Cancel / No);
      2. a system prompt WDA CAN'T see (App Tracking) or the in-app Terms &
         Conditions pop-up — tapped by image (ATT_ALLOW / TC_ACCEPT);
      3. a cross-promo interstitial ad (× ).
    Returns how many were dismissed. Safe to call anytime — a no-op when the
    screen is clear — so launch_to_menu() runs it automatically on every launch.
    """
    sid = sid or helpers.current_session()
    dismissed = 0
    for _ in range(rounds):
        if not _dismiss_one(sid):
            break
        dismissed += 1
        sleep(1.0)                      # let the screen settle after dismissing
    return dismissed


def _dismiss_one(sid: str) -> bool:
    """Dismiss a single pop-up by its positive option. False if none is present."""
    if sid:                             # system alert WDA can see -> affirmative button
        buttons = helpers.alert_buttons(sid)
        if buttons:
            helpers.alert_tap(sid, helpers.positive_button(buttons))
            return True
    for anchor in (ATT_ALLOW, TC_ACCEPT):   # ATT / in-app T&C, by image
        if _tap_if_present(anchor):
            return True
    return dismiss_ad(timeout=0.5)      # cross-promo interstitial


def _tap_if_present(name: str) -> bool:
    """Tap template <name> — but only if its asset exists AND it's on screen.

    Lets the first-launch handler stay robust when a pop-up's template hasn't
    been cropped yet (e.g. TC_ACCEPT): the step is skipped rather than crashing.
    """
    if not os.path.exists(os.path.join(config.ASSETS, name + ".png")):
        return False
    if exists(T(name)):
        touch(T(name))
        return True
    return False


# ── interactions ──────────────────────────────────────────────────
def start_game(difficulty: str = EASY, shoot_picker: str = None):
    """From the main menu, start a game: tap Play, choose a difficulty, deal.

    Spider's Play opens a difficulty picker rather than dealing directly, so this
    is at least two taps: Play, then the difficulty label. If a game is already
    paused, choosing a difficulty prompts to abandon it — we confirm (Yes) to
    deal a fresh game. Returns as soon as the taps are done; the deal animation
    may still be running, so call capture_table() (or seen(IN_GAME)) afterwards
    to wait for the table. Raises if the picker never appears.

    If `shoot_picker` is given, the difficulty picker is screenshotted into
    log/<shoot_picker>.png once it appears and *before* a difficulty is chosen
    (so the capture is of the picker itself, not the dealt table).
    """
    tap(PLAY)
    if not seen(difficulty):
        raise AssertionError(
            f"difficulty picker did not appear after tapping Play "
            f"(anchor {difficulty} not found)"
        )
    if shoot_picker:
        shoot(shoot_picker)             # capture the picker before choosing a level
    tap(difficulty)
    # Choosing a difficulty while a game is paused asks to abandon it first.
    if seen(CONFIRM_YES, timeout=2.0):
        tap(CONFIRM_YES)


def capture_table(name: str, cards_settle: float = 2.0, timeout: float = 8.0,
                  attempts: int = 3) -> str:
    """Once the game table is shown, let the cards load, then screenshot it.

    Waits for the in-game top bar to appear (proof the table is up), then sleeps
    `cards_settle` seconds so the deal/card animation finishes before capturing —
    otherwise the screenshot can land mid-deal with cards still flying in.

    Crucially, it RE-ASSERTS the top bar is still on screen right before the
    shot: a rules/tutorial overlay can slip in during the settle, and without
    this re-check we'd shoot that overlay yet still "pass". If an overlay is up
    we dismiss it (back) and retry; if the table never settles we raise instead
    of capturing the wrong screen. Writes log/<name>.png and returns its path.
    Raises if the table never appears / isn't showing at capture time.
    """
    if not seen(IN_GAME, timeout=timeout):
        raise AssertionError(
            "game table did not appear (in-game 'menu' bar not found)"
        )
    for _ in range(attempts):
        sleep(cards_settle)                 # let the dealt cards finish loading
        # The table is genuinely showing only if the in-game bar is up AND the
        # rules/tutorial overlay (its "Introduction" heading) is NOT — IN_GAME
        # alone can loosely match that overlay, so we exclude it explicitly.
        on_rules = exists(T(SCREEN_HELP))
        if exists(T(IN_GAME)) and not on_rules:
            return shoot(name)
        if on_rules:
            tap_back()                      # dismiss the rules overlay, then retry
    raise AssertionError(
        "game table not on screen at capture time — a rules/overlay screen "
        "appeared during the settle (the capture would have been wrong)"
    )


def open_ingame_menu(timeout: float = 4.0) -> bool:
    """Ensure the in-game menu bar (replay/abandon/options/new/help/faq) is open.

    Idempotent: taps the top-bar "menu" button (IN_GAME) only if the bar isn't
    already showing — tapping it while open would close it. Returns True once the
    bar's Replay button is visible. Used before each menu-bar action, since those
    actions (Replay/Options/Help/FAQ/New) return to the plain table with the bar
    closed.
    """
    if seen(INGAME_REPLAY, timeout=1.0):
        return True
    touch(T(IN_GAME))
    sleep(1.0)
    return seen(INGAME_REPLAY, timeout=timeout)


def open_choose_look(retries: int = 4) -> bool:
    """Open the Choose Look window from the menu, showing the Surface tab.

    Two wrinkles handled here: (1) the menu's promo-icon strip can animate in and
    eat the first tap, so we retry; (2) the window reopens on whichever tab
    (Surface/Cards) was last used, so once it's open we normalise to the Surface
    tab. Returns True once the Surface tab is showing.
    """
    opened = False
    for _ in range(retries):
        if exists(T(SCREEN_SURFACE)) or exists(T(SCREEN_CARDS)):
            opened = True
            break
        if exists(T(CHOOSE_LOOK)):
            touch(T(CHOOSE_LOOK))
        sleep(1.5)
    if not opened:
        return False
    if not exists(T(SCREEN_SURFACE)):   # opened on the Cards tab -> switch to Surface
        touch(T(LOOK_SURFACE_TAB))
    return seen(SCREEN_SURFACE, timeout=4.0)


def open_options(timeout: float = 6.0) -> bool:
    """Open the Options sub-screen and STAY on it (no walk back to the menu).

    Unlike visit_sub_screen (which returns to the menu afterwards), this leaves
    the app on the Options screen. Used by verifyOptions before it chains into
    verifyHelpShift, and by verifyHelpShift to satisfy its "on the Options page"
    pre-req when it's run on its own. Idempotent: a no-op if Options is already
    showing. Returns True once the Options header is on screen.
    """
    connect_device(config.DEVICE_URI)      # exists() below needs a live device
    if exists(T(SCREEN_OPTIONS)):
        return True
    launch_to_menu()
    expect(on_main_menu(), "open_options: did not reach the main menu")
    tap(OPTIONS)
    return seen(SCREEN_OPTIONS, timeout=timeout)


def seen(name: str, timeout: float = 8.0, threshold: float = _THRESH) -> bool:
    """True if template <name> appears on screen within `timeout` seconds.

    Deadline-based on the wall clock: a present template returns on the first
    check, and an absent one polls until `timeout` actually elapses. (The old
    fixed poll-count version slept 0.5s AFTER each exists(), so its real runtime
    was timeout + polls*exists_cost — roughly double — which dominated the
    walk-back path.)
    """
    deadline = time.time() + timeout
    while True:
        if exists(T(name, threshold)):
            return True
        if time.time() >= deadline:
            return False
        sleep(0.2)


def tap(name: str, timeout: float = 8.0, threshold: float = _THRESH):
    """Wait for template <name>, then tap it. Raises if it never appears."""
    if not seen(name, timeout, threshold):
        raise AssertionError(f"template not found on screen: {name}")
    touch(T(name, threshold))


def rapid_tap(pos, times: int = 10):
    """Tap a fixed screen coordinate `times` in quick succession, no added delay.

    For hidden debug gestures that count N *rapid* taps. `pos` is an (x, y) in
    capture-pixel space (same space as our screenshots). Uses airtest's
    touch(times=) so the taps fire back-to-back (~0.05s apart) instead of the ~1s
    settle a normal tap uses — and we match on a coordinate, not a template, so no
    per-tap screenshot/re-match slows the burst down.
    """
    touch(pos, times=times)


def type_text(content: str):
    """Type `content` into the focused text field via the device keyboard (WDA).

    Used for the debug/QA passcode entry — types into the on-screen numeric
    keypad's focused field rather than tapping each key by coordinate.
    """
    text(content, enter=False)


def tap_at(pos, settle: float = 1.0):
    """Tap a fixed screen coordinate (capture-pixel space), then settle briefly.

    For on-table controls (the undo/lower/hints cards + numbers) that have no
    stable template of their own — their positions are fixed in the game screen's
    layout, so we tap by coordinate.
    """
    touch(pos)
    sleep(settle)


# ── QA / debug mode ───────────────────────────────────────────────
def enter_qa_code():
    """From the main menu, walk the hidden QA passcode flow and enter QA_CODE.

    About -> tap the "Version" line (reveals the build info) -> tap the Spider
    logo 10x rapidly (opens the passcode keypad) -> type QA_CODE. Entering the
    code TOGGLES QA mode and pops an "Enabling QA" / "Disabling QA" prompt, which
    this LEAVES on screen (it does not return to the menu) so a caller can read
    which way it flipped. Raises if the About screen / build info never appear.
    """
    tap(ABOUT)
    expect(seen(SCREEN_ABOUT), "QA code: the About screen did not open")
    tap(ABOUT_VERSION)
    expect(seen(DEBUG_BUILD),
           "QA code: tapping Version did not reveal the build info")
    rapid_tap(ABOUT_LOGO_XY, times=10)      # hidden gesture -> passcode keypad
    sleep(1.5)                              # let the keypad slide up
    type_text(QA_CODE)
    sleep(1.5)                              # let the Enabling/Disabling prompt show


def qa_enabled(timeout: float = 1.5) -> bool:
    """True if QA debug mode is ON, read from the home-screen debug watermark.

    This internal build paints the 'CONFIDENTIAL / <build>' watermark (QA_WATERMARK)
    on the menu ONLY while QA is enabled, so its presence is a stable, unambiguous
    QA-state signal — unlike the brief Enabling/Disabling prompt the passcode flashes.
    Call while on the main menu.
    """
    return seen(QA_WATERMARK, timeout=timeout)


def set_qa(on: bool, max_toggles: int = 4) -> bool:
    """Force QA debug mode on (True) or off (False) via the toggle passcode.

    QA_CODE only TOGGLES QA, so this reads the real state from the home-screen
    watermark (qa_enabled) and enters the passcode until it matches — a no-op if
    already there. Ends on the main menu. Returns True once QA is confirmed in the
    requested state.

    (openDebugTools enables QA earlier in the suite; verifyMoreGamesIcons calls
    set_qa(False) to guarantee a clean, non-QA menu before its capture.)
    """
    for _ in range(max_toggles):
        launch_to_menu()
        expect(on_main_menu(), "set_qa: could not reach the main menu")
        if qa_enabled() == on:              # already in the requested state
            return True
        enter_qa_code()                     # flip it
        back_to_menu()
    launch_to_menu()
    return qa_enabled() == on


def shoot(name: str) -> str:
    """Screenshot into log/<name>.png and return the path.

    When VIS_SHOTS>1 (baseline-capture mode for visual regression), also writes
    log/<name>.<i>.volshot.png a few times ~0.7s apart, so
    scripts/update_baselines.py can learn which pixels flicker (animation) and
    exclude them from the exact-pixel comparison. Normal runs take one shot.
    """
    fn = name if name.endswith(".png") else name + ".png"
    out = os.path.join(config.LOG, fn)
    snapshot(filename=out)
    for i in range(1, int(os.environ.get("VIS_SHOTS", "1"))):
        sleep(0.7)
        snapshot(filename=os.path.join(config.LOG, fn[:-4] + f".{i}.volshot.png"))
    return out


def scroll(down: bool = True, dist: float = 0.5, duration: float = 0.4):
    """Scroll the current page vertically with a swipe.

    For long screens that run below the fold (Help rules, Options settings).
    down=True reveals content further down (swipes the finger up); down=False
    scrolls back toward the top. `dist` is the fraction of screen height moved.
    The swipe stays inside the content band (below the top bar, above the ad
    banner) so it grabs the scroll view rather than chrome.
    """
    w, h = 828, 1792
    x = w // 2
    span = int(h * dist)
    top, bottom = int(h * 0.30), int(h * 0.82)      # content band
    if down:
        swipe((x, bottom), (x, bottom - span), duration=duration)
    else:
        swipe((x, top), (x, top + span), duration=duration)
    sleep(0.6)                                       # let the scroll settle


def scroll_to(name: str, max_swipes: int = 8, threshold: float = _THRESH) -> bool:
    """Scroll down until template <name> is on screen (or max_swipes). True if found."""
    for _ in range(max_swipes):
        if exists(T(name, threshold)):
            return True
        scroll(down=True)
    return exists(T(name, threshold))


def expect(cond: bool, msg: str):
    """Assert with a readable message (used by the test scripts)."""
    if not cond:
        raise AssertionError(msg)


def on_main_menu(timeout: float = 8.0) -> bool:
    """Heuristic: we're on the main menu if the Play + Options labels show."""
    return seen(PLAY, timeout) and exists(T(OPTIONS))


def visit_sub_screen(anchor: str, shot_name: str, on_screen: str = None):
    """Open a main-menu sub-screen, verify we're on it, capture it, return.

    Asserts we left the menu, and — when `on_screen` is given — that a positive
    anchor unique to the sub-screen is visible, so we know we opened the *right*
    screen rather than merely that the menu closed. Screenshots the screen into
    log/<shot_name>.png, then returns to the menu and confirms we're back.
    """
    launch_to_menu()
    expect(on_main_menu(), "did not start on the main menu")

    tap(anchor)
    # Wait adaptively on the positive anchor (proof the transition finished)
    # instead of a fixed sleep. With no anchor, fall back to a short settle.
    if on_screen is not None:
        expect(seen(on_screen),
               f"tapping {anchor} did not open the expected screen "
               f"(anchor {on_screen} not found)")
    else:
        sleep(1.5)
    expect(not exists(T(PLAY)),
           f"tapping {anchor} did not leave the main menu")
    shoot(shot_name)

    expect(back_to_menu(), f"could not return to the main menu after {anchor}")


def tap_back() -> bool:
    """Tap whichever on-screen '◄ back' button is visible (game or sub-screen).

    Tries the game-table back button first, then the sub-screen one. Both go up
    one screen, so it doesn't matter which matches. Returns False if neither is
    on screen.
    """
    for anchor in (BACK_GAME, BACK_BAR):
        if exists(T(anchor)):
            touch(T(anchor))
            return True
    return False


def dismiss_ad(timeout: float = 2.0) -> bool:
    """Close a cross-promo interstitial ad if one is showing (tap its × button).

    FingerArts games pop these when leaving the table, covering the menu.
    Returns True if an ad was found and dismissed.
    """
    if seen(AD_CLOSE, timeout=timeout):
        touch(T(AD_CLOSE))
        sleep(1.0)
        return True
    return False


def back_to_menu(max_steps: int = 6) -> bool:
    """Return to the main menu using the on-screen back buttons — no relaunch.

    Walks up one screen at a time: if the menu is showing we're done; if a
    cross-promo interstitial is up we close it; otherwise we tap a back button.
    Repeats up to `max_steps` (the table is a couple of screens + a possible ad
    deep). Returns True once the menu is visible, so it doubles as a check that
    we're not in some unknown state (in which case the caller can relaunch).
    """
    for _ in range(max_steps):
        if on_main_menu(timeout=1.0):
            return True
        # A shortish ad check is fine: if an interstitial is up it stays up, and
        # the loop re-checks each pass, so we still catch a slow-rendering one.
        if dismiss_ad(timeout=0.6):
            continue
        if exists(T(LOOK_CLOSE)):       # Choose Look modal closes via × (no back button)
            touch(T(LOOK_CLOSE))
            sleep(0.7)
            continue
        if not tap_back():
            break                       # not on menu, no ad/modal, no back button
        sleep(0.7)                      # brief settle; next on_main_menu waits adaptively
    return on_main_menu(timeout=2.0)


# ── offline preflight ─────────────────────────────────────────────
# Why this is behavioral: iOS gives us no per-device internet-reachability query
# over USB (WDA has no such endpoint; libimobiledevice/tidevice don't report live
# connectivity). So we confirm the device is offline from what the APP shows.
#
# Authoritative signal: the Airplane-Mode icon in the status bar. Airplane Mode is
# the recommended way to take this rig offline (WDA still works over the USB cable
# via iproxy), and it draws an airplane glyph in the status bar — a direct, stable
# "radios are off" indicator. It needs a one-time per-device calibration crop
# (assets/status_airplane.png), because it can't be cropped while online.
#
# Weaker fallback (only if the icon template isn't cropped yet): no cross-promo
# interstitial ad on screen — those load only online. This is best-effort: at a
# resolution whose AD_CLOSE template doesn't match, absence can't be trusted, so
# assert_offline() keeps the airplane icon as the default requirement.
#
# The surest guarantee remains enabling Airplane Mode by hand before a run; this
# assertion exists to catch the "forgot to go offline" mistake before it pollutes
# a capture/baseline with a live ad.

def offline_report(settle: float = 3.0) -> dict:
    """Reach the menu, let ads settle, and collect offline signals (no assert).

    Captures log/preflight_offline.png as evidence (also the frame to crop the
    airplane-icon template from during first-time calibration). Returns a dict:
      - shot:              path to the evidence capture
      - airplane_template: whether assets/<STATUS_AIRPLANE>.png exists yet
      - airplane_icon:     True/False if the template exists (else None)
      - no_interstitial:   True if no cross-promo interstitial (AD_CLOSE) is shown
    """
    launch_to_menu()
    sleep(settle)                       # give any live ad time to load if online
    shot = shoot("preflight_offline")
    have_tpl = os.path.exists(os.path.join(config.ASSETS, STATUS_AIRPLANE + ".png"))
    return {
        "shot": shot,
        "airplane_template": have_tpl,
        "airplane_icon": (exists(T(STATUS_AIRPLANE)) if have_tpl else None),
        "no_interstitial": not exists(T(AD_CLOSE)),
    }


def assert_offline(settle: float = 3.0, require_airplane_icon: bool = True) -> dict:
    """Preflight assertion: raise unless the device looks OFFLINE.

    Pass criteria:
      - if the airplane-icon template exists: the icon MUST be visible;
      - else, with require_airplane_icon=False: fall back to "no interstitial ad";
      - else (template missing, still requiring it): raise with calibration steps.
    Returns the signal dict on success; raises AssertionError (including the
    evidence-shot path) otherwise. Call at the start of a capture/regression run.
    """
    s = offline_report(settle)
    if s["airplane_template"]:
        if not s["airplane_icon"]:
            raise AssertionError(
                f"Airplane-Mode icon not found in the status bar — the device may "
                f"be ONLINE. Enable Airplane Mode and retry. Signals: {s}"
            )
        return s
    if require_airplane_icon:
        raise AssertionError(
            "offline preflight needs a one-time calibration: put the iPhone in "
            "Airplane Mode, run tests/preflight_offline.py to capture "
            f"{s['shot']}, then crop the status-bar airplane glyph into "
            f"{os.path.join(config.ASSETS, STATUS_AIRPLANE + '.png')}. "
            "Or pass require_airplane_icon=False to use the weaker "
            f"no-interstitial fallback. Signals: {s}"
        )
    if not s["no_interstitial"]:
        raise AssertionError(
            f"a cross-promo interstitial ad is on screen — the device is ONLINE. "
            f"Signals: {s}"
        )
    return s
