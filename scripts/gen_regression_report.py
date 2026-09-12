#!/usr/bin/env python3
"""Build a self-contained HTML report for the Spider functional regression run.

The report is one expandable card per manual TestRail case. A case inherits the
result of the automated test that covers it; cases whose parent was not run are
shown as skipped. Screenshots are embedded as compressed JPEG data so the
artifact remains portable without reproducing the Word Search report's very
large raw-PNG size.

Run:
    ./.venv/bin/python scripts/gen_regression_report.py
    ./.venv/bin/python scripts/gen_regression_report.py --out reports/Spider_Regression.html
"""
import argparse
import base64
import html
import io
import json
import os
import sys
from collections import OrderedDict
from datetime import datetime

from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADER_LOGO = os.path.join(REPO, "reports", "spider_report_header.jpg")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "docs", "testrail"))
import config  # noqa: E402
from cases import CASES  # noqa: E402


# The TestRail list remains the person-facing source of truth. This catalog
# only connects each manual case to the automated parent and its evidence.
CASE_CATALOG = OrderedDict([
    ("installFromTestFlight", {
        "ids": ["FL-06"],
        "shots": ["TestFlightBuild.png"],
    }),
    ("verifyFirstLaunch", {
        "ids": ["FL-01", "FL-02", "FL-03", "FL-04", "FL-05"],
        "shots": ["first_launch.png"],
        "extra": {
            "FL-04": ["first_launch_terms_page.png"],
            "FL-05": ["first_launch_privacy_page.png"],
        },
    }),
    ("verifyMainMenu", {
        "ids": ["MM-01"],
        "shots": ["MainMenu.png"],
    }),
    ("verifyStatsPage", {
        "ids": ["ST-01", "ST-03", "ST-04"],
        "shots": ["StatsPage.png"],
        "extra": {"ST-03": ["StatsResetBtn.png"]},
    }),
    ("verifyOptions", {
        "ids": ["OP-01", "OP-03", "OP-04", "OP-05", "OP-06", "OP-07"],
        "shots": ["OptionsPage.png"],
    }),
    ("verifyHelpShift", {
        "ids": ["HS-02"],
        "shots": ["HelpShift.png"],
    }),
    ("verifyHelpPage", {
        "ids": ["HP-01", "HP-02", "HP-03"],
        "shots": ["HelpPage.png"],
        "extra": {"HP-02": ["HelpPageBottom.png"]},
    }),
    ("verifySpiderLogo", {
        "ids": ["AB-01", "AB-03", "AB-04", "AB-05", "AB-06"],
        "shots": ["SpiderAboutPage.png"],
        "extra": {"AB-04": ["SpiderFAQ.png"],
                  "AB-05": ["SpiderFAQBottom.png"]},
    }),
    ("verifyMoreGamesBtn", {
        "ids": ["MG-01", "MG-02", "MG-03"],
        "shots": ["MoreGames.png"],
        "extra": {"MG-02": ["MoreGamesBottom.png"]},
    }),
    ("verifyPlay", {
        "ids": ["PL-01", "PL-02", "PL-03"],
        "shots": ["DifficultyLevels.png", "Play.png"],
    }),
    ("verifyAbandonNo", {
        "ids": ["PL-04"],
        "shots": ["AbandonNo.png"],
    }),
    ("openDebugTools", {
        "ids": ["QA-02", "QA-03", "QA-04"],
        "shots": ["debug_tools.png"],
    }),
    ("verifyGamePlay", {
        "ids": [
            "GP-01", "GP-02", "GP-03", "GP-04", "GP-05", "GP-06",
            "GP-07", "GP-08", "GP-09", "GP-10", "GP-11", "GP-14",
        ],
        "shots": ["GamePlay.png", "InGameMenu.png"],
    }),
    ("verifyVictory", {
        "ids": ["VI-01", "VI-02", "VI-03", "VI-04"],
        "shots": ["VictoryScreen.png"],
    }),
    ("verifyDifficultyLevels", {
        "ids": ["DL-01", "DL-02", "DL-03", "DL-04"],
        "shots": [
            "unity_difficulty_medium.png", "unity_victory_medium.png",
            "unity_difficulty_hard.png", "unity_victory_hard.png",
            "unity_difficulty_bold.png", "unity_victory_bold.png",
            "unity_difficulty_expert.png", "unity_victory_expert.png",
        ],
    }),
    ("verifyMoreGamesIcons", {
        "ids": ["PI-01", "PI-02", "PI-03", "PI-04", "PI-05", "PI-06"],
        "shots": ["more_games_icons.png"],
        "extra": {
            "PI-02": ["promo_store_promo_solitaire.png"],
            "PI-03": ["promo_store_promo_sudoku2.png"],
            "PI-04": ["promo_store_promo_cardgames.png"],
            "PI-05": ["promo_store_promo_freecell.png"],
            "PI-06": ["promo_store_promo_spiderette.png"],
        },
    }),
    ("resetStats", {
        "ids": ["RS-01", "RS-02"],
        "shots": ["ResetStats.png"],
    }),
    ("verifyResetCancelled", {
        "ids": ["RS-03"],
        "shots": ["StatsResetCancelledBefore.png",
                  "StatsResetCancelledAfter.png"],
    }),
    ("verifyHelpShiftOnline", {
        "ids": ["HS-01"],
        "shots": ["HelpShiftOnline.png"],
    }),
    ("verifyChooseLook", {
        "ids": ["CL-01", "CL-03", "CL-04", "CL-05"],
        "shots": ["choose_look_surface.png", "choose_look_cards.png"],
        "extra": {"CL-04": ["choose_look_table.png"],
                  "CL-05": ["choose_look_table.png"]},
    }),
    ("verifyAds", {
        "ids": ["AD-01", "AD-02", "AD-03", "AD-04", "AD-06", "AD-07"],
        "shots": [
            "ad_dev_panel.png", "ad_max_debugger.png", "ad_ads_section.png",
            "ad_applovin.png", "ad_back_on_table.png",
        ],
    }),
    ("triggerAdPoints", {
        "ids": [
            "TA-01", "TA-02", "TA-03", "TA-04", "TA-05",
            "TA-06", "TA-07", "TA-08", "TA-09", "TA-10",
        ],
        "shots": ["ad_back_on_table.png"],
    }),
    ("visitLastScore", {
        "ids": ["LS-01", "LS-02", "LS-03", "LS-04", "LS-05"],
        "shots": ["unity_last_score.png"],
        "extra": {
            "LS-03": ["unity_game_center_leaderboards.png"],
            "LS-04": ["unity_game_center_achievements.png"],
        },
    }),
    ("verifyAdFreeVersion", {
        "ids": ["AF-01", "AF-02", "AF-03", "AF-04"],
        "shots": ["AdFreeVersionNo.png", "AdFreeVersion.png"],
    }),
    ("submitFeedback", {
        "ids": ["FB-02", "FB-03", "FB-04", "FB-05", "FB-06"],
        "shots": ["SubmitFeedback.png"],
    }),
    ("verifyRelaunch", {
        "ids": ["RL-01", "RL-02"],
        "shots": ["relaunch_short_played.png", "relaunch_short.png",
                  "relaunch_long_played.png", "relaunch_long.png"],
    }),
])


