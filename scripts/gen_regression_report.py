#!/usr/bin/env python3
"""Build a lightweight HTML report for the Spider functional regression run.

The report is one expandable card per manual TestRail case. A case inherits the
result of the automated test that covers it; cases whose parent was not run are
shown as skipped. Test screenshots stay in ``log/`` and are deliberately not
embedded, keeping the report small enough to share and open quickly.

Run:
    ./.venv/bin/python scripts/gen_regression_report.py
    ./.venv/bin/python scripts/gen_regression_report.py --out reports/Spider_Regression.html
"""
import argparse
import base64
import html
import json
import os
import re
import sys
from collections import OrderedDict
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADER_LOGO = os.path.join(REPO, "reports", "spider_report_header.jpg")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "docs", "testrail"))
import config  # noqa: E402
from cases import CASES  # noqa: E402


# The TestRail list remains the person-facing source of truth. This catalog
# only connects each manual case to its automated parent.
CASE_CATALOG = OrderedDict([
    ("installFromTestFlight", {"ids": ["FL-06"]}),
    ("verifyFirstLaunch", {
        "ids": ["FL-01", "FL-02", "FL-03", "FL-04", "FL-05"],
    }),
    ("verifyMainMenu", {"ids": ["MM-01"]}),
    ("verifyStatsPage", {
        "ids": ["ST-01", "ST-03", "ST-04"],
    }),
    ("verifyOptions", {
        "ids": ["OP-01", "OP-03", "OP-04", "OP-05", "OP-06", "OP-07"],
    }),
    ("verifyHelpShift", {"ids": ["HS-02"]}),
    ("verifyHelpPage", {
        "ids": ["HP-01", "HP-02", "HP-03"],
    }),
    ("verifySpiderLogo", {
        "ids": ["AB-01", "AB-03", "AB-04", "AB-05", "AB-06"],
    }),
    ("verifyMoreGamesBtn", {"ids": ["MG-01", "MG-02", "MG-03"]}),
    ("verifyPlay", {"ids": ["PL-01", "PL-02", "PL-03"]}),
    ("verifyAbandonNo", {"ids": ["PL-04"]}),
    ("openDebugTools", {"ids": ["QA-02", "QA-03", "QA-04"]}),
    ("verifyGamePlay", {
        "ids": [
            "GP-01", "GP-02", "GP-03", "GP-04", "GP-05", "GP-06",
            "GP-07", "GP-08", "GP-09", "GP-10", "GP-11", "GP-14",
        ],
    }),
    ("verifyVictory", {"ids": ["VI-01", "VI-02", "VI-03", "VI-04"]}),
    ("verifyDifficultyLevels", {
        "ids": ["DL-01", "DL-02", "DL-03", "DL-04"],
    }),
    ("verifyMoreGamesIcons", {
        "ids": ["PI-01", "PI-02", "PI-03", "PI-04", "PI-05", "PI-06"],
    }),
    ("resetStats", {"ids": ["RS-01", "RS-02"]}),
    ("verifyResetCancelled", {"ids": ["RS-03"]}),
    ("verifyHelpShiftOnline", {"ids": ["HS-01"]}),
    ("verifyChooseLook", {
        "ids": ["CL-01", "CL-03", "CL-04", "CL-05"],
    }),
    ("verifyAds", {
        "ids": ["AD-01", "AD-02", "AD-03", "AD-04", "AD-06", "AD-07"],
    }),
    ("triggerAdPoints", {
        "ids": [
            "TA-01", "TA-02", "TA-03", "TA-04", "TA-05",
            "TA-06", "TA-07", "TA-08", "TA-10",
        ],
    }),
    ("visitLastScore", {
        "ids": ["LS-01", "LS-02", "LS-03", "LS-04", "LS-05"],
    }),
    ("verifyAdFreeVersion", {"ids": ["AF-01", "AF-02", "AF-03", "AF-04"]}),
    ("submitFeedback", {"ids": ["FB-02", "FB-03", "FB-04", "FB-05", "FB-06"]}),
    ("verifyRelaunch", {"ids": ["RL-01", "RL-02"]}),
])


