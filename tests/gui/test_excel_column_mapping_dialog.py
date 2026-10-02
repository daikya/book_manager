"""列割り当ての入力と確定・キャンセル処理をGUI表示なしで検証する。"""
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from book_manager.gui.excel_column_mapping_dialog import (
    ExcelColumnMappingDialog, column_name, parse_excluded_rows,
)
from book_manager.models.excel_workbook import ExcelCell, ExcelRow, ExcelSheetData


class ExcelColumnMappingDialogTests(unittest.TestCase):
    def setUp(self):
        self.dialog = ExcelColumnMappingDialog.__new__(ExcelColumnMappingDialog)
        self.dialog._window = Mock()
        self.dialog.result = None
        self.dialog._choices = ["取り込まない", "A列：書名", "B列：著者"]
        self.dialog._variables = {"title": Mock(), "author": Mock()}
        self.dialog._variables["title"].get.return_value = "A列：書名"
        self.dialog._variables["author"].get.return_value = "B列：著者"
        self.dialog._excluded = Mock()
        self.dialog._excluded.get.return_value = ""
        self.dialog._default_format = Mock()
        self.dialog._default_format.get.return_value = ""
        self.dialog._sheet = ExcelSheetData(Path("source.xlsx"), "hash", 1, "読書",
            ExcelRow(1, (ExcelCell("A1", "書名", "General"), ExcelCell("B1", "著者", "General"))),
            (ExcelRow(2, (ExcelCell("A2", "本", "General"), ExcelCell("B2", "著者名", "General"))),))

    def test_column_names(self):
        self.assertEqual([column_name(n) for n in (1, 26, 27, 52, 256)], ["A", "Z", "AA", "AZ", "IV"])

    def test_invalid_column_number(self):
        for value in (0, -1, True):
            with self.assertRaises(ValueError):
                column_name(value)

    def test_excluded_rows(self):
        self.assertEqual(parse_excluded_rows("2,5,8-10,5"), (2, 5, 8, 9, 10))
        self.assertEqual(parse_excluded_rows(""), ())

    def test_invalid_exclusion(self):
        for value in ("0", "5-2", "abc", "2,", "1-100001", "1-2-3"):
            with self.assertRaises(ValueError):
                parse_excluded_rows(value)

    def test_confirm_returns_mapping(self):
        self.dialog._confirm()
        self.assertEqual(self.dialog.result.column_mapping, (("title", 1), ("author", 2)))
        self.dialog._window.destroy.assert_called_once_with()

    def test_optional_unassigned_field(self):
        self.dialog._variables["author"].get.return_value = "取り込まない"
        self.dialog._confirm()
        self.assertEqual(self.dialog.result.column_mapping, (("title", 1),))

    def test_missing_title_keeps_dialog_open(self):
        self.dialog._variables["title"].get.return_value = "取り込まない"
        with patch("book_manager.gui.excel_column_mapping_dialog.messagebox.showwarning") as warning:
            self.dialog._confirm()
        warning.assert_called_once()
        self.dialog._window.destroy.assert_not_called()
        self.assertIsNone(self.dialog.result)

    def test_duplicate_columns_keeps_dialog_open(self):
        self.dialog._variables["author"].get.return_value = "A列：書名"
        with patch("book_manager.gui.excel_column_mapping_dialog.messagebox.showwarning") as warning:
            self.dialog._confirm()
        warning.assert_called_once()
        self.dialog._window.destroy.assert_not_called()

    def test_header_row_cannot_be_excluded(self):
        self.dialog._excluded.get.return_value = "1"
        with patch("book_manager.gui.excel_column_mapping_dialog.messagebox.showwarning") as warning:
            self.dialog._confirm()
        warning.assert_called_once()
        self.dialog._window.destroy.assert_not_called()

    def test_exclusion_and_default_format(self):
        self.dialog._excluded.get.return_value = "2"
        self.dialog._default_format.get.return_value = " Audible "
        self.dialog._confirm()
        self.assertEqual(self.dialog.result.excluded_rows, (2,))
        self.assertEqual(self.dialog.result.default_publication_format, "Audible")

    def test_cancel_has_no_result(self):
        self.dialog._cancel()
        self.assertIsNone(self.dialog.result)
        self.dialog._window.destroy.assert_called_once_with()

    def test_sample_and_empty_choice(self):
        self.assertEqual(self.dialog._sample("A列：書名"), "例：本")
        self.assertEqual(self.dialog._sample("取り込まない"), "")

    def test_show_waits_for_dialog(self):
        self.assertIsNone(self.dialog.show())
        self.dialog._window.grab_set.assert_called_once_with()
        self.dialog._window.wait_window.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
