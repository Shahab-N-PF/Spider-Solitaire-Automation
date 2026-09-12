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

from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "docs", "testrail"))
import config  # noqa: E402
from cases import CASES  # noqa: E402


# The TestRail list remains the person-facing source of truth. This catalog
# only connects each manual case to the automated parent and its evidence.
CASE_CATALOG = OrderedDict([
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
  color:#eaf1ff; background:linear-gradient(160deg,#12294f,#0a1226); min-height:100vh; }
.wrap { max-width:1040px; margin:0 auto; padding:28px 20px 60px; }
header { display:flex; align-items:center; gap:18px; }
.mark { width:64px; height:64px; border-radius:16px; background:linear-gradient(135deg,#ff5ea8,#ff9d3c);
  box-shadow:0 6px 22px rgba(0,0,0,.45); display:grid; place-items:center; font-size:28px; font-weight:800; }
h1 { font-size:26px; margin:0; font-weight:800; letter-spacing:.2px; }
.sub { color:#93a8cc; font-size:14px; margin-top:3px; }
.accent { height:4px; border-radius:4px; background:linear-gradient(120deg,#ff5ea8,#ff9d3c); margin:16px 0 22px; }
.chips { display:flex; flex-wrap:wrap; gap:10px; margin-bottom:22px; }
.chip { background:#152a52; border:1px solid #24406f; border-radius:12px; padding:8px 13px; display:flex; flex-direction:column; }
.chip .k { font-size:11px; text-transform:uppercase; letter-spacing:.6px; color:#93a8cc; }
.chip .v { font-size:14px; font-weight:600; margin-top:2px; }
.cards { display:flex; gap:14px; flex-wrap:wrap; margin-bottom:12px; }
.summary { flex:1; min-width:130px; background:#152a52; border:1px solid #24406f; border-radius:16px; padding:16px 18px; }
.summary .num { font-size:30px; font-weight:800; }
.summary .lbl { font-size:12px; color:#93a8cc; text-transform:uppercase; letter-spacing:.6px; }
.rate-wrap { background:#152a52; border:1px solid #24406f; border-radius:16px; padding:16px 18px; margin:14px 0 26px; }
.rate-top { display:flex; justify-content:space-between; font-size:13px; color:#93a8cc; }
.bar { height:12px; border-radius:8px; background:#0c1a35; margin-top:10px; overflow:hidden; }
.bar > i { display:block; height:100%; background:linear-gradient(120deg,#ff5ea8,#ff9d3c); }
.sec { font-size:15px; font-weight:800; letter-spacing:.3px; margin:26px 0 10px; display:flex; align-items:baseline; gap:12px; }
.secstat { font-size:12px; font-weight:600; color:#93a8cc; }
.case { background:#152a52; border:1px solid #24406f; border-radius:12px; margin-bottom:9px; overflow:hidden; }
.case.failed { border-color:#ff5a6a; }
.case.skipped { border-color:#f2b544; }
summary { list-style:none; cursor:pointer; display:flex; align-items:center; gap:12px; padding:13px 16px; }
summary::-webkit-details-marker { display:none; }
.cid { font-family:ui-monospace,Menlo,monospace; font-size:13px; color:#93a8cc; min-width:64px; }
.title { flex:1; font-weight:600; font-size:14.5px; }
.pill { color:#08122a; font-weight:800; font-size:11px; padding:3px 10px; border-radius:20px; letter-spacing:.4px; }
.dur { color:#93a8cc; font-size:12px; min-width:56px; text-align:right; }
.detail { padding:0 16px 16px; }
.shot { display:block; max-width:100%; max-height:620px; border-radius:10px; border:1px solid #24406f; margin:0 0 12px; }
.shot-caption { color:#93a8cc; font-size:11px; margin:-7px 0 12px; }
.noshot { color:#93a8cc; font-size:13px; margin:0 0 12px; }
.msg { background:#0c1a35; border:1px solid #24406f; border-radius:8px; padding:10px; color:#ffd7db; font-size:12px; white-space:pre-wrap; overflow-x:auto; margin:0 0 12px; }
.evidence { background:#0a1930; border:1px solid #24406f; border-left:3px solid #5aa9ff; border-radius:8px; padding:10px; color:#cfe3ff; font-size:12px; white-space:pre-wrap; overflow-x:auto; margin:0 0 12px; }
footer { color:#93a8cc; font-size:12px; text-align:center; margin-top:34px; }
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


def _shots_for(case_id, spec):
    names = list(spec.get("shots", []))
    names.extend(spec.get("extra", {}).get(case_id, []))
    return list(dict.fromkeys(names))


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
    uri_cache = {}
    body = []
    for case in CASES:
        case_id = case["id"]
        parent = mapped[case_id]
        spec = CASE_CATALOG[parent]
        status, result = _status(parent, result_by_name)
        counts[status] += 1
        cards_by_section.setdefault(case["section"].split(" > ")[-1], []).append(
            (case, parent, spec, status, result)
        )

    for section, section_cases in cards_by_section.items():
        passed = sum(status == "passed" for _, _, _, status, _ in section_cases)
        total = len(section_cases)
        cards = [f'<h2 class="sec">{html.escape(section)}'
                 f'<span class="secstat">{passed}/{total} passed</span></h2>']
        for case, parent, spec, status, result in section_cases:
            case_id = case["id"]
            title = html.escape(case["title"])
            duration = _format_duration(result.get("seconds") if result else None)
            status_label = status.upper()
            color = {"passed": "#3ddc84", "failed": "#ff5a6a",
                     "skipped": "#f2b544"}[status]
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
            found = 0
            if status != "skipped":
                for shot_name in shot_names:
                    path = os.path.join(config.LOG, shot_name)
                    if shot_name not in uri_cache:
                        uri_cache[shot_name] = _image_uri(path)
                    uri = uri_cache[shot_name]
                    if uri:
                        found += 1
                        detail.append(
                            f'<img class="shot" src="{uri}" alt="{html.escape(shot_name)}">'
                            f'<div class="shot-caption">Evidence: '
                            f'{html.escape(shot_name)}</div>'
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
            detail_html = "".join(detail)
            cards.append(
                f'<details class="case {status}">'
                f'<summary><span class="cid">{html.escape(case_id)}</span>'
                f'<span class="title">{title}</span>'
                f'<span class="pill" style="background:{color}">{status_label}</span>'
                f'<span class="dur">{duration}</span></summary>'
                f'<div class="detail"><div class="evidence">Automated parent: '
                f'{html.escape(parent)}</div>{detail_html}</div></details>'
            )
        body.extend(cards)

    executed = counts["passed"] + counts["failed"]
    rate = (100 * counts["passed"] / executed) if executed else 0
    device = payload.get("device", {})
    app = payload.get("app", {})
    run_duration = _format_duration(payload.get("duration_seconds"))
    run_time = payload.get("finished") or payload.get("started") or "No run recorded"
    app_value = " ".join(x for x in (
        app.get("name"), app.get("version"),
        f"(build {app['build']})" if app.get("build") else "",
    ) if x).strip()
    if not app_value:
        app_value = "—"

    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spider Solitaire — Regression Report</title>
<style>{CSS}</style></head><body><div class="wrap">
<header><div class="mark">S</div><div><h1>Spider Solitaire — Regression Report</h1>
<div class="sub">Unity functional suite · one card per TestRail case</div></div></header>
<div class="accent"></div>
<div class="chips">
{_chip("Device", device.get("model"))}
{_chip("Platform", "iOS " + device.get("ios", "") if device.get("ios") else "")}
{_chip("App", app_value)}
{_chip("Screen", device.get("screen"))}
{_chip("Duration", run_duration)}
{_chip("Run", run_time)}
</div>
<div class="cards">
<div class="summary"><div class="num">{len(CASES)}</div><div class="lbl">Total</div></div>
<div class="summary"><div class="num" style="color:#3ddc84">{counts["passed"]}</div><div class="lbl">Passed</div></div>
<div class="summary"><div class="num" style="color:#ff5a6a">{counts["failed"]}</div><div class="lbl">Failed</div></div>
<div class="summary"><div class="num" style="color:#f2b544">{counts["skipped"]}</div><div class="lbl">Skipped</div></div>
</div>
<div class="rate-wrap"><div class="rate-top"><span>Pass rate (of executed)</span>
<span>{rate:.0f}% &nbsp;·&nbsp; {counts["passed"]}/{executed}</span></div>
<div class="bar"><i style="width:{rate:.2f}%"></i></div></div>
{"".join(body)}
<footer>Generated by scripts/gen_regression_report.py · screenshots are compressed
JPEG evidence from log/</footer>
</div></body></html>
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
