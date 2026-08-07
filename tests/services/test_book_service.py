"""Tests for BookService."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest

from book_manager.database.initializer import (
    initialize_database,
)
from book_manager.models.book_item import BookItem
from book_manager.repositories.book_repository import (
    BookRepository,
)
from book_manager.services.book_service import BookService
from book_manager.metadata.exceptions import (
    BookMetadataConfigurationError,
)
from book_manager.models.fetched_book_data import (
    FetchedBookData,
)

FIXED_NOW = datetime(
    2026,
    7,
    22,
    10,
    30,
    0,
)

UPDATED_NOW = datetime(
    2026,
    7,
    23,
    11,
    45,
    30,
)

class FakeBookMetadataService:
    """BookServiceテスト用の外部書誌情報取得Service。"""

    def __init__(
        self,
        result: FetchedBookData,
    ) -> None:
        self._result = result
        self.calls: list[str] = []

    def fetch_by_isbn(
        self,
        isbn: str,
    ) -> FetchedBookData:
        """呼び出しISBNを記録して固定結果を返す。"""
        self.calls.append(isbn)

        return self._result
class FakeCoverImageService:
    """BookServiceテスト用の表紙画像取得Service。"""

    def __init__(
        self,
        result: Path,
    ) -> None:
        self._result = result
        self.calls: list[str] = []

    def fetch(
        self,
        image_url: str,
    ) -> Path:
        """呼び出しURLを記録して固定パスを返す。"""
        self.calls.append(image_url)

        return self._result

@pytest.fixture
def repository(
    tmp_path: Path,
) -> BookRepository:
    """テスト用Repositoryを生成する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    return BookRepository(database_path)


@pytest.fixture
def service(
    repository: BookRepository,
) -> BookService:
    """固定日時を使用するBookServiceを生成する。"""
    return BookService(
        repository,
        now_provider=lambda: FIXED_NOW,
    )


def add_sample_book(
    service: BookService,
    *,
    title: str = "吾輩は猫である",
    author: str | None = "夏目漱石",
    publisher: str | None = "新潮社",
    isbn: str | None = "9784101010014",
    magazine_code: str | None = None,
    cover_image_url: str | None = (
        "https://example.com/cover.jpg"
    ),
    cover_image_path: str | None = (
        "cache/covers/cover.jpg"
    ),
) -> BookItem:
    """テスト用の書籍を登録する。"""
    return service.add_book(
        title=title,
        isbn=isbn,
        magazine_code=magazine_code,
        author=author,
        publisher=publisher,
        publication_format="文庫",
        description="猫の視点から描かれた小説。",
        cover_image_url=cover_image_url,
        cover_image_path=cover_image_path,
        completion_month="2026-07",
        notes="テスト用データ",
    )


def test_add_book_registers_book(
    service: BookService,
) -> None:
    registered = add_sample_book(service)

    assert registered.id is not None
    assert registered.title == "吾輩は猫である"
    assert registered.isbn == "9784101010014"
    assert (
        registered.cover_image_url
        == "https://example.com/cover.jpg"
    )
    assert (
        registered.cover_image_path
        == "cache/covers/cover.jpg"
    )

def test_add_book_sets_created_and_updated_at(
    service: BookService,
) -> None:
    registered = add_sample_book(service)

    assert registered.created_at == "2026-07-22 10:30:00"
    assert registered.updated_at == "2026-07-22 10:30:00"
    assert registered.created_at == registered.updated_at


def test_add_book_normalizes_title(
    service: BookService,
) -> None:
    registered = service.add_book(
        title="  吾輩は猫である  ",
    )

    assert registered.title == "吾輩は猫である"


def test_add_book_normalizes_optional_text(
    service: BookService,
) -> None:
    registered = service.add_book(
        title="テスト書籍",
        author="  著者名  ",
        publisher="  出版社名  ",
        publication_format="  文庫  ",
        description="  内容紹介  ",
        cover_image_url="  https://example.com/cover.jpg  ",
        cover_image_path="  cache/covers/cover.jpg  ",
        completion_month="  2026-07  ",
        notes="  備考  ",
    )

    assert registered.author == "著者名"
    assert registered.publisher == "出版社名"
    assert registered.publication_format == "文庫"
    assert registered.description == "内容紹介"
    assert (
        registered.cover_image_url
        == "https://example.com/cover.jpg"
    )
    assert (
        registered.cover_image_path
        == "cache/covers/cover.jpg"
    )
    assert registered.completion_month == "2026-07"
    assert registered.notes == "備考"