CSS = r"""
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin:0; font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
  color:#f4ece4; background:#2a211c; min-height:100vh; }
.wrap { max-width:1040px; margin:0 auto; padding:32px 20px 64px; }
.hero { display:flex; align-items:center; justify-content:space-between;
  gap:28px; flex-wrap:wrap; margin-bottom:22px; }
.brand { display:flex; align-items:center; gap:16px; min-width:240px; }
.mark { width:64px; height:64px; border-radius:16px; object-fit:cover;
  background:#c45c32; box-shadow:0 4px 16px rgba(0,0,0,.25); }
h1 { font-family:"Iowan Old Style","Palatino Linotype",Palatino,serif;
  font-size:26px; margin:0; font-weight:700; letter-spacing:0; color:#f4ece4; }
.sub { color:#c4b2a3; font-size:14px; margin-top:4px; }
.hero-stat { display:flex; align-items:center; gap:20px; }
.donut { width:132px; height:132px; border-radius:50%;
  display:grid; place-items:center; flex:0 0 132px;
  box-shadow:inset 0 0 0 1px #4a3b33; }
.donut-hole { width:86px; height:86px; border-radius:50%; background:#2a211c;
  display:flex; flex-direction:column; align-items:center; justify-content:center; }
.donut-pct { font-family:"Iowan Old Style","Palatino Linotype",Palatino,serif;
  font-size:26px; font-weight:700; line-height:1; }
.donut-lbl { color:#c4b2a3; font-size:10px; letter-spacing:.3px; margin-top:3px; }
.legend { display:flex; flex-direction:column; gap:7px; font-size:13px; color:#c4b2a3; }
.legend b { color:#f4ece4; font-weight:600; }
.swatch { display:inline-block; width:9px; height:9px; border-radius:50%;
  margin-right:7px; vertical-align:middle; }
.chips { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px; }
.filters { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:28px; }
.filter { appearance:none; background:#3a2e28; border:1px solid #4a3b33;
  color:#c4b2a3; border-radius:999px; padding:6px 12px; font:inherit;
  font-size:13px; cursor:pointer; }
.filter b { color:#f4ece4; font-weight:600; }
.filter.is-on { color:#f4ece4; border-color:#c45c32; background:#4a342c; }
.filter[data-filter="passed"].is-on { border-color:#6f9e7a; }
.filter[data-filter="failed"].is-on { border-color:#b85a48; }
.filter[data-filter="skipped"].is-on { border-color:#d4b483; }
body[data-filter="passed"] .attention,
body[data-filter="failed"] .attention,
body[data-filter="skipped"] .attention { display:none; }
body[data-filter="passed"] .case:not(.passed),
body[data-filter="failed"] .case:not(.failed),
body[data-filter="skipped"] .case:not(.skipped) { display:none; }
body[data-filter="passed"] .group:not([data-has~="passed"]),
body[data-filter="failed"] .group:not([data-has~="failed"]),
body[data-filter="skipped"] .group:not([data-has~="skipped"]) { display:none; }
.chip { background:#3a2e28; border:1px solid #4a3b33; border-radius:10px;
  padding:7px 11px; display:flex; flex-direction:column; min-width:88px; }
.chip .k { font-size:11px; letter-spacing:.2px; color:#c4b2a3; }
.chip .v { font-size:13px; font-weight:600; margin-top:2px; }
.attention { background:#3a2e28; border:1px solid #4a3b33; border-left:4px solid #b85a48;
  border-radius:12px; padding:16px 16px 8px; margin-bottom:28px; }
.attention h2 { font-family:"Iowan Old Style","Palatino Linotype",Palatino,serif;
  font-size:17px; margin:0 0 4px; font-weight:700; }
.attention .lead { color:#c4b2a3; font-size:13px; margin:0 0 12px; }
.sec { font-family:"Iowan Old Style","Palatino Linotype",Palatino,serif;
  font-size:17px; font-weight:700; margin:28px 0 10px; padding-left:12px;
  border-left:3px solid #c45c32; display:flex; align-items:baseline; gap:10px; }
.secstat { font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
  font-size:12px; font-weight:500; color:#c4b2a3; }
.case { background:#3a2e28; border:1px solid #4a3b33; border-radius:10px;
  margin-bottom:8px; overflow:hidden; border-left:8px solid #6f9e7a; }
.case.failed { border-left-color:#b85a48; }
.case.skipped { border-left-color:#d4b483; }
summary { list-style:none; cursor:pointer; display:flex; align-items:center;
  gap:12px; padding:12px 14px; }
summary::-webkit-details-marker { display:none; }
.title { flex:1; font-weight:600; font-size:14px; }
.pill { color:#2a211c; font-weight:700; font-size:10px; padding:3px 8px;
  border-radius:999px; letter-spacing:.3px; }
.dur { color:#c4b2a3; font-size:12px; min-width:52px; text-align:right; }
.detail { padding:0 14px 14px; }
.shots { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
  gap:12px; margin-top:4px; }
.shot-card { margin:0; }
.shot { display:block; width:100%; max-height:420px; object-fit:contain;
  border-radius:8px; border:1px solid #4a3b33; background:#2a211c; }
.shot-caption { color:#c4b2a3; font-size:11px; margin:6px 0 0; }
.noshot { color:#c4b2a3; font-size:13px; margin:0 0 10px; }
.msg { background:#2a211c; border:1px solid #4a3b33; border-radius:8px;
  padding:10px; color:#e8cfc4; font-size:12px; white-space:pre-wrap;
  overflow-x:auto; margin:0 0 12px; }
.evidence { background:#322822; border:1px solid #4a3b33; border-left:3px solid #c45c32;
  border-radius:8px; padding:10px; color:#f4ece4; font-size:12px;
  white-space:pre-wrap; overflow-x:auto; margin:0 0 12px; }
footer { color:#c4b2a3; font-size:12px; text-align:center; margin-top:36px; }
@media (max-width:720px) {
  .hero-stat { width:100%; }
}
"""


