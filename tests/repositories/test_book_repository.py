"""Tests for the BookRepository."""

from pathlib import Path

import pytest

from book_manager.database.initializer import initialize_database
from book_manager.models.book_item import BookItem
from book_manager.repositories.book_repository import BookRepository


@pytest.fixture
def repository(
    tmp_path: Path,
) -> BookRepository:
    """初期化済みの一時データベースを使用するRepositoryを返す。"""
    database_path = tmp_path / "test_book_manager.db"
    initialize_database(database_path)

    return BookRepository(database_path)


def create_book_item(
    *,
    title: str = "吾輩は猫である",
    isbn: str | None = "9784101010014",
    magazine_code: str | None = None,
    author: str | None = "夏目漱石",
    publisher: str | None = "新潮社",
    publication_format: str | None = "文庫",
    description: str | None = "猫の視点から人間社会を描いた作品。",
    cover_image_url: str | None = (
        "https://example.com/cover.jpg"
    ),
    cover_image_path: str | None = (
        "cache/covers/cover.jpg"
    ),
    completion_month: str | None = "2026-07",
    notes: str | None = "再読。",
    created_at: str = "2026-07-22 10:00:00",
    updated_at: str = "2026-07-22 10:00:00",
) -> BookItem:
    """Repositoryテスト用のBookItemを生成する。"""
    return BookItem(
        title=title,
        isbn=isbn,
        magazine_code=magazine_code,
        author=author,
        publisher=publisher,
        publication_format=publication_format,
        description=description,
        cover_image_url=cover_image_url,
        cover_image_path=cover_image_path,
        completion_month=completion_month,
        notes=notes,
        created_at=created_at,
        updated_at=updated_at,
    )

def test_repository_accepts_path(
    tmp_path: Path,
) -> None:
    """Pathを使用してRepositoryを生成できることを確認する。"""
    database_path = tmp_path / "test.db"

    repository = BookRepository(database_path)

    assert repository._database_path == database_path


def test_repository_accepts_string_path(
    tmp_path: Path,
) -> None:
    """文字列パスを使用してRepositoryを生成できることを確認する。"""
    database_path = tmp_path / "test.db"

    repository = BookRepository(str(database_path))

    assert repository._database_path == database_path


def test_add_registers_book(
    repository: BookRepository,
) -> None:
    """書籍情報を登録できることを確認する。"""
    book_item = create_book_item()

    registered = repository.add(book_item)

    assert registered.id is not None

    stored = repository.get_by_id(registered.id)

    assert stored == registered


def test_add_does_not_modify_input_model(
    repository: BookRepository,
) -> None:
    """登録時に入力モデルを直接変更しないことを確認する。"""
    book_item = create_book_item()

    registered = repository.add(book_item)

    assert book_item.id is None
    assert registered.id is not None
    assert registered is not book_item


def test_add_accepts_none_optional_fields(
    repository: BookRepository,
) -> None:
    """任意項目がNoneでも登録できることを確認する。"""
    book_item = BookItem(
        title="坊っちゃん",
        created_at="2026-07-22 11:00:00",
        updated_at="2026-07-22 11:00:00",
    )

    registered = repository.add(book_item)

    assert registered.id is not None

    stored = repository.get_by_id(registered.id)

    assert stored == registered
    assert stored is not None
    assert stored.isbn is None
    assert stored.author is None
    assert stored.cover_image_url is None
    assert stored.cover_image_path is None

def test_add_and_get_preserve_cover_image_fields(
    repository: BookRepository,
) -> None:
    """表紙画像情報を登録して取得できることを確認する。"""
    book_item = create_book_item(
        cover_image_url=(
            "https://example.com/books/cover.jpg"
        ),
        cover_image_path=(
            "cache/covers/abc123.jpg"
        ),
    )

    registered = repository.add(
        book_item,
    )

    stored = repository.get_by_id(
        registered.id  # type: ignore[arg-type]
    )

    assert stored is not None
    assert (
        stored.cover_image_url
        == "https://example.com/books/cover.jpg"
    )
    assert (
        stored.cover_image_path
        == "cache/covers/abc123.jpg"
    )

def test_get_by_id_returns_book_item(
    repository: BookRepository,
) -> None:
    """存在するIDからBookItemを取得できることを確認する。"""
    registered = repository.add(
        create_book_item()
    )

    result = repository.get_by_id(registered.id)  # type: ignore[arg-type]

    assert isinstance(result, BookItem)
    assert result == registered


def test_get_by_id_returns_none_for_missing_id(
    repository: BookRepository,
) -> None:
    """存在しないIDではNoneを返すことを確認する。"""
    result = repository.get_by_id(999)

    assert result is None


def test_get_all_returns_empty_list(
    repository: BookRepository,
) -> None:
    """データが存在しない場合に空のリストを返すことを確認する。"""
    result = repository.get_all()

    assert result == []


def test_get_all_returns_books_in_descending_id_order(
    repository: BookRepository,
) -> None:
    """書籍をIDの降順で取得することを確認する。"""
    first = repository.add(
        create_book_item(title="1冊目")
    )
    second = repository.add(
        create_book_item(title="2冊目")
    )
    third = repository.add(
        create_book_item(title="3冊目")
    )

    result = repository.get_all()

    assert result == [
        third,
        second,
        first,
    ]


def test_search_by_title_finds_exact_match(
    repository: BookRepository,
) -> None:
    """書籍名の完全一致でも検索できることを確認する。"""
    registered = repository.add(
        create_book_item(title="吾輩は猫である")
    )

    result = repository.search_by_title(
        "吾輩は猫である"
    )

    assert result == [registered]