def test_add_book_converts_empty_optional_text_to_none(
    service: BookService,
) -> None:
    registered = service.add_book(
        title="テスト書籍",
        isbn=" ",
        magazine_code=" ",
        author=" ",
        publisher=" ",
        publication_format=" ",
        description=" ",
        cover_image_url=" ",
        cover_image_path=" ",
        completion_month=" ",
        notes=" ",
    )

    assert registered.isbn is None
    assert registered.magazine_code is None
    assert registered.author is None
    assert registered.publisher is None
    assert registered.publication_format is None
    assert registered.description is None
    assert registered.cover_image_url is None
    assert registered.cover_image_path is None
    assert registered.completion_month is None
    assert registered.notes is None

def test_add_book_normalizes_isbn(
    service: BookService,
) -> None:
    registered = service.add_book(
        title="テスト書籍",
        isbn=" 978-4-10-101001-4 ",
    )

    assert registered.isbn == "9784101010014"


def test_add_book_rejects_empty_title(
    service: BookService,
) -> None:
    with pytest.raises(
        ValueError,
        match="書籍名を入力してください。",
    ):
        service.add_book(title="   ")


def test_add_book_rejects_invalid_isbn(
    service: BookService,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "ISBNのチェックデジットが正しくありません。"
        ),
    ):
        service.add_book(
            title="テスト書籍",
            isbn="9784101010015",
        )

    assert service.get_all_books() == []


def test_add_book_rejects_invalid_magazine_code(
    service: BookService,
) -> None:
    with pytest.raises(
        ValueError,
        match="雑誌コードは半角数字で入力してください。",
    ):
        service.add_book(
            title="テスト書籍",
            magazine_code="12A45",
        )

    assert service.get_all_books() == []


def test_add_book_rejects_invalid_completion_month(
    service: BookService,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "読了年月の月は01から12で入力してください。"
        ),
    ):
        service.add_book(
            title="テスト書籍",
            completion_month="2026-13",
        )

    assert service.get_all_books() == []


def test_get_book_returns_book(
    service: BookService,
) -> None:
    registered = add_sample_book(service)

    result = service.get_book(registered.id or 0)

    assert result == registered


def test_get_book_returns_none_when_not_found(
    service: BookService,
) -> None:
    result = service.get_book(999)

    assert result is None


def test_get_all_books_returns_books_in_id_descending_order(
    service: BookService,
) -> None:
    first = add_sample_book(
        service,
        title="1冊目",
        isbn=None,
    )
    second = add_sample_book(
        service,
        title="2冊目",
        isbn=None,
    )

    results = service.get_all_books()

    assert [book.id for book in results] == [
        second.id,
        first.id,
    ]


def test_get_all_books_returns_empty_list(
    service: BookService,
) -> None:
    assert service.get_all_books() == []


def test_search_books_by_title_returns_partial_matches(
    service: BookService,
) -> None:
    add_sample_book(
        service,
        title="Python入門",
        isbn=None,
    )
    add_sample_book(
        service,
        title="Python実践",
        isbn=None,
    )
    add_sample_book(
        service,
        title="SQLite入門",
        isbn=None,
    )

    results = service.search_books_by_title("Python")

    assert len(results) == 2
    assert all(
        "Python" in book.title
        for book in results
    )


def test_search_books_by_title_strips_keyword(
    service: BookService,
) -> None:
    registered = add_sample_book(
        service,
        title="Python入門",
        isbn=None,
    )

    results = service.search_books_by_title(
        "  Python  "
    )

    assert results == [registered]


