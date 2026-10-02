"""評価機能のGUIテスト。"""

from unittest.mock import Mock

import pytest

from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)
from book_manager.models.book_item import BookItem


@pytest.mark.parametrize(
    ("rating", "expected"),
    [
        (None, "未評価"),
        (1, "★"),
        (2, "★★"),
        (3, "★★★"),
        (4, "★★★★"),
        (5, "★★★★★"),
    ],
)
def test_rating_labels_convert_internal_value_to_display(
    rating: int | None,
    expected: str,
) -> None:
    """内部評価値をGUI表示文字列へ変換する。"""
    assert (
        BookManagerApplication.RATING_LABELS[rating]
        == expected
    )


@pytest.mark.parametrize(
    ("display_value", "expected"),
    [
        ("未評価", None),
        ("★", 1),
        ("★★", 2),
        ("★★★", 3),
        ("★★★★", 4),
        ("★★★★★", 5),
    ],
)
def test_rating_values_convert_display_to_internal_value(
    display_value: str,
    expected: int | None,
) -> None:
    """GUI表示文字列を内部評価値へ変換する。"""
    assert (
        BookManagerApplication.RATING_VALUES[
            display_value
        ]
        == expected
    )


@pytest.mark.parametrize(
    ("display_value", "expected"),
    [
        ("未評価", None),
        ("★", 1),
        ("★★", 2),
        ("★★★", 3),
        ("★★★★", 4),
        ("★★★★★", 5),
    ],
)
def test_get_form_values_converts_rating(
    display_value: str,
    expected: int | None,
) -> None:
    """フォームの評価表示を内部評価値へ変換する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )

    application._title_var = Mock()
    application._title_var.get.return_value = "テスト書籍"

    application._isbn_var = Mock()
    application._reference_isbn_var = Mock()
    application._reference_isbn_var.get.return_value = ""
    application._isbn_var.get.return_value = ""

    application._magazine_code_var = Mock()
    application._magazine_code_var.get.return_value = ""

    application._author_var = Mock()
    application._author_var.get.return_value = ""

    application._publisher_var = Mock()
    application._publisher_var.get.return_value = ""

    application._publication_format_var = Mock()
    application._publication_format_var.get.return_value = ""

    application._completion_month_var = Mock()
    application._completion_month_var.get.return_value = ""

    application._reading_status_var = Mock()
    application._reading_status_var.get.return_value = (
        "未設定"
    )

    application._is_favorite_var = Mock()
    application._is_favorite_var.get.return_value = False

    application._rating_var = Mock()
    application._tags_var = Mock()
    application._tags_var.get.return_value = ""
    application._rating_var.get.return_value = (
        display_value
    )

    application._description_text = Mock()
    application._description_text.get.return_value = ""

    application._notes_text = Mock()
    application._notes_text.get.return_value = ""

    application._current_cover_image_url = None
    application._current_cover_image_path = None

    values = application._get_form_values()

    assert values["rating"] == expected


def test_create_book_item_from_form_sets_rating() -> None:
    """フォームの評価値をBookItemへ設定する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )

    application._get_form_values = Mock(
        return_value={
            "title": "テスト書籍",
            "isbn": None,
            "reference_isbn": None,
            "magazine_code": None,
            "author": None,
            "publisher": None,
            "publication_format": None,
            "description": None,
            "cover_image_url": None,
            "cover_image_path": None,
            "completion_month": None,
            "reading_status": None,
            "is_favorite": False,
            "rating": 5,
            "tags": (),
            "notes": None,
        },
    )

    book = application._create_book_item_from_form()

    assert book.rating == 5


@pytest.mark.parametrize(
    ("rating", "expected"),
    [
        (1, "★"),
        (2, "★★"),
        (3, "★★★"),
        (4, "★★★★"),
        (5, "★★★★★"),
    ],
)
def test_display_book_in_form_sets_rating(
    rating: int,
    expected: str,
) -> None:
    """書籍選択時に評価を星表示へ変換する。"""
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
        rating=rating,
    )

    application._display_book_in_form(
        book,
    )

    application._rating_var.set.assert_called_once_with(
        expected,
    )


def test_display_book_in_form_sets_unrated() -> None:
    """未評価の書籍を「未評価」と表示する。"""
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
        rating=None,
    )

    application._display_book_in_form(
        book,
    )

    application._rating_var.set.assert_called_once_with(
        "未評価",
    )


def test_clear_form_resets_rating() -> None:
    """フォームクリア時に評価を未評価へ戻す。"""
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

    application._rating_var.set.assert_called_once_with(
        "未評価",
    )


@pytest.mark.parametrize(
    ("rating", "expected"),
    [
        (1, "★"),
        (2, "★★"),
        (3, "★★★"),
        (4, "★★★★"),
        (5, "★★★★★"),
    ],
)
def test_display_books_shows_rating(
    rating: int,
    expected: str,
) -> None:
    """一覧へ評価を星印で表示する。"""
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
        rating=rating,
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

    assert values[-2] == expected


def test_display_books_shows_empty_string_for_unrated() -> None:
    """一覧では未評価を書かず空欄で表示する。"""
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
        rating=None,
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

    assert values[-2] == ""
