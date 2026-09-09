#!/usr/bin/env python3
"""Emit TestRail + Google-Sheets files from the curated case list.

Writes three files under docs/testrail/:

* spider_unity_testrail.csv — multi-row TestRail Steps import
* spider_unity_cases.csv    — one row per case (browse / Google Sheets)
* spider_unity_cases.xlsx   — same two tabs, for File → Import in Sheets

    ./.venv/bin/python scripts/export_testrail_csv.py
"""
import csv
import os
import sys
import zipfile
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "docs", "testrail"))

from cases import CASES, validate  # noqa: E402

DIR = os.path.join(ROOT, "docs", "testrail")
OUT_STEPS = os.path.join(DIR, "spider_unity_testrail.csv")
OUT_CASES = os.path.join(DIR, "spider_unity_cases.csv")
OUT_XLSX = os.path.join(DIR, "spider_unity_cases.xlsx")

STEP_FIELDS = (
    "Case ID",
    "Title",
    "Section Hierarchy",
    "Type",
    "Priority",
    "Step",
    "Expected Result",
    "Automation",
)

CASE_FIELDS = (
    "Case ID",
    "Title",
    "Section Hierarchy",
    "Type",
    "Priority",
    "Steps",
    "Expected Result",
    "Automation",
)


def numbered(items):
    return "\n".join(f"{i}. {text}" for i, text in enumerate(items, 1))


def step_rows(cases=CASES):
    """One CSV row per step. Metadata repeats so TestRail groups by Title."""
    for case in cases:
        for action, expected in case["steps"]:
            yield {
                "Case ID": case["id"],
                "Title": case["title"],
                "Section Hierarchy": case["section"],
                "Type": case["type"],
                "Priority": case["priority"],
                "Step": action,
                "Expected Result": expected,
                "Automation": "Manual",
            }


def case_rows(cases=CASES):
    """One row per case — the view people actually browse in a spreadsheet."""
    for case in cases:
        yield {
            "Case ID": case["id"],
            "Title": case["title"],
            "Section Hierarchy": case["section"],
            "Type": case["type"],
            "Priority": case["priority"],
            "Steps": numbered(action for action, _ in case["steps"]),
            "Expected Result": numbered(expected for _, expected in case["steps"]),
            "Automation": "Manual",
        }


def write_csv(path, fields, records):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        n = 0
        for row in records:
            writer.writerow(row)
            n += 1
    return n


def _cell(value):
    text = escape(str(value), {"'": "&apos;", '"': "&quot;"})
    return f'<c t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def _sheet_xml(fields, records):
    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        "<sheetData>",
        "<row>" + "".join(_cell(h) for h in fields) + "</row>",
    ]
    for record in records:
        lines.append("<row>" + "".join(_cell(record[h]) for h in fields) + "</row>")
    lines.extend(["</sheetData>", "</worksheet>"])
    return "\n".join(lines)


def write_xlsx(path, sheets):
    """Minimal xlsx (stdlib only) so Google Sheets can File → Import it."""
    ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    workbook_sheets = []
    overrides = []
    rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            f'<Relationships xmlns="{ns}">']
    for i, (name, fields, records) in enumerate(sheets, 1):
        workbook_sheets.append(
            f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>'
        )
        overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument'
            '.spreadsheetml.worksheet+xml"/>'
        )
        rels.append(
            f'<Relationship Id="rId{i}" '
            f'Type="{ns}/worksheet" Target="worksheets/sheet{i}.xml"/>'
        )
    rels.append("</Relationships>")

    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument'
        '.spreadsheetml.sheet.main+xml"/>',
        *overrides,
        "</Types>",
    ]
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{ns}/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'xmlns:r="{ns}"><sheets>'
        + "".join(workbook_sheets)
        + "</sheets></workbook>"
    )

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "\n".join(content_types))
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", "\n".join(rels))
        for i, (_, fields, records) in enumerate(sheets, 1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", _sheet_xml(fields, records))


def main():
    n = validate(CASES)
    os.makedirs(DIR, exist_ok=True)
    steps = list(step_rows())
    cases = list(case_rows())
    n_steps = write_csv(OUT_STEPS, STEP_FIELDS, steps)
    n_cases = write_csv(OUT_CASES, CASE_FIELDS, cases)
    write_xlsx(OUT_XLSX, (
        ("Cases", CASE_FIELDS, cases),
        ("TestRail steps", STEP_FIELDS, steps),
    ))
    print(f"wrote {n_steps} step rows for {n} cases → {OUT_STEPS}")
    print(f"wrote {n_cases} case rows → {OUT_CASES}")
    print(f"wrote xlsx (Cases + TestRail steps) → {OUT_XLSX}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