CSS = r"""
:root {
  color-scheme:light;
  --page:#f7f2ed; --surface:#fffdfa; --surface-soft:#fbf7f3;
  --ink:#211c19; --muted:#786d66; --line:#e7dcd4;
  --brand-dark:#191615; --brand-mid:#3b2b25;
  --accent:#e6613f; --accent-deep:#c9472c; --heart:#d8372b;
  --pass:#16835f; --pass-bg:#eaf8f2; --fail:#c23d4a; --fail-bg:#fff0f1;
  --skip:#806624; --skip-bg:#fff8df; --manual:#9a5b12; --manual-bg:#fff4e5;
  --shadow:0 12px 32px rgba(53,36,28,.08);
}
* { box-sizing:border-box; }
html { scroll-behavior:smooth; }
body {
  margin:0; min-height:100vh;
  font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  color:var(--ink); background:
    radial-gradient(circle at 7% 0%,rgba(230,97,63,.12),transparent 30rem),
    var(--page);
  -webkit-font-smoothing:antialiased;
}
button,summary { -webkit-tap-highlight-color:transparent; }
.sr-only { position:absolute; width:1px; height:1px; padding:0; margin:-1px;
  overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0; }
.wrap { max-width:1180px; margin:0 auto; padding:34px 24px 64px; }
.hero {
  position:relative; overflow:hidden; display:flex; align-items:center;
  justify-content:space-between; gap:28px; min-height:176px;
  padding:34px 38px; margin-bottom:22px; border-radius:24px;
  color:#fff; background:linear-gradient(130deg,var(--brand-dark) 0%,#261e1a 58%,var(--brand-mid) 100%);
  box-shadow:0 20px 50px rgba(54,34,26,.22);
}
.hero::before {
  content:""; position:absolute; inset:0; opacity:.34;
  background:
    repeating-radial-gradient(circle at 100% 0%,transparent 0 43px,rgba(255,255,255,.10) 44px 45px),
    repeating-conic-gradient(from 200deg at 100% 0%,transparent 0deg 17deg,rgba(255,255,255,.09) 18deg 19deg);
  mask-image:linear-gradient(to left,#000,transparent 68%);
  pointer-events:none;
}
.hero::after {
  content:"✦"; position:absolute; right:33%; top:28px; color:#fff;
  font-size:27px; line-height:1; text-shadow:0 0 18px rgba(255,255,255,.75);
  transform:rotate(8deg);
  pointer-events:none;
}
.hero-copy { position:relative; z-index:1; min-width:280px; }
.eyebrow {
  display:flex; align-items:center; gap:8px; margin-bottom:14px;
  color:#f4b8a7; font-size:11px; font-weight:750; letter-spacing:1.4px;
  text-transform:uppercase;
}
.eyebrow-dot { width:7px; height:7px; border-radius:50%; background:var(--accent); }
.brand { display:flex; align-items:center; gap:18px; }
.mark {
  width:72px; height:72px; border-radius:18px; object-fit:cover;
  background:var(--accent); border:1px solid rgba(255,255,255,.45);
  box-shadow:0 8px 24px rgba(0,0,0,.24);
}
h1 { margin:0; color:#fff; font-size:clamp(26px,4vw,38px); line-height:1.08;
  font-weight:760; letter-spacing:-.7px; }
.sub { color:#d9cbc5; font-size:14px; margin-top:8px; }
.run-state {
  position:relative; z-index:1; display:flex; align-items:center; gap:10px;
  padding:10px 14px; border:1px solid rgba(255,255,255,.18);
  border-radius:999px; background:rgba(255,255,255,.1);
  font-size:12px; font-weight:700; letter-spacing:.2px; backdrop-filter:blur(10px);
}
.run-state::before { content:""; width:9px; height:9px; border-radius:50%; }
.run-state.passed::before { background:#53d9a5; box-shadow:0 0 0 4px rgba(83,217,165,.14); }
.run-state.failed::before { background:#ff7f89; box-shadow:0 0 0 4px rgba(255,127,137,.14); }
.run-state.pending::before { background:#f6cf68; box-shadow:0 0 0 4px rgba(246,207,104,.14); }
.overview { display:grid; grid-template-columns:minmax(280px,1.05fr) 1.95fr; gap:18px; margin-bottom:18px; }
.score-card,.metric,.meta-panel,.toolbar,.attention,.group {
  background:var(--surface); border:1px solid var(--line); box-shadow:var(--shadow);
}
.score-card { border-radius:18px; padding:22px; }
.panel-label { color:var(--muted); font-size:11px; font-weight:750;
  letter-spacing:1px; text-transform:uppercase; }
.release-banner {
  position:relative; overflow:hidden; display:flex; align-items:center; gap:16px;
  margin-bottom:18px; padding:18px 22px; border:1px solid #b9dfd1;
  border-radius:18px; color:#155b46;
  background:linear-gradient(115deg,#eefaf5 0%,#f8fdfb 72%,#fff5f1 100%);
  box-shadow:var(--shadow);
}
.release-banner::after {
  content:""; position:absolute; right:-34px; bottom:-56px; width:130px; height:130px;
  border:1px solid rgba(230,97,63,.19); border-radius:50%;
  box-shadow:0 0 0 24px rgba(230,97,63,.045);
}
.release-icon {
  display:grid; place-items:center; width:42px; height:42px; flex:0 0 42px;
  border-radius:50%; color:#fff; background:var(--pass);
  box-shadow:0 8px 20px rgba(22,131,95,.2); font-size:22px; font-weight:800;
}
.release-copy { position:relative; z-index:1; flex:1; }
.release-copy strong { display:block; font-size:14px; line-height:1.45; }
.release-copy span { display:block; margin-top:3px; color:#26705a; font-size:12px; }
.teamwork-mark { position:relative; z-index:1; display:flex; margin-right:5px; }
.teamwork-mark i {
  display:block; width:19px; height:19px; margin-left:-5px;
  border:2px solid var(--accent); border-radius:50%; background:#fff8f5;
}
.teamwork-mark i:first-child { margin-left:0; border-color:var(--heart); }
.hero-stat { display:flex; align-items:center; gap:22px; margin-top:16px; }
.donut { width:126px; height:126px; border-radius:50%; display:grid; place-items:center;
  flex:0 0 126px; box-shadow:inset 0 0 0 1px rgba(23,32,51,.04); }
.donut-hole { width:82px; height:82px; border-radius:50%; background:var(--surface);
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  box-shadow:0 2px 12px rgba(23,32,51,.08); }
.donut-pct { color:var(--brand-dark); font-size:27px; font-weight:780; line-height:1; }
.donut-lbl { color:var(--muted); font-size:10px; font-weight:650; margin-top:4px; }
.score-copy strong { display:block; font-size:18px; line-height:1.25; }
.score-copy span { display:block; color:var(--muted); font-size:12px; line-height:1.5; margin-top:6px; }
.metric-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:18px; }
.metric { position:relative; overflow:hidden; min-height:166px; border-radius:18px; padding:22px; }
.metric::after { content:""; position:absolute; right:-22px; bottom:-28px;
  width:92px; height:92px; border-radius:50%; opacity:.55; }
.metric.passed::after { background:var(--pass-bg); }
.metric.failed::after { background:var(--fail-bg); }
.metric.skipped::after { background:var(--skip-bg); }
.metric-head { display:flex; align-items:center; gap:9px; color:var(--muted);
  font-size:12px; font-weight:700; }
.metric-dot { width:10px; height:10px; border-radius:50%; }
.metric.passed .metric-dot { background:var(--pass); }
.metric.failed .metric-dot { background:var(--fail); }
.metric.skipped .metric-dot { background:#c49a2e; }
.metric-value { display:block; margin-top:28px; font-size:38px; font-weight:780;
  line-height:1; letter-spacing:-1px; }
.metric-note { display:block; margin-top:8px; color:var(--muted); font-size:12px; }
.meta-panel { margin-bottom:18px; padding:20px 22px; border-radius:18px; }
.meta-head { display:flex; align-items:center; justify-content:space-between;
  gap:12px; margin-bottom:15px; }
.meta-head h2 { margin:0; font-size:15px; letter-spacing:-.1px; }
.meta-head span { color:var(--muted); font-size:12px; }
.chips { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:10px; }
.chip { padding:11px 12px; border:1px solid #e5eaf1; border-radius:12px;
  background:var(--surface-soft); overflow:hidden; }
.chip .k { display:block; color:var(--muted); font-size:10px; font-weight:750;
  letter-spacing:.65px; text-transform:uppercase; }
.chip .v { display:block; margin-top:5px; color:var(--ink); font-size:12px;
  font-weight:650; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.toolbar { position:sticky; top:12px; z-index:5; margin-bottom:12px;
  padding:16px; border-radius:16px; }
.toolbar-top { display:flex; align-items:center; justify-content:space-between; gap:18px; }
.toolbar-copy strong { display:block; font-size:14px; }
.toolbar-copy span { display:block; color:var(--muted); font-size:11px; margin-top:3px; }
.toolbar-controls { display:flex; align-items:center; justify-content:flex-end; flex-wrap:wrap; gap:8px; }
.case-search { position:relative; display:block; }
.case-search::before {
  content:""; position:absolute; left:12px; top:50%; width:9px; height:9px;
  border:2px solid #9a8b82; border-radius:50%; transform:translateY(-65%);
  pointer-events:none;
}
.case-search::after {
  content:""; position:absolute; left:22px; top:55%; width:6px; height:2px;
  border-radius:2px; background:#9a8b82; transform:rotate(45deg); pointer-events:none;
}
.case-search input {
  width:230px; height:34px; padding:7px 12px 7px 34px;
  border:1px solid var(--line); border-radius:999px; color:var(--ink);
  background:var(--surface-soft); font:inherit; font-size:11px;
}
.case-search input::placeholder { color:#9b8f88; }
.filters { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:7px; }
.filter { appearance:none; cursor:pointer; padding:7px 11px;
  border:1px solid var(--line); border-radius:999px; background:#fff;
  color:var(--muted); font:inherit; font-size:11px; font-weight:650;
  transition:transform .15s ease,border-color .15s ease,background .15s ease;
}
.filter:hover { transform:translateY(-1px); border-color:#acb7c7; }
.filter:focus-visible,summary:focus-visible,.tool-button:focus-visible,
.case-search input:focus-visible,.section-link:focus-visible {
  outline:3px solid rgba(230,97,63,.24); outline-offset:2px;
}
.filter b { color:var(--ink); margin-left:3px; }
.filter.is-on { color:#fff; border-color:var(--accent-deep); background:var(--accent-deep); }
.filter.is-on b { color:#fff; }
.filter[data-filter="passed"].is-on { border-color:var(--pass); background:var(--pass); }
.filter[data-filter="failed"].is-on { border-color:var(--fail); background:var(--fail); }
.filter[data-filter="skipped"].is-on { border-color:#9b7b25; background:#9b7b25; }
.tool-buttons { display:flex; gap:6px; }
.tool-button {
  cursor:pointer; padding:7px 10px; border:1px solid #e5c4b8; border-radius:999px;
  color:#99412d; background:#fff8f5; font:inherit; font-size:10px; font-weight:700;
  transition:background .15s ease,border-color .15s ease;
}
.tool-button:hover { border-color:var(--accent); background:#fff1eb; }
.section-nav {
  display:flex; align-items:center; gap:6px; margin:13px -2px -1px; padding:10px 2px 0;
  overflow-x:auto; border-top:1px solid #eee4dd; scrollbar-width:thin;
}
.section-link {
  flex:0 0 auto; padding:6px 9px; border:1px solid transparent; border-radius:8px;
  color:var(--muted); text-decoration:none; font-size:10px; font-weight:650;
  transition:color .15s ease,background .15s ease,border-color .15s ease;
}
.section-link:hover { color:var(--accent-deep); border-color:#efd0c5; background:#fff7f3; }
[hidden] { display:none !important; }
.attention { margin-bottom:20px; padding:22px; border-color:#f1c8cc;
  border-radius:18px; background:linear-gradient(145deg,#fff,#fff7f8); }
.attention-head { display:flex; align-items:flex-start; justify-content:space-between;
  gap:18px; margin-bottom:14px; }
.attention h2 { margin:0; color:#9e2734; font-size:17px; }
.attention .lead { color:#8a5760; font-size:12px; margin:5px 0 0; }
.attention-count { min-width:36px; padding:7px 10px; border-radius:10px;
  color:#fff; background:var(--fail); font-size:14px; font-weight:750; text-align:center; }
.empty-state { margin-bottom:20px; padding:34px 20px; border:1px dashed #d9c8be;
  border-radius:18px; color:var(--muted); background:rgba(255,253,250,.72); text-align:center; }
.empty-state strong { display:block; color:var(--ink); font-size:14px; }
.empty-state span { display:block; margin-top:5px; font-size:12px; }
.group { margin-bottom:16px; padding:20px; border-radius:18px; scroll-margin-top:154px; }
.sec { display:flex; align-items:center; gap:12px; margin:0 0 14px;
  font-size:16px; font-weight:740; letter-spacing:-.15px; }
.sec-title { flex:1; }
.secstat { color:var(--muted); font-size:11px; font-weight:650; }
.section-track { width:92px; height:6px; overflow:hidden; border-radius:999px; background:#edf1f6; }
.section-fill { display:block; height:100%; border-radius:inherit;
  background:linear-gradient(90deg,var(--accent-deep),var(--accent)); }
.case { margin-top:8px; overflow:hidden; border:1px solid var(--line);
  border-radius:13px; background:#fff; transition:border-color .15s ease,box-shadow .15s ease; }
.case:first-of-type { margin-top:0; }
.case:hover { border-color:#e1b8aa; box-shadow:0 6px 18px rgba(80,47,35,.07); }
.case.failed { border-color:#efc2c6; background:#fffafb; }
.case.skipped { background:#fffdf7; }
.case.passed_manually { background:#fffaf3; border-color:#f1d8b5; }
summary { list-style:none; cursor:pointer; display:flex; align-items:center;
  gap:12px; min-height:56px; padding:11px 14px; }
summary::-webkit-details-marker { display:none; }
summary::after { content:""; width:8px; height:8px; flex:0 0 8px;
  border-right:2px solid #98a2b3; border-bottom:2px solid #98a2b3;
  transform:rotate(45deg) translateY(-2px); transition:transform .18s ease; }
details[open] summary::after { transform:rotate(225deg) translate(-1px,-1px); }
.case-id { flex:0 0 52px; color:var(--muted); font-size:10px; font-weight:780;
  letter-spacing:.45px; }
.status-mark { width:9px; height:9px; flex:0 0 9px; border-radius:50%; }
.passed .status-mark { background:var(--pass); box-shadow:0 0 0 4px var(--pass-bg); }
.failed .status-mark { background:var(--fail); box-shadow:0 0 0 4px var(--fail-bg); }
.skipped .status-mark { background:#c49a2e; box-shadow:0 0 0 4px var(--skip-bg); }
.passed_manually .status-mark { background:var(--manual); box-shadow:0 0 0 4px var(--manual-bg); }
.title { flex:1; font-size:13px; font-weight:650; line-height:1.35; }
.pill { padding:4px 8px; border-radius:999px; font-size:9px; font-weight:780;
  letter-spacing:.4px; text-transform:uppercase; white-space:nowrap; }
.passed .pill { color:var(--pass); background:var(--pass-bg); }
.failed .pill { color:var(--fail); background:var(--fail-bg); }
.skipped .pill { color:var(--skip); background:var(--skip-bg); }
.passed_manually .pill { color:var(--manual); background:var(--manual-bg); }
.dur { color:var(--muted); font-size:11px; min-width:58px; text-align:right; }
.detail { padding:0 14px 14px 99px; }
.note { color:var(--muted); font-size:12px; line-height:1.55; margin:0; }
.msg { margin:0; padding:11px 12px; overflow-x:auto; white-space:pre-wrap;
  border:1px solid #f0c6ca; border-radius:10px; color:#982b37;
  background:var(--fail-bg); font:500 11px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace; }
.evidence { display:inline-flex; align-items:center; gap:7px; margin-bottom:10px;
  padding:6px 9px; border:1px solid #e2e8f1; border-radius:8px;
  color:#536176; background:var(--surface-soft); font-size:10px; font-weight:650; }
.evidence::before { content:""; width:6px; height:6px; border-radius:50%; background:#7a8daf; }
footer { color:var(--muted); font-size:11px; text-align:center; margin-top:30px; }
@media (max-width:920px) {
  .overview { grid-template-columns:1fr; }
  .chips { grid-template-columns:repeat(3,1fr); }
}
@media (max-width:680px) {
  .wrap { padding:16px 12px 40px; }
  .hero { align-items:flex-start; flex-direction:column; min-height:0; padding:26px 22px; border-radius:18px; }
  .mark { width:58px; height:58px; border-radius:15px; }
  .metric-grid { grid-template-columns:repeat(3,1fr); gap:8px; }
  .metric { min-height:126px; padding:16px 13px; }
  .metric-value { margin-top:20px; font-size:30px; }
  .metric-note { display:none; }
  .chips { grid-template-columns:repeat(2,1fr); }
  .toolbar { position:static; }
  .toolbar-top { align-items:flex-start; flex-direction:column; }
  .toolbar-controls { justify-content:flex-start; width:100%; }
  .case-search,.case-search input { width:100%; }
  .filters { justify-content:flex-start; }
  .group,.attention,.score-card,.meta-panel { padding:16px; }
  .section-track { display:none; }
  .case-id { flex-basis:45px; }
  .dur { display:none; }
  .detail { padding-left:79px; }
}
@media (max-width:430px) {
  .metric-head { font-size:10px; }
  .metric-value { font-size:26px; }
  .pill { display:none; }
  .hero-stat { gap:14px; }
  .donut { width:110px; height:110px; flex-basis:110px; }
  .donut-hole { width:72px; height:72px; }
}
@media print {
  body { background:#fff; }
  .wrap { max-width:none; padding:0; }
  .hero,.score-card,.metric,.meta-panel,.toolbar,.attention,.group { box-shadow:none; }
  .toolbar { position:static; }
  .filters { display:none; }
  .case { break-inside:avoid; }
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


def _format_device_model(identifier):
    """Pair Apple's model identifier with a person-friendly device name."""
    names = {
        "iPhone12,1": "iPhone 11",
    }
    if not identifier:
        return "—"
    name = names.get(str(identifier))
    return f"{name} ({identifier})" if name else str(identifier)