def _validate_catalog():
    cases = {case["id"]: case for case in CASES}
    mapped = {}
    for parent, spec in CASE_CATALOG.items():
        for case_id in spec["ids"]:
            if case_id in mapped:
                raise ValueError(f"{case_id} is mapped more than once")
            if case_id not in cases:
                raise ValueError(f"{case_id} is not in docs/testrail/cases.py")
            mapped[case_id] = parent
    missing = sorted(set(cases) - set(mapped))
    if missing:
        raise ValueError(f"unmapped TestRail case(s): {', '.join(missing)}")
    return cases, mapped


def _format_duration(seconds):
    if seconds in (None, ""):
        return "—"
    seconds = float(seconds)
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, remainder = divmod(round(seconds), 60)
    return f"{minutes}m {remainder:02d}s"


def _format_run_time(value):
    """Render the stored ISO timestamp as a readable local time with offset."""
    if not value:
        return "No run recorded"
    try:
        moment = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return str(value)
    pretty = moment.strftime("%b %-d, %Y, %-I:%M %p")
    offset = moment.strftime("%z")
    if len(offset) == 5:
        offset = f"{offset[:3]}:{offset[3:]}"
    return f"{pretty} (UTC{offset or ' local'})"


def _image_uri(path):
    """Embed a resized JPEG, returning None when evidence is unavailable."""
    if not os.path.isfile(path):
        return None
    try:
        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail((900, 900))
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=78, optimize=True)
        encoded = base64.b64encode(output.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"
    except (OSError, ValueError):
        return None


def _load_results(path):
    try:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError):
        return {}


