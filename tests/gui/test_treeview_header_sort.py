"""Treeviewヘッダークリックソートのテスト。"""

from unittest.mock import Mock

import pytest

from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)


def _create_application_stub() -> BookManagerApplication:
    """ヘッダーソート用の最小限のApplicationを作成する。"""
    app = BookManagerApplication.__new__(
        BookManagerApplication,
    )

    app._sort_type_var = Mock()
    app._sort_direction_var = Mock()
    app._on_sort_changed = Mock()

    return app


def test_heading_click_changes_to_ascending_for_new_sort_type() -> None:
    """別の列をクリックした場合は昇順にする。"""
    app = _create_application_stub()

    app._sort_type_var.get.return_value = "登録順"
    app._sort_direction_var.get.return_value = "descending"

    app._on_tree_heading_click(
        "title",
    )

    app._sort_type_var.set.assert_called_once_with(
        "書籍名",
    )
    app._sort_direction_var.set.assert_called_once_with(
        "ascending",
    )
    app._on_sort_changed.assert_called_once_with()


def test_heading_click_toggles_ascending_to_descending() -> None:
    """同じ列を再クリックすると昇順から降順へ切り替える。"""
    app = _create_application_stub()

    app._sort_type_var.get.return_value = "書籍名"
    app._sort_direction_var.get.return_value = "ascending"

    app._on_tree_heading_click(
        "title",
    )

    app._sort_type_var.set.assert_called_once_with(
        "書籍名",
    )
    app._sort_direction_var.set.assert_called_once_with(
        "descending",
    )
    app._on_sort_changed.assert_called_once_with()


def test_heading_click_toggles_descending_to_ascending() -> None:
    """同じ列を再クリックすると降順から昇順へ切り替える。"""
    app = _create_application_stub()

    app._sort_type_var.get.return_value = "書籍名"
    app._sort_direction_var.get.return_value = "descending"

    app._on_tree_heading_click(
        "title",
    )

    app._sort_type_var.set.assert_called_once_with(
        "書籍名",
    )
    app._sort_direction_var.set.assert_called_once_with(
        "ascending",
    )
    app._on_sort_changed.assert_called_once_with()


def test_heading_click_ignores_unsupported_column() -> None:
    """対象外列ではソート状態を変更しない。"""
    app = _create_application_stub()

    app._on_tree_heading_click(
        "isbn",
    )

    app._sort_type_var.set.assert_not_called()
    app._sort_direction_var.set.assert_not_called()
    app._on_sort_changed.assert_not_called()


def test_sort_types_include_reading_information() -> None:
    """並べ替え選択肢に読書情報の3項目を含める。"""
    assert BookManagerApplication.SORT_TYPES[-3:] == (
        "読書状態",
        "お気に入り",
        "評価",
    )


@pytest.mark.parametrize(
    ("display_name", "sort_by"),
    [
        (
            "読書状態",
            "reading_status",
        ),
        (
            "お気に入り",
            "is_favorite",
        ),
        (
            "評価",
            "rating",
        ),
    ],
)
def test_get_sort_settings_maps_reading_information(
    display_name: str,
    sort_by: str,
) -> None:
    """読書情報の表示名をService用識別子へ変換する。"""
    app = _create_application_stub()

    app._sort_type_var.get.return_value = display_name
    app._sort_direction_var.get.return_value = "ascending"

    result = app._get_sort_settings()

    assert result == (
        sort_by,
        False,
    )


@pytest.mark.parametrize(
    ("column_name", "display_name"),
    [
        (
            "reading_status",
            "読書状態",
        ),
        (
            "is_favorite",
            "お気に入り",
        ),
        (
            "rating",
            "評価",
        ),
    ],
)
def test_heading_click_supports_reading_information(
    column_name: str,
    display_name: str,
) -> None:
    """読書情報の列見出しから並べ替えを開始する。"""
    app = _create_application_stub()

    app._sort_type_var.get.return_value = "登録順"
    app._sort_direction_var.get.return_value = "descending"

    app._on_tree_heading_click(
        column_name,
    )

    app._sort_type_var.set.assert_called_once_with(
        display_name,
    )
    app._sort_direction_var.set.assert_called_once_with(
        "ascending",
    )
    app._on_sort_changed.assert_called_once_with()