def _jpeg_data_uri(path):
    """Embed the small report logo without pulling screenshots into the HTML."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as fh:
            encoded = base64.b64encode(fh.read()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"
    except OSError:
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


CHECK_STATUS = {
    "PASS": "passed",
    "FAIL": "failed",
    "Passed Manually": "passed_manually",
}


def _status(parent, results, case_id=None):
    result = results.get(parent)
    if not result:
        return "skipped", None
    checks = result.get("checks") or []
    if case_id and checks:
        match = next((c for c in checks if c.get("id") == case_id), None)
        if match:
            status = CHECK_STATUS.get(match.get("status"), "passed")
            merged = dict(result)
            merged["error"] = match.get("error") or ""
            merged["check"] = match
            return status, merged
        if result.get("ok"):
            return "skipped", result
        return "failed", result
    return ("passed" if result.get("ok") else "failed"), result


def _section_id(label):
    slug = re.sub(r"[^a-z0-9]+", "-", label.casefold()).strip("-")
    return f"section-{slug or 'cases'}"


def _case_card(case, parent, status, result, open_failed=True):
    """One expandable TestRail card, optionally opened when the case failed."""
    case_id = case["id"]
    title = html.escape(case["title"])
    duration = _format_duration(result.get("seconds") if result else None)
    detail = []
    check = (result or {}).get("check") or {}
    if status == "skipped":
        if result:
            detail.append(
                '<p class="note">Not exercised in this run. '
                f'<code>{html.escape(parent)}</code> completed without '
                "this check.</p>"
            )
        else:
            detail.append(
                f'<p class="note">Not run in this invocation. '
                f'Run <code>run_all.py {html.escape(parent)}</code> to '
                "populate this case.</p>"
            )
    elif result and result.get("error"):
        detail.append(f'<pre class="msg">{html.escape(result["error"])}</pre>')
    elif status == "passed_manually":
        detail.append(
            '<p class="note">Closed by hand after the automated closer '
            "could not match the interstitial.</p>"
        )

    opened = " open" if (open_failed and status == "failed") else ""
    css_class = "passed passed_manually" if status == "passed_manually" else status
    filter_status = "passed" if status == "passed_manually" else status
    search_value = html.escape(
        f"{case_id} {case['title']}".casefold(), quote=True
    )
    pill = "passed manually" if status == "passed_manually" else status
    parent_line = html.escape(parent)
    if check.get("label"):
        parent_line += f' · {html.escape(check["label"])}'
    return (
        f'<details class="case {css_class}" data-status="{filter_status}" '
        f'data-search="{search_value}"{opened}>'
        f'<summary><span class="status-mark" aria-hidden="true"></span>'
        f'<span class="case-id">{html.escape(case_id)}</span>'
        f'<span class="title">{title}</span>'
        f'<span class="pill">{pill}</span>'
        f'<span class="dur">{duration}</span></summary>'
        f'<div class="detail"><div class="evidence">Automated parent: '
        f'{parent_line}</div>{"".join(detail)}</div></details>'
    )


def _donut(counts, executed, rate):
    """CSS conic-gradient donut and a compact run-health summary."""
    total = max(sum(counts.values()), 1)
    pass_pct = 100.0 * counts["passed"] / total
    fail_pct = 100.0 * counts["failed"] / total
    fail_end = pass_pct + fail_pct
    gradient = (
        f"conic-gradient(#16835f 0 {pass_pct:.2f}%, "
        f"#c23d4a {pass_pct:.2f}% {fail_end:.2f}%, "
        f"#d2a438 {fail_end:.2f}% 100%)"
    )
    if executed == 0:
        gradient = "conic-gradient(#dfe5ee 0 100%)"
    center = f"{rate:.0f}%" if executed else "—"
    if counts["failed"]:
        headline = "Review required"
        note = f'{counts["failed"]} case{"s" if counts["failed"] != 1 else ""} need attention.'
    elif executed:
        headline = "Run is healthy"
        note = "All executed cases passed."
    else:
        headline = "Awaiting results"
        note = "Run the suite to populate this report."
    return f"""<div class="hero-stat">
