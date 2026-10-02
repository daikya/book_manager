"""Excel取込GUIのキャンセル・承認・エラー処理を検証する。"""
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from book_manager.gui.book_manager_application import BookManagerApplication

MODULE = "book_manager.gui.book_manager_application"


class ExcelImportGuiTests(unittest.TestCase):
    def setUp(self):
        self.application = BookManagerApplication.__new__(BookManagerApplication)
        self.application._root = Mock()
        self.application._excel_workbook_reader_service = Mock()
        self.application._excel_import_preflight_service = Mock()
        self.application._excel_import_service = Mock()
        self.application._refresh_tag_options = Mock()
        self.application._load_all_books = Mock()
        self.reader = self.application._excel_workbook_reader_service
        self.preflight = self.application._excel_import_preflight_service
        self.importer = self.application._excel_import_service
        self.options = Mock()
        self.preview = self.preflight.preview_sheet.return_value
        self.mapping = self.enterContext(patch(f"{MODULE}.ExcelColumnMappingDialog"))
        self.mapping.return_value.show.return_value = self.options
        self.confirmation = self.enterContext(patch(f"{MODULE}.ExcelImportPreviewDialog"))
        self.confirmation.return_value.show.return_value = True
        self.file = self.enterContext(patch(f"{MODULE}.filedialog.askopenfilename", return_value="source.xlsx"))
        self.info = self.enterContext(patch(f"{MODULE}.messagebox.showinfo"))
        self.error = self.enterContext(patch(f"{MODULE}.messagebox.showerror"))
        self.warning = self.enterContext(patch(f"{MODULE}.messagebox.showwarning"))
        self.enterContext(patch(f"{MODULE}.logger"))

    def test_all_services_required(self):
        self.assertTrue(self.application._has_excel_import_services())
        self.application._excel_import_service = None
        self.assertFalse(self.application._has_excel_import_services())

    def test_missing_services_warns_without_file_selection(self):
        self.application._excel_import_service = None
        self.application._on_import_excel()
        self.warning.assert_called_once()
        self.file.assert_not_called()

    def test_file_selection_cancel(self):
        self.file.return_value = ""
        self.application._on_import_excel()
        self.reader.read_sheet.assert_not_called()
        self.importer.import_preview.assert_not_called()

    def test_mapping_cancel(self):
        self.mapping.return_value.show.return_value = None
        self.application._on_import_excel()
        self.preflight.preview_sheet.assert_not_called()
        self.importer.import_preview.assert_not_called()

    def test_confirmation_cancel_returns_to_mapping(self):
        self.mapping.return_value.show.side_effect = [self.options, None]
        self.confirmation.return_value.show.return_value = False
        self.application._on_import_excel()
        self.assertEqual(self.mapping.call_count, 2)
        self.importer.import_preview.assert_not_called()

    def test_approved_preview_imports_and_refreshes(self):
        self.application._on_import_excel()
        self.reader.read_sheet.assert_called_once_with(Path("source.xlsx"))
        self.preflight.preview_sheet.assert_called_once_with(self.reader.read_sheet.return_value, options=self.options)
        self.importer.import_preview.assert_called_once_with(self.preview)
        self.application._refresh_tag_options.assert_called_once_with()
        self.application._load_all_books.assert_called_once_with()
        self.info.assert_called_once()

    def test_read_failure_does_not_import(self):
        self.reader.read_sheet.side_effect = ValueError("1シートにしてください")
        self.application._on_import_excel()
        self.error.assert_called_once()
        self.mapping.assert_not_called()
        self.importer.import_preview.assert_not_called()

    def test_preflight_failure_does_not_import(self):
        self.preflight.preview_sheet.side_effect = ValueError("列が不正")
        self.application._on_import_excel()
        self.error.assert_called_once()
        self.importer.import_preview.assert_not_called()

    def test_import_failure_does_not_report_success(self):
        self.importer.import_preview.side_effect = ValueError("Excelが変更されました")
        self.application._on_import_excel()
        self.error.assert_called_once()
        self.info.assert_not_called()
        self.application._load_all_books.assert_not_called()

    def test_menu_includes_excel_only_when_available(self):
        self.application._data_io_button = Mock()
        self.application._data_io_button.winfo_rootx.return_value = 10
        self.application._data_io_button.winfo_rooty.return_value = 20
        self.application._data_io_button.winfo_height.return_value = 30
        for name in ("_on_export_csv", "_on_import_csv", "_on_export_csv_data_package", "_on_import_csv_data_package"):
            setattr(self.application, name, Mock())
        self.application._has_csv_data_package_services = Mock(return_value=False)
        with patch(f"{MODULE}.tk.Menu") as menu:
            self.application._show_data_io_menu()
        labels = [call.kwargs["label"] for call in menu.return_value.add_command.call_args_list]
        self.assertIn("Excelから書籍と読書履歴をインポート", labels)
        self.application._excel_import_service = None
        with patch(f"{MODULE}.tk.Menu") as menu:
            self.application._show_data_io_menu()
        labels = [call.kwargs["label"] for call in menu.return_value.add_command.call_args_list]
        self.assertNotIn("Excelから書籍と読書履歴をインポート", labels)


if __name__ == "__main__":
    unittest.main()
