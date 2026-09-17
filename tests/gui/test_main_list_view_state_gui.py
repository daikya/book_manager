"""一覧表示状態の復元に関するGUIロジックテスト。"""

from __future__ import annotations

import tkinter as tk
from unittest.mock import Mock, call, patch

import pytest

from book_manager.config.list_view_state_store import (
    ListViewStateStoreError,
)
from book_manager.gui.book_manager_application import BookManagerApplication
from book_manager.models.list_view_state import ListViewState


MINIMUM_WIDTHS = {
    "#0": 60,
    "id": 50,
    "title": 160,
    "author": 100,
    "publisher": 100,
    "publication_format": 80,
    "isbn": 110,
    "magazine_code": 90,
    "completion_month": 80,
    "reading_status": 70,
    "is_favorite": 50,
    "rating": 90,
    "tags": 120,
}


def _create_application(
    saved_state: ListViewState | None,
) -> tuple[BookManagerApplication, Mock, Mock]:
    """復元処理の試験に必要な最小構成を作る。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication
    )
    store = Mock()
    store.load.return_value = saved_state
    tree = Mock()

    def column(
        column_id: str,
        option: str | None = None,
        **kwargs: object,
    ) -> object:
        del kwargs
        if option == "minwidth":
            return MINIMUM_WIDTHS[column_id]
        return {}

    tree.column.side_effect = column
    application._list_view_state_store = store
    application._book_tree = tree
    application._sort_type_var = Mock()
    application._sort_direction_var = Mock()
    application._service = Mock()
    return application, store, tree


def test_restore_does_nothing_without_store() -> None:
    """Storeがない場合は既定の表示状態を維持する。"""
    application, store, tree = _create_application(None)
    application._list_view_state_store = None

    application._restore_list_view_state()

    store.load.assert_not_called()
    tree.column.assert_not_called()
    application._sort_type_var.set.assert_not_called()
    application._sort_direction_var.set.assert_not_called()


def test_restore_does_nothing_without_saved_state() -> None:
    """保存状態がない場合は既定の表示状態を維持する。"""
    application, store, tree = _create_application(None)

    application._restore_list_view_state()

    store.load.assert_called_once_with()
    tree.column.assert_not_called()
    application._sort_type_var.set.assert_not_called()
    application._sort_direction_var.set.assert_not_called()


def test_restore_applies_saved_known_column_widths() -> None:
    """保存されている既知列の幅を復元する。"""
    state = ListViewState(
        column_widths={
            "#0": 72,
            "title": 320,
            "author": 210,
        },
        sort_by="registered",
        descending=True,
    )
    application, _, tree = _create_application(state)

    application._restore_list_view_state()

    assert tree.column.call_args_list == [
        call("#0", "minwidth"),
        call("#0", width=72),
        call("title", "minwidth"),
        call("title", width=320),
        call("author", "minwidth"),
        call("author", width=210),
    ]


def test_restore_leaves_unsaved_columns_at_default_width() -> None:
    """保存値がない列には幅を設定しない。"""
    state = ListViewState(
        column_widths={"title": 300},
        sort_by="registered",
        descending=True,
    )
    application, _, tree = _create_application(state)

    application._restore_list_view_state()

    assert tree.column.call_args_list == [
        call("title", "minwidth"),
        call("title", width=300),
    ]


def test_restore_ignores_unknown_saved_column() -> None:
    """現在の一覧に存在しない保存列を無視する。"""
    state = ListViewState(
        column_widths={
            "title": 300,
            "removed_column": 200,
        },
        sort_by="registered",
        descending=True,
    )
    application, _, tree = _create_application(state)

    application._restore_list_view_state()

    assert tree.column.call_args_list == [
        call("title", "minwidth"),
        call("title", width=300),
    ]


def test_restore_clamps_width_to_current_minimum() -> None:
    """保存幅が現在の最小幅未満なら最小幅を適用する。"""
    state = ListViewState(
        column_widths={"title": 1},
        sort_by="registered",
        descending=True,
    )
    application, _, tree = _create_application(state)

    application._restore_list_view_state()

    tree.column.assert_has_calls(
        [
            call("title", "minwidth"),
            call("title", width=160),
        ]
    )


@pytest.mark.parametrize(
    ("sort_by", "expected_label"),
    list(BookManagerApplication.SORT_KEY_TYPE_MAP.items()),
)
def test_restore_applies_supported_sort_key(
    sort_by: str,
    expected_label: str,
) -> None:
    """内部識別子を画面の並び替え表示へ変換する。"""
    state = ListViewState(
        column_widths={},
        sort_by=sort_by,
        descending=True,
    )
    application, _, _ = _create_application(state)

    application._restore_list_view_state()

    application._sort_type_var.set.assert_called_once_with(
        expected_label
    )


@pytest.mark.parametrize(
    ("descending", "expected_direction"),
    [
        (True, "descending"),
        (False, "ascending"),
    ],
)
def test_restore_applies_sort_direction(
    descending: bool,
    expected_direction: str,
) -> None:
    """降順と昇順を画面変数へ復元する。"""
    state = ListViewState(
        column_widths={},
        sort_by="registered",
        descending=descending,
    )
    application, _, _ = _create_application(state)

    application._restore_list_view_state()

    application._sort_direction_var.set.assert_called_once_with(
        expected_direction
    )


def test_restore_does_not_sort_or_load_books_directly() -> None:
    """復元処理自体は再検索や一覧取得を行わない。"""
    state = ListViewState(
        column_widths={},
        sort_by="rating",
        descending=False,
    )
    application, _, _ = _create_application(state)
    application._on_sort_changed = Mock()
    application._load_all_books = Mock()

    application._restore_list_view_state()

    application._on_sort_changed.assert_not_called()
    application._load_all_books.assert_not_called()
    application._service.assert_not_called()


def test_load_all_books_uses_restored_sort_settings() -> None:
    """最初の一覧取得が復元後の並び順を使用する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication
    )
    application._root = Mock()
    application._service = Mock()
    application._service.get_sorted_books.return_value = []
    application._sort_type_var = Mock()
    application._sort_type_var.get.return_value = "評価"
    application._sort_direction_var = Mock()
    application._sort_direction_var.get.return_value = "ascending"
    application._display_books = Mock()

    application._load_all_books()

    application._service.get_sorted_books.assert_called_once_with(
        sort_by="rating",
        descending=False,
    )
    application._display_books.assert_called_once_with(
        [],
        status_prefix="全",
    )


