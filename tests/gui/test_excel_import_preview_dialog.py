"""Excel事前検査画面の表示内容と登録可否を検証する。"""
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from book_manager.gui.excel_import_preview_dialog import (
    ExcelImportPreviewDialog, preview_summary, record_details,
)
from book_manager.models.book_item import BookItem
from book_manager.models.excel_import import (
    ExcelImportIssue, ExcelImportOptions, ExcelImportPreview, ExcelImportRecord,
)


class ExcelImportPreviewDialogTests(unittest.TestCase):
    def setUp(self):
        self.record = ExcelImportRecord(2, BookItem(title="音声の本", author="著者",
            reference_isbn="9784101010014", description="紹介\n全文", tags=("音声",),
            reading_status="completed"), completed_on="2022-03", history_notes="感想",
            reading_status_suggested=True)
        self.preview = ExcelImportPreview(Path("source.xlsx"), "hash", "読書", 1,
            ExcelImportOptions((("title", 1),)), (self.record,))
        self.dialog = ExcelImportPreviewDialog.__new__(ExcelImportPreviewDialog)
        self.dialog._preview = self.preview
        self.dialog._window = Mock()
        self.dialog._accepted = Mock()
        self.dialog._accepted.get.return_value = True
        self.dialog._import_button = Mock()
        self.dialog.result = False

    def test_full_details_include_reference_isbn_and_history(self):
        details = record_details(self.record)
        for expected in ("参照ISBN：9784101010014", "紹介\n全文", "読了日・年月：2022-03",
                         "読書履歴の備考：感想", "読了（日付からの提案）", "読書履歴の追加：あり"):
            self.assertIn(expected, details)

    def test_empty_history_and_unset_state(self):
        details = record_details(ExcelImportRecord(2, BookItem(title="本")))
        self.assertIn("読書状態：未設定", details)
        self.assertIn("読書履歴の追加：なし", details)

    def test_summary_counts(self):
        preview = replace(self.preview, warnings=(ExcelImportIssue(2, "注意"),),
                          skipped=(ExcelImportIssue(3, "除外"),))
        self.assertIn("書籍 1 件／読書履歴 1 件", preview_summary(preview))
        self.assertIn("注意事項 1 件／除外・空行 1 件", preview_summary(preview))

    def test_confirm_accepts_valid_preview(self):
        self.dialog._confirm()
        self.assertTrue(self.dialog.result)
        self.dialog._window.destroy.assert_called_once_with()

    def test_no_checkbox_prevents_import(self):
        self.dialog._accepted.get.return_value = False
        with patch("book_manager.gui.excel_import_preview_dialog.messagebox.showwarning") as warning:
            self.dialog._confirm()
        warning.assert_called_once()
        self.assertFalse(self.dialog.result)
        self.dialog._window.destroy.assert_not_called()

    def test_error_prevents_import_even_when_checked(self):
        self.dialog._preview = replace(self.preview, errors=(ExcelImportIssue(3, "エラー"),))
        with patch("book_manager.gui.excel_import_preview_dialog.messagebox.showwarning"):
            self.dialog._confirm()
        self.assertFalse(self.dialog.result)
        self.dialog._window.destroy.assert_not_called()

    def test_no_records_prevents_import(self):
        self.dialog._preview = replace(self.preview, records=())
        with patch("book_manager.gui.excel_import_preview_dialog.messagebox.showwarning"):
            self.dialog._confirm()
        self.assertFalse(self.dialog.result)

    def test_button_enabled_after_confirmation(self):
        self.dialog._update_button()
        self.dialog._import_button.configure.assert_called_once_with(state="normal")

    def test_button_disabled_without_confirmation(self):
        self.dialog._accepted.get.return_value = False
        self.dialog._update_button()
        self.dialog._import_button.configure.assert_called_once_with(state="disabled")

    def test_button_disabled_with_error(self):
        self.dialog._preview = replace(self.preview, errors=(ExcelImportIssue(2, "エラー"),))
        self.dialog._update_button()
        self.dialog._import_button.configure.assert_called_once_with(state="disabled")

    def test_cancel(self):
        self.dialog.result = True
        self.dialog._cancel()
        self.assertFalse(self.dialog.result)
        self.dialog._window.destroy.assert_called_once_with()

    def test_selection_displays_full_details_readonly(self):
        self.dialog._records_table = Mock()
        self.dialog._records_table.selection.return_value = ("0",)
        self.dialog._details = Mock()
        self.dialog._show_details()
        self.dialog._details.insert.assert_called_once_with("1.0", record_details(self.record))
        self.assertEqual(self.dialog._details.configure.call_args.kwargs, {"state": "disabled"})

    def test_empty_selection(self):
        self.dialog._records_table = Mock()
        self.dialog._records_table.selection.return_value = ()
        self.dialog._details = Mock()
        self.dialog._show_details()
        self.dialog._details.insert.assert_not_called()

    def test_modal_wait(self):
        self.assertFalse(self.dialog.show())
        self.dialog._window.grab_set.assert_called_once_with()
        self.dialog._window.wait_window.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
