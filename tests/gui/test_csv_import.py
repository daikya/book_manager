"""単一CSVの確認・キャンセル・一括実行のGUIテスト。"""
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

from book_manager.gui.book_manager_application import BookManagerApplication
from book_manager.models.book_item import BookItem
from book_manager.models.csv_import_result import CsvImportIssue, CsvImportPreview, CsvImportResult


def make_application():
    app = BookManagerApplication.__new__(BookManagerApplication)
    app._root = Mock()
    app._backup_service = Mock()
    app._csv_import_service = Mock()
    app._load_all_books = Mock()
    app._refresh_tag_options = Mock()
    app._csv_import_service.preview_file.return_value = CsvImportPreview(
        Path("books.csv"), "hash", (BookItem(title="書籍"),), (), (),
    )
    app._csv_import_service.execute_preview.return_value = CsvImportResult(1, 0, 0, (), (), Path("backup.db"))
    return app


def invoke(app, *, selected="books.csv", confirm=True):
    with ExitStack() as stack:
        base = "book_manager.gui.book_manager_application."
        stack.enter_context(patch(base + "filedialog.askopenfilename", return_value=selected))
        ask = stack.enter_context(patch(base + "messagebox.askyesno", return_value=confirm))
        info = stack.enter_context(patch(base + "messagebox.showinfo"))
        error = stack.enter_context(patch(base + "messagebox.showerror"))
        stack.enter_context(patch(base + "traceback.print_exc"))
        app._on_import_csv()
    return ask, info, error


def test_file_cancel_does_not_inspect():
    app = make_application()
    invoke(app, selected="")
    app._csv_import_service.preview_file.assert_not_called()
    app._csv_import_service.execute_preview.assert_not_called()


def test_confirmation_cancel_does_not_execute():
    app = make_application()
    ask, _, _ = invoke(app, confirm=False)
    ask.assert_called_once()
    app._csv_import_service.execute_preview.assert_not_called()
    app._load_all_books.assert_not_called()


def test_confirmed_import_uses_preview_and_backup_service():
    app = make_application()
    _, info, error = invoke(app)
    app._csv_import_service.preview_file.assert_called_once_with(Path("books.csv"))
    app._csv_import_service.execute_preview.assert_called_once_with(
        app._csv_import_service.preview_file.return_value, backup_service=app._backup_service,
    )
    app._csv_import_service.import_file.assert_not_called()
    app._load_all_books.assert_called_once_with()
    app._refresh_tag_options.assert_called_once_with()
    assert "backup.db" in info.call_args.args[1]
    error.assert_not_called()


def test_no_importable_rows_does_not_execute():
    app = make_application()
    app._csv_import_service.preview_file.return_value = CsvImportPreview(
        Path("books.csv"), "hash", (), (), (CsvImportIssue(2, "不正な値"),),
    )
    ask, info, _ = invoke(app)
    ask.assert_not_called()
    assert "2行目: 不正な値" in info.call_args.args[1]
    app._csv_import_service.execute_preview.assert_not_called()


def test_preview_explains_excluded_rows():
    app = make_application()
    app._csv_import_service.preview_file.return_value = CsvImportPreview(
        Path("books.csv"), "hash", (BookItem(title="書籍"),),
        (CsvImportIssue(3, "重複"),), (CsvImportIssue(4, "不正"),),
    )
    ask, _, _ = invoke(app, confirm=False)
    text = ask.call_args.args[1]
    assert "3行目: 重複" in text and "4行目: 不正" in text
    assert "登録しません" in text


def test_preview_failure_does_not_execute():
    app = make_application()
    app._csv_import_service.preview_file.side_effect = ValueError("ヘッダー不正")
    _, _, error = invoke(app)
    error.assert_called_once()
    app._csv_import_service.execute_preview.assert_not_called()
    app._load_all_books.assert_not_called()


def test_execution_failure_does_not_refresh_or_show_success():
    app = make_application()
    app._csv_import_service.execute_preview.side_effect = RuntimeError("バックアップ失敗")
    _, info, error = invoke(app)
    error.assert_called_once()
    info.assert_not_called()
    app._load_all_books.assert_not_called()
