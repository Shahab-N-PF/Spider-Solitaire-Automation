"""Manual TestRail cases for the Unity build of Spider.

Written for a person on the phone, not for Airtest. One case per behaviour
a tester can fail independently. Includes the Back-to-menu and Opens-from-menu
cases.

    ./.venv/bin/python scripts/export_testrail_csv.py
"""


def C(cid, title, section, steps, *, type="Functional", priority="Medium"):
    if not steps:
        raise ValueError(f"{cid}: steps must not be empty")
    return {
        "id": cid,
        "title": title,
        "section": section,
        "type": type,
        "priority": priority,
        "steps": list(steps),
        "automation": "Manual",
    }


S = "Spider Solitaire Unity"

CASES = [
    # ── Launch ────────────────────────────────────────────────────────
    C("FL-01", "Launch - Force-quit and reopen reaches the main menu",
      f"{S} > Launch",
      [
          ("If Spider is already open, swipe it away from the app switcher, "
           "then tap the Spider icon.",
           "The app opens."),
          ("If Terms & Conditions or the tracking prompt appear, dismiss "
           "them (Continue, then Allow).",
           "No pop-up is left on screen."),
          ("Wait until the menu finishes appearing.",
           "You can see Play and the rest of the main menu."),
      ],
      priority="High"),
    C("FL-02", "Launch - Fresh install shows Terms & Conditions",
      f"{S} > Launch",
      [
          ("Delete Spider and reinstall it, or otherwise reset it so it "
           "has never agreed to the terms. Open the app.",
           "A Terms & Conditions card appears."),
          ("Tap Continue.",
           "The card goes away. The iOS tracking prompt may appear next."),
      ]),
    C("FL-03", "Launch - Fresh install shows the tracking prompt",
      f"{S} > Launch",
      [
          ("After Terms & Conditions, wait for the iOS tracking prompt "
           "(Allow / Ask App Not to Track).",
           "The system tracking alert is on screen."),
          ("Tap Allow. Do not tap Ask App Not to Track — that does not "
           "clear the gate.",
           "The prompt goes away and you can reach the main menu."),
      ]),
    C("FL-04", "Launch - Terms & Conditions link opens the terms page",
      f"{S} > Launch",
      [
          ("Delete Spider and reinstall it, or otherwise reset it so the "
           "Terms & Conditions card is on screen. Do not tap Continue yet.",
           "The card shows links for Terms & Conditions and Privacy Policy."),
          ("Tap the Terms & Conditions link.",
           "A terms web page opens, not the Privacy Policy page."),
          ("If Accept All Cookies appears, tap it and wait for the cookie "
           "banner to disappear.",
           "The banner is gone and the Terms of Service heading is fully "
           "visible."),
          ("Close the page or tap Back.",
           "The Terms & Conditions card is still there. Do not tap "
           "Continue yet."),
      ],
      priority="High"),
    C("FL-05", "Launch - Privacy Policy link opens the privacy page",
      f"{S} > Launch",
      [
          ("On the same Terms & Conditions card, tap Privacy Policy.",
           "A privacy web page opens, not the Terms & Conditions page."),
          ("If Accept All Cookies appears, tap it and wait for the cookie "
           "banner to disappear.",
           "The banner is gone and the Privacy Notice heading is fully "
           "visible."),
          ("Close the page or tap Back.",
           "The Terms & Conditions card is still there. Continue is "
           "checked separately in FL-02."),
      ],
      priority="High"),

    C("FL-06", "Launch - Latest odd TestFlight build installs",
      f"{S} > Launch",
      [
          ("Open TestFlight and tap Spider / Spider Solitaire.",
           "The TestFlight page for this game is showing."),
          ("Scroll to Previous Builds and tap it. Review all individual "
           "build rows.",
           "The greatest odd-numbered build is identified, regardless of "
           "where it appears in the list."),
          ("If an odd build exists, delete Spider if it is installed, then "
           "tap Install for that exact row and wait. If all builds are even, "
           "stop.",
           "The greatest odd build installs. An all-even list leaves the "
           "existing Spider installation unchanged."),
      ],
      priority="High"),

    # ── Main Menu ─────────────────────────────────────────────────────
    C("MM-01", "Main Menu - All eight controls are visible",
      f"{S} > Main Menu",
      [
          ("Open the app and wait until the menu finishes animating "
           "(a Game Center toast or sparkle can hide a label for a moment).",
           "Play, Stats, Options, Help, About, More Games, Choose Look, "
           "and the Spider logo are all on screen."),
      ],
      priority="High"),

    # ── Statistics ────────────────────────────────────────────────────
    C("ST-01", "Statistics - Opens from the main menu",
      f"{S} > Statistics",
      [
          ("From the main menu, tap Stats.",
           "The Statistics screen opens. The header reads Statistics. "
           "The main menu is gone."),
      ]),
    C("ST-03", "Statistics - Page scrolls down to Reset Statistics",
      f"{S} > Statistics",
      [
          ("From the main menu, tap Stats.",
           "The Statistics screen opens. Game Center is in the header."),
          ("Scroll the page all the way down. Do not tap Reset.",
           "Reset Statistics is at the bottom. If you cannot reach it, "
           "the lower difficulty blocks did not render."),
      ]),
    C("ST-04", "Statistics - Back returns to the main menu",
      f"{S} > Statistics",
      [
          ("From Statistics, tap Back.",
           "The main menu is showing."),
      ]),

    # ── Options ───────────────────────────────────────────────────────
    C("OP-01", "Options - Opens from the main menu",
      f"{S} > Options",
      [
          ("From the main menu, tap Options.",
           "The Options screen opens. The main menu is gone."),
      ]),
    C("OP-03", "Options - Applause Volume moves to min, max, and middle",
      f"{S} > Options",
      [
          ("From the main menu, tap Options and find Applause Volume.",
           "A slider with a knob is on the row. The - and + marks are "
           "labels, not buttons."),
          ("Drag the knob all the way left, all the way right, then to "
           "the middle.",
           "The knob sits at the left end, then the right end, then "
           "somewhere in the middle — not only at the two ends."),
      ],
      priority="High"),
    C("OP-04", "Options - Applause Volume stays after you leave the screen",
      f"{S} > Options",
      [
          ("On Options, drag Applause Volume to a new position and remember "
           "where the knob sits.",
           "The knob moves."),
          ("Go back to the main menu, then open Options again.",
           "The knob is still where you left it."),
      ],
      priority="High"),
    C("OP-05", "Options - Auto Mute Sounds turns off and on",
      f"{S} > Options",
      [
          ("Open Options and look at Auto Mute Sounds (it ships ON).",
           "You can tell whether the toggle is on or off."),
          ("Tap the toggle, then tap it again.",
           "It flips the first time and returns the second time. A tap "
           "that does nothing fails."),
      ],
      priority="High"),
    C("OP-06", "Options - Card Lowering moves to min, max, and middle",
      f"{S} > Options",
      [
          ("Open Options, scroll to Card Lowering, and drag the knob all "
           "the way left, all the way right, then to the middle.",
           "The knob reaches both ends and can sit in the middle. It is "
           "not a stepped control that only snaps to the ends."),
      ],
      priority="High"),
    C("OP-07", "Options - Use Hearts turns on and off",
      f"{S} > Options",
      [
          ("Open Options, scroll to Use Hearts (it ships OFF), and tap "
           "the toggle twice.",
           "It turns on, then back off."),
      ],
      priority="High"),

    # ── Help ──────────────────────────────────────────────────────────
    C("HP-01", "Help - Opens on Introduction",
      f"{S} > Help",
      [
          ("From the main menu, tap Help.",
           "Help opens with the Introduction heading. The main menu is gone."),
      ]),
    C("HP-02", "Help - Rules scroll down to the FAQ link",
      f"{S} > Help",
      [
          ("From the main menu, tap Help.",
           "Help opens on Introduction."),
          ("Scroll the rules text down.",
           "A frequently asked questions link appears at the bottom. "
           "A header with an empty body fails."),
      ]),
    C("HP-03", "Help - Back returns to the main menu",
      f"{S} > Help",
      [
          ("From Help, tap Back.",
           "The main menu is showing."),
      ]),

    # ── About ─────────────────────────────────────────────────────────
    C("AB-01", "About - Opens from the About menu item",
      f"{S} > About",
      [
          ("From the main menu, tap About.",
           "The About screen opens. You can see the copyright line."),
      ]),
    C("AB-03", "About - Version and links are on the page",
      f"{S} > About",
      [
          ("From the main menu, tap About.",
           "About opens with a version line, copyright, and links for "
           "Help, frequently asked questions, and submit feedback. Do not "
           "tap ad free version or submit feedback here — they leave the app."),
      ]),
    C("AB-04", "About - Frequently asked questions stays in the app",
      f"{S} > About",
      [
          ("On About, tap frequently asked questions.",
           "An FAQ screen opens inside Spider. You do not leave for a "
           "browser or the App Store."),
      ]),
    C("AB-05", "About - FAQ scrolls down to submit feedback",
      f"{S} > About",
      [
          ("Open FAQ from About. The first screen ends mid-answer. Scroll down.",
           "Submit feedback appears at the bottom. The FAQ title at the "
           "top stays put; you are still on FAQ."),
      ]),
    C("AB-06", "About - Spider logo also opens About",
      f"{S} > About",
      [
          ("From the main menu, tap the Spider logo at the top.",
           "About opens, the same screen as the About menu item."),
      ],
      priority="High"),

    # ── More Games (in-app page) ──────────────────────────────────────
    C("MG-01", "More Games - Gift icon opens the in-app promo page",
      f"{S} > More Games",
      [
          ("From the main menu, tap More Games (the gift icon).",
           "An in-app page opens with Tap any game to download it! "
           "You do not jump to the App Store."),
      ]),
    C("MG-02", "More Games - Swipe reveals FreeCell and Spiderette",
      f"{S} > More Games",
      [
          ("On the More Games page, swipe the list of games up once.",
           "FreeCell and Spiderette come into view. The back button and "
           "instruction line at the top stay put."),
      ]),
    C("MG-03", "More Games - Back returns to the main menu",
      f"{S} > More Games",
      [
          ("From the More Games page, tap Back.",
           "The main menu is showing."),
      ]),

    # ── Play ──────────────────────────────────────────────────────────
    C("PL-01", "Play - Opens the difficulty picker",
      f"{S} > Play",
      [
          ("From the main menu, tap Play.",
           "A difficulty picker opens. A game does not start yet."),
      ],
      priority="High"),
    C("PL-02", "Play - Picker shows all five levels",
      f"{S} > Play",
      [
          ("Open Play.",
           "Easy, Medium, Hard, Bold, and Expert are all listed."),
      ],
      priority="High"),
    C("PL-03", "Play - Easy starts a game",
      f"{S} > Play",
      [
          ("On the picker, tap Easy. If the app asks whether to abandon "
           "a paused game, tap Yes.",
           "You are on the game table (cards and the in-game bar). "
           "A prompt that only closed the picker is not enough."),
      ],
      priority="High"),
    C("PL-04", "Play - Declining abandon stays on the picker",
      f"{S} > Play",
      [
          ("With a paused game, open Play and tap its difficulty again.",
           "An abandon confirmation appears."),
          ("Tap No.",
           "The new deal is cancelled. The difficulty picker remains "
           "open, the game table has not started, and the paused game "
           "has not been discarded."),
      ]),

    # ── QA / Dev Panel ────────────────────────────────────────────────
    C("QA-02", "QA - Dev Panel is hidden until you unlock it",
      f"{S} > QA / Dev Panel",
      [
          ("Open About. If a Dev Panel button is already in the "
           "bottom-right, tap the spider emblem (the spider above the "
           "wordmark, not the words) five times quickly to hide it.",
           "No Dev Panel button is showing. A build that always shows "
           "the button fails."),
      ]),
    C("QA-03", "QA - Five quick taps on the emblem show Dev Panel",
      f"{S} > QA / Dev Panel",
      [
          ("On About, tap the spider emblem five times quickly. Tap the "
           "emblem, not the Spider SOLITAIRE wordmark under it.",
           "A Dev Panel button appears in the bottom-right corner."),
      ],
      priority="High"),
    C("QA-04", "QA - Five more taps hide Dev Panel again",
      f"{S} > QA / Dev Panel",
      [
          ("With the Dev Panel button showing on About, tap the emblem "
           "five times quickly again.",
           "The Dev Panel button disappears. The gesture turns it on "
           "and off."),
      ]),

    # ── Gameplay ──────────────────────────────────────────────────────
    C("GP-01", "Gameplay - Table controls are on screen",
      f"{S} > Gameplay",
      [
          ("Start or resume an Easy game.",
           "You can see Back, the in-game menu, tap to undo, tap to "
           "lower, and tap for hints."),
      ],
      priority="High"),
    C("GP-02", "Gameplay - Dealing from the stock changes the board",
      f"{S} > Gameplay",
      [
          ("On a table that still has cards in the stock, look at the "
           "tableau, then tap the stock pile.",
           "The board changes (new cards appear). A tap that does "
           "nothing fails."),
      ],
      priority="High"),
    C("GP-03", "Gameplay - Undo puts the board back",
      f"{S} > Gameplay",
      [
          ("After a stock deal that changed the board, tap tap to undo.",
           "The board looks like it did before the deal. Undo must "
           "restore the cards, not only play an animation."),
      ],
      priority="High"),
    C("GP-04", "Gameplay - Tap to lower drops the playfield",
      f"{S} > Gameplay",
      [
          ("If the table is already shifted down, tap tap to lower once "
           "to raise it first (this setting survives leaving a game).",
           "The top bar sits in its normal (raised) place."),
          ("Tap tap to lower once.",
           "The whole playfield slides down, including the top bar."),
      ],
      priority="High"),
    C("GP-05", "Gameplay - Tap to raise brings the playfield back",
      f"{S} > Gameplay",
      [
          ("With the playfield lowered, tap tap to lower again (same "
           "control).",
           "The playfield slides back up to where it started."),
      ],
      priority="High"),
    C("GP-06", "Gameplay - Tap for hints highlights a move",
      f"{S} > Gameplay",
      [
          ("On a table that has a legal move, tap tap for hints. Watch "
           "the board as you tap — the highlight lasts less than a second.",
           "A move is highlighted briefly. If you look away and look "
           "back, the board may look unchanged; that is expected."),
      ],
      priority="High"),
    C("GP-07", "Gameplay - In-game menu shows all six actions",
      f"{S} > Gameplay",
      [
          ("On the table, open the in-game menu.",
           "You see Replay, Abandon, Options, New, Help, and FAQ. "
           "Do not tap Abandon — it ends the game."),
      ]),
    C("GP-08", "Gameplay - Use Hearts ON turns Easy cards into hearts",
      f"{S} > Gameplay",
      [
          ("Start Easy. The cards should be black spades. If they are "
           "already hearts, open Options and turn Use Hearts off first.",
           "The dealt cards are black spades."),
          ("Open the in-game menu, tap Options, turn Use Hearts on, and "
           "go back to the table.",
           "The same deal is now red hearts. Easy only — Medium already "
           "mixes suits."),
      ],
      priority="High"),
    C("GP-09", "Gameplay - Use Hearts OFF turns the cards back to spades",
      f"{S} > Gameplay",
      [
          ("With Use Hearts on and hearts on the Easy table, open Options, "
           "turn Use Hearts off, and go back to the table.",
           "The cards are black spades again."),
      ],
      priority="High"),
    C("GP-10", "Gameplay - Rich Features OFF hides timer, score, multiplier",
      f"{S} > Gameplay",
      [
          ("On the table, look under the cards for the timer, score, "
           "and multiplier.",
           "Those three items are visible."),
          ("Open the in-game menu, tap Options, turn Rich Features off, "
           "and go back to the table.",
           "Timer, score, and multiplier are gone."),
      ],
      priority="High"),
    C("GP-11", "Gameplay - Rich Features ON brings timer, score, multiplier back",
      f"{S} > Gameplay",
      [
          ("With Rich Features off, open Options, turn Rich Features on, "
           "and go back to the table.",
           "Timer, score, and multiplier are visible again. Turn this "
           "back on before you leave — tap to lower also disappears "
           "while it is off."),
      ],
      priority="High"),
    C("GP-14", "Gameplay - New deals a different board",
      f"{S} > Gameplay",
      [
          ("Look at the current board, open the in-game menu, and tap New. "
           "If a tip card appears, tap OK.",
           "You are still on a game table, and the cards are a different "
           "deal."),
      ],
      priority="High"),

    # ── Victory ───────────────────────────────────────────────────────
    C("VI-01", "Victory - Complete Game from the table shows the win screen",
      f"{S} > Victory",
      [
          ("Unlock Dev Panel on About if needed (five quick taps on the "
           "spider emblem). Deal Easy. Open Dev Panel on the table and "
           "tap Complete Game. Do not fire Complete Game from About — "
           "it only works on a game that is already open.",
           "The Victory screen appears."),
          ("Close the Dev Panel so it is not covering the right side.",
           "The Victory buttons on the right are visible."),
      ],
      priority="High"),
    C("VI-02", "Victory - Win screen shows all of its parts",
      f"{S} > Victory",
      [
          ("On the Victory screen, with Dev Panel closed, look over the page.",
           "You can see the ranking-for header, current / rank / best "
           "columns, leaderboards, achievements, help, new, and stats."),
      ]),
    C("VI-03", "Victory - Footer names the level you just played",
      f"{S} > Victory",
      [
          ("Win an Easy game with Complete Game and read the footer.",
           "It says Easy level, matching the game you started, not some "
           "other level."),
      ],
      priority="High"),
    C("VI-04", "Victory - Back returns to the main menu",
      f"{S} > Victory",
      [
          ("On Victory, tap the screen's own Back control — not New.",
           "The main menu is showing. Leaving by Back leaves no game "
           "in progress."),
      ]),

    # ── Difficulty ────────────────────────────────────────────────────
    C("DL-01", "Difficulty - Medium starts and can be completed",
      f"{S} > Difficulty",
      [
          ("From the menu, tap Play, then Medium.",
           "A Medium game is on the table."),
          ("Open Dev Panel on the table, tap Complete Game, close the "
           "panel, then tap Back on Victory.",
           "Victory appeared for Medium, then you can get back to the menu."),
      ],
      priority="High"),
    C("DL-02", "Difficulty - Hard starts and can be completed",
      f"{S} > Difficulty",
      [
          ("From the menu, tap Play, then Hard. Complete the game from "
           "Dev Panel on the table, then tap Back on Victory.",
           "Hard dealt a table, Victory appeared, and you can get back "
           "to the menu."),
      ],
      priority="High"),
    C("DL-03", "Difficulty - Bold starts and can be completed",
      f"{S} > Difficulty",
      [
          ("From the menu, tap Play, then Bold. Complete the game from "
           "Dev Panel on the table, then tap Back on Victory.",
           "Bold dealt a table, Victory appeared, and you can get back "
           "to the menu."),
      ],
      priority="High"),
    C("DL-04", "Difficulty - Expert starts and can be completed",
      f"{S} > Difficulty",
      [
          ("From the menu, tap Play, then Expert. Complete the game from "
           "Dev Panel on the table, then tap Back on Victory.",
           "Expert dealt a table, Victory appeared, and you can get back "
           "to the menu."),
      ],
      priority="High"),

    # ── Promo icons ───────────────────────────────────────────────────
    C("PI-01", "Promo icons - Five game icons on the menu after a win",
      f"{S} > More Games",
      [
          ("Finish at least one game (or use Complete Game), then go to "
           "the main menu. Wait a few seconds.",
           "Five icons sit on the left: Solitaire, Sudoku 2, Card Games, "
           "FreeCell, and Spiderette. A fresh install with no wins does "
           "not show this strip — that is normal."),
      ]),
    C("PI-02", "Promo icons - Solitaire opens Solitaire: Classic Cards",
      f"{S} > More Games",
      [
          ("On the menu, tap the Solitaire icon. Wi-Fi must be on.",
           "The App Store opens."),
          ("Read the store page name.",
           "The page is Solitaire: Classic Cards."),
          ("Tap ◀ Spider in the status bar (or switch back to Spider).",
           "You are back on the main menu. Spider did not restart."),
      ]),
    C("PI-03", "Promo icons - Sudoku 2 opens Sudoku",
      f"{S} > More Games",
      [
          ("Tap the Sudoku 2 icon.",
           "The App Store opens on a Sudoku page."),
          ("Switch back to Spider.",
           "The main menu is showing."),
      ]),
    C("PI-04", "Promo icons - Card Games opens Card Games",
      f"{S} > More Games",
      [
          ("Tap the Card Games icon.",
           "The App Store opens on Card Games — not another Solitaire "
           "or card title."),
          ("Switch back to Spider.",
           "The main menu is showing."),
      ]),
    C("PI-05", "Promo icons - FreeCell opens FreeCell",
      f"{S} > More Games",
      [
          ("Tap the FreeCell icon.",
           "The App Store opens on FreeCell."),
          ("Switch back to Spider.",
           "The main menu is showing."),
      ]),
    C("PI-06", "Promo icons - Spiderette opens Spiderette",
      f"{S} > More Games",
      [
          ("Tap the Spiderette icon.",
           "The App Store opens on Spiderette."),
          ("Switch back to Spider.",
           "The main menu is showing."),
      ]),

    # ── Reset (destructive) ───────────────────────────────────────────
    C("RS-01", "Reset Statistics - Link asks you to confirm",
      f"{S} > Statistics",
      [
          ("Open Stats, scroll to Reset Statistics, and tap it.",
           "A confirmation appears (reset local scores?). Game Center "
           "scores are not part of this wipe."),
      ],
      type="Destructive",
      priority="High"),
    C("RS-02", "Reset Statistics - Confirming wipes local scores",
      f"{S} > Statistics",
      [
          ("Accept every confirmation. The app asks twice (a second "
           "just to be on the safe side).",
           "Local statistics are cleared. You can get back to the menu. "
           "Do this last — it wipes play history on the device."),
      ],
      type="Destructive",
      priority="High"),
    C("RS-03", "Reset Statistics - Declining leaves scores alone",
      f"{S} > Statistics",
      [
          ("Open Stats, scroll to Reset Statistics, and tap it.",
           "A reset confirmation appears."),
          ("Tap No.",
           "The confirmation closes, Statistics remains open, and the "
           "local scores are unchanged."),
      ],
      type="Destructive"),

    # ── Choose Look ───────────────────────────────────────────────────
    C("CL-01", "Choose Look - Opens on the Surface tab",
      f"{S} > Choose Look",
      [
          ("From the main menu, tap Choose Look. If Cards is showing, "
           "tap Surface.",
           "The look picker opens. Surface content (Simulate Depth) "
           "is showing."),
      ]),
    C("CL-03", "Choose Look - Surface and Cards tabs switch",
      f"{S} > Choose Look",
      [
          ("In Choose Look, tap Cards, then tap Surface again.",
           "Cards shows Extra Large Card-Symbols. Surface comes back "
           "to Simulate Depth."),
      ]),
    C("CL-04", "Choose Look - Sixth surface shows on the game table",
      f"{S} > Choose Look",
      [
          ("On Surface, tap the 6th palette (second row, third column — "
           "light checkered wood).",
           "That palette is selected."),
          ("Close Choose Look, start or resume Easy, and look at the felt.",
           "The table felt matches the palette you picked, not only "
           "the thumbnail in the picker."),
      ],
      priority="High"),
    C("CL-05", "Choose Look - Fifth card back shows on the table",
      f"{S} > Choose Look",
      [
          ("On Cards, tap the 5th palette (second row, second column — "
           "black filigree).",
           "That deck is selected."),
          ("On the game table, look at the face-down card backs.",
           "The backs match the deck you picked."),
      ],
      priority="High"),

    # ── Ads (MAX + leave-game) ────────────────────────────────────────
    C("AD-01", "Ads - Dev Panel opens (unlock if needed)",
      f"{S} > Ads",
      [
          ("Turn Wi-Fi on. Open Spider. If an old debugger or ad is still "
           "up, close it. If you are on the table, do not tap Back yet "
           "(that can fire an ad).",
           "Spider is in front."),
          ("If Dev Panel is already on screen, tap it. If not, go to About, "
           "tap the spider emblem five times quickly, then tap Dev Panel.",
           "Dev Panel is open and shows Max Debugger."),
      ],
      priority="High"),
    C("AD-02", "Ads - Max Debugger opens",
      f"{S} > Ads",
      [
          ("With Dev Panel open, tap Max Debugger.",
           "MAX Mediation Debugger opens. You are still in Spider."),
      ],
      priority="High"),
    C("AD-03", "Ads - Ads section shows the Live Network row",
      f"{S} > Ads",
      [
          ("In the debugger, scroll until you can tap the Ads row. It "
           "reads Select Live Network when empty, or Live Network when "
           "a network is already chosen.",
           "That row is on screen and you can tap it."),
      ]),
    C("AD-04", "Ads - AppLovin is the live network",
      f"{S} > Ads",
      [
          ("Tap the Live Network row. Wait for the picker (its title is "
           "Select Live Network). AppLovin also appears higher up under "
           "Completed SDK Integrations — ignore that one.",
           "The Select Live Network list is open."),
          ("If AppLovin is not already ticked, tap AppLovin.",
           "A checkmark sits on AppLovin."),
      ],
      priority="High"),
    C("AD-06", "Ads - Leave-game ad: close the store X, then the ad X",
      f"{S} > Ads",
      [
          ("Close the debugger (Done, then close Dev Panel). Start or "
           "resume a game. Wait about 30 seconds, then tap Back. If no "
           "ad appears, resume or deal again — that second enter is "
           "allowed.",
           "A full-screen ad plays inside Spider. You did not leave "
           "for another app."),
          ("First tap the App Store product sheet's X (if that sheet "
           "appears). Then tap the ad's own circular X. Do not tap the "
           "skip arrows that move around.",
           "The store sheet closes first, then the ad."),
      ],
      priority="High"),
    C("AD-07", "Ads - After the ad you are back on the table",
      f"{S} > Ads",
      [
          ("After both X buttons, wait for the game.",
           "The game table is showing."),
      ],
      priority="High"),

    # ── Interstitial trigger / cooldown ───────────────────────────────
    C("TA-01", "Ads - Under 30s on the table, Options has no ad",
      f"{S} > Ads",
      [
          ("Start a game. Within about 8 seconds, open the in-game menu "
           "and tap Options. If an ad from an earlier session appears, "
           "close it, get back to the table, and try once more within 8 "
           "seconds.",
           "Options opens with no ad."),
      ],
      priority="High"),
    C("TA-02", "Ads - Over 30s on the table, Help shows an ad",
      f"{S} > Ads",
      [
          ("Stay on the table more than 30 seconds. Open the in-game "
           "menu and tap Help.",
           "An ad plays. Close the store X, then the ad X."),
      ],
      priority="High"),
    C("TA-03", "Ads - Options within 30s of the Help ad has no ad",
      f"{S} > Ads",
      [
          ("Right after you close the Help ad, go back to the table, "
           "open the in-game menu, and tap Options.",
           "Options opens with no ad. The cooldown applies everywhere, "
           "not only on Victory."),
      ],
      priority="High"),
    C("TA-04", "Ads - Over 30s on the table, Complete Game shows a Victory ad",
      f"{S} > Ads",
      [
          ("Stay on the table more than 30 seconds. Open Dev Panel and "
           "tap Complete Game.",
           "Victory appears with an ad on top."),
          ("Close the store X, then the ad X, then close Dev Panel.",
           "The Victory screen is visible. Close the ad before the "
           "panel — the ad covers it."),
      ],
      priority="High"),
    C("TA-05", "Ads - New within 30s of the Victory ad has no ad",
      f"{S} > Ads",
      [
          ("After closing the Victory ad, tap New within 30 seconds.",
           "A new table deals with no ad."),
      ],
      priority="High"),
    C("TA-06", "Ads - New after 30s on Victory shows an ad",
      f"{S} > Ads",
      [
          ("Win again with Complete Game after more than 30 seconds on "
           "the table. Close that Victory ad, stay on Victory more than "
           "30 seconds, then tap New.",
           "An ad plays before the next table. Close the store X, then "
           "the ad X."),
      ],
      priority="High"),
    C("TA-07", "Ads - Over 30s on the table, Back shows an ad then the menu",
      f"{S} > Ads",
      [
          ("Stay on the table more than 30 seconds and tap Back.",
           "An ad plays. After the store X and the ad X, you are on "
           "the main menu — not the table."),
      ],
      priority="High"),
    C("TA-08", "Ads - Starting a game within 30s on the menu has no ad",
      f"{S} > Ads",
      [
          ("After the Back ad closed onto the menu, wait under 30 "
           "seconds and resume or deal a game.",
           "The table appears with no ad."),
      ],
      priority="High"),
    C("TA-09", "Ads - Starting a game after 30s on the menu shows an ad",
      f"{S} > Ads",
      [
          ("Leave a table with Back after more than 30 seconds, close "
           "that ad onto the menu, stay on the menu more than 30 "
           "seconds, then resume or deal.",
           "An ad plays as you enter the game. This is the menu wait, "
           "not the same as the leave-game ad."),
      ],
      priority="High"),
    C("TA-10", "Ads - Over 30s on the table, FAQ shows an ad",
      f"{S} > Ads",
      [
          ("Stay on the table more than 30 seconds. Open the in-game "
           "menu and tap FAQ.",
           "An ad plays. After it closes you can get back to the table."),
      ],
      priority="High"),

    # ── Last Score ────────────────────────────────────────────────────
    C("LS-01", "Last Score - LAST SCORE opens Last Won Game Score",
      f"{S} > Last Score",
      [
          ("From the menu, tap Play, then LAST SCORE. Wi-Fi should be on.",
           "A ranking screen opens. The header reads Last Won Game Score."),
      ]),
    C("LS-02", "Last Score - Arrow cycles week, month, overall, day",
      f"{S} > Last Score",
      [
          ("On Last Won Game Score, tap the forward arrow beside ranking "
           "for four times, about two seconds apart.",
           "The period moves week → month → overall → day → week. You "
           "stay on Last Won Game Score — the arrow must not leave "
           "the screen."),
      ]),
    C("LS-03", "Last Score - Leaderboards opens Game Center",
      f"{S} > Last Score",
      [
          ("On Last Score, tap leaderboards. You need a signed-in Apple ID.",
           "Game Center opens, headed Leaderboards. If a notice card "
           "appears instead (scores may take a little time to upload), "
           "tap OK — Leaderboards opens from that, do not tap the "
           "link again."),
          ("Tap Game Center's back arrow, then dismiss the sheet.",
           "Last Score is showing again."),
      ]),
    C("LS-04", "Last Score - Achievements opens Game Center",
      f"{S} > Last Score",
      [
          ("On Last Score, tap achievements.",
           "Game Center opens, headed Achievements. If the same notice "
           "card appears, tap OK — Achievements opens from that, do "
           "not tap the link again."),
          ("Tap back and dismiss the sheet.",
           "Last Score is showing again."),
      ]),
    C("LS-05", "Last Score - Back returns to the main menu",
      f"{S} > Last Score",
      [
          ("From Last Score, tap Back until you reach the menu.",
           "The main menu is showing."),
      ]),

    # ── App Store / Mail ──────────────────────────────────────────────
    C("AF-01", "Ad-free - No leaves you on About",
      f"{S} > App Store / Mail",
      [
          ("On About, tap ad free version and tap No on the confirmation.",
           "The card closes. Spider stays in front on About and the "
           "App Store does not open."),
      ]),
    C("AF-02", "Ad-free - Link asks No or Yes before the store",
      f"{S} > App Store / Mail",
      [
          ("On About, tap ad free version.",
           "A card asks if you want to look at the ad-free version "
           "(No on the left, Yes on the right). You are still in Spider."),
      ]),
    C("AF-03", "Ad-free - Yes opens Spider Solitaire +",
      f"{S} > App Store / Mail",
      [
          ("On that card, tap Yes.",
           "The App Store opens."),
          ("Read the store page name.",
           "The page is Spider Solitaire +, the paid build of this game."),
      ],
      priority="High"),
    C("AF-04", "Ad-free - Status-bar back lands on About",
      f"{S} > App Store / Mail",
      [
          ("From the App Store, tap ◀ Spider in the status bar.",
           "You are back on About. If you land on the main menu, the "
           "app restarted instead of resuming."),
      ],
      priority="High"),
    C("FB-02", "Feedback - Submit feedback asks Cancel or Write Email",
      f"{S} > App Store / Mail",
      [
          ("On About, tap submit feedback. A Mail account must be set up.",
           "An alert offers Cancel and Write Email."),
      ]),
    C("FB-03", "Feedback - Write Email opens a Mail draft",
      f"{S} > App Store / Mail",
      [
          ("Tap Write Email.",
           "Mail opens with a draft. If you see No Mail Accounts, that "
           "is the phone setup, not the game."),
      ],
      priority="High"),
    C("FB-04", "Feedback - Subject names the game, version, phone, and iOS",
      f"{S} > App Store / Mail",
      [
          ("Read the draft subject. Compare it to Settings → General → "
           "About for the model and iOS version, and to About in the "
           "game for the version.",
           "The subject names Spider, the app version, this phone's "
           "model, and this iOS version."),
      ],
      priority="High"),
    C("FB-05", "Feedback - Delete the draft — do not send",
      f"{S} > App Store / Mail",
      [
          ("Delete the draft. Do not tap send. Do this even if the "
           "subject was wrong.",
           "The draft is gone. Nothing was sent."),
      ],
      priority="High"),
    C("FB-06", "Feedback - Status-bar back returns to Spider",
      f"{S} > App Store / Mail",
      [
          ("From Mail, tap ◀ Spider in the status bar.",
           "Spider is in front. The main menu (not About) is expected — "
           "Mail is a separate app."),
      ]),
    C("HS-01", "Options - Contact Us opens support",
      f"{S} > Options",
      [
          ("Open Options and tap Contact Us. Wi-Fi must be on.",
           "You leave Options and a support page opens. What that page "
           "then loads can vary with the network."),
      ]),
    C("HS-02", "Options - Contact Us still leaves Options without internet",
      f"{S} > Options",
      [
          ("Turn Airplane Mode on and turn Wi-Fi off. Open Options and "
           "tap Contact Us.",
           "You leave Options. The support page may show a no-connection "
           "or failed-load screen instead of PeopleFun Support. That is "
           "the case — the redirect still happened."),
      ]),

    # ── Relaunch ──────────────────────────────────────────────────────
    C("RL-01", "Relaunch - Same board after closing the app for a few seconds",
      f"{S} > Relaunch",
      [
          ("Start or resume a game and make one move (a card, or deal "
           "from the stock). Remember how the board looks.",
           "The board has changed from the dealt position."),
          ("Press Home first (the app saves when it goes to the "
           "background), swipe Spider away, wait about 3 seconds, and "
           "open it again. Do not kill it from the foreground without "
           "Home — that comes back on the menu.",
           "You are on the game table with the same cards. A tap a "
           "card to start overlay is fine."),
      ],
      priority="High"),
    C("RL-02", "Relaunch - Same board after closing the app for 35 seconds",
      f"{S} > Relaunch",
      [
          ("On a game you have already moved, press Home, swipe Spider "
           "away, wait about 35 seconds, and open it again.",
           "You are on the same board as before the kill. This is a "
           "second wait, not a repeat of the short one."),
      ],
      priority="High"),
]


def validate(cases=CASES):
    """Raise if titles or ids collide, or a case has no steps."""
    ids, titles = [], []
    for case in cases:
        if not case["steps"]:
            raise ValueError(f"{case['id']}: empty steps")
        ids.append(case["id"])
        titles.append(case["title"])
    dups = {i for i in ids if ids.count(i) > 1}
    if dups:
        raise ValueError(f"duplicate case ids: {sorted(dups)}")
    dups = {t for t in titles if titles.count(t) > 1}
    if dups:
        raise ValueError(f"duplicate titles: {sorted(dups)}")
    return len(cases)


if __name__ == "__main__":
    n = validate()
    print(f"{n} manual TestRail cases, titles unique")
