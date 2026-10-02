"""読書ステータス管理に関するGUIロジックのテスト。"""

from unittest.mock import Mock

import pytest

from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)
from book_manager.models.book_item import BookItem


@pytest.mark.parametrize(
    (
        "reading_status",
        "expected",
    ),
    [
        (None, "未設定"),
        ("unread", "未読"),
        ("reading", "読書中"),
        ("completed", "読了"),
    ],
)
def test_reading_status_labels_convert_internal_value_to_display(
    reading_status: str | None,
    expected: str,
) -> None:
    """内部値をGUI表示値へ変換できる。"""
    assert (
        BookManagerApplication.READING_STATUS_LABELS[
            reading_status
        ]
        == expected
    )


@pytest.mark.parametrize(
    (
        "display_value",
        "expected",
    ),
    [
        ("未設定", None),
        ("未読", "unread"),
        ("読書中", "reading"),
        ("読了", "completed"),
    ],
)
def test_reading_status_values_convert_display_to_internal_value(
    display_value: str,
    expected: str | None,
) -> None:
    """GUI表示値を内部値へ変換できる。"""
    assert (
        BookManagerApplication.READING_STATUS_VALUES[
            display_value
        ]
        == expected
    )


def create_form_application(
    *,
    reading_status: str = "未設定",
) -> BookManagerApplication:
    """フォーム値取得用のApplicationを作成する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )

    application._title_var = Mock()
    application._isbn_var = Mock()
    application._reference_isbn_var = Mock()
    application._reference_isbn_var.get.return_value = ""
    application._magazine_code_var = Mock()
    application._author_var = Mock()
    application._publisher_var = Mock()
    application._publication_format_var = Mock()
    application._completion_month_var = Mock()
    application._reading_status_var = Mock()
    application._is_favorite_var = Mock()
    application._rating_var = Mock()
    application._tags_var = Mock()
    application._tags_var.get.return_value = ""
    application._title_var.get.return_value = "テスト書籍"
    application._isbn_var.get.return_value = ""
    application._magazine_code_var.get.return_value = ""
    application._author_var.get.return_value = ""
    application._publisher_var.get.return_value = ""
    application._publication_format_var.get.return_value = ""
    application._completion_month_var.get.return_value = ""
    application._reading_status_var.get.return_value = (
        reading_status
    )
    application._is_favorite_var.get.return_value = False
    application._description_text = Mock()
    application._description_text.get.return_value = ""

    application._notes_text = Mock()
    application._notes_text.get.return_value = ""

    application._current_cover_image_url = None
    application._current_cover_image_path = None

    return application


@pytest.mark.parametrize(
    (
        "display_value",
        "expected",
    ),
    [
        ("未設定", None),
        ("未読", "unread"),
        ("読書中", "reading"),
        ("読了", "completed"),
    ],
)
def test_get_form_values_converts_reading_status(
    display_value: str,
    expected: str | None,
) -> None:
    """フォーム取得時に読書状態を内部値へ変換する。"""
    application = create_form_application(
        reading_status=display_value,
    )

    values = application._get_form_values()

    assert values["reading_status"] == expected


def test_create_book_item_from_form_sets_reading_status() -> None:
    """フォームから作成したBookItemへ読書状態を設定する。"""
    application = create_form_application(
        reading_status="読書中",
    )

    book_item = application._create_book_item_from_form()

    assert book_item.reading_status == "reading"


def test_display_book_in_form_sets_reading_status() -> None:
    """書籍選択時に読書状態を日本語表示へ変換する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )

    application._title_var = Mock()
    application._isbn_var = Mock()
    application._reference_isbn_var = Mock()
    application._reference_isbn_var.get.return_value = ""
    application._magazine_code_var = Mock()
    application._author_var = Mock()
    application._publisher_var = Mock()
    application._publication_format_var = Mock()
    application._completion_month_var = Mock()
    application._reading_status_var = Mock()
    application._is_favorite_var = Mock()
    application._rating_var = Mock()
    application._tags_var = Mock()
    application._tags_var.get.return_value = ""
    application._description_text = Mock()
    application._notes_text = Mock()

    application._replace_text = Mock()
    application._set_edit_buttons_enabled = Mock()
    application._edit_status_var = Mock()
    application._display_saved_cover_image = Mock()

    book = BookItem(
        id=1,
        title="テスト書籍",
        reading_status="reading",
    )

    application._display_book_in_form(
        book,
    )

    application._reading_status_var.set.assert_called_once_with(
        "読書中",
    )


def test_display_book_in_form_sets_unconfigured_status() -> None:
    """未設定の読書状態を「未設定」と表示する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )

    application._title_var = Mock()
    application._isbn_var = Mock()
    application._reference_isbn_var = Mock()
    application._reference_isbn_var.get.return_value = ""
    application._magazine_code_var = Mock()
    application._author_var = Mock()
    application._publisher_var = Mock()
    application._publication_format_var = Mock()
    application._completion_month_var = Mock()
    application._reading_status_var = Mock()
    application._is_favorite_var = Mock()
    application._rating_var = Mock()
    application._tags_var = Mock()
    application._tags_var.get.return_value = ""
    application._description_text = Mock()
    application._notes_text = Mock()

    application._replace_text = Mock()
    application._set_edit_buttons_enabled = Mock()
    application._edit_status_var = Mock()
    application._display_saved_cover_image = Mock()

    book = BookItem(
        id=1,
        title="テスト書籍",
        reading_status=None,
    )

    application._display_book_in_form(
        book,
    )

    application._reading_status_var.set.assert_called_once_with(
        "未設定",
    )


def test_clear_form_resets_reading_status() -> None:
    """フォームクリア時に読書状態を未設定へ戻す。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )

    application._title_var = Mock()
    application._isbn_var = Mock()
    application._reference_isbn_var = Mock()
    application._reference_isbn_var.get.return_value = ""
    application._magazine_code_var = Mock()
    application._author_var = Mock()
    application._publisher_var = Mock()
    application._publication_format_var = Mock()
    application._completion_month_var = Mock()
    application._reading_status_var = Mock()
    application._is_favorite_var = Mock()
    application._rating_var = Mock()
    application._tags_var = Mock()
    application._tags_var.get.return_value = ""
    application._description_text = Mock()
    application._notes_text = Mock()
    application._book_tree = Mock()
    application._book_tree.selection.return_value = ()

    application._edit_status_var = Mock()
    application._set_edit_buttons_enabled = Mock()
    application._clear_cover_state = Mock()

    application._clear_form()

    application._reading_status_var.set.assert_called_once_with(
        "未設定",
    )


def test_display_books_shows_reading_status_in_japanese() -> None:
    """一覧へ読書状態を日本語で表示する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )

    application._book_tree = Mock()
    application._book_tree.get_children.return_value = ()

    application._thumbnail_photos = {}
    application._create_thumbnail_photo = Mock(
        return_value=None,
    )
    application._count_status_var = Mock()

    book = BookItem(
        id=1,
        title="テスト書籍",
        reading_status="completed",
    )

    application._display_books(
        [book],
        status_prefix="全",
    )

    values = (
        application._book_tree.insert.call_args.kwargs[
            "values"
        ]
    )

    assert values[-4] == "読了"