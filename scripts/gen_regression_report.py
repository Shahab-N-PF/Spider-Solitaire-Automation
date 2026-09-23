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
import csv
import html
import json
import os
import re
import sys
from collections import OrderedDict
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADER_LOGO = os.path.join(REPO, "reports", "spider_report_header.jpg")
MANUAL_CASES_CSV = os.path.join(
    REPO, "docs", "testrail", "manual_spider_solitaire_8.0.3_regression.csv"
)
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
.coverage-strip {
  display:flex; align-items:center; justify-content:space-between; gap:16px;
  margin-bottom:12px; padding:13px 18px; border:1px solid var(--line);
  border-radius:14px; color:var(--muted); background:var(--surface);
  box-shadow:var(--shadow); font-size:12px;
}
.coverage-strip strong { color:var(--ink); font-size:13px; }
.verification-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr));
  gap:18px; margin-bottom:18px; }
.score-card,.metric,.meta-panel,.toolbar,.attention,.group,.coverage-strip {
  background:var(--surface); border:1px solid var(--line); box-shadow:var(--shadow);
}
.score-card { border-radius:18px; padding:22px; }
.verification-card { min-width:0; }
.verification-stats { display:grid; grid-template-columns:repeat(4,minmax(0,1fr));
  gap:8px; margin-top:18px; }
.verification-stat { min-width:0; padding:10px 11px; border:1px solid #e5eaf1;
  border-radius:11px; background:var(--surface-soft); }
.verification-stat .k { display:flex; align-items:center; gap:6px; color:var(--muted);
  font-size:9px; font-weight:750; letter-spacing:.55px; text-transform:uppercase; }
