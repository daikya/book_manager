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
    application._search_reading_status_var = Mock()
    application._search_favorite_var = Mock()
    application._search_rating_var = Mock()
    application._search_tag_var = Mock()
    application._search_tag_var.get.return_value = "すべて"

    return application


def test_get_filtered_books_passes_all_search_conditions() -> None:
    """8つの検索条件をServiceへ渡す。"""
    application = create_application()

    application._search_title_var.get.return_value = "書籍名"
    application._search_author_var.get.return_value = "著者名"
    application._search_publisher_var.get.return_value = "出版社"
    application._search_isbn_var.get.return_value = "ISBN"
    application._search_magazine_code_var.get.return_value = (
        "雑誌コード"
    )
    application._search_reading_status_var.get.return_value = (
        "読了"
    )
    application._search_favorite_var.get.return_value = (
        "お気に入りのみ"
    )
    application._search_rating_var.get.return_value = (
        "★3以上"
    )
    application._search_tag_var.get.return_value = "技術書"

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
        reading_status_filter="completed",
        favorite_filter="favorite",
        rating_filter=3,
        tag_name="技術書",
        untagged_only=False,
    )


def test_has_search_conditions_returns_false_when_all_blank() -> None:
    """すべての検索条件が初期状態ならFalseを返す。"""
    application = create_application()

    application._search_title_var.get.return_value = ""
    application._search_author_var.get.return_value = " "
    application._search_publisher_var.get.return_value = ""
    application._search_isbn_var.get.return_value = "   "
    application._search_magazine_code_var.get.return_value = ""
    application._search_reading_status_var.get.return_value = (
        "すべて"
    )
    application._search_favorite_var.get.return_value = (
        "すべて"
    )
    application._search_rating_var.get.return_value = (
        "すべて"
    )

    assert application._has_search_conditions() is False


def test_has_search_conditions_returns_true_when_condition_exists() -> None:
    """検索条件が1つ以上入力されていればTrueを返す。"""
    application = create_application()

    application._search_title_var.get.return_value = ""
    application._search_author_var.get.return_value = "村上"
    application._search_publisher_var.get.return_value = ""
    application._search_isbn_var.get.return_value = ""
    application._search_magazine_code_var.get.return_value = ""
    application._search_reading_status_var.get.return_value = (
        "すべて"
    )
    application._search_favorite_var.get.return_value = (
        "すべて"
    )
    application._search_rating_var.get.return_value = (
        "すべて"
    )

    assert application._has_search_conditions() is True


def test_has_search_conditions_returns_true_for_reading_status() -> None:
    """読書状態だけ指定されていてもTrueを返す。"""
    application = create_application()

    application._search_title_var.get.return_value = ""
    application._search_author_var.get.return_value = ""
    application._search_publisher_var.get.return_value = ""
    application._search_isbn_var.get.return_value = ""
    application._search_magazine_code_var.get.return_value = ""
    application._search_reading_status_var.get.return_value = (
        "読了"
    )
    application._search_favorite_var.get.return_value = (
        "すべて"
    )
    application._search_rating_var.get.return_value = (
        "すべて"
    )

    assert application._has_search_conditions() is True


def test_has_search_conditions_returns_true_for_favorite() -> None:
    """お気に入りだけ指定されていてもTrueを返す。"""
    application = create_application()

    application._search_title_var.get.return_value = ""
    application._search_author_var.get.return_value = ""
    application._search_publisher_var.get.return_value = ""
    application._search_isbn_var.get.return_value = ""
    application._search_magazine_code_var.get.return_value = ""
    application._search_reading_status_var.get.return_value = (
        "すべて"
    )
    application._search_favorite_var.get.return_value = (
        "お気に入りのみ"
    )
    application._search_rating_var.get.return_value = (
        "すべて"
    )

    assert application._has_search_conditions() is True


def test_has_search_conditions_returns_true_for_rating() -> None:
    """評価だけ指定されていてもTrueを返す。"""
    application = create_application()

    application._search_title_var.get.return_value = ""
    application._search_author_var.get.return_value = ""
    application._search_publisher_var.get.return_value = ""
    application._search_isbn_var.get.return_value = ""
    application._search_magazine_code_var.get.return_value = ""
    application._search_reading_status_var.get.return_value = (
        "すべて"
    )
    application._search_favorite_var.get.return_value = (
        "すべて"
    )
    application._search_rating_var.get.return_value = (
        "★4以上"
    )

    assert application._has_search_conditions() is True


def test_clear_search_clears_all_conditions_and_loads_all_books() -> None:
    """検索条件クリアで全条件を初期状態にして全件表示する。"""
    application = create_application()

    application._load_all_books = Mock()
    application._search_title_entry = Mock()

    application._on_clear_search()

    application._search_title_var.set.assert_called_once_with("")
    application._search_author_var.set.assert_called_once_with("")
    application._search_publisher_var.set.assert_called_once_with("")
    application._search_isbn_var.set.assert_called_once_with("")
    application._search_magazine_code_var.set.assert_called_once_with("")
    application._search_reading_status_var.set.assert_called_once_with(
        "すべて"
    )
    application._search_favorite_var.set.assert_called_once_with(
        "すべて"
    )
    application._search_rating_var.set.assert_called_once_with(
        "すべて"
    )
    application._search_tag_var.set.assert_called_once_with(
        "すべて"
    )

    application._load_all_books.assert_called_once_with()
    application._search_title_entry.focus_set.assert_called_once_with()


