from pathlib import Path
from unittest.mock import Mock, patch

from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)


def create_application() -> BookManagerApplication:
    """バックアップ復元用の最小限のApplicationを作成する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )
    application._root = Mock()
    application._backup_service = Mock()
    application._selected_book_id = 123

    return application


def test_on_restore_backup_does_nothing_when_file_selection_is_cancelled() -> None:
    """ファイル選択をキャンセルした場合は復元しない。"""
    application = create_application()

    with (
        patch(
            "book_manager.gui.book_manager_application."
            "filedialog.askopenfilename",
            return_value="",
        ) as askopenfilename,
        patch.object(
            BookManagerApplication,
            "_load_all_books",
        ) as load_all_books,
    ):
        application._on_restore_backup()

    askopenfilename.assert_called_once()
    application._backup_service.restore_backup.assert_not_called()
    load_all_books.assert_not_called()


def test_on_restore_backup_does_nothing_when_confirmation_is_cancelled() -> None:
    """確認ダイアログでキャンセルした場合は復元しない。"""
    application = create_application()
    selected_path = "C:/temp/books_20260831_120000.db"

    with (
        patch(
            "book_manager.gui.book_manager_application."
            "filedialog.askopenfilename",
            return_value=selected_path,
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.askyesno",
            return_value=False,
        ) as askyesno,
        patch.object(
            BookManagerApplication,
            "_load_all_books",
        ) as load_all_books,
    ):
        application._on_restore_backup()

    askyesno.assert_called_once()
    application._backup_service.restore_backup.assert_not_called()
    load_all_books.assert_not_called()


def test_on_restore_backup_calls_service_with_selected_path() -> None:
    """選択したDBをBackupServiceへ渡す。"""
    application = create_application()
    selected_path = "C:/temp/books_20260831_120000.db"

    with (
        patch(
            "book_manager.gui.book_manager_application."
            "filedialog.askopenfilename",
            return_value=selected_path,
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.askyesno",
            return_value=True,
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.showinfo",
        ),
        patch.object(
            BookManagerApplication,
            "_load_all_books",
        ),
    ):
        application._on_restore_backup()

    application._backup_service.restore_backup.assert_called_once_with(
        Path(selected_path),
    )


def test_on_restore_backup_refreshes_book_list_after_restore() -> None:
    """復元成功後に書籍一覧を再読み込みする。"""
    application = create_application()
    selected_path = "C:/temp/books_20260831_120000.db"

    with (
        patch(
            "book_manager.gui.book_manager_application."
            "filedialog.askopenfilename",
            return_value=selected_path,
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.askyesno",
            return_value=True,
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.showinfo",
        ),
        patch.object(
            BookManagerApplication,
            "_load_all_books",
        ) as load_all_books,
    ):
        application._on_restore_backup()

    load_all_books.assert_called_once_with()
    assert application._selected_book_id is None


def test_on_restore_backup_shows_success_message() -> None:
    """復元成功時に完了メッセージを表示する。"""
    application = create_application()
    selected_path = "C:/temp/books_20260831_120000.db"

    with (
        patch(
            "book_manager.gui.book_manager_application."
            "filedialog.askopenfilename",
            return_value=selected_path,
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.askyesno",
            return_value=True,
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.showinfo",
        ) as showinfo,
        patch.object(
            BookManagerApplication,
            "_load_all_books",
        ),
    ):
        application._on_restore_backup()

    showinfo.assert_called_once_with(
        "バックアップ復元完了",
        "バックアップからデータを復元しました。",
        parent=application._root,
    )


def test_on_restore_backup_shows_error_when_restore_fails() -> None:
    """復元失敗時にエラーを表示して一覧を再読み込みしない。"""
    application = create_application()
    selected_path = "C:/temp/books_20260831_120000.db"

    application._backup_service.restore_backup.side_effect = (
        ValueError(
            "復元元データベースが不正です。",
        )
    )

    with (
        patch(
            "book_manager.gui.book_manager_application."
            "filedialog.askopenfilename",
            return_value=selected_path,
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.askyesno",
            return_value=True,
        ),
        patch(
            "book_manager.gui.book_manager_application."
            "messagebox.showerror",
        ) as showerror,
        patch(
            "book_manager.gui.book_manager_application."
            "traceback.print_exc",
        ) as print_exc,
        patch.object(
            BookManagerApplication,
            "_load_all_books",
        ) as load_all_books,
    ):
        application._on_restore_backup()

    print_exc.assert_called_once_with()

    showerror.assert_called_once_with(
        "バックアップ復元エラー",
        "バックアップからデータを復元できませんでした。",
        parent=application._root,
    )

    load_all_books.assert_not_called()
    assert application._selected_book_id == 123