def test_search_books_by_title_returns_all_for_empty_keyword(
    service: BookService,
) -> None:
    first = add_sample_book(
        service,
        title="1冊目",
        isbn=None,
    )
    second = add_sample_book(
        service,
        title="2冊目",
        isbn=None,
    )

    results = service.search_books_by_title("   ")

    assert [book.id for book in results] == [
        second.id,
        first.id,
    ]

def test_search_books_by_author_returns_partial_matches(
    service: BookService,
) -> None:
    """著者名の部分一致検索結果を返す。"""
    first = add_sample_book(
        service,
        title="吾輩は猫である",
        isbn=None,
        author="夏目漱石",
    )
    second = add_sample_book(
        service,
        title="坊っちゃん",
        isbn=None,
        author="夏目漱石",
    )
    add_sample_book(
        service,
        title="羅生門",
        isbn=None,
        author="芥川龍之介",
    )

    results = service.search_books_by_author(
        "夏目",
    )

    assert results == [
        second,
        first,
    ]

def test_search_books_by_author_strips_keyword(
    service: BookService,
) -> None:
    """著者名検索文字列の前後空白を除去する。"""
    registered = add_sample_book(
        service,
        isbn=None,
        author="夏目漱石",
    )

    results = service.search_books_by_author(
        "  夏目  ",
    )

    assert results == [registered]

def test_search_books_by_author_returns_all_for_empty_keyword(
    service: BookService,
) -> None:
    """著者名検索が空の場合は全件を返す。"""
    first = add_sample_book(
        service,
        title="1冊目",
        isbn=None,
    )
    second = add_sample_book(
        service,
        title="2冊目",
        isbn=None,
    )

    results = service.search_books_by_author(
        "   ",
    )

    assert [book.id for book in results] == [
        second.id,
        first.id,
    ]

def test_search_books_by_publisher_returns_partial_matches(
    service: BookService,
) -> None:
    """出版社名の部分一致検索結果を返す。"""
    first = add_sample_book(
        service,
        title="1冊目",
        isbn=None,
        publisher="新潮社",
    )
    second = add_sample_book(
        service,
        title="2冊目",
        isbn=None,
        publisher="新潮社",
    )
    add_sample_book(
        service,
        title="3冊目",
        isbn=None,
        publisher="文藝春秋",
    )

    results = service.search_books_by_publisher(
        "新潮",
    )

    assert results == [
        second,
        first,
    ]

def test_search_books_by_publisher_strips_keyword(
    service: BookService,
) -> None:
    """出版社検索文字列の前後空白を除去する。"""
    registered = add_sample_book(
        service,
        isbn=None,
        publisher="新潮社",
    )

    results = service.search_books_by_publisher(
        "  新潮  ",
    )

    assert results == [registered]

def test_search_books_by_publisher_returns_all_for_empty_keyword(
    service: BookService,
) -> None:
    """出版社検索が空の場合は全件を返す。"""
    first = add_sample_book(
        service,
        title="1冊目",
        isbn=None,
    )
    second = add_sample_book(
        service,
        title="2冊目",
        isbn=None,
    )

    results = service.search_books_by_publisher(
        "   ",
    )

    assert [book.id for book in results] == [
        second.id,
        first.id,
    ]

def test_find_books_by_isbn_normalizes_isbn(
    service: BookService,
) -> None:
    registered = add_sample_book(service)

    results = service.find_books_by_isbn(
        " 978-4-10-101001-4 "
    )

    assert results == [registered]


def test_find_books_by_isbn_returns_empty_for_blank_value(
    service: BookService,
) -> None:
    assert service.find_books_by_isbn("   ") == []


def test_find_books_by_isbn_rejects_invalid_value(
    service: BookService,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "ISBNのチェックデジットが正しくありません。"
        ),
    ):
        service.find_books_by_isbn(
            "9784101010015"
        )


def test_find_books_by_magazine_code_normalizes_value(
    service: BookService,
) -> None:
    registered = add_sample_book(
        service,
        isbn=None,
        magazine_code="12345",
    )

    results = service.find_books_by_magazine_code(
        "  12345  "
    )

    assert results == [registered]


def test_find_books_by_magazine_code_returns_empty_for_blank_value(
    service: BookService,
) -> None:
    assert (
        service.find_books_by_magazine_code("   ")
        == []
    )


