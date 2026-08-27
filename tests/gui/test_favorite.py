"""お気に入り機能に関するGUIロジックのテスト。"""

from unittest.mock import Mock

from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)
from book_manager.models.book_item import BookItem


def create_form_application(
    *,
    is_favorite: bool = False,
) -> BookManagerApplication:
    """フォーム値取得用のApplicationを作成する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )

    application._title_var = Mock()
    application._isbn_var = Mock()
    application._magazine_code_var = Mock()
    application._author_var = Mock()
    application._publisher_var = Mock()
    application._publication_format_var = Mock()
    application._completion_month_var = Mock()
    application._reading_status_var = Mock()
    application._is_favorite_var = Mock()

    application._title_var.get.return_value = "テスト書籍"
    application._isbn_var.get.return_value = ""
    application._magazine_code_var.get.return_value = ""
    application._author_var.get.return_value = ""
    application._publisher_var.get.return_value = ""
    application._publication_format_var.get.return_value = ""
    application._completion_month_var.get.return_value = ""
    application._reading_status_var.get.return_value = "未設定"
    application._is_favorite_var.get.return_value = is_favorite

    application._description_text = Mock()
    application._description_text.get.return_value = ""

    application._notes_text = Mock()
    application._notes_text.get.return_value = ""

    application._current_cover_image_url = None
    application._current_cover_image_path = None

    return application


def test_get_form_values_returns_false_is_favorite() -> None:
    """お気に入りOFFをFalseとして取得できる。"""
    application = create_form_application(
        is_favorite=False,
    )

    values = application._get_form_values()

    assert values["is_favorite"] is False


def test_get_form_values_returns_true_is_favorite() -> None:
    """お気に入りONをTrueとして取得できる。"""
    application = create_form_application(
        is_favorite=True,
    )

    values = application._get_form_values()

    assert values["is_favorite"] is True


def test_create_book_item_from_form_sets_is_favorite() -> None:
    """フォームから作成したBookItemへお気に入り状態を設定する。"""
    application = create_form_application(
        is_favorite=True,
    )

    book_item = application._create_book_item_from_form()

    assert book_item.is_favorite is True


def test_display_book_in_form_sets_true_is_favorite() -> None:
    """書籍選択時にお気に入りONをフォームへ反映する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )

    application._title_var = Mock()
    application._isbn_var = Mock()
    application._magazine_code_var = Mock()
    application._author_var = Mock()
    application._publisher_var = Mock()
    application._publication_format_var = Mock()
    application._completion_month_var = Mock()
    application._reading_status_var = Mock()
    application._is_favorite_var = Mock()

    application._description_text = Mock()
    application._notes_text = Mock()

    application._replace_text = Mock()
    application._set_edit_buttons_enabled = Mock()
    application._edit_status_var = Mock()
    application._display_saved_cover_image = Mock()

    book = BookItem(
        id=1,
        title="お気に入り書籍",
        is_favorite=True,
    )

    application._display_book_in_form(
        book,
    )

    application._is_favorite_var.set.assert_called_once_with(
        True,
    )


def test_display_book_in_form_sets_false_is_favorite() -> None:
    """書籍選択時にお気に入りOFFをフォームへ反映する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )

    application._title_var = Mock()
    application._isbn_var = Mock()
    application._magazine_code_var = Mock()
    application._author_var = Mock()
    application._publisher_var = Mock()
    application._publication_format_var = Mock()
    application._completion_month_var = Mock()
    application._reading_status_var = Mock()
    application._is_favorite_var = Mock()

    application._description_text = Mock()
    application._notes_text = Mock()

    application._replace_text = Mock()
    application._set_edit_buttons_enabled = Mock()
    application._edit_status_var = Mock()
    application._display_saved_cover_image = Mock()

    book = BookItem(
        id=1,
        title="通常書籍",
        is_favorite=False,
    )

    application._display_book_in_form(
        book,
    )

    application._is_favorite_var.set.assert_called_once_with(
        False,
    )


def test_clear_form_resets_is_favorite() -> None:
    """フォームクリア時にお気に入りをOFFへ戻す。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )

    application._title_var = Mock()
    application._isbn_var = Mock()
    application._magazine_code_var = Mock()
    application._author_var = Mock()
    application._publisher_var = Mock()
    application._publication_format_var = Mock()
    application._completion_month_var = Mock()
    application._reading_status_var = Mock()
    application._is_favorite_var = Mock()

    application._description_text = Mock()
    application._notes_text = Mock()
    application._book_tree = Mock()
    application._book_tree.selection.return_value = ()

    application._edit_status_var = Mock()
    application._set_edit_buttons_enabled = Mock()
    application._clear_cover_state = Mock()

    application._clear_form()

    application._is_favorite_var.set.assert_called_once_with(
        False,
    )


def test_display_books_shows_star_for_favorite() -> None:
    """一覧でお気に入りONを星印として表示する。"""
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
        title="お気に入り書籍",
        is_favorite=True,
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

    assert values[-1] == "★"


def test_display_books_shows_empty_string_for_non_favorite() -> None:
    """一覧でお気に入りOFFを空欄として表示する。"""
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
        title="通常書籍",
        is_favorite=False,
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

    assert values[-1] == ""