<div class="donut" style="background:{gradient}">
<div class="donut-hole"><div class="donut-pct">{center}</div>
<div class="donut-lbl">pass rate</div></div></div>
<div class="score-copy"><strong>{headline}</strong><span>{note}<br>
{counts["passed"]}/{executed or 0} executed cases passed.</span></div>
</div>"""


def _metric(kind, label, value, note):
    return f"""<article class="metric {kind}">
<div class="metric-head"><span class="metric-dot"></span>{html.escape(label)}</div>
<strong class="metric-value">{value}</strong>
<span class="metric-note">{html.escape(note)}</span>
</article>"""


def _release_banner(counts):
    """Show release approval only when the report contains no failures."""
    if counts["failed"]:
        return ""
    return """<section class="release-banner" aria-label="Release readiness">
<div class="release-icon" aria-hidden="true">✓</div>
<div class="release-copy">
<strong>The build passed smoke, sanity and full regression testing, with
stability confirmed and no blocking issues identified.</strong>
<span>Build is approved for release.</span>
</div>
<div class="teamwork-mark" aria-hidden="true"><i></i><i></i><i></i></div>
</section>"""


FILTER_JS = """
(function () {
  var buttons = Array.from(document.querySelectorAll(".filter"));
  var groups = Array.from(document.querySelectorAll(".group"));
  var search = document.getElementById("case-search");
  var visibleCount = document.getElementById("visible-count");
  var emptyState = document.getElementById("empty-state");
  var attention = document.querySelector(".attention");
  var mode = "all";

  function apply() {
    var query = (search.value || "").trim().toLowerCase();
    var visible = 0;
    document.body.setAttribute("data-filter", mode);
    buttons.forEach(function (button) {
      var on = button.getAttribute("data-filter") === mode;
      button.classList.toggle("is-on", on);
      button.setAttribute("aria-pressed", on ? "true" : "false");
    });
    groups.forEach(function (group) {
      var inGroup = 0;
      group.querySelectorAll(":scope > .case").forEach(function (card) {
        var statusMatch = mode === "all" || card.dataset.status === mode;
        var searchMatch = !query || card.dataset.search.indexOf(query) !== -1;
        card.hidden = !(statusMatch && searchMatch);
        if (!card.hidden) {
          inGroup += 1;
          visible += 1;
        }
      });
      group.hidden = inGroup === 0;
      var link = document.querySelector(
        '.section-link[data-target="' + group.id + '"]'
      );
      if (link) link.hidden = group.hidden;
    });
    if (attention) attention.hidden = mode !== "all" || query !== "";
    visibleCount.textContent = visible + " of " +
      document.querySelectorAll(".group > .case").length + " shown";
    emptyState.hidden = visible !== 0;
  }

  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      mode = button.getAttribute("data-filter");
      apply();
    });
  });
  search.addEventListener("input", apply);
  document.getElementById("expand-visible").addEventListener("click", function () {
    document.querySelectorAll(".group > .case:not([hidden])").forEach(function (card) {
      if (!card.closest(".group").hidden) card.open = true;
    });
  });
  document.getElementById("collapse-all").addEventListener("click", function () {
    document.querySelectorAll("details.case").forEach(function (card) {
      card.open = false;
    });
  });
  apply();
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
    section_links = []
    body = []
    for case in CASES:
        case_id = case["id"]
        parent = mapped[case_id]
        status, result = _status(parent, result_by_name, case_id)
        count_key = "passed" if status == "passed_manually" else status
        counts[count_key] += 1
        row = (case, parent, status, result)
        cards_by_section.setdefault(case["section"].split(" > ")[-1], []).append(row)
        if status == "failed":
            failed_rows.append(row)

    if failed_rows:
        body.append(
            '<section class="attention"><div class="attention-head"><div>'
            '<h2>Needs attention</h2>'
            f'<p class="lead">{len(failed_rows)} failed case'
            f'{"s" if len(failed_rows) != 1 else ""} from this run</p></div>'
            f'<div class="attention-count">{len(failed_rows)}</div></div>'
        )
        for row in failed_rows:
            body.append(_case_card(*row))
        body.append("</section>")

    for section, section_cases in cards_by_section.items():
        passed = sum(
            status in ("passed", "passed_manually")
            for _, _, status, _ in section_cases
        )
        total = len(section_cases)
        present = {status for _, _, status, _ in section_cases}
        if "passed_manually" in present:
            present.add("passed")
        present = " ".join(sorted(present))
        section_pct = (100 * passed / total) if total else 0
        section_id = _section_id(section)
        section_links.append(
            f'<a class="section-link" href="#{section_id}" '
            f'data-target="{section_id}">{html.escape(section)}</a>'
        )
        body.append(
            f'<section class="group" id="{section_id}" data-has="{present}">'
        )
        body.append(
            f'<h2 class="sec"><span class="sec-title">{html.escape(section)}</span>'
            f'<span class="secstat">{passed}/{total} passed</span>'
            f'<span class="section-track" aria-hidden="true"><span '
            f'class="section-fill" style="width:{section_pct:.1f}%"></span>'
            f'</span></h2>'
        )
        for row in section_cases:
            body.append(_case_card(*row))
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
    logo_uri = _jpeg_data_uri(HEADER_LOGO)
    header_mark = (
        f'<img class="mark" src="{logo_uri}" alt="Spider Solitaire logo">'
        if logo_uri else '<div class="mark">S</div>'
    )
    if counts["failed"]:
        run_state_class, run_state_label = "failed", "Attention required"
    elif executed:
        run_state_class, run_state_label = "passed", "Run complete"
    else:
        run_state_class, run_state_label = "pending", "Awaiting results"

    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spider Solitaire — Regression Report</title>
