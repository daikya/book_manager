"""読書履歴ダイアログのGUIロジックを検証する。"""

from unittest.mock import Mock, patch

from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)
from book_manager.models.book_item import BookItem
from book_manager.models.reading_history import ReadingHistory


def create_application() -> BookManagerApplication:
    """読書履歴GUIテスト用Applicationを生成する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )
    application._root = Mock()
    application._service = Mock()
    application._reading_history_service = Mock()
    application._selected_book_id = 10
    application._reading_history_book_id = 10
    application._selected_reading_history_id = None
    application._reading_history_started_on_var = Mock()
    application._reading_history_completed_on_var = Mock()
    application._reading_history_notes_text = Mock()
    application._reading_history_tree = Mock()
    application._reading_history_tree.selection.return_value = ()
    application._get_reading_history_form_values = Mock(
        return_value=(
            "2026-09-01",
            "2026-09-07",
            "読了した。",
        )
    )
    application._populate_reading_history_tree = Mock()
    application._clear_reading_history_form = Mock()

    return application


def test_manage_reading_histories_warns_without_selected_book() -> None:
    """書籍未選択時は警告してダイアログを開かない。"""
    application = create_application()
    application._selected_book_id = None
    application._open_reading_history_dialog = Mock()

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showwarning"
    ) as showwarning:
        application._on_manage_reading_histories()

    showwarning.assert_called_once()
    application._open_reading_history_dialog.assert_not_called()


def test_manage_reading_histories_opens_selected_book() -> None:
    """選択中の書籍を取得してダイアログへ渡す。"""
    application = create_application()
    book = BookItem(id=10, title="対象書籍")
    application._service.get_book.return_value = book
    application._open_reading_history_dialog = Mock()

    application._on_manage_reading_histories()

    application._service.get_book.assert_called_once_with(10)
    application._open_reading_history_dialog.assert_called_once_with(
        book
    )


def test_populate_reading_history_tree_displays_histories() -> None:
    """履歴一覧へ日付と改行を除いたメモ概要を表示する。"""
    application = create_application()
    history_tree = Mock()
    history_tree.get_children.return_value = ("old",)
    application._reading_history_service.get_histories_for_book.return_value = [
        ReadingHistory(
            id=2,
            book_item_id=10,
            started_on="2026-09-01",
            completed_on="2026-09-07",
            notes="一行目\n二行目",
        ),
        ReadingHistory(
            id=1,
            book_item_id=10,
            notes=None,
        ),
    ]
    application._populate_reading_history_tree = (
        BookManagerApplication._populate_reading_history_tree.__get__(
            application
        )
    )

    application._populate_reading_history_tree(10, history_tree)

    history_tree.delete.assert_called_once_with("old")
    history_tree.insert.assert_any_call(
        "",
        "end",
        iid="2",
        values=("2026-09-01", "2026-09-07", "一行目 二行目"),
    )
    history_tree.insert.assert_any_call(
        "",
        "end",
        iid="1",
        values=("", "", ""),
    )


def test_populate_reading_history_tree_accepts_empty_list() -> None:
    """履歴0件でも既存表示を削除して正常終了する。"""
    application = create_application()
    history_tree = Mock()
    history_tree.get_children.return_value = ("old",)
    application._reading_history_service.get_histories_for_book.return_value = []
    method = BookManagerApplication._populate_reading_history_tree.__get__(
        application
    )

    method(10, history_tree)

    history_tree.delete.assert_called_once_with("old")
    history_tree.insert.assert_not_called()


def test_reading_history_notes_summary_truncates_long_text() -> None:
    """長いメモ概要を省略表示する。"""
    summary = BookManagerApplication._reading_history_notes_summary(
        "あ" * 51
    )

    assert summary == f"{'あ' * 50}…"


def test_select_reading_history_restores_form_values() -> None:
    """選択した履歴の全内容を入力欄へ復元する。"""
    application = create_application()
    application._reading_history_tree.selection.return_value = ("3",)
    history = ReadingHistory(
        id=3,
        book_item_id=10,
        started_on="2026-09-01",
        completed_on="2026-09-07",
        notes="全文メモ",
    )
    application._reading_history_service.get_history.return_value = history

    application._on_reading_history_select()

    assert application._selected_reading_history_id == 3
    application._reading_history_started_on_var.set.assert_called_once_with(
        "2026-09-01"
    )
    application._reading_history_completed_on_var.set.assert_called_once_with(
        "2026-09-07"
    )
    application._reading_history_notes_text.insert.assert_called_once_with(
        "1.0",
        "全文メモ",
    )


def test_add_reading_history_passes_form_values_and_refreshes() -> None:
    """新規登録時に入力値をServiceへ渡して表示を更新する。"""
    application = create_application()

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showinfo"
    ):
        application._add_reading_history()

    application._reading_history_service.add_history.assert_called_once_with(
        book_item_id=10,
        started_on="2026-09-01",
        completed_on="2026-09-07",
        notes="読了した。",
    )
    application._populate_reading_history_tree.assert_called_once_with(
        10,
        application._reading_history_tree,
    )
    application._clear_reading_history_form.assert_called_once_with()


def test_add_reading_history_displays_validation_error() -> None:
    """新規登録時の入力エラーをそのまま表示する。"""
    application = create_application()
    application._reading_history_service.add_history.side_effect = ValueError(
        "入力内容を確認してください。"
    )

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showerror"
    ) as showerror:
        application._add_reading_history()

    assert showerror.call_args.args[1] == "入力内容を確認してください。"
    application._populate_reading_history_tree.assert_not_called()


def test_update_reading_history_warns_without_selection() -> None:
    """履歴未選択時は更新しない。"""
    application = create_application()

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showwarning"
    ):
        application._update_reading_history()

    application._reading_history_service.update_history.assert_not_called()


def test_update_reading_history_uses_selected_history_id() -> None:
    """選択中の履歴IDと入力値を使用して更新する。"""
    application = create_application()
    application._selected_reading_history_id = 4
    application._reading_history_service.update_history.return_value = True

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showinfo"
    ):
        application._update_reading_history()

    update_target = (
        application._reading_history_service.update_history.call_args.args[0]
    )
    assert update_target.id == 4
    assert update_target.book_item_id == 10
    assert update_target.started_on == "2026-09-01"
    application._populate_reading_history_tree.assert_called_once()
    application._clear_reading_history_form.assert_called_once_with()


def test_delete_reading_history_warns_without_selection() -> None:
    """履歴未選択時は削除しない。"""
    application = create_application()

    with patch(
        "book_manager.gui.book_manager_application.messagebox.showwarning"
    ):
        application._delete_reading_history()

    application._reading_history_service.delete_history.assert_not_called()


def test_delete_reading_history_cancels_without_service_call() -> None:
    """削除確認を取り消した場合は削除しない。"""
    application = create_application()
    application._selected_reading_history_id = 5

    with patch(
        "book_manager.gui.book_manager_application.messagebox.askyesno",
        return_value=False,
    ):
        application._delete_reading_history()

    application._reading_history_service.delete_history.assert_not_called()


def test_delete_reading_history_refreshes_after_success() -> None:
    """削除成功後に履歴一覧と入力欄を更新する。"""
    application = create_application()
    application._selected_reading_history_id = 5
    application._reading_history_service.delete_history.return_value = True

    with (
        patch(
            "book_manager.gui.book_manager_application.messagebox.askyesno",
            return_value=True,
        ),
        patch(
            "book_manager.gui.book_manager_application.messagebox.showinfo"
        ),
    ):
        application._delete_reading_history()

    application._reading_history_service.delete_history.assert_called_once_with(
        5
    )
    application._populate_reading_history_tree.assert_called_once_with(
        10,
        application._reading_history_tree,
    )
    application._clear_reading_history_form.assert_called_once_with()


def test_clear_reading_history_form_resets_input_and_selection() -> None:
    """入力クリアで新規入力状態へ戻す。"""
    application = create_application()
    application._selected_reading_history_id = 8
    application._reading_history_tree.selection.return_value = ("8",)
    method = BookManagerApplication._clear_reading_history_form.__get__(
        application
    )

    method()

    assert application._selected_reading_history_id is None
    application._reading_history_started_on_var.set.assert_called_once_with("")
    application._reading_history_completed_on_var.set.assert_called_once_with("")
    application._reading_history_notes_text.delete.assert_called_once()
    application._reading_history_tree.selection_remove.assert_called_once_with(
        "8"
    )