def test_init_restores_state_before_first_book_load() -> None:
    """ウィジェット作成後かつ最初の一覧取得前に復元する。"""
    events: list[str] = []

    def create_widgets(application: BookManagerApplication) -> None:
        events.append("create_widgets")
        application._title_entry = Mock()

    with (
        patch(
            "book_manager.gui.book_manager_application.tk.StringVar",
            return_value=Mock(),
        ),
        patch(
            "book_manager.gui.book_manager_application.tk.BooleanVar",
            return_value=Mock(),
        ),
        patch.object(
            BookManagerApplication,
            "_configure_root",
            side_effect=lambda: events.append("configure_root"),
        ),
        patch.object(
            BookManagerApplication,
            "_create_widgets",
            autospec=True,
            side_effect=create_widgets,
        ),
        patch.object(
            BookManagerApplication,
            "_restore_list_view_state",
            side_effect=lambda: events.append("restore"),
        ),
        patch.object(
            BookManagerApplication,
            "_refresh_tag_options",
            side_effect=lambda: events.append("refresh_tags"),
        ),
        patch.object(
            BookManagerApplication,
            "_load_all_books",
            side_effect=lambda: events.append("load_books"),
        ),
    ):
        BookManagerApplication(
            root=Mock(),
            service=Mock(),
            csv_export_service=Mock(),
            csv_import_service=Mock(),
            backup_service=Mock(),
            reading_history_service=Mock(),
            application_settings_service=Mock(),
            on_google_books_api_key_changed=Mock(),
            window_state_store=Mock(),
            list_view_state_store=Mock(),
        )

    assert events == [
        "configure_root",
        "create_widgets",
        "restore",
        "refresh_tags",
        "load_books",
    ]


