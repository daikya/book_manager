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
    isbn: str | None = "9784101010014",
    magazine_code: str | None = None,
) -> BookItem:
    """テスト用の書籍を登録する。"""
    return service.add_book(
        title=title,
        isbn=isbn,
        magazine_code=magazine_code,
        author="夏目漱石",
        publisher="新潮社",
        publication_format="文庫",
        description="猫の視点から描かれた小説。",
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
        completion_month="  2026-07  ",
        notes="  備考  ",
    )

    assert registered.author == "著者名"
    assert registered.publisher == "出版社名"
    assert registered.publication_format == "文庫"
    assert registered.description == "内容紹介"
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
        completion_month=" ",
        notes=" ",
    )

    assert registered.isbn is None
    assert registered.magazine_code is None
    assert registered.author is None
    assert registered.publisher is None
    assert registered.publication_format is None
    assert registered.description is None
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