def _chip(label, value):
    return (f'<div class="chip"><span class="k">{html.escape(label)}</span>'
            f'<span class="v">{html.escape(str(value or "—"))}</span></div>')


def _status(parent, results):
    result = results.get(parent)
    if not result:
        return "skipped", None
    return ("passed" if result.get("ok") else "failed"), result


STATUS_PILL = {
    "passed": "#6f9e7a",
    "failed": "#b85a48",
    "skipped": "#d4b483",
}


def _shots_for(case_id, spec):
    names = list(spec.get("shots", []))
    names.extend(spec.get("extra", {}).get(case_id, []))
    return list(dict.fromkeys(names))


def _case_card(case, parent, spec, status, result, uri_cache, open_failed=True):
    """One expandable TestRail card, optionally opened when the case failed."""
    case_id = case["id"]
    title = html.escape(case["title"])
    duration = _format_duration(result.get("seconds") if result else None)
    color = STATUS_PILL[status]
    detail = []
    if status == "skipped":
        detail.append(
            f'<p class="noshot">Not run in this invocation. '
            f'Run <code>run_all.py {html.escape(parent)}</code> to '
            "populate this case.</p>"
        )
    elif result and result.get("error"):
        detail.append(f'<pre class="msg">{html.escape(result["error"])}</pre>')

    shot_names = _shots_for(case_id, spec)
    found = []
    if status != "skipped":
        for shot_name in shot_names:
            path = os.path.join(config.LOG, shot_name)
            if shot_name not in uri_cache:
                uri_cache[shot_name] = _image_uri(path)
            uri = uri_cache[shot_name]
            if uri:
                found.append(
                    f'<figure class="shot-card">'
                    f'<img class="shot" src="{uri}" alt="{html.escape(shot_name)}">'
                    f'<figcaption class="shot-caption">'
                    f'{html.escape(shot_name)}</figcaption></figure>'
                )
    if status == "skipped":
        detail.append(
            f'<p class="noshot">Expected evidence after running: '
            f'{html.escape(", ".join(shot_names))}</p>'
        )
    elif not found:
        detail.append(
            '<p class="noshot">No screenshot was captured for this case '
            f'in <code>log/</code>. Expected evidence: '
            f'{html.escape(", ".join(shot_names))}</p>'
        )
    elif found:
        detail.append(f'<div class="shots">{"".join(found)}</div>')
    opened = " open" if (open_failed and status == "failed") else ""
    return (
        f'<details class="case {status}"{opened}>'
        f'<summary><span class="title">{title}</span>'
        f'<span class="pill" style="background:{color}">{status}</span>'
        f'<span class="dur">{duration}</span></summary>'
        f'<div class="detail"><div class="evidence">Automated parent: '
        f'{html.escape(parent)}</div>{"".join(detail)}</div></details>'
    )


