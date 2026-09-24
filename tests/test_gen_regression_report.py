import csv
import json
import os
import tempfile
import unittest

from scripts import gen_regression_report as report


class ManualRegressionReportTests(unittest.TestCase):
    def test_manual_cases_render_separately_and_start_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = os.path.join(tmp, "results.json")
            output = os.path.join(tmp, "report.html")
            with open(results, "w", encoding="utf-8") as fh:
                json.dump({"tests": []}, fh)

            report.build(results, output)

            with open(output, encoding="utf-8") as fh:
                document = fh.read()
            self.assertEqual(
                document.count('class="case manual-case skipped selectable"'), 46
            )
            self.assertIn('id="manual-total">46<', document)
            self.assertIn('id="manual-passed">0<', document)
            self.assertIn('id="manual-failed">0<', document)
            self.assertIn('id="manual-skipped">46<', document)
            self.assertIn('data-id="C126829"', document)
            self.assertIn('data-id="C126856"', document)
            self.assertIn('data-id="C128602"', document)
            self.assertIn('data-id="C128612"', document)
            self.assertIn(">Localization<", document)
            self.assertIn("do not change automated release readiness", document)
            self.assertIn("146 of 146 shown", document)
            self.assertIn("Automated verification", document)
            self.assertIn("Manual verification", document)
            self.assertIn('id="manual-donut-value">0/46<', document)
            self.assertIn(
                'id="coverage-summary">146 total cases ·\n'
                "100 automated · 46 manual ·\n"
                "46 awaiting manual review",
                document,
            )
            self.assertIn('data-filter="all" aria-pressed="true">All <b>146</b>', document)
            self.assertIn(
                'data-filter="skipped" aria-pressed="false">Skipped <b>146</b>',
                document,
            )
            self.assertIn("averageRate > 92", document)
            self.assertIn('id="release-banner"', document)
            self.assertNotIn("Average verification", document)
            self.assertNotIn("Build is approved for release", document)
            self.assertIn('id="bulk-bar"', document)
            self.assertIn('id="bulk-select-visible"', document)
            self.assertIn('id="bulk-status"', document)
            self.assertIn('id="bulk-apply"', document)
            self.assertEqual(document.count('class="case-check"'), 146)

    def test_manual_csv_rejects_duplicate_case_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "manual.csv")
            fieldnames = ["ID", "Title", "Case ID", "Priority", "Section", "Type"]
            with open(path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                row = {
                    "ID": "T1",
                    "Title": "Manual case",
                    "Case ID": "C1",
                    "Priority": "High",
                    "Section": "Manual",
                    "Type": "Functional",
                }
                writer.writerow(row)
                writer.writerow(row)

            with self.assertRaisesRegex(ValueError, "duplicate Case ID C1"):
                report._load_manual_cases(path)


if __name__ == "__main__":
    unittest.main()