def test_find_duplicate_candidates_by_isbn(
    service: BookService,
) -> None:
    registered = add_sample_book(service)

    results = service.find_duplicate_candidates(
        isbn="978-4-10-101001-4",
    )

    assert results == [registered]


def test_find_duplicate_candidates_by_magazine_code(
    service: BookService,
) -> None:
    registered = add_sample_book(
        service,
        isbn=None,
        magazine_code="12345",
    )

    results = service.find_duplicate_candidates(
        magazine_code=" 12345 ",
    )

    assert results == [registered]


def test_find_duplicate_candidates_removes_duplicate_ids(
    service: BookService,
) -> None:
    registered = add_sample_book(
        service,
        isbn="9784101010014",
        magazine_code="12345",
    )

    results = service.find_duplicate_candidates(
        isbn="9784101010014",
        magazine_code="12345",
    )

    assert results == [registered]


def test_find_duplicate_candidates_returns_id_descending_order(
    service: BookService,
) -> None:
    first = add_sample_book(
        service,
        title="1冊目",
        isbn="9784101010014",
    )
    second = add_sample_book(
        service,
        title="2冊目",
        isbn="9784101010014",
    )

    results = service.find_duplicate_candidates(
        isbn="9784101010014",
    )

    assert [book.id for book in results] == [
        second.id,
        first.id,
    ]


def test_find_duplicate_candidates_returns_empty_when_values_are_blank(
    service: BookService,
) -> None:
    results = service.find_duplicate_candidates(
        isbn=" ",
        magazine_code=" ",
    )

    assert results == []


def test_update_book_updates_existing_book(
    repository: BookRepository,
) -> None:
    create_service = BookService(
        repository,
        now_provider=lambda: FIXED_NOW,
    )
    registered = add_sample_book(create_service)

    update_service = BookService(
        repository,
        now_provider=lambda: UPDATED_NOW,
    )

    update_target = BookItem(
        id=registered.id,
        title="  更新後の書籍名  ",
        isbn=" 978-4-16-391773-3 ",
        magazine_code=" 12345 ",
        author="  更新後の著者  ",
        publisher="  更新後の出版社  ",
        publication_format="  単行本  ",
        description="  更新後の内容紹介  ",
        cover_image_url=(
            "  https://example.com/updated-cover.png  "
        ),
        cover_image_path=(
            "  cache/covers/updated-cover.png  "
        ),
        completion_month=" 2026-08 ",
        notes="  更新後の備考  ",
        created_at="不正な作成日時",
        updated_at="不正な更新日時",
    )

    result = update_service.update_book(
        update_target
    )

    assert result is True

    updated = update_service.get_book(
        registered.id or 0
    )

    assert updated is not None
    assert updated.title == "更新後の書籍名"
    assert updated.isbn == "9784163917733"
    assert updated.magazine_code == "12345"
    assert updated.author == "更新後の著者"
    assert updated.publisher == "更新後の出版社"
    assert updated.publication_format == "単行本"
    assert updated.description == "更新後の内容紹介"
    assert (
        updated.cover_image_url
        == "https://example.com/updated-cover.png"
    )
    assert (
        updated.cover_image_path
        == "cache/covers/updated-cover.png"
    )
    assert updated.completion_month == "2026-08"
    assert updated.notes == "更新後の備考"
    assert updated.created_at == "2026-07-22 10:30:00"
    assert updated.updated_at == "2026-07-23 11:45:30"


def test_update_book_does_not_modify_input_model(
    repository: BookRepository,
) -> None:
    create_service = BookService(
        repository,
        now_provider=lambda: FIXED_NOW,
    )
    registered = add_sample_book(create_service)

    update_target = BookItem(
        id=registered.id,
        title="  更新後  ",
        isbn=" 978-4-16-391773-3 ",
        cover_image_url="  https://example.com/cover.jpg  ",
        cover_image_path="  cache/covers/cover.jpg  ",
        created_at="入力された作成日時",
        updated_at="入力された更新日時",
    )

    update_service = BookService(
        repository,
        now_provider=lambda: UPDATED_NOW,
    )

    update_service.update_book(update_target)

    assert update_target.title == "  更新後  "
    assert update_target.isbn == " 978-4-16-391773-3 "
    assert (
        update_target.created_at
        == "入力された作成日時"
    )
    assert (
        update_target.updated_at
        == "入力された更新日時"
    )
    assert (
        update_target.cover_image_url
        == "  https://example.com/cover.jpg  "
    )
    assert (
        update_target.cover_image_path
        == "  cache/covers/cover.jpg  "
    )