def _donut(counts, executed, rate):
    """CSS conic-gradient donut: pass / fail / skip of all cases."""
    total = max(sum(counts.values()), 1)
    pass_pct = 100.0 * counts["passed"] / total
    fail_pct = 100.0 * counts["failed"] / total
    fail_end = pass_pct + fail_pct
    gradient = (
        f"conic-gradient(#6f9e7a 0 {pass_pct:.2f}%, "
        f"#b85a48 {pass_pct:.2f}% {fail_end:.2f}%, "
        f"#d4b483 {fail_end:.2f}% 100%)"
    )
    if executed == 0:
        gradient = "conic-gradient(#4a3b33 0 100%)"
    center = f"{rate:.0f}%" if executed else "—"
    return f"""<div class="hero-stat">
<div class="donut" style="background:{gradient}">
<div class="donut-hole"><div class="donut-pct">{center}</div>
<div class="donut-lbl">pass rate</div></div></div>
<div class="legend">
<div><span class="swatch" style="background:#6f9e7a"></span>
<b>{counts["passed"]}</b> passed</div>
<div><span class="swatch" style="background:#b85a48"></span>
<b>{counts["failed"]}</b> failed</div>
<div><span class="swatch" style="background:#d4b483"></span>
<b>{counts["skipped"]}</b> skipped</div>
<div style="margin-top:4px">{counts["passed"]}/{executed or 0} executed</div>
</div></div>"""


FILTER_JS = """
(function () {
  var buttons = document.querySelectorAll(".filter");
  function apply(mode) {
    document.body.setAttribute("data-filter", mode);
    buttons.forEach(function (button) {
      var on = button.getAttribute("data-filter") === mode;
      button.classList.toggle("is-on", on);
      button.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }
  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      apply(button.getAttribute("data-filter"));
    });
  });
  apply("all");
})();
"""


def _filters(counts):
    """All / Passed / Failed / Skipped chips for the case list."""
    total = sum(counts.values())
    chips = [
        ("all", "All", total),
        ("passed", "Passed", counts["passed"]),
        ("failed", "Failed", counts["failed"]),
        ("skipped", "Skipped", counts["skipped"]),
    ]
    buttons = []
    for key, label, n in chips:
        pressed = "true" if key == "all" else "false"
        on = " is-on" if key == "all" else ""
        buttons.append(
            f'<button type="button" class="filter{on}" data-filter="{key}" '
            f'aria-pressed="{pressed}">{html.escape(label)} <b>{n}</b></button>'
        )
    return f'<div class="filters" role="group" aria-label="Filter cases">{"".join(buttons)}</div>'