def _create_application_for_save() -> tuple[
    BookManagerApplication,
    Mock,
    Mock,
    dict[str, int],
]:
    """終了保存の試験に必要な最小構成を作る。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication
    )
    root = Mock()
    store = Mock()
    column_widths = {
        column_id: 100 + index
        for index, column_id in enumerate(
            ("#0", *BookManagerApplication.TREE_COLUMNS)
        )
    }
    tree = Mock()

    def column(
        column_id: str,
        option: str | None = None,
        **kwargs: object,
    ) -> object:
        del kwargs
        if option == "width":
            return column_widths[column_id]
        return {}

    tree.column.side_effect = column
    application._root = root
    application._list_view_state_store = store
    application._list_view_state_save_suppressed = False
    application._book_tree = tree
    application._sort_type_var = Mock()
    application._sort_type_var.get.return_value = "著者名"
    application._sort_direction_var = Mock()
    application._sort_direction_var.get.return_value = "ascending"
    application._save_window_state_on_exit = Mock()
    return application, root, store, column_widths


def test_exit_saves_current_list_view_state_once() -> None:
    """終了時に全列幅と並び順を一度保存する。"""
    application, root, store, column_widths = (
        _create_application_for_save()
    )

    application._on_exit()

    store.save.assert_called_once_with(
        ListViewState(
            column_widths=column_widths,
            sort_by="author",
            descending=False,
        )
    )
    application._save_window_state_on_exit.assert_called_once_with()
    root.destroy.assert_called_once_with()


def test_save_reads_every_current_tree_column_width() -> None:
    """表紙列を含む現在の全列幅をTreeviewから取得する。"""
    application, _, _, _ = _create_application_for_save()

    application._save_list_view_state_on_exit()

    assert application._book_tree.column.call_args_list == [
        call(column_id, "width")
        for column_id in (
            "#0",
            *BookManagerApplication.TREE_COLUMNS,
        )
    ]


@pytest.mark.parametrize(
    (
        "sort_label",
        "direction",
        "expected_sort_by",
        "expected_descending",
    ),
    [
        ("登録順", "descending", "registered", True),
        ("書籍名", "ascending", "title", False),
        ("評価", "descending", "rating", True),
    ],
)
def test_save_converts_current_sort_settings(
    sort_label: str,
    direction: str,
    expected_sort_by: str,
    expected_descending: bool,
) -> None:
    """現在の画面表示を保存用の並び順へ変換する。"""
    application, _, store, column_widths = (
        _create_application_for_save()
    )
    application._sort_type_var.get.return_value = sort_label
    application._sort_direction_var.get.return_value = direction

    application._save_list_view_state_on_exit()

    store.save.assert_called_once_with(
        ListViewState(
            column_widths=column_widths,
            sort_by=expected_sort_by,
            descending=expected_descending,
        )
    )


def test_exit_does_not_save_list_state_without_store() -> None:
    """Storeがない場合もウィンドウ保存と終了を継続する。"""
    application, root, store, _ = _create_application_for_save()
    application._list_view_state_store = None

    application._on_exit()

    store.save.assert_not_called()
    application._book_tree.column.assert_not_called()
    application._save_window_state_on_exit.assert_called_once_with()
    root.destroy.assert_called_once_with()


def test_exit_does_not_save_list_state_when_suppressed() -> None:
    """初期化後の保存抑止中は状態ファイルを再作成しない。"""
    application, root, store, _ = _create_application_for_save()
    application._list_view_state_save_suppressed = True

    application._on_exit()

    store.save.assert_not_called()
    application._book_tree.column.assert_not_called()
    application._save_window_state_on_exit.assert_called_once_with()
    root.destroy.assert_called_once_with()


def test_exit_continues_when_list_state_save_fails() -> None:
    """一覧状態の保存失敗時も終了処理を継続する。"""
    application, root, store, _ = _create_application_for_save()
    store.save.side_effect = ListViewStateStoreError(
        "save failed"
    )

    with patch(
        "book_manager.gui.book_manager_application.logger.warning"
    ) as warning:
        application._on_exit()

    warning.assert_called_once()
    application._save_window_state_on_exit.assert_called_once_with()
    root.destroy.assert_called_once_with()


def test_exit_continues_when_tree_width_cannot_be_read() -> None:
    """列幅取得失敗時もウィンドウ保存と終了を継続する。"""
    application, root, store, _ = _create_application_for_save()
    application._book_tree.column.side_effect = tk.TclError(
        "tree unavailable"
    )

    with patch(
        "book_manager.gui.book_manager_application.logger.warning"
    ) as warning:
        application._on_exit()

    store.save.assert_not_called()
    warning.assert_called_once()
    application._save_window_state_on_exit.assert_called_once_with()
    root.destroy.assert_called_once_with()
