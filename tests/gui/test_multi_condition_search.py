"""複合条件検索に関するGUIロジックのテスト。"""

from unittest.mock import Mock

from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)


def create_application() -> BookManagerApplication:
    """テスト用のBookManagerApplicationを作成する。"""
    application = BookManagerApplication.__new__(
        BookManagerApplication,
    )

    application._service = Mock()

    application._search_title_var = Mock()
    application._search_author_var = Mock()
    application._search_publisher_var = Mock()
    application._search_isbn_var = Mock()
    application._search_magazine_code_var = Mock()

    return application


def test_get_filtered_books_passes_all_search_conditions() -> None:
    """5つの検索条件をServiceへ渡す。"""
    application = create_application()

    application._search_title_var.get.return_value = "書籍名"
    application._search_author_var.get.return_value = "著者名"
    application._search_publisher_var.get.return_value = "出版社"
    application._search_isbn_var.get.return_value = "ISBN"
    application._search_magazine_code_var.get.return_value = (
        "雑誌コード"
    )

    expected = [
        Mock(),
    ]
    application._service.search_books.return_value = expected

    result = application._get_filtered_books()

    assert result == expected

    application._service.search_books.assert_called_once_with(
        title="書籍名",
        author="著者名",
        publisher="出版社",
        isbn="ISBN",
        magazine_code="雑誌コード",
    )


def test_has_search_conditions_returns_false_when_all_blank() -> None:
    """すべての検索条件が空欄ならFalseを返す。"""
    application = create_application()

    application._search_title_var.get.return_value = ""
    application._search_author_var.get.return_value = " "
    application._search_publisher_var.get.return_value = ""
    application._search_isbn_var.get.return_value = "   "
    application._search_magazine_code_var.get.return_value = ""

    assert application._has_search_conditions() is False


def test_has_search_conditions_returns_true_when_condition_exists() -> None:
    """検索条件が1つ以上入力されていればTrueを返す。"""
    application = create_application()

    application._search_title_var.get.return_value = ""
    application._search_author_var.get.return_value = "村上"
    application._search_publisher_var.get.return_value = ""
    application._search_isbn_var.get.return_value = ""
    application._search_magazine_code_var.get.return_value = ""

    assert application._has_search_conditions() is True


def test_clear_search_clears_all_conditions_and_loads_all_books() -> None:
    """検索条件クリアで全条件を空欄にして全件表示する。"""
    application = create_application()

    application._load_all_books = Mock()
    application._search_title_entry = Mock()

    application._on_clear_search()

    application._search_title_var.set.assert_called_once_with("")
    application._search_author_var.set.assert_called_once_with("")
    application._search_publisher_var.set.assert_called_once_with("")
    application._search_isbn_var.set.assert_called_once_with("")
    application._search_magazine_code_var.set.assert_called_once_with("")

    application._load_all_books.assert_called_once_with()
    application._search_title_entry.focus_set.assert_called_once_with()