def test_get_filtered_books_converts_all_filters_to_none() -> None:
    """すべてを選択した絞り込み条件はNoneとしてServiceへ渡す。"""
    application = create_application()

    application._search_title_var.get.return_value = ""
    application._search_author_var.get.return_value = ""
    application._search_publisher_var.get.return_value = ""
    application._search_isbn_var.get.return_value = ""
    application._search_magazine_code_var.get.return_value = ""
    application._search_reading_status_var.get.return_value = (
        "すべて"
    )
    application._search_favorite_var.get.return_value = (
        "すべて"
    )
    application._search_rating_var.get.return_value = (
        "すべて"
    )

    application._service.search_books.return_value = []

    application._get_filtered_books()

    application._service.search_books.assert_called_once_with(
        title="",
        author="",
        publisher="",
        isbn="",
        magazine_code="",
        reading_status_filter=None,
        favorite_filter=None,
        rating_filter=None,
        tag_name=None,
        untagged_only=False,
    )


def test_get_filtered_books_converts_unset_reading_status() -> None:
    """未設定の読書状態をService用の値へ変換する。"""
    application = create_application()

    application._search_title_var.get.return_value = ""
    application._search_author_var.get.return_value = ""
    application._search_publisher_var.get.return_value = ""
    application._search_isbn_var.get.return_value = ""
    application._search_magazine_code_var.get.return_value = ""
    application._search_reading_status_var.get.return_value = (
        "未設定"
    )
    application._search_favorite_var.get.return_value = (
        "すべて"
    )
    application._search_rating_var.get.return_value = (
        "すべて"
    )

    application._service.search_books.return_value = []

    application._get_filtered_books()

    application._service.search_books.assert_called_once_with(
        title="",
        author="",
        publisher="",
        isbn="",
        magazine_code="",
        reading_status_filter="unset",
        favorite_filter=None,
        rating_filter=None,
        tag_name=None,
        untagged_only=False,
    )


def test_get_filtered_books_converts_non_favorite_filter() -> None:
    """お気に入り以外をService用の値へ変換する。"""
    application = create_application()

    application._search_title_var.get.return_value = ""
    application._search_author_var.get.return_value = ""
    application._search_publisher_var.get.return_value = ""
    application._search_isbn_var.get.return_value = ""
    application._search_magazine_code_var.get.return_value = ""
    application._search_reading_status_var.get.return_value = (
        "すべて"
    )
    application._search_favorite_var.get.return_value = (
        "お気に入り以外"
    )
    application._search_rating_var.get.return_value = (
        "すべて"
    )

    application._service.search_books.return_value = []

    application._get_filtered_books()

    application._service.search_books.assert_called_once_with(
        title="",
        author="",
        publisher="",
        isbn="",
        magazine_code="",
        reading_status_filter=None,
        favorite_filter="not_favorite",
        rating_filter=None,
        tag_name=None,
        untagged_only=False,
    )


def test_get_filtered_books_converts_unrated_filter() -> None:
    """未評価をService用の値へ変換する。"""
    application = create_application()

    application._search_title_var.get.return_value = ""
    application._search_author_var.get.return_value = ""
    application._search_publisher_var.get.return_value = ""
    application._search_isbn_var.get.return_value = ""
    application._search_magazine_code_var.get.return_value = ""
    application._search_reading_status_var.get.return_value = (
        "すべて"
    )
    application._search_favorite_var.get.return_value = (
        "すべて"
    )
    application._search_rating_var.get.return_value = (
        "未評価"
    )

    application._service.search_books.return_value = []

    application._get_filtered_books()

    application._service.search_books.assert_called_once_with(
        title="",
        author="",
        publisher="",
        isbn="",
        magazine_code="",
        reading_status_filter=None,
        favorite_filter=None,
        rating_filter="unrated",
        tag_name=None,
        untagged_only=False,
    )


def test_get_filtered_books_converts_untagged_filter() -> None:
    """タグ未設定を専用の検索条件へ変換する。"""
    application = create_application()
    application._search_title_var.get.return_value = ""
    application._search_author_var.get.return_value = ""
    application._search_publisher_var.get.return_value = ""
    application._search_isbn_var.get.return_value = ""
    application._search_magazine_code_var.get.return_value = ""
    application._search_reading_status_var.get.return_value = "すべて"
    application._search_favorite_var.get.return_value = "すべて"
    application._search_rating_var.get.return_value = "すべて"
    application._search_tag_var.get.return_value = "タグ未設定"
    application._service.search_books.return_value = []

    application._get_filtered_books()

    application._service.search_books.assert_called_once_with(
        title="",
        author="",
        publisher="",
        isbn="",
        magazine_code="",
        reading_status_filter=None,
        favorite_filter=None,
        rating_filter=None,
        tag_name=None,
        untagged_only=True,
    )


def test_has_search_conditions_returns_true_for_tag() -> None:
    """タグだけ指定されていても検索条件ありと判定する。"""
    application = create_application()
    application._search_title_var.get.return_value = ""
    application._search_author_var.get.return_value = ""
    application._search_publisher_var.get.return_value = ""
    application._search_isbn_var.get.return_value = ""
    application._search_magazine_code_var.get.return_value = ""
    application._search_reading_status_var.get.return_value = "すべて"
    application._search_favorite_var.get.return_value = "すべて"
    application._search_rating_var.get.return_value = "すべて"
    application._search_tag_var.get.return_value = "小説"

    assert application._has_search_conditions() is True