def test_search_by_title_finds_partial_match(
    repository: BookRepository,
) -> None:
    """書籍名を部分一致で検索できることを確認する。"""
    first = repository.add(
        create_book_item(title="吾輩は猫である")
    )
    second = repository.add(
        create_book_item(title="猫と庄造と二人のをんな")
    )
    repository.add(
        create_book_item(title="坊っちゃん")
    )

    result = repository.search_by_title("猫")

    assert result == [
        second,
        first,
    ]


def test_search_by_title_returns_empty_list(
    repository: BookRepository,
) -> None:
    """該当する書籍がない場合に空のリストを返すことを確認する。"""
    repository.add(
        create_book_item(title="吾輩は猫である")
    )

    result = repository.search_by_title("存在しない書籍")

    assert result == []


def test_find_by_isbn_returns_matching_books(
    repository: BookRepository,
) -> None:
    """同じISBNの書籍をすべてID降順で取得することを確認する。"""
    first = repository.add(
        create_book_item(
            title="吾輩は猫である・上",
            isbn="9784101010014",
        )
    )
    second = repository.add(
        create_book_item(
            title="吾輩は猫である・下",
            isbn="9784101010014",
        )
    )
    repository.add(
        create_book_item(
            title="坊っちゃん",
            isbn="9784101010021",
        )
    )

    result = repository.find_by_isbn(
        "9784101010014"
    )

    assert result == [
        second,
        first,
    ]


def test_find_by_isbn_returns_empty_list(
    repository: BookRepository,
) -> None:
    """該当するISBNがない場合に空のリストを返すことを確認する。"""
    result = repository.find_by_isbn(
        "0000000000000"
    )

    assert result == []


def test_find_by_magazine_code_returns_matching_books(
    repository: BookRepository,
) -> None:
    """同じ雑誌コードの書籍をすべてID降順で取得することを確認する。"""
    first = repository.add(
        create_book_item(
            title="月刊テスト 7月号",
            isbn=None,
            magazine_code="1234507",
        )
    )
    second = repository.add(
        create_book_item(
            title="月刊テスト 増刊号",
            isbn=None,
            magazine_code="1234507",
        )
    )
    repository.add(
        create_book_item(
            title="別冊テスト",
            isbn=None,
            magazine_code="9876507",
        )
    )

    result = repository.find_by_magazine_code(
        "1234507"
    )

    assert result == [
        second,
        first,
    ]


def test_find_by_magazine_code_returns_empty_list(
    repository: BookRepository,
) -> None:
    """該当する雑誌コードがない場合に空のリストを返すことを確認する。"""
    result = repository.find_by_magazine_code(
        "0000000"
    )

    assert result == []


def test_update_updates_existing_book(
    repository: BookRepository,
) -> None:
    """既存の書籍情報を更新できることを確認する。"""
    registered = repository.add(
        create_book_item()
    )

    updated_book = BookItem(
        id=registered.id,
        title="吾輩は猫である 改訂版",
        isbn="9784101010014",
        magazine_code=None,
        author="夏目漱石",
        publisher="新潮社",
        publication_format="文庫",
        description="更新後の内容紹介。",
        cover_image_url=(
            "https://example.com/updated-cover.png"
        ),
        cover_image_path=(
            "cache/covers/updated-cover.png"
        ),        completion_month="2026-08",
        notes="更新済み。",
        created_at=registered.created_at,
        updated_at="2026-07-22 12:00:00",
    )

    result = repository.update(updated_book)

    assert result is True

    stored = repository.get_by_id(
        registered.id  # type: ignore[arg-type]
    )

    assert stored == updated_book


def test_update_does_not_change_created_at(
    repository: BookRepository,
) -> None:
    """更新時にcreated_atが変更されないことを確認する。"""
    registered = repository.add(
        create_book_item()
    )

    updated_book = BookItem(
        id=registered.id,
        title="更新後の書籍名",
        created_at="2099-01-01 00:00:00",
        updated_at="2026-07-22 13:00:00",
    )

    result = repository.update(updated_book)

    assert result is True

    stored = repository.get_by_id(
        registered.id  # type: ignore[arg-type]
    )

    assert stored is not None
    assert stored.created_at == registered.created_at
    assert stored.updated_at == "2026-07-22 13:00:00"


def test_update_returns_false_for_missing_id(
    repository: BookRepository,
) -> None:
    """存在しないIDではFalseを返すことを確認する。"""
    book_item = create_book_item()
    book_item.id = 999

    result = repository.update(book_item)

    assert result is False


def test_update_raises_value_error_without_id(
    repository: BookRepository,
) -> None:
    """idがNoneの場合にValueErrorを送出することを確認する。"""
    book_item = create_book_item()

    with pytest.raises(
        ValueError,
        match="更新対象のBookItemにはidが必要です。",
    ):
        repository.update(book_item)


def test_delete_removes_existing_book(
    repository: BookRepository,
) -> None:
    """既存の書籍情報を削除できることを確認する。"""
    registered = repository.add(
        create_book_item()
    )

    result = repository.delete(
        registered.id  # type: ignore[arg-type]
    )

    assert result is True
    assert repository.get_by_id(
        registered.id  # type: ignore[arg-type]
    ) is None
    assert repository.get_all() == []


def test_delete_returns_false_for_missing_id(
    repository: BookRepository,
) -> None:
    """存在しないIDではFalseを返すことを確認する。"""
    result = repository.delete(999)

    assert result is False