.verification-stat .k::before { content:""; width:6px; height:6px; flex:0 0 6px;
  border-radius:50%; background:#98a2b3; }
.verification-stat.passed .k::before { background:var(--pass); }
.verification-stat.failed .k::before { background:var(--fail); }
.verification-stat.skipped .k::before { background:#c49a2e; }
.verification-stat .v { display:block; margin-top:5px; color:var(--ink);
  font-size:22px; font-weight:780; line-height:1; }
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
.manual-verification {
  margin-top:26px; padding:22px; border:1px solid var(--line); border-radius:18px;
  background:var(--surface); box-shadow:var(--shadow); scroll-margin-top:154px;
}
.manual-head { display:flex; align-items:flex-start; justify-content:space-between;
  gap:18px; margin-bottom:16px; }
.manual-head h2 { margin:0; font-size:19px; letter-spacing:-.2px; }
.manual-head p { max-width:68ch; margin:5px 0 0; color:var(--muted);
  font-size:12px; line-height:1.5; }
.manual-stats { display:grid; grid-template-columns:repeat(4,minmax(0,1fr));
  gap:10px; margin-bottom:20px; }
.manual-stat { padding:13px 14px; border:1px solid #e5eaf1; border-radius:12px;
  background:var(--surface-soft); }
.manual-stat .k { display:block; color:var(--muted); font-size:10px;
  font-weight:750; letter-spacing:.65px; text-transform:uppercase; }
.manual-stat .v { display:block; margin-top:4px; font-size:25px; font-weight:780;
  line-height:1; }
.manual-category { margin:20px 2px 8px; color:var(--accent-deep); font-size:11px;
  font-weight:780; letter-spacing:.7px; text-transform:uppercase; }
.manual-category:first-of-type { margin-top:0; }
.manual-case .case-id { flex-basis:66px; }
.manual-case .detail { padding-left:113px; }
.case.selectable .detail { padding-left:126px; }
.manual-case.selectable .detail { padding-left:140px; }
.manual-case.passed .status-edit { color:var(--pass); background-color:var(--pass-bg); }
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
.case-search input:focus-visible,.section-link:focus-visible,
.status-edit:focus-visible,#bulk-status:focus-visible,.case-check:focus-visible {
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
.bulk-bar {
  display:flex; align-items:center; flex-wrap:wrap; gap:10px;
  margin:12px -2px -1px; padding:12px 2px 0; border-top:1px solid #eee4dd;
}
.bulk-select-all {
  display:inline-flex; align-items:center; gap:7px; cursor:pointer;
  color:var(--ink); font-size:11px; font-weight:650;
}
.bulk-select-all input,.case-check {
  width:15px; height:15px; margin:0; accent-color:var(--accent-deep); cursor:pointer;
}
.case-pick { display:flex; align-items:center; flex:0 0 15px; cursor:pointer; }
.case.selected { border-color:#e8b39f; box-shadow:0 0 0 2px rgba(230,97,63,.16); }
.bulk-count { color:var(--muted); font-size:11px; font-weight:650; min-width:72px; }
.bulk-apply-label {
  display:inline-flex; align-items:center; gap:7px;
  color:var(--muted); font-size:11px; font-weight:650;
}
#bulk-status {
  appearance:none; -webkit-appearance:none; height:34px;
  padding:0 28px 0 12px; border:1px solid var(--line); border-radius:999px;
  color:var(--ink); background-color:var(--surface-soft);
  font:inherit; font-size:11px; font-weight:650;
  background-repeat:no-repeat; background-position:right 10px center;
  background-size:8px 8px;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='8' height='8' viewBox='0 0 8 8'%3E%3Cpath fill='%23786d66' d='M1 2.5l3 3 3-3'/%3E%3C/svg%3E");
}
.tool-button:disabled { opacity:.45; cursor:not-allowed; }
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
.status-edit {
  appearance:none; -webkit-appearance:none; cursor:pointer; flex:0 0 auto;
  max-width:154px; padding:4px 20px 4px 8px; border:0; border-radius:999px;
  font:inherit; font-size:9px; font-weight:780; letter-spacing:.4px;
  text-transform:uppercase; white-space:nowrap;
  background-repeat:no-repeat; background-position:right 7px center;
  background-size:8px 8px;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='8' height='8' viewBox='0 0 8 8'%3E%3Cpath fill='%23786d66' d='M1 2.5l3 3 3-3'/%3E%3C/svg%3E");
}
.failed .status-edit { color:var(--fail); background-color:var(--fail-bg); }
.skipped .status-edit { color:var(--skip); background-color:var(--skip-bg); }
.passed_manually .status-edit { color:var(--manual); background-color:var(--manual-bg); }
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
  .verification-grid { grid-template-columns:1fr; }
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
  .coverage-strip { align-items:flex-start; flex-direction:column; }
  .verification-stats { grid-template-columns:repeat(2,1fr); }
  .chips { grid-template-columns:repeat(2,1fr); }
  .toolbar { position:static; }
  .toolbar-top { align-items:flex-start; flex-direction:column; }
  .toolbar-controls { justify-content:flex-start; width:100%; }
  .case-search,.case-search input { width:100%; }
  .filters { justify-content:flex-start; }
  .group,.attention,.score-card,.meta-panel,.manual-verification { padding:16px; }
  .manual-stats { grid-template-columns:repeat(2,1fr); }
  .section-track { display:none; }
  .case-id { flex-basis:45px; }
  .manual-case .case-id { flex-basis:58px; }
  .dur { display:none; }
  .detail { padding-left:79px; }
  .manual-case .detail { padding-left:92px; }
  .case.selectable .detail { padding-left:106px; }
  .manual-case.selectable .detail { padding-left:119px; }
}
@media (max-width:430px) {
  .metric-head { font-size:10px; }
  .metric-value { font-size:26px; }
  .pill { display:none; }
  .status-edit { display:inline-block; font-size:8px; max-width:132px; }
  .hero-stat { gap:14px; }
  .donut { width:110px; height:110px; flex-basis:110px; }
  .donut-hole { width:72px; height:72px; }
}
@media print {
  body { background:#fff; }
  .wrap { max-width:none; padding:0; }
  .hero,.score-card,.metric,.meta-panel,.toolbar,.attention,.group,.coverage-strip,
  .manual-verification { box-shadow:none; }
  .toolbar { position:static; }
  .filters,.bulk-bar,.case-pick { display:none; }
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


def _load_manual_cases(path):
    """Load the manual-only TestRail export and reject ambiguous inputs."""
    required = {"ID", "Title", "Case ID", "Priority", "Section", "Type"}
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(
                    "manual case CSV is missing column(s): "
                    + ", ".join(sorted(missing))
                )
            cases = []
            seen = set()
            for line_number, row in enumerate(reader, start=2):
                case_id = (row.get("Case ID") or "").strip()
                title = (row.get("Title") or "").strip()
                section = (row.get("Section") or "").strip()
                if not case_id or not title or not section:
                    raise ValueError(
                        f"manual case CSV line {line_number} requires "
                        "Case ID, Title, and Section"
                    )
                if case_id in seen:
                    raise ValueError(
                        f"manual case CSV contains duplicate Case ID {case_id}"
                    )
                seen.add(case_id)
                cases.append({
                    "id": case_id,
                    "test_id": (row.get("ID") or "").strip(),
                    "title": title,
                    "section": section,
                    "priority": (row.get("Priority") or "—").strip(),
                    "type": (row.get("Type") or "—").strip(),
                })
    except OSError as exc:
        raise ValueError(f"cannot read manual case CSV {path}: {exc}") from exc
    if not cases:
        raise ValueError(f"manual case CSV contains no cases: {path}")
    return cases


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


def _case_pick(case_id):
    safe_id = html.escape(case_id)
    return (
        f'<label class="case-pick">'
        f'<input type="checkbox" class="case-check" '
        f'aria-label="Select {safe_id}"></label>'
    )


def _status_control(case_id, status):
    """Editable badge for failed/skipped cards; static pill otherwise."""
    if status not in ("failed", "skipped"):
        pill = "passed manually" if status == "passed_manually" else status
        return f'<span class="pill">{html.escape(pill)}</span>'
    if status == "failed":
        options = (
            '<option value="failed" selected>Failed</option>'
            '<option value="passed_manually">Passed manually</option>'
        )
    else:
        options = (
            '<option value="skipped" selected>Skipped</option>'
            '<option value="passed_manually">Passed manually</option>'
        )
    safe_id = html.escape(case_id)
    return (
        f'<select class="status-edit" aria-label="Set status for {safe_id}">'
        f'{options}</select>'
    )


def _manual_status_control(case_id):
    safe_id = html.escape(case_id)
    return (
        f'<select class="status-edit manual-status-edit" '
        f'aria-label="Set manual status for {safe_id}">'
        '<option value="passed">Passed</option>'
        '<option value="failed">Failed</option>'
        '<option value="skipped" selected>Skipped</option>'
        "</select>"
    )


def _manual_case_card(case):
    case_id = case["id"]
    safe_id = html.escape(case_id, quote=True)
    title = html.escape(case["title"])
    search_value = html.escape(
        f"{case_id} {case['test_id']} {case['title']} {case['section']}".casefold(),
        quote=True,
    )
    context = " · ".join(
        html.escape(value)
        for value in (case["section"], case["priority"], case["type"])
    )
    return (
        f'<details class="case manual-case skipped selectable" data-id="{safe_id}" '
        'data-manual="true" data-original-status="skipped" '
        f'data-current-status="skipped" data-status="skipped" '
        f'data-search="{search_value}">'
        f'<summary>{_case_pick(case_id)}'
        '<span class="status-mark" aria-hidden="true"></span>'
        f'<span class="case-id">{html.escape(case_id)}</span>'
        f'<span class="title">{title}</span>'
        f'{_manual_status_control(case_id)}</summary>'
        f'<div class="detail"><div class="evidence">{context}</div>'
        '<p class="note">Manual-only coverage. Set the result after verifying '
        "this case on the device.</p></div></details>"
    )


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
    if status in ("failed", "skipped"):
        detail.append(
            '<p class="note review-note" hidden>'
            "Marked Passed Manually after review.</p>"
        )

    opened = " open" if (open_failed and status == "failed") else ""
    css_class = "passed passed_manually" if status == "passed_manually" else status
    selectable = status in ("failed", "skipped")
    if selectable:
        css_class += " selectable"
    filter_status = "passed" if status == "passed_manually" else status
    search_value = html.escape(
        f"{case_id} {case['title']}".casefold(), quote=True
    )
    parent_line = html.escape(parent)
    if check.get("label"):
        parent_line += f' · {html.escape(check["label"])}'
    safe_id = html.escape(case_id, quote=True)
    pick = _case_pick(case_id) if selectable else ""
    return (
        f'<details class="case {css_class}" data-id="{safe_id}" '
        f'data-original-status="{status}" data-current-status="{status}" '
        f'data-status="{filter_status}" data-search="{search_value}"{opened}>'
        f'<summary>{pick}<span class="status-mark" aria-hidden="true"></span>'
        f'<span class="case-id">{html.escape(case_id)}</span>'
        f'<span class="title">{title}</span>'
        f'{_status_control(case_id, status)}'
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
<div class="donut" id="donut" style="background:{gradient}">
<div class="donut-hole"><div class="donut-pct" id="donut-pct">{center}</div>
<div class="donut-lbl">pass rate</div></div></div>
<div class="score-copy"><strong id="score-headline">{headline}</strong>
<span id="score-note">{note}<br>
{counts["passed"]}/{executed or 0} executed cases passed.</span></div>
</div>"""


def _manual_donut(total):
    return f"""<div class="hero-stat">
<div class="donut" id="manual-donut"
style="background:conic-gradient(#d2a438 0 100%)">
<div class="donut-hole"><div class="donut-pct" id="manual-donut-value">0/{total}</div>
<div class="donut-lbl">reviewed</div></div></div>
<div class="score-copy"><strong id="manual-score-headline">Awaiting manual review</strong>
<span id="manual-score-note">0 completed · {total} awaiting review.</span></div>
</div>"""


def _verification_stat(kind, label, value, element_id=None):
    identifier = f' id="{html.escape(element_id)}"' if element_id else ""
    return (
        f'<div class="verification-stat {html.escape(kind)}">'
        f'<span class="k">{html.escape(label)}</span>'
        f'<strong class="v"{identifier}>{value}</strong></div>'
    )


def _metric(kind, label, value, note):
    return f"""<article class="metric {kind}">
<div class="metric-head"><span class="metric-dot"></span>{html.escape(label)}</div>
<strong class="metric-value" id="metric-{html.escape(kind)}">{value}</strong>
<span class="metric-note">{html.escape(note)}</span>
</article>"""


def _release_banner():
    """Emit the banner hidden; live automated/manual scores decide visibility."""
    return """<section class="release-banner" id="release-banner"
aria-label="Release readiness" hidden>
<div class="release-icon" aria-hidden="true">✓</div>
<div class="release-copy">
<strong>The build passed smoke, sanity and full regression testing, with
stability confirmed and no blocking issues identified.</strong>
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
  var attention = document.getElementById("attention");
  var releaseBanner = document.getElementById("release-banner");
  var runState = document.getElementById("run-state");
  var overrideNode = document.getElementById("status-overrides");
  var fileHandle = null;
  var mode = "all";

  function storageKey() {
    return "spider-regression-status:" + (document.body.dataset.runId || "default");
  }

  function countKey(status) {
    return status === "passed_manually" ? "passed" : status;
  }

  function filterStatus(status) {
    return status === "passed_manually" ? "passed" : status;
  }

  function cardStatus(card) {
    return card.dataset.currentStatus || "passed";
  }

  function applyStatus(card, status) {
    card.dataset.currentStatus = status;
    card.dataset.status = filterStatus(status);
    card.classList.remove("passed", "failed", "skipped", "passed_manually");
    if (status === "passed_manually") {
      card.classList.add("passed", "passed_manually");
    } else {
      card.classList.add(status);
    }
    var select = card.querySelector(".status-edit");
    if (select) {
      select.value = status;
      Array.from(select.options).forEach(function (opt) {
        if (opt.value === status) opt.setAttribute("selected", "selected");
        else opt.removeAttribute("selected");
      });
    }
    var note = card.querySelector(".review-note");
    if (note) {
      note.hidden = !(status === "passed_manually" &&
        card.dataset.originalStatus !== "passed_manually");
    }
  }

  function selectableCards() {
    return Array.from(document.querySelectorAll(
      ".group > .case.selectable, .manual-case"
    ));
  }

  function visibleSelectableCards() {
    return selectableCards().filter(function (card) { return !card.hidden; });
  }

  function selectedCards() {
    return visibleSelectableCards().filter(function (card) {
      var box = card.querySelector(".case-check");
      return box && box.checked;
    });
  }

  function setCardSelected(card, on) {
    var box = card.querySelector(".case-check");
    if (box) box.checked = !!on;
    card.classList.toggle("selected", !!on);
  }

  function syncBulkBar() {
    var selected = selectedCards();
    var visible = visibleSelectableCards();
    var master = document.getElementById("bulk-select-visible");
    var count = document.getElementById("bulk-count");
    var applyBtn = document.getElementById("bulk-apply");
    if (count) count.textContent = selected.length + " selected";
    if (applyBtn) applyBtn.disabled = selected.length === 0;
    if (master) {
      master.checked = visible.length > 0 && selected.length === visible.length;
      master.indeterminate = selected.length > 0 &&
        selected.length < visible.length;
    }
    selectableCards().forEach(function (card) {
      var box = card.querySelector(".case-check");
      card.classList.toggle("selected", !!(box && box.checked && !card.hidden));
    });
  }

  function mappedStatus(card, status) {
    if (status === "passed" && card.getAttribute("data-manual") !== "true") {
      return "passed_manually";
    }
    return status;
  }

  function canApply(card, status) {
    var select = card.querySelector(".status-edit");
    if (!select) return false;
    var next = mappedStatus(card, status);
    return Array.from(select.options).some(function (opt) {
      return opt.value === next;
    });
  }

  function applyBulk() {
    var statusInput = document.getElementById("bulk-status");
    if (!statusInput) return;
    var status = statusInput.value;
    var applied = {};
    selectedCards().forEach(function (card) {
      var id = card.dataset.id;
      if (!id || applied[id] || !canApply(card, status)) return;
      applied[id] = true;
      var next = mappedStatus(card, status);
      document.querySelectorAll('.case[data-id="' + id + '"]').forEach(
        function (clone) { applyStatus(clone, next); }
      );
    });
    recompute();
    persistOverrides();
    if (fileHandle) {
      writeReportFile(reportHtml()).catch(function () { fileHandle = null; });
    }
  }

  function countsFromCards() {
    var counts = {passed: 0, failed: 0, skipped: 0};
    document.querySelectorAll(".group > .case").forEach(function (card) {
      counts[countKey(cardStatus(card))] += 1;
    });
    return counts;
  }

  function countsFromAllCases() {
    var counts = {passed: 0, failed: 0, skipped: 0};
    document.querySelectorAll(".group > .case, .manual-case").forEach(
      function (card) {
        counts[countKey(cardStatus(card))] += 1;
      }
    );
    return counts;
  }

  function manualStatusGradient(counts) {
    var total = Math.max(counts.passed + counts.failed + counts.skipped, 1);
    var passPct = 100 * counts.passed / total;
    var failPct = 100 * counts.failed / total;
    var failEnd = passPct + failPct;
    return "conic-gradient(#16835f 0 " + passPct.toFixed(2) + "%, #c23d4a " +
      passPct.toFixed(2) + "% " + failEnd.toFixed(2) + "%, #d2a438 " +
      failEnd.toFixed(2) + "% 100%)";
  }

  function recomputeManual(automatedCounts) {
    var counts = {passed: 0, failed: 0, skipped: 0};
    var cards = document.querySelectorAll(".manual-case");
    cards.forEach(function (card) {
      counts[countKey(cardStatus(card))] += 1;
    });
    var values = {
      total: cards.length,
      passed: counts.passed,
      failed: counts.failed,
      skipped: counts.skipped
    };
    Object.keys(values).forEach(function (key) {
      ["manual-" + key, "manual-top-" + key].forEach(function (id) {
        var node = document.getElementById(id);
        if (node) node.textContent = values[key];
      });
    });
    var reviewed = counts.passed + counts.failed;
    document.getElementById("manual-donut").style.background =
      manualStatusGradient(counts);
    document.getElementById("manual-donut-value").textContent =
      reviewed + "/" + cards.length;
    var headline = counts.failed
      ? "Manual failures need review"
      : (!reviewed
        ? "Awaiting manual review"
        : (counts.skipped ? "Manual review in progress" : "Manual review complete"));
    document.getElementById("manual-score-headline").textContent = headline;
    document.getElementById("manual-score-note").textContent =
      counts.passed + " passed · " + counts.failed + " failed · " +
      counts.skipped + " skipped.";
    var automatedTotal = automatedCounts.passed + automatedCounts.failed +
      automatedCounts.skipped;
    var combinedTotal = automatedTotal + cards.length;
    document.getElementById("coverage-summary").textContent =
      combinedTotal + " total cases · " + automatedTotal + " automated · " +
      cards.length + " manual · " + counts.skipped +
      " awaiting manual review";
    return cards.length ? (100 * reviewed / cards.length) : 0;
  }

  function donutGradient(counts, executed) {
    var total = Math.max(counts.passed + counts.failed + counts.skipped, 1);
    var passPct = 100 * counts.passed / total;
    var failPct = 100 * counts.failed / total;
    var failEnd = passPct + failPct;
    if (!executed) return "conic-gradient(#dfe5ee 0 100%)";
    return "conic-gradient(#16835f 0 " + passPct.toFixed(2) + "%, #c23d4a " +
      passPct.toFixed(2) + "% " + failEnd.toFixed(2) + "%, #d2a438 " +
      failEnd.toFixed(2) + "% 100%)";
  }

  function recompute() {
    var counts = countsFromCards();
    var allCounts = countsFromAllCases();
    var executed = counts.passed + counts.failed;
    var exactRate = executed ? (100 * counts.passed / executed) : 0;
    var rate = Math.round(exactRate);
    var manualRate = recomputeManual(counts);
    var averageRate = (exactRate + manualRate) / 2;
    var headline, note, stateClass, stateLabel;
    if (counts.failed) {
      headline = "Review required";
      note = counts.failed + " case" + (counts.failed === 1 ? "" : "s") +
        " need attention.";
      stateClass = "failed";
      stateLabel = "Attention required";
    } else if (executed) {
      headline = "Run is healthy";
      note = "All executed cases passed.";
      stateClass = "passed";
      stateLabel = "Run complete";
    } else {
      headline = "Awaiting results";
      note = "Run the suite to populate this report.";
      stateClass = "pending";
      stateLabel = "Awaiting results";
    }
    document.getElementById("donut").style.background =
      donutGradient(counts, executed);
    document.getElementById("donut-pct").textContent =
      executed ? rate + "%" : "—";
    document.getElementById("score-headline").textContent = headline;
    document.getElementById("score-note").innerHTML = note + "<br>" +
      counts.passed + "/" + (executed || 0) + " executed cases passed.";
    document.getElementById("metric-passed").textContent = counts.passed;
    document.getElementById("metric-failed").textContent = counts.failed;
    document.getElementById("metric-skipped").textContent = counts.skipped;
    runState.className = "run-state " + stateClass;
    runState.textContent = stateLabel;
    if (releaseBanner) {
      releaseBanner.hidden = !(executed && averageRate > 92);
    }
    buttons.forEach(function (button) {
      var key = button.getAttribute("data-filter");
      var n = key === "all"
        ? allCounts.passed + allCounts.failed + allCounts.skipped
        : allCounts[key];
      button.querySelector("b").textContent = n;
    });
    groups.forEach(function (group) {
      var passed = 0;
      var total = 0;
      group.querySelectorAll(":scope > .case").forEach(function (card) {
        total += 1;
        var status = cardStatus(card);
        if (status === "passed" || status === "passed_manually") passed += 1;
      });
      var stat = group.querySelector(".secstat");
      var fill = group.querySelector(".section-fill");
      if (stat) stat.textContent = passed + "/" + total + " passed";
      if (fill) fill.style.width = (total ? (100 * passed / total) : 0) + "%";
    });
    if (attention) {
      var failedLeft = 0;
      attention.querySelectorAll(":scope > .case").forEach(function (card) {
        if (cardStatus(card) === "failed") failedLeft += 1;
      });
      var lead = attention.querySelector(".lead");
      var countEl = attention.querySelector(".attention-count");
      if (lead) {
        lead.textContent = failedLeft + " failed case" +
          (failedLeft === 1 ? "" : "s") + " from this run";
      }
      if (countEl) countEl.textContent = failedLeft;
    }
    apply();
  }

  function collectOverrides() {
    var overrides = {};
    document.querySelectorAll(".case[data-id]").forEach(function (card) {
      var current = cardStatus(card);
      if (current !== card.dataset.originalStatus) {
        overrides[card.dataset.id] = current;
      }
    });
    return overrides;
  }

  function persistOverrides() {
    var json = JSON.stringify(collectOverrides());
    if (overrideNode) overrideNode.textContent = json;
    try { localStorage.setItem(storageKey(), json); } catch (err) {}
    return json;
  }

  function readOverrides() {
    var fromFile = {};
    var fromStore = {};
    try {
      fromFile = JSON.parse((overrideNode && overrideNode.textContent) || "{}") || {};
    } catch (err) {}
    try {
      fromStore = JSON.parse(localStorage.getItem(storageKey()) || "{}") || {};
    } catch (err) {}
    var merged = {};
    Object.keys(fromFile).forEach(function (id) { merged[id] = fromFile[id]; });
    Object.keys(fromStore).forEach(function (id) { merged[id] = fromStore[id]; });
    return merged;
  }

  function restoreOverrides() {
    var overrides = readOverrides();
    Object.keys(overrides).forEach(function (id) {
      document.querySelectorAll('.case[data-id="' + id + '"]').forEach(
        function (card) { applyStatus(card, overrides[id]); }
      );
    });
  }

  function reportHtml() {
    persistOverrides();
    return "<!doctype html>\\n" + document.documentElement.outerHTML;
  }

  function downloadReport(html) {
    var blob = new Blob([html], {type: "text/html;charset=utf-8"});
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "spider_regression.html";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(function () { URL.revokeObjectURL(link.href); }, 1000);
  }

  async function writeReportFile(html) {
    if (fileHandle) {
      var writable = await fileHandle.createWritable();
      await writable.write(html);
      await writable.close();
      return true;
    }
    if (!window.showSaveFilePicker) return false;
    fileHandle = await window.showSaveFilePicker({
      suggestedName: "spider_regression.html",
      types: [{description: "HTML report", accept: {"text/html": [".html"]}}]
    });
    var stream = await fileHandle.createWritable();
    await stream.write(html);
    await stream.close();
    return true;
  }

  async function saveReport() {
    var html = reportHtml();
    try {
      if (await writeReportFile(html)) return;
    } catch (err) {
      if (err && err.name === "AbortError") return;
      fileHandle = null;
    }
    downloadReport(html);
  }

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
    var manual = document.getElementById("manual-verification");
    if (manual) {
      var manualVisible = 0;
      manual.querySelectorAll(".manual-case").forEach(function (card) {
        var statusMatch = mode === "all" || card.dataset.status === mode;
        var searchMatch = !query || card.dataset.search.indexOf(query) !== -1;
        card.hidden = !(statusMatch && searchMatch);
        if (!card.hidden) {
          manualVisible += 1;
          visible += 1;
        }
      });
      manual.querySelectorAll(".manual-category").forEach(function (heading) {
        var categoryVisible = 0;
        var sibling = heading.nextElementSibling;
        while (sibling && !sibling.classList.contains("manual-category")) {
          if (sibling.classList.contains("manual-case") && !sibling.hidden) {
            categoryVisible += 1;
          }
          sibling = sibling.nextElementSibling;
        }
        heading.hidden = categoryVisible === 0;
      });
      manual.hidden = manualVisible === 0;
      var manualLink = document.querySelector(
        '.section-link[data-target="manual-verification"]'
      );
      if (manualLink) manualLink.hidden = manual.hidden;
    }
    if (attention) {
      var failedLeft = 0;
      attention.querySelectorAll(":scope > .case").forEach(function (card) {
        var show = cardStatus(card) === "failed";
        card.hidden = !show;
        if (show) failedLeft += 1;
      });
      attention.hidden = failedLeft === 0 || mode !== "all" || query !== "";
    }
    visibleCount.textContent = visible + " of " +
      document.querySelectorAll(".group > .case, .manual-case").length + " shown";
    emptyState.hidden = visible !== 0;
    selectableCards().forEach(function (card) {
      if (card.hidden) setCardSelected(card, false);
    });
    syncBulkBar();
  }

  function stopToggle(event) {
    event.stopPropagation();
  }

  document.querySelectorAll(".status-edit").forEach(function (select) {
    ["click", "mousedown", "pointerdown", "keydown"].forEach(function (type) {
      select.addEventListener(type, stopToggle);
    });
    select.addEventListener("change", function () {
      var card = select.closest(".case");
      var status = select.value;
      var id = card.dataset.id;
      document.querySelectorAll('.case[data-id="' + id + '"]').forEach(
        function (clone) { applyStatus(clone, status); }
      );
      recompute();
      persistOverrides();
      if (fileHandle) {
        writeReportFile(reportHtml()).catch(function () { fileHandle = null; });
      }
    });
  });

  document.querySelectorAll(".case-pick, .case-check").forEach(function (node) {
    ["click", "mousedown", "pointerdown", "keydown"].forEach(function (type) {
      node.addEventListener(type, stopToggle);
    });
  });
  document.querySelectorAll(".case-check").forEach(function (box) {
    box.addEventListener("change", function (event) {
      event.stopPropagation();
      var card = box.closest(".case");
      if (card) card.classList.toggle("selected", box.checked);
      syncBulkBar();
    });
  });
  var master = document.getElementById("bulk-select-visible");
  if (master) {
    master.addEventListener("change", function () {
      var on = master.checked;
      visibleSelectableCards().forEach(function (card) {
        setCardSelected(card, on);
      });
      syncBulkBar();
    });
  }
  var bulkApply = document.getElementById("bulk-apply");
  if (bulkApply) bulkApply.addEventListener("click", applyBulk);

  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      mode = button.getAttribute("data-filter");
      apply();
    });
  });
  search.addEventListener("input", apply);
  document.getElementById("expand-visible").addEventListener("click", function () {
    document.querySelectorAll(
      ".group > .case:not([hidden]), .manual-case:not([hidden])"
    ).forEach(function (card) { card.open = true; });
  });
  document.getElementById("collapse-all").addEventListener("click", function () {
    document.querySelectorAll("details.case").forEach(function (card) {
      card.open = false;
    });
  });
  var saveButton = document.getElementById("save-report");
  if (saveButton) saveButton.addEventListener("click", function () { saveReport(); });
  restoreOverrides();
  recompute();
})();
"""


def _filters(counts, manual_total=0):
    """All / Passed / Failed / Skipped chips for the case list."""
    combined = dict(counts)
    combined["skipped"] += manual_total
    total = sum(combined.values())
    chips = [
        ("all", "All", total),
        ("passed", "Passed", combined["passed"]),
        ("failed", "Failed", combined["failed"]),
        ("skipped", "Skipped", combined["skipped"]),
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


def build(results_path=None, out_path=None, manual_cases_path=None):
    """Generate the report and return its output path."""
    cases, mapped = _validate_catalog()
    results_path = results_path or os.path.join(config.LOG, "run_results.json")
    out_path = out_path or os.path.join(config.LOG, "spider_regression.html")
    manual_cases_path = manual_cases_path or MANUAL_CASES_CSV
    manual_cases = _load_manual_cases(manual_cases_path)
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
            '<section class="attention" id="attention">'
            '<div class="attention-head"><div>'
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
    manual_body = [
        '<section class="manual-verification" id="manual-verification">',
        '<div class="manual-head"><div><h2>Manually verified</h2>'
        '<p>Cases outside the automation suite. They begin as Skipped; set each '
        "result after checking it on the device. These results are reported "
        "separately and do not change automated release readiness.</p></div></div>",
        '<div class="manual-stats" aria-label="Manual verification summary">',
        f'<div class="manual-stat"><span class="k">Total cases</span>'
        f'<strong class="v" id="manual-total">{len(manual_cases)}</strong></div>',
        '<div class="manual-stat"><span class="k">Passed</span>'
        '<strong class="v" id="manual-passed">0</strong></div>',
        '<div class="manual-stat"><span class="k">Failed</span>'
        '<strong class="v" id="manual-failed">0</strong></div>',
        '<div class="manual-stat"><span class="k">Skipped</span>'
        f'<strong class="v" id="manual-skipped">{len(manual_cases)}</strong></div>',
        "</div>",
    ]
    current_manual_section = None
    for case in manual_cases:
        if case["section"] != current_manual_section:
            current_manual_section = case["section"]
            manual_body.append(
                f'<h3 class="manual-category">{html.escape(current_manual_section)}</h3>'
            )
        manual_body.append(_manual_case_card(case))
    manual_body.append("</section>")

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
<style>{CSS}</style></head>
<body data-run-id="{html.escape(str(payload.get("finished") or payload.get("started") or "none"), quote=True)}">
<div class="wrap">
<div class="hero">
<div class="hero-copy"><div class="eyebrow"><span class="eyebrow-dot"></span>
Quality assurance report</div>
<div class="brand">{header_mark}<div><h1>Spider Solitaire</h1>
<div class="sub">Unity functional regression · {html.escape(run_time)}</div></div></div>
</div>
<div class="run-state {run_state_class}" id="run-state">{run_state_label}</div>
</div>
<section class="coverage-strip" aria-label="Verification coverage">
<strong>Verification coverage</strong>
<span id="coverage-summary">{sum(counts.values()) + len(manual_cases)} total cases ·
{sum(counts.values())} automated · {len(manual_cases)} manual ·
{len(manual_cases)} awaiting manual review</span>
</section>
<section class="verification-grid" aria-label="Run summary">
<article class="score-card verification-card">
<div class="panel-label">Automated verification</div>
{_donut(counts, executed, rate)}
<div class="verification-stats">
{_verification_stat("total", "Total", sum(counts.values()), "metric-total")}
{_verification_stat("passed", "Passed", counts["passed"], "metric-passed")}
{_verification_stat("failed", "Failed", counts["failed"], "metric-failed")}
{_verification_stat("skipped", "Skipped", counts["skipped"], "metric-skipped")}
</div></article>
<article class="score-card verification-card">
<div class="panel-label">Manual verification</div>
{_manual_donut(len(manual_cases))}
<div class="verification-stats">
{_verification_stat("total", "Total", len(manual_cases), "manual-top-total")}
{_verification_stat("passed", "Passed", 0, "manual-top-passed")}
{_verification_stat("failed", "Failed", 0, "manual-top-failed")}
{_verification_stat("skipped", "Skipped", len(manual_cases), "manual-top-skipped")}
</div></article>
</section>
{_release_banner()}
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
<span id="visible-count">{sum(counts.values()) + len(manual_cases)} of {sum(counts.values()) + len(manual_cases)} shown</span></div>
<div class="toolbar-controls">
<label class="case-search"><span class="sr-only">Search test cases</span>
<input id="case-search" type="search" placeholder="Search ID or case title"
autocomplete="off"></label>
{_filters(counts, len(manual_cases))}
<div class="tool-buttons">
<button class="tool-button" id="save-report" type="button">Save report</button>
<button class="tool-button" id="expand-visible" type="button">Expand visible</button>
<button class="tool-button" id="collapse-all" type="button">Collapse all</button>
</div>
</div></div>
<div class="bulk-bar" id="bulk-bar">
<label class="bulk-select-all"><input type="checkbox" id="bulk-select-visible">
<span>Select visible</span></label>
<span class="bulk-count" id="bulk-count">0 selected</span>
<label class="bulk-apply-label" for="bulk-status">Set status</label>
<select id="bulk-status" aria-label="Status to apply to selected cases">
<option value="passed">Passed</option>
<option value="failed">Failed</option>
<option value="skipped">Skipped</option>
</select>
<button class="tool-button" id="bulk-apply" type="button" disabled>Apply</button>
</div>
<nav class="section-nav" aria-label="Report sections">{"".join(section_links)}
<a class="section-link" href="#manual-verification"
data-target="manual-verification">Manually verified</a></nav>
</div>
<section class="empty-state" id="empty-state" hidden>
<strong>No matching test cases</strong>
<span>Try a different search term or status filter.</span>
</section>
{"".join(body)}
{"".join(manual_body)}
<footer>Generated by scripts/gen_regression_report.py · test screenshots remain
available separately in log/ and are not embedded here.</footer>
</div><script type="application/json" id="status-overrides">{{}}</script>
<script>{FILTER_JS}</script></body></html>
"""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(document)
    return out_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", default=os.path.join(config.LOG, "run_results.json"))
    parser.add_argument("--out", default=os.path.join(config.LOG, "spider_regression.html"))
    parser.add_argument("--manual-cases", default=MANUAL_CASES_CSV)
    args = parser.parse_args(argv)
    print(f"wrote {build(args.results, args.out, args.manual_cases)}")


if __name__ == "__main__":
    main()