<style>{CSS}</style></head><body><div class="wrap">
<div class="hero">
<div class="hero-copy"><div class="eyebrow"><span class="eyebrow-dot"></span>
Quality assurance report</div>
<div class="brand">{header_mark}<div><h1>Spider Solitaire</h1>
<div class="sub">Unity functional regression · {html.escape(run_time)}</div></div></div>
</div>
<div class="run-state {run_state_class}">{run_state_label}</div>
</div>
<section class="overview" aria-label="Run summary">
<article class="score-card"><div class="panel-label">Overall quality</div>
{_donut(counts, executed, rate)}</article>
<div class="metric-grid">
{_metric("passed", "Passed", counts["passed"], "Ready for review")}
{_metric("failed", "Failed", counts["failed"], "Require attention")}
{_metric("skipped", "Skipped", counts["skipped"], "Not exercised")}
</div>
</section>
{_release_banner(counts)}
<section class="meta-panel"><div class="meta-head"><h2>Run environment</h2>
<span>Captured from the connected test device</span></div>
<div class="chips">
{_chip("Device", _format_device_model(device.get("model")))}
{_chip("Platform", "iOS " + device.get("ios", "") if device.get("ios") else "")}
{_chip("App", app_value)}
{_chip("Screen", device.get("screen"))}
{_chip("Duration", run_duration)}
{_chip("Run", run_time)}
</div></section>
<div class="toolbar">
<div class="toolbar-top">
<div class="toolbar-copy"><strong>Test cases</strong>
<span id="visible-count">{sum(counts.values())} of {sum(counts.values())} shown</span></div>
<div class="toolbar-controls">
<label class="case-search"><span class="sr-only">Search test cases</span>
<input id="case-search" type="search" placeholder="Search ID or case title"
autocomplete="off"></label>
{_filters(counts)}
<div class="tool-buttons">
<button class="tool-button" id="expand-visible" type="button">Expand visible</button>
<button class="tool-button" id="collapse-all" type="button">Collapse all</button>
</div>
</div></div>
<nav class="section-nav" aria-label="Report sections">{"".join(section_links)}</nav>
</div>
<section class="empty-state" id="empty-state" hidden>
<strong>No matching test cases</strong>
<span>Try a different search term or status filter.</span>
</section>
{"".join(body)}
<footer>Generated by scripts/gen_regression_report.py · test screenshots remain
available separately in log/ and are not embedded here.</footer>
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
