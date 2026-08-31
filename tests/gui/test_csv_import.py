from pathlib import Path
from unittest.mock import Mock, patch

from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)
from book_manager.models.csv_import_result import (
    CsvImportIssue,
    CsvImportResult,
)


def create_application() -> BookManagerApplication:
    """CSVインポート用の最小限のApplicationを作成する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )
    application._root = Mock()
    application._csv_import_service = Mock()
    application._csv_import_service.import_file.return_value = (
        CsvImportResult(
            imported_count=0,
            skipped_count=0,
            error_count=0,
            skipped=(),
            errors=(),
        )
    )
    application._load_all_books = Mock()

    return application


def test_on_import_csv_does_nothing_when_file_selection_is_cancelled() -> None:
    """CSVファイル選択をキャンセルした場合はインポートしない。"""
    application = create_application()

    with patch(
        "book_manager.gui.book_manager_application.filedialog.askopenfilename",
        return_value="",
    ) as askopenfilename:
        application._on_import_csv()

    askopenfilename.assert_called_once()

    application._csv_import_service.import_file.assert_not_called()


def test_on_import_csv_calls_import_service_with_selected_path() -> None:
    """選択したCSVファイルをインポートサービスへ渡す。"""
    application = create_application()

    selected_path = "C:/temp/books.csv"

    with (
        patch(
            "book_manager.gui.book_manager_application.filedialog.askopenfilename",
            return_value=selected_path,
        ),
        patch(
            "book_manager.gui.book_manager_application.messagebox.showinfo",
        ),
    ):
        application._on_import_csv()

    application._csv_import_service.import_file.assert_called_once_with(
        Path(selected_path),
    )


def test_on_import_csv_refreshes_book_list_after_import() -> None:
    """CSVインポート後に一覧を再読み込みする。"""
    application = create_application()

    selected_path = "C:/temp/books.csv"

    with (
        patch(
            "book_manager.gui.book_manager_application.filedialog.askopenfilename",
            return_value=selected_path,
        ),
        patch(
            "book_manager.gui.book_manager_application.messagebox.showinfo",
        ),
    ):
        application._on_import_csv()

    application._load_all_books.assert_called_once_with()


def test_on_import_csv_shows_result_summary() -> None:
    """CSVインポート結果の件数を表示する。"""
    application = create_application()

    application._csv_import_service.import_file.return_value = (
        CsvImportResult(
            imported_count=3,
            skipped_count=2,
            error_count=1,
            skipped=(),
            errors=(),
        )
    )

    selected_path = "C:/temp/books.csv"

    with (
        patch(
            "book_manager.gui.book_manager_application.filedialog.askopenfilename",
            return_value=selected_path,
        ),
        patch(
            "book_manager.gui.book_manager_application.messagebox.showinfo",
        ) as showinfo,
    ):
        application._on_import_csv()

    showinfo.assert_called_once_with(
        "CSVインポート完了",
        (
            "CSVインポートが完了しました。\n\n"
            "登録: 3件\n"
            "スキップ: 2件\n"
            "エラー: 1件"
        ),
        parent=application._root,
    )


def test_on_import_csv_shows_skipped_and_error_details() -> None:
    """CSVインポート結果にスキップとエラーの詳細を表示する。"""
    application = create_application()

    application._csv_import_service.import_file.return_value = (
        CsvImportResult(
            imported_count=2,
            skipped_count=2,
            error_count=2,
            skipped=(
                CsvImportIssue(
                    row_number=3,
                    message="ISBNが既存データと重複しています。",
                ),
                CsvImportIssue(
                    row_number=5,
                    message="雑誌コードが既存データと重複しています。",
                ),
            ),
            errors=(
                CsvImportIssue(
                    row_number=4,
                    message="読書状態が不正です。",
                ),
                CsvImportIssue(
                    row_number=6,
                    message="評価が不正です。",
                ),
            ),
        )
    )

    selected_path = "C:/temp/books.csv"

    with (
        patch(
            "book_manager.gui.book_manager_application.filedialog.askopenfilename",
            return_value=selected_path,
        ),
        patch(
            "book_manager.gui.book_manager_application.messagebox.showinfo",
        ) as showinfo,
    ):
        application._on_import_csv()

    showinfo.assert_called_once_with(
        "CSVインポート完了",
        (
            "CSVインポートが完了しました。\n\n"
            "登録: 2件\n"
            "スキップ: 2件\n"
            "エラー: 2件\n\n"
            "【スキップ】\n"
            "3行目: ISBNが既存データと重複しています。\n"
            "5行目: 雑誌コードが既存データと重複しています。\n\n"
            "【エラー】\n"
            "4行目: 読書状態が不正です。\n"
            "6行目: 評価が不正です。"
        ),
        parent=application._root,
    )


def test_on_import_csv_shows_error_when_import_fails() -> None:
    """CSVインポートに失敗した場合はエラーを表示する。"""
    application = create_application()

    application._csv_import_service.import_file.side_effect = ValueError(
        "CSVヘッダーが不正です。",
    )

    selected_path = "C:/temp/books.csv"

    with (
        patch(
            "book_manager.gui.book_manager_application.filedialog.askopenfilename",
            return_value=selected_path,
        ),
        patch(
            "book_manager.gui.book_manager_application.messagebox.showerror",
        ) as showerror,
        patch(
            "book_manager.gui.book_manager_application.traceback.print_exc",
        ) as print_exc,
    ):
        application._on_import_csv()

    print_exc.assert_called_once_with()

    showerror.assert_called_once_with(
        "CSVインポートエラー",
        "CSVファイルをインポートできませんでした。",
        parent=application._root,
    )

    application._load_all_books.assert_not_called()