def test_update_book_requires_id(
    service: BookService,
) -> None:
    book_item = BookItem(
        title="更新対象",
    )

    with pytest.raises(
        ValueError,
        match="更新対象のBookItemにはidが必要です。",
    ):
        service.update_book(book_item)


def test_update_book_returns_false_when_not_found(
    service: BookService,
) -> None:
    book_item = BookItem(
        id=999,
        title="存在しない書籍",
    )

    assert service.update_book(book_item) is False


def test_update_book_does_not_validate_when_not_found(
    service: BookService,
) -> None:
    book_item = BookItem(
        id=999,
        title="",
        isbn="invalid",
        completion_month="invalid",
    )

    assert service.update_book(book_item) is False


def test_update_book_rejects_invalid_title(
    service: BookService,
) -> None:
    registered = add_sample_book(service)

    update_target = BookItem(
        id=registered.id,
        title="   ",
        created_at=registered.created_at,
        updated_at=registered.updated_at,
    )

    with pytest.raises(
        ValueError,
        match="書籍名を入力してください。",
    ):
        service.update_book(update_target)

    stored = service.get_book(registered.id or 0)

    assert stored == registered


def test_delete_book_deletes_existing_book(
    service: BookService,
) -> None:
    registered = add_sample_book(service)

    result = service.delete_book(
        registered.id or 0
    )

    assert result is True
    assert service.get_book(registered.id or 0) is None


def test_delete_book_returns_false_when_not_found(
    service: BookService,
) -> None:
    assert service.delete_book(999) is False

def test_fetch_book_metadata_delegates_to_metadata_service(
    repository: BookRepository,
) -> None:
    """外部書誌情報取得Serviceへ処理を委譲する。"""
    expected = FetchedBookData(
        isbn="9784163917733",
        title="テスト書籍",
        author="テスト著者",
        publisher="テスト出版社",
        sources=(
            "Google Books",
            "openBD",
        ),
    )
    metadata_service = FakeBookMetadataService(
        expected,
    )
    service = BookService(
        repository,
        metadata_service=metadata_service,  # type: ignore[arg-type]
    )

    result = service.fetch_book_metadata(
        "978-4-16-391773-3",
    )

    assert result == expected
    assert metadata_service.calls == [
        "978-4-16-391773-3",
    ]


def test_fetch_book_metadata_requires_metadata_service(
    repository: BookRepository,
) -> None:
    """外部書誌情報取得Service未設定時は設定例外となる。"""
    service = BookService(
        repository,
    )

    with pytest.raises(
        BookMetadataConfigurationError,
        match=(
            "外部書誌情報取得Serviceが"
            "設定されていません。"
        ),
    ):
        service.fetch_book_metadata(
            "9784163917733",
        )

def test_fetch_cover_image_delegates_to_cover_image_service(
    repository: BookRepository,
    tmp_path: Path,
) -> None:
    """表紙画像取得Serviceへ処理を委譲する。"""
    expected = tmp_path / "cover.jpg"
    cover_image_service = FakeCoverImageService(
        expected,
    )
    service = BookService(
        repository,
        cover_image_service=cover_image_service,  # type: ignore[arg-type]
    )

    result = service.fetch_cover_image(
        "https://example.com/cover.jpg",
    )

    assert result == expected
    assert cover_image_service.calls == [
        "https://example.com/cover.jpg",
    ]


def test_fetch_cover_image_requires_cover_image_service(
    repository: BookRepository,
) -> None:
    """表紙画像取得Service未設定時は設定例外となる。"""
    service = BookService(
        repository,
    )

    with pytest.raises(
        BookMetadataConfigurationError,
        match=(
            "表紙画像取得Serviceが"
            "設定されていません。"
        ),
    ):
        service.fetch_cover_image(
            "https://example.com/cover.jpg",
        )