def build(results_path=None, out_path=None):
    """Generate the report and return its output path."""
    cases, mapped = _validate_catalog()
    results_path = results_path or os.path.join(config.LOG, "run_results.json")
    out_path = out_path or os.path.join(config.LOG, "spider_regression.html")
    payload = _load_results(results_path)
    result_by_name = {
        item["name"]: item for item in payload.get("tests", [])
        if isinstance(item, dict) and item.get("name")
    }

    counts = {"passed": 0, "failed": 0, "skipped": 0}
    cards_by_section = OrderedDict()
    failed_rows = []
    uri_cache = {}
    body = []
    for case in CASES:
        case_id = case["id"]
        parent = mapped[case_id]
        spec = CASE_CATALOG[parent]
        status, result = _status(parent, result_by_name)
        counts[status] += 1
        row = (case, parent, spec, status, result)
        cards_by_section.setdefault(case["section"].split(" > ")[-1], []).append(row)
        if status == "failed":
            failed_rows.append(row)

    if failed_rows:
        body.append(
            '<section class="attention"><h2>Needs attention</h2>'
            f'<p class="lead">{len(failed_rows)} failed case'
            f'{"s" if len(failed_rows) != 1 else ""} from this run</p>'
        )
        for row in failed_rows:
            body.append(_case_card(*row, uri_cache))
        body.append("</section>")

    for section, section_cases in cards_by_section.items():
        passed = sum(status == "passed" for _, _, _, status, _ in section_cases)
        total = len(section_cases)
        present = " ".join(sorted({status for _, _, _, status, _ in section_cases}))
        body.append(f'<section class="group" data-has="{present}">')
        body.append(
            f'<h2 class="sec">{html.escape(section)}'
            f'<span class="secstat">· {passed}/{total}</span></h2>'
        )
        for row in section_cases:
            body.append(_case_card(*row, uri_cache))
        body.append("</section>")

    executed = counts["passed"] + counts["failed"]
    rate = (100 * counts["passed"] / executed) if executed else 0
    device = payload.get("device", {})
    app = payload.get("app", {})
    run_duration = _format_duration(payload.get("duration_seconds"))
    run_time = _format_run_time(
        payload.get("finished") or payload.get("started")
    )
    app_value = " ".join(x for x in (
        app.get("name"), app.get("version"),
        f"(build {app['build']})" if app.get("build") else "",
    ) if x).strip()
    if not app_value:
        app_value = "—"
    logo_uri = _image_uri(HEADER_LOGO)
    header_mark = (
        f'<img class="mark" src="{logo_uri}" alt="Spider Solitaire logo">'
        if logo_uri else '<div class="mark">S</div>'
    )

    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spider Solitaire — Regression Report</title>
<style>{CSS}</style></head><body><div class="wrap">
<div class="hero">
<div class="brand">{header_mark}<div><h1>Spider Solitaire</h1>
<div class="sub">Regression report · Unity functional suite</div></div></div>
{_donut(counts, executed, rate)}
</div>
<div class="chips">
{_chip("Device", device.get("model"))}
{_chip("Platform", "iOS " + device.get("ios", "") if device.get("ios") else "")}
{_chip("App", app_value)}
{_chip("Screen", device.get("screen"))}
{_chip("Duration", run_duration)}
{_chip("Run", run_time)}
</div>
{_filters(counts)}
{"".join(body)}
<footer>Generated by scripts/gen_regression_report.py · screenshots are compressed
JPEG evidence from log/</footer>
</div><script>{FILTER_JS}</script></body></html>
"""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(document)
    return out_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", default=os.path.join(config.LOG, "run_results.json"))
    parser.add_argument("--out", default=os.path.join(config.LOG, "spider_regression.html"))
    args = parser.parse_args(argv)
    print(f"wrote {build(args.results, args.out)}")


if __name__ == "__main__":
    main()
