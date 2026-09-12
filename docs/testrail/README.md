# Manual TestRail cases — Unity build

Cases a **person** can run on the phone. One case per behaviour, written as
Tap / Wait / Check. The Automation column is Manual even where an automated
test covers the same behaviour.

**101 cases.** Back-to-menu and Opens-from-menu cases are included.
“The link is there” / harness-cleanup cases stay out.

| File | Role |
|---|---|
| [`cases.py`](cases.py) | Source of truth — edit this |
| [`spider_unity_testrail.csv`](spider_unity_testrail.csv) | TestRail import (one row per step) |
| [`spider_unity_cases.csv`](spider_unity_cases.csv) | One row per case — browse or import into Google Sheets |
| [`spider_unity_cases.xlsx`](spider_unity_cases.xlsx) | Same data, two tabs (`Cases` + `TestRail steps`) |
| [`../../scripts/export_testrail_csv.py`](../../scripts/export_testrail_csv.py) | Regenerates the CSV / xlsx |

```bash
./.venv/bin/python scripts/export_testrail_csv.py
```

Pixel-compare tools (`compare_unity*`) and harness smokes (`connect_check`,
`launch_and_shoot`, `preflight_offline`) are not in this list.

## Open in Google Sheets

This repo cannot host a `docs.google.com` link — that lives in *your* Drive.
Import once, then copy the Share URL.

1. Open [https://sheets.google.com](https://sheets.google.com) and sign in.
2. **File → Import → Upload** and choose
   [`spider_unity_cases.xlsx`](spider_unity_cases.xlsx)
   (or the one-row [`spider_unity_cases.csv`](spider_unity_cases.csv) if you
   only want the browseable tab).
3. Import location: **Create new spreadsheet**. Separator: **comma** (CSV only).
4. **Share → Anyone with the link → Viewer** (or Editor).
5. Copy the URL. It looks like
   `https://docs.google.com/spreadsheets/d/<id>/edit`.

The `Cases` tab is one row per test case (numbered Steps / Expected Result in
a single cell). The `TestRail steps` tab is the multi-row file TestRail wants.

## Import into TestRail

1. Open the project → **Test Cases** → **Import** → **Import from CSV**.
2. Upload `spider_unity_testrail.csv`.
3. Encoding **UTF-8**, delimiter **comma**, start row **1**, header row **on**.
4. Template: **Test Case (Steps)**.
5. Row layout: **Test cases use multiple rows**.
6. Column that detects a new case: **Title**.
7. Leave **Ignore rows without a title** on — every step row repeats Title, so
   continuation steps are not dropped.

Map the columns:

| CSV column | TestRail field |
|---|---|
| Title | Title |
| Section Hierarchy | Section Hierarchy |
| Type | Type |
| Priority | Priority |
| Step | Steps (Step) |
| Expected Result | Steps (Expected Result) |
| Case ID | custom field, or skip |
| Automation | custom field, or skip |

`Section Hierarchy` uses `>` (`Spider Solitaire Unity > Gameplay`). TestRail
creates those folders on import.

The export omits **Preconditions**, **References**, **Network**, and **Suite**.
**Automation** is Manual on every row.

## How the list is split

A case is something a tester can fail on its own. Back-to-menu and
Opens-from-menu are separate cases. “The button is there” is not.