def test_get_sorted_books_returns_title_ascending(
    service: BookService,
) -> None:
    """書籍名の昇順で取得できることを確認する。"""
    second = add_sample_book(
        service,
        title="B書籍",
        isbn=None,
    )
    first = add_sample_book(
        service,
        title="A書籍",
        isbn=None,
    )

    results = service.get_sorted_books(
        sort_by="title",
    )

    assert results == [
        first,
        second,
    ]

def test_get_sorted_books_returns_title_descending(
    service: BookService,
) -> None:
    """書籍名の降順で取得できることを確認する。"""
    second = add_sample_book(
        service,
        title="B書籍",
        isbn=None,
    )
    first = add_sample_book(
        service,
        title="A書籍",
        isbn=None,
    )

    results = service.get_sorted_books(
        sort_by="title",
        descending=True,
    )

    assert results == [
        second,
        first,
    ]

def test_get_sorted_books_returns_registered_descending(
    service: BookService,
) -> None:
    """登録順の降順で取得できることを確認する。"""
    first = add_sample_book(
        service,
        title="1冊目",
        isbn=None,
    )
    second = add_sample_book(
        service,
        title="2冊目",
        isbn=None,
    )

    results = service.get_sorted_books(
        sort_by="registered",
        descending=True,
    )

    assert results == [
        second,
        first,
    ]

def test_get_sorted_books_rejects_invalid_sort_by(
    service: BookService,
) -> None:
    """未対応の並べ替え項目を拒否する。"""
    with pytest.raises(
        ValueError,
        match="指定された並べ替え項目が正しくありません。",
    ):
        service.get_sorted_books(
            sort_by="invalid",
        )

def test_sort_books_sorts_search_results_by_title(
    service: BookService,
) -> None:
    """取得済み一覧を書籍名順に並べ替えられる。"""
    second = add_sample_book(
        service,
        title="B書籍",
        isbn=None,
    )
    first = add_sample_book(
        service,
        title="A書籍",
        isbn=None,
    )

    results = service.sort_books(
        [
            second,
            first,
        ],
        sort_by="title",
    )

    assert results == [
        first,
        second,
    ]

def test_sort_books_sorts_search_results_descending(
    service: BookService,
) -> None:
    """取得済み一覧を降順に並べ替えられる。"""
    second = add_sample_book(
        service,
        title="B書籍",
        isbn=None,
    )
    first = add_sample_book(
        service,
        title="A書籍",
        isbn=None,
    )

    results = service.sort_books(
        [
            first,
            second,
        ],
        sort_by="title",
        descending=True,
    )

    assert results == [
        second,
        first,
    ]

def test_sort_books_places_none_last(
    service: BookService,
) -> None:
    """値のない書籍は検索結果ソートでも最後になる。"""
    without_author = add_sample_book(
        service,
        title="著者なし",
        isbn=None,
        author=None,
    )
    with_author = add_sample_book(
        service,
        title="著者あり",
        isbn=None,
        author="夏目漱石",
    )

    results = service.sort_books(
        [
            without_author,
            with_author,
        ],
        sort_by="author",
    )

    assert results == [
        with_author,
        without_author,
    ]

def test_sort_books_sorts_by_registered_descending(
    service: BookService,
) -> None:
    """取得済み一覧を登録順の降順にできる。"""
    first = add_sample_book(
        service,
        title="1冊目",
        isbn=None,
    )
    second = add_sample_book(
        service,
        title="2冊目",
        isbn=None,
    )

    results = service.sort_books(
        [
            first,
            second,
        ],
        sort_by="registered",
        descending=True,
    )

    assert results == [
        second,
        first,
    ]

def test_sort_books_rejects_invalid_sort_by(
    service: BookService,
) -> None:
    """未対応の並べ替え項目を拒否する。"""
    with pytest.raises(
        ValueError,
        match="指定された並べ替え項目が正しくありません。",
    ):
        service.sort_books(
            [],
            sort_by="invalid",
        )