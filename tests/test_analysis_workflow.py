"""Focused checks for the deterministic workflow and report exports."""

from __future__ import annotations

import unittest
from io import BytesIO

import pandas as pd

from data.analyzer import DataAnalyzer
from data.loader import DataLoader
from data.profiler import DataProfiler
from data.validator import DataValidator
from models.schemas import AIAnalysisResult, parse_model_json
from reports.excel_generator import generate_excel_report
from reports.pdf_generator import generate_pdf_report
from reports.word_generator import generate_word_report


class AnalysisWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.DataFrame({
            "Date": pd.to_datetime(["2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01"]),
            "Department": ["A", "A", "B", "B"],
            "Revenue": [10.0, 20.0, 30.0, 1000.0],
            "Units": [1, 2, 3, 4],
        })

    def test_excel_load_lists_and_reads_all_sheets(self) -> None:
        source = BytesIO()
        with pd.ExcelWriter(source, engine="openpyxl") as writer:
            self.frame.to_excel(writer, sheet_name="Sales", index=False)
            self.frame.head(2).to_excel(writer, sheet_name="Summary", index=False)
        payload = source.getvalue()
        loader = DataLoader()
        self.assertEqual(loader.get_sheets(payload, "report.xlsx"), ["Sales", "Summary"])
        loaded = loader.load_sheet(payload, "Summary", "report.xlsx")
        self.assertEqual(len(loaded), 2)

    def test_csv_loader_handles_utf8_bom_and_values(self) -> None:
        loaded = DataLoader().load_csv("name,value\nөгөгдөл,12\n".encode("utf-8-sig"), "report.csv")
        self.assertEqual(loaded.loc[0, "name"], "өгөгдөл")
        self.assertEqual(loaded.loc[0, "value"], 12)

    def test_validation_and_profiling_do_not_mutate_dataframe(self) -> None:
        frame = self.frame.copy(deep=True)
        original = frame.copy(deep=True)
        validation = DataValidator().validate(frame)
        profile = DataProfiler().profile(frame)
        self.assertTrue(validation["is_valid"])
        self.assertEqual(profile["numeric_columns"], ["Revenue", "Units"])
        pd.testing.assert_frame_equal(frame, original)

    def test_validation_reports_quality_issues_without_cleaning(self) -> None:
        frame = pd.DataFrame({
            "Amount": ["100", "200", "300", "400", "invalid", None, None],
            "Date": ["2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01", "not-a-date", None, None],
            "Empty": [None, None, None, None, None, None, None],
            "Record": range(7),
        })
        frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
        original = frame.copy(deep=True)
        result = DataValidator().validate(frame)
        self.assertTrue(result["missing_values"])
        self.assertEqual(result["duplicate_rows"], 1)
        self.assertIn("Amount", result["numeric_strings"])
        self.assertIn("Empty", result["empty_columns"])
        self.assertIn("Date", result["invalid_dates"])
        pd.testing.assert_frame_equal(frame, original)

    def test_invalid_excel_is_reported_as_user_facing_value_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Excel файлыг унших боломжгүй"):
            DataLoader().get_sheets(b"not an excel file", "bad.xlsx")

    def test_analysis_calculates_stats_trends_groups_and_outliers(self) -> None:
        analysis = DataAnalyzer(self.frame).generate_analysis()
        self.assertEqual(analysis["statistics"]["Revenue"]["sum"], 1060)
        self.assertEqual(analysis["statistics"]["Revenue"]["median"], 25)
        self.assertEqual(analysis["kpis"][0]["column"], "Revenue")
        self.assertTrue(analysis["trends"])
        self.assertTrue(analysis["category_comparisons"])
        self.assertTrue(any(item["value"] == 1000 for item in analysis["outliers"]))
        self.assertTrue(any(item["column_a"] == "Revenue" for item in analysis["correlations"]))

    def test_analysis_supports_non_string_headers_and_unhinted_dates(self) -> None:
        frame = pd.DataFrame({
            0: ["2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01"],
            1: ["A", "A", "B", "B"],
            2: ["10", "20", "30", "40"],
        })
        profile = DataProfiler().profile(frame)
        analysis = DataAnalyzer(frame, profile).generate_analysis()
        self.assertIn("0", profile["date_columns"])
        self.assertEqual(analysis["statistics"]["2"]["sum"], 100)
        self.assertTrue(analysis["trends"])

    def test_excel_report_has_required_sheets_and_escapes_formulas(self) -> None:
        frame = self.frame.copy()
        frame.loc[0, "Department"] = "=HYPERLINK(\"https://example.invalid\")"
        analysis = DataAnalyzer(frame).generate_analysis()
        result = generate_excel_report(analysis, {"summary": [], "insights": [], "recommendations": []})
        workbook = pd.ExcelFile(BytesIO(result))
        self.assertEqual(
            workbook.sheet_names,
            ["Summary", "KPI", "Statistics", "Trend", "Category Comparison", "Outliers", "Correlation", "AI Insights"],
        )
        categories = pd.read_excel(BytesIO(result), sheet_name="Category Comparison")
        self.assertTrue(categories["category"].astype(str).str.startswith("'=").any())

    def test_pdf_and_word_reports_generate_in_memory(self) -> None:
        profile = DataProfiler().profile(self.frame)
        analysis = DataAnalyzer(self.frame, profile).generate_analysis()
        empty_insights = {"summary": [], "insights": [], "recommendations": []}
        pdf = generate_pdf_report(analysis, empty_insights, df=self.frame, profile=profile)
        word = generate_word_report(analysis, empty_insights, df=self.frame, profile=profile)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertTrue(word.startswith(b"PK"))

    def test_ai_json_schema_validation(self) -> None:
        result = parse_model_json(
            '```json\n{"summary":["Товч"],"insights":[],"recommendations":[]}\n```',
            AIAnalysisResult,
        )
        self.assertIsInstance(result, AIAnalysisResult)
        with self.assertRaises(ValueError):
            parse_model_json('{"summary": 4}', AIAnalysisResult)


if __name__ == "__main__":
    unittest.main()