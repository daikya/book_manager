"""Tests for the BookRepository."""

import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from book_manager.database.initializer import initialize_database
from book_manager.models.book_item import BookItem
from book_manager.models.tag import Tag
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
    reading_status: str | None = None,
    is_favorite: bool = False,
    rating: int | None = None,
    notes: str | None = "再読。",
    created_at: str = "2026-07-22 10:00:00",
    updated_at: str = "2026-07-22 10:00:00",
    tags: tuple[str, ...] = (),
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
        reading_status=reading_status,
        is_favorite=is_favorite,
        rating=rating,
        notes=notes,
        created_at=created_at,
        updated_at=updated_at,
        tags=tags,
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

def test_get_all_sorted_by_registered_ascending(
    repository: BookRepository,
) -> None:
    """登録順の昇順で取得できることを確認する。"""
    first = repository.add(
        create_book_item(title="1冊目")
    )
    second = repository.add(
        create_book_item(title="2冊目")
    )
    third = repository.add(
        create_book_item(title="3冊目")
    )

    result = repository.get_all_sorted(
        sort_by="registered",
        descending=False,
    )

    assert result == [
        first,
        second,
        third,
    ]

def test_get_all_sorted_by_registered_descending(
    repository: BookRepository,
) -> None:
    """登録順の降順で取得できることを確認する。"""
    first = repository.add(
        create_book_item(title="1冊目")
    )
    second = repository.add(
        create_book_item(title="2冊目")
    )

    result = repository.get_all_sorted(
        sort_by="registered",
        descending=True,
    )

    assert result == [
        second,
        first,
    ]

def test_get_all_sorted_by_title(
    repository: BookRepository,
) -> None:
    """書籍名の昇順で取得できることを確認する。"""
    second = repository.add(
        create_book_item(title="B書籍")
    )
    first = repository.add(
        create_book_item(title="A書籍")
    )

    result = repository.get_all_sorted(
        sort_by="title",
    )

    assert result == [
        first,
        second,
    ]

@pytest.mark.parametrize(
    ("sort_by", "field_name", "first_value", "second_value"),
    [
        (
            "author",
            "author",
            "A著者",
            "B著者",
        ),
        (
            "publisher",
            "publisher",
            "A出版社",
            "B出版社",
        ),
        (
            "completion_month",
            "completion_month",
            "2026-01",
            "2026-12",
        ),
    ],
)

def test_get_all_sorted_by_optional_field(
    repository: BookRepository,
    sort_by: str,
    field_name: str,
    first_value: str,
    second_value: str,
) -> None:
    """任意項目の昇順で取得できることを確認する。"""
    second = repository.add(
        create_book_item(
            title="2冊目",
            **{
                field_name: second_value,
            },
        )
    )
    first = repository.add(
        create_book_item(
            title="1冊目",
            **{
                field_name: first_value,
            },
        )
    )

    result = repository.get_all_sorted(
        sort_by=sort_by,
    )

    assert result == [
        first,
        second,
    ]

def test_get_all_sorted_places_none_last(
    repository: BookRepository,
) -> None:
    """値がない書籍は並べ替え時に最後へ配置する。"""
    without_author = repository.add(
        create_book_item(
            title="著者なし",
            author=None,
        )
    )
    with_author = repository.add(
        create_book_item(
            title="著者あり",
            author="夏目漱石",
        )
    )

    result = repository.get_all_sorted(
        sort_by="author",
    )

    assert result == [
        with_author,
        without_author,
    ]


@pytest.mark.parametrize(
    ("descending", "expected_titles"),
    [
        (
            False,
            [
                "未設定",
                "未読",
                "読書中",
                "読了",
            ],
        ),
        (
            True,
            [
                "読了",
                "読書中",
                "未読",
                "未設定",
            ],
        ),
    ],
)
def test_get_all_sorted_by_reading_status(
    repository: BookRepository,
    descending: bool,
    expected_titles: list[str],
) -> None:
    """読書状態を定義した順序で取得する。"""
    repository.add(
        create_book_item(
            title="読書中",
            reading_status="reading",
        )
    )
    repository.add(
        create_book_item(
            title="未設定",
            reading_status=None,
        )
    )
    repository.add(
        create_book_item(
            title="読了",
            reading_status="completed",
        )
    )
    repository.add(
        create_book_item(
            title="未読",
            reading_status="unread",
        )
    )

    result = repository.get_all_sorted(
        sort_by="reading_status",
        descending=descending,
    )

    assert [book.title for book in result] == (
        expected_titles
    )


@pytest.mark.parametrize(
    ("descending", "expected_titles"),
    [
        (
            False,
            [
                "お気に入り以外",
                "お気に入り",
            ],
        ),
        (
            True,
            [
                "お気に入り",
                "お気に入り以外",
            ],
        ),
    ],
)
def test_get_all_sorted_by_favorite(
    repository: BookRepository,
    descending: bool,
    expected_titles: list[str],
) -> None:
    """お気に入り状態で昇順・降順に取得する。"""
    repository.add(
        create_book_item(
            title="お気に入り",
            is_favorite=True,
        )
    )
    repository.add(
        create_book_item(
            title="お気に入り以外",
            is_favorite=False,
        )
    )

    result = repository.get_all_sorted(
        sort_by="is_favorite",
        descending=descending,
    )

    assert [book.title for book in result] == (
        expected_titles
    )


@pytest.mark.parametrize(
    ("descending", "expected_titles"),
    [
        (
            False,
            [
                "未評価",
                "評価1",
                "評価3",
                "評価5",
            ],
        ),
        (
            True,
            [
                "評価5",
                "評価3",
                "評価1",
                "未評価",
            ],
        ),
    ],
)
def test_get_all_sorted_by_rating(
    repository: BookRepository,
    descending: bool,
    expected_titles: list[str],
) -> None:
    """評価を未評価を含む定義した順序で取得する。"""
    repository.add(
        create_book_item(
            title="評価3",
            rating=3,
        )
    )
    repository.add(
        create_book_item(
            title="未評価",
            rating=None,
        )
    )
    repository.add(
        create_book_item(
            title="評価5",
            rating=5,
        )
    )
    repository.add(
        create_book_item(
            title="評価1",
            rating=1,
        )
    )

    result = repository.get_all_sorted(
        sort_by="rating",
        descending=descending,
    )

    assert [book.title for book in result] == (
        expected_titles
    )


@pytest.mark.parametrize(
    ("sort_by", "field_values"),
    [
        (
            "reading_status",
            {
                "reading_status": "reading",
            },
        ),
        (
            "is_favorite",
            {
                "is_favorite": True,
            },
        ),
        (
            "rating",
            {
                "rating": 3,
            },
        ),
    ],
)
def test_get_all_sorted_uses_descending_id_for_same_value(
    repository: BookRepository,
    sort_by: str,
    field_values: dict[str, str | bool | int],
) -> None:
    """同順位の書籍はID降順で取得する。"""
    first = repository.add(
        create_book_item(
            title="先に登録",
            **field_values,
        )
    )
    second = repository.add(
        create_book_item(
            title="後に登録",
            **field_values,
        )
    )

    result = repository.get_all_sorted(
        sort_by=sort_by,
    )

    assert result == [
        second,
        first,
    ]

def test_get_all_sorted_rejects_invalid_sort_by(
    repository: BookRepository,
) -> None:
    """未対応の並べ替え項目を拒否する。"""
    with pytest.raises(
        ValueError,
        match="指定された並べ替え項目が正しくありません。",
    ):
        repository.get_all_sorted(
            sort_by="invalid",
        )

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

def test_search_by_author_finds_partial_match(
    repository: BookRepository,
) -> None:
    """著者名を部分一致で検索できることを確認する。"""
    first = repository.add(
        create_book_item(
            title="吾輩は猫である",
            author="夏目漱石",
        )
    )
    second = repository.add(
        create_book_item(
            title="坊っちゃん",
            author="夏目漱石",
        )
    )
    repository.add(
        create_book_item(
            title="羅生門",
            author="芥川龍之介",
        )
    )

    result = repository.search_by_author(
        "夏目",
    )

    assert result == [
        second,
        first,
    ]

def test_search_by_author_returns_empty_list(
    repository: BookRepository,
) -> None:
    """該当する著者名がない場合に空のリストを返す。"""
    repository.add(
        create_book_item(
            author="夏目漱石",
        )
    )

    result = repository.search_by_author(
        "存在しない著者",
    )

    assert result == []

def test_search_by_publisher_finds_partial_match(
    repository: BookRepository,
) -> None:
    """出版社名を部分一致で検索できることを確認する。"""
    first = repository.add(
        create_book_item(
            title="1冊目",
            publisher="新潮社",
        )
    )
    second = repository.add(
        create_book_item(
            title="2冊目",
            publisher="新潮社",
        )
    )
    repository.add(
        create_book_item(
            title="3冊目",
            publisher="文藝春秋",
        )
    )

    result = repository.search_by_publisher(
        "新潮",
    )

    assert result == [
        second,
        first,
    ]

def test_search_by_publisher_returns_empty_list(
    repository: BookRepository,
) -> None:
    """該当する出版社がない場合に空のリストを返す。"""
    repository.add(
        create_book_item(
            publisher="新潮社",
        )
    )

    result = repository.search_by_publisher(
        "存在しない出版社",
    )

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

def test_search_by_conditions_finds_title_partial_match(
    repository: BookRepository,
) -> None:
    """書籍名を部分一致で複合条件検索できる。"""
    first = repository.add(
        create_book_item(
            title="吾輩は猫である",
        )
    )
    second = repository.add(
        create_book_item(
            title="猫と庄造と二人のをんな",
        )
    )
    repository.add(
        create_book_item(
            title="坊っちゃん",
        )
    )

    result = repository.search_by_conditions(
        title="猫",
    )

    assert result == [
        second,
        first,
    ]


def test_search_by_conditions_finds_author_partial_match(
    repository: BookRepository,
) -> None:
    """著者名を部分一致で複合条件検索できる。"""
    registered = repository.add(
        create_book_item(
            title="吾輩は猫である",
            author="夏目漱石",
        )
    )
    repository.add(
        create_book_item(
            title="羅生門",
            author="芥川龍之介",
        )
    )

    result = repository.search_by_conditions(
        author="夏目",
    )

    assert result == [
        registered,
    ]


def test_search_by_conditions_finds_publisher_partial_match(
    repository: BookRepository,
) -> None:
    """出版社を部分一致で複合条件検索できる。"""
    registered = repository.add(
        create_book_item(
            title="吾輩は猫である",
            publisher="新潮社",
        )
    )
    repository.add(
        create_book_item(
            title="別の書籍",
            publisher="講談社",
        )
    )

    result = repository.search_by_conditions(
        publisher="新潮",
    )

    assert result == [
        registered,
    ]


def test_search_by_conditions_finds_isbn_exact_match(
    repository: BookRepository,
) -> None:
    """ISBNを完全一致で複合条件検索できる。"""
    registered = repository.add(
        create_book_item(
            title="吾輩は猫である",
            isbn="9784101010014",
        )
    )
    repository.add(
        create_book_item(
            title="坊っちゃん",
            isbn="9784101010021",
        )
    )

    result = repository.search_by_conditions(
        isbn="9784101010014",
    )

    assert result == [
        registered,
    ]


def test_search_by_conditions_finds_magazine_code_exact_match(
    repository: BookRepository,
) -> None:
    """雑誌コードを完全一致で複合条件検索できる。"""
    registered = repository.add(
        create_book_item(
            title="月刊テスト",
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

    result = repository.search_by_conditions(
        magazine_code="1234507",
    )

    assert result == [
        registered,
    ]


def test_search_by_conditions_uses_and_for_multiple_conditions(
    repository: BookRepository,
) -> None:
    """複数条件をAND条件として検索できる。"""
    matched = repository.add(
        create_book_item(
            title="海辺のカフカ",
            author="村上春樹",
            publisher="新潮社",
        )
    )
    repository.add(
        create_book_item(
            title="ノルウェイの森",
            author="村上春樹",
            publisher="講談社",
        )
    )
    repository.add(
        create_book_item(
            title="別の書籍",
            author="別の著者",
            publisher="新潮社",
        )
    )

    result = repository.search_by_conditions(
        author="村上",
        publisher="新潮",
    )

    assert result == [
        matched,
    ]


def test_search_by_conditions_uses_all_specified_conditions(
    repository: BookRepository,
) -> None:
    """指定されたすべての条件を満たす書籍だけを取得する。"""
    matched = repository.add(
        create_book_item(
            title="海辺のカフカ",
            author="村上春樹",
            publisher="新潮社",
            isbn="9784101001547",
        )
    )
    repository.add(
        create_book_item(
            title="海辺のカフカ",
            author="村上春樹",
            publisher="新潮社",
            isbn="9784101001554",
        )
    )

    result = repository.search_by_conditions(
        title="海辺",
        author="村上",
        publisher="新潮",
        isbn="9784101001547",
    )

    assert result == [
        matched,
    ]


def test_search_by_conditions_returns_empty_list_when_no_match(
    repository: BookRepository,
) -> None:
    """複合条件に一致する書籍がない場合は空リストを返す。"""
    repository.add(
        create_book_item(
            title="吾輩は猫である",
        )
    )

    result = repository.search_by_conditions(
        title="存在しない書籍",
    )

    assert result == []


def test_search_by_conditions_without_conditions_returns_all(
    repository: BookRepository,
) -> None:
    """検索条件がない場合は全件をID降順で返す。"""
    first = repository.add(
        create_book_item(
            title="1冊目",
        )
    )
    second = repository.add(
        create_book_item(
            title="2冊目",
        )
    )

    result = repository.search_by_conditions()

    assert result == [
        second,
        first,
    ]


def test_search_by_conditions_returns_results_in_descending_id_order(
    repository: BookRepository,
) -> None:
    """複合条件検索結果をID降順で返す。"""
    first = repository.add(
        create_book_item(
            title="1冊目",
            author="共通著者",
        )
    )
    second = repository.add(
        create_book_item(
            title="2冊目",
            author="共通著者",
        )
    )

    result = repository.search_by_conditions(
        author="共通",
    )

    assert result == [
        second,
        first,
    ]

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
        ),
        completion_month="2026-08",
        reading_status="completed",
        is_favorite=True,
        rating=5,
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

def test_search_by_conditions_handles_sql_special_characters(
    repository: BookRepository,
) -> None:
    """SQLで特別な意味を持つ文字を含む値も安全に検索できる。"""
    registered = repository.add(
        create_book_item(
            title="O'Reilly Python",
        )
    )

    result = repository.search_by_conditions(
        title="O'Reilly",
    )

    assert result == [
        registered,
    ]

def test_add_stores_reading_status(
    repository: BookRepository,
) -> None:
    """読書ステータスを登録できる。"""
    book = BookItem(
        title="テスト書籍",
        reading_status="reading",
        created_at="2026-08-25 10:00:00",
        updated_at="2026-08-25 10:00:00",
    )

    registered = repository.add(book)

    assert registered.id is not None

    loaded = repository.get_by_id(
        registered.id,
    )

    assert loaded is not None
    assert loaded.reading_status == "reading"


def test_add_stores_none_reading_status(
    repository: BookRepository,
) -> None:
    """未設定の読書ステータスをNoneとして保存できる。"""
    book = BookItem(
        title="テスト書籍",
        reading_status=None,
        created_at="2026-08-25 10:00:00",
        updated_at="2026-08-25 10:00:00",
    )

    registered = repository.add(book)

    assert registered.id is not None

    loaded = repository.get_by_id(
        registered.id,
    )

    assert loaded is not None
    assert loaded.reading_status is None


def test_update_changes_reading_status(
    repository: BookRepository,
) -> None:
    """読書ステータスを更新できる。"""
    registered = repository.add(
        BookItem(
            title="更新対象書籍",
            reading_status="unread",
            created_at="2026-08-25 10:00:00",
            updated_at="2026-08-25 10:00:00",
        )
    )

    updated_book = BookItem(
        id=registered.id,
        title=registered.title,
        isbn=registered.isbn,
        magazine_code=registered.magazine_code,
        author=registered.author,
        publisher=registered.publisher,
        publication_format=registered.publication_format,
        description=registered.description,
        cover_image_url=registered.cover_image_url,
        cover_image_path=registered.cover_image_path,
        completion_month=registered.completion_month,
        reading_status="completed",
        is_favorite=registered.is_favorite,
        notes=registered.notes,
        created_at=registered.created_at,
        updated_at=registered.updated_at,
    )

    result = repository.update(
        updated_book,
    )

    assert result is True

    loaded = repository.get_by_id(
        registered.id,
    )

    assert loaded is not None
    assert loaded.reading_status == "completed"


def test_update_can_clear_reading_status(
    repository: BookRepository,
) -> None:
    """読書ステータスをNoneへ戻せる。"""
    registered = repository.add(
        BookItem(
            title="更新対象書籍",
            reading_status="unread",
            created_at="2026-08-25 10:00:00",
            updated_at="2026-08-25 10:00:00",
        )
    )

    updated_book = BookItem(
        id=registered.id,
        title=registered.title,
        isbn=registered.isbn,
        magazine_code=registered.magazine_code,
        author=registered.author,
        publisher=registered.publisher,
        publication_format=registered.publication_format,
        description=registered.description,
        cover_image_url=registered.cover_image_url,
        cover_image_path=registered.cover_image_path,
        completion_month=registered.completion_month,
        reading_status=None,
        is_favorite=registered.is_favorite,
        notes=registered.notes,
        created_at=registered.created_at,
        updated_at=registered.updated_at,
    )

    result = repository.update(
        updated_book,
    )

    assert result is True

    loaded = repository.get_by_id(
        registered.id,
    )

    assert loaded is not None
    assert loaded.reading_status is None


def test_add_stores_false_is_favorite(
    repository: BookRepository,
) -> None:
    """お気に入りOFFを登録・取得できる。"""
    book = create_book_item(
        title="お気に入りOFF書籍",
        is_favorite=False,
    )

    registered = repository.add(book)

    assert registered.id is not None

    loaded = repository.get_by_id(
        registered.id,
    )

    assert loaded is not None
    assert loaded.is_favorite is False


def test_add_stores_true_is_favorite(
    repository: BookRepository,
) -> None:
    """お気に入りONを登録・取得できる。"""
    book = create_book_item(
        title="お気に入りON書籍",
        is_favorite=True,
    )

    registered = repository.add(book)

    assert registered.id is not None

    loaded = repository.get_by_id(
        registered.id,
    )

    assert loaded is not None
    assert loaded.is_favorite is True


def test_update_changes_is_favorite_from_false_to_true(
    repository: BookRepository,
) -> None:
    """お気に入りをOFFからONへ更新できる。"""
    registered = repository.add(
        create_book_item(
            title="更新対象書籍",
            is_favorite=False,
        )
    )

    updated_book = BookItem(
        id=registered.id,
        title=registered.title,
        isbn=registered.isbn,
        magazine_code=registered.magazine_code,
        author=registered.author,
        publisher=registered.publisher,
        publication_format=registered.publication_format,
        description=registered.description,
        cover_image_url=registered.cover_image_url,
        cover_image_path=registered.cover_image_path,
        completion_month=registered.completion_month,
        reading_status=registered.reading_status,
        is_favorite=True,
        notes=registered.notes,
        created_at=registered.created_at,
        updated_at=registered.updated_at,
    )

    result = repository.update(
        updated_book,
    )

    assert result is True

    loaded = repository.get_by_id(
        registered.id,
    )

    assert loaded is not None
    assert loaded.is_favorite is True


def test_update_changes_is_favorite_from_true_to_false(
    repository: BookRepository,
) -> None:
    """お気に入りをONからOFFへ更新できる。"""
    registered = repository.add(
        create_book_item(
            title="更新対象書籍",
            is_favorite=True,
        )
    )

    updated_book = BookItem(
        id=registered.id,
        title=registered.title,
        isbn=registered.isbn,
        magazine_code=registered.magazine_code,
        author=registered.author,
        publisher=registered.publisher,
        publication_format=registered.publication_format,
        description=registered.description,
        cover_image_url=registered.cover_image_url,
        cover_image_path=registered.cover_image_path,
        completion_month=registered.completion_month,
        reading_status=registered.reading_status,
        is_favorite=False,
        notes=registered.notes,
        created_at=registered.created_at,
        updated_at=registered.updated_at,
    )

    result = repository.update(
        updated_book,
    )

    assert result is True

    loaded = repository.get_by_id(
        registered.id,
    )

    assert loaded is not None
    assert loaded.is_favorite is False


def test_is_favorite_is_independent_from_reading_status_and_completion_month(
    repository: BookRepository,
) -> None:
    """お気に入りを読書状態・読了年月と独立して保持できる。"""
    registered = repository.add(
        create_book_item(
            title="独立性確認書籍",
            completion_month="2025-05",
            reading_status="reading",
            is_favorite=True,
        )
    )

    loaded = repository.get_by_id(
        registered.id,
    )

    assert loaded is not None
    assert loaded.completion_month == "2025-05"
    assert loaded.reading_status == "reading"
    assert loaded.is_favorite is True


def test_add_stores_none_rating(
    repository: BookRepository,
) -> None:
    """未評価を登録・取得できる。"""
    book = create_book_item(
        title="未評価書籍",
        rating=None,
    )

    registered = repository.add(book)

    assert registered.id is not None

    loaded = repository.get_by_id(
        registered.id,
    )

    assert loaded is not None
    assert loaded.rating is None


@pytest.mark.parametrize(
    "rating",
    [
        1,
        2,
        3,
        4,
        5,
    ],
)
def test_add_stores_rating(
    repository: BookRepository,
    rating: int,
) -> None:
    """1から5の評価を登録・取得できる。"""
    book = create_book_item(
        title="評価済み書籍",
        rating=rating,
    )

    registered = repository.add(book)

    assert registered.id is not None

    loaded = repository.get_by_id(
        registered.id,
    )

    assert loaded is not None
    assert loaded.rating == rating


def test_update_changes_rating_from_none_to_five(
    repository: BookRepository,
) -> None:
    """評価を未評価から5へ更新できる。"""
    registered = repository.add(
        create_book_item(
            title="更新対象書籍",
            rating=None,
        )
    )

    updated_book = BookItem(
        id=registered.id,
        title=registered.title,
        isbn=registered.isbn,
        magazine_code=registered.magazine_code,
        author=registered.author,
        publisher=registered.publisher,
        publication_format=registered.publication_format,
        description=registered.description,
        cover_image_url=registered.cover_image_url,
        cover_image_path=registered.cover_image_path,
        completion_month=registered.completion_month,
        reading_status=registered.reading_status,
        is_favorite=registered.is_favorite,
        rating=5,
        notes=registered.notes,
        created_at=registered.created_at,
        updated_at=registered.updated_at,
    )

    result = repository.update(
        updated_book,
    )

    assert result is True

    loaded = repository.get_by_id(
        registered.id,
    )

    assert loaded is not None
    assert loaded.rating == 5


def test_update_changes_rating(
    repository: BookRepository,
) -> None:
    """評価値を別の評価値へ更新できる。"""
    registered = repository.add(
        create_book_item(
            title="更新対象書籍",
            rating=5,
        )
    )

    updated_book = BookItem(
        id=registered.id,
        title=registered.title,
        isbn=registered.isbn,
        magazine_code=registered.magazine_code,
        author=registered.author,
        publisher=registered.publisher,
        publication_format=registered.publication_format,
        description=registered.description,
        cover_image_url=registered.cover_image_url,
        cover_image_path=registered.cover_image_path,
        completion_month=registered.completion_month,
        reading_status=registered.reading_status,
        is_favorite=registered.is_favorite,
        rating=2,
        notes=registered.notes,
        created_at=registered.created_at,
        updated_at=registered.updated_at,
    )

    result = repository.update(
        updated_book,
    )

    assert result is True

    loaded = repository.get_by_id(
        registered.id,
    )

    assert loaded is not None
    assert loaded.rating == 2


def test_update_can_clear_rating(
    repository: BookRepository,
) -> None:
    """評価を未評価へ戻せる。"""
    registered = repository.add(
        create_book_item(
            title="更新対象書籍",
            rating=5,
        )
    )

    updated_book = BookItem(
        id=registered.id,
        title=registered.title,
        isbn=registered.isbn,
        magazine_code=registered.magazine_code,
        author=registered.author,
        publisher=registered.publisher,
        publication_format=registered.publication_format,
        description=registered.description,
        cover_image_url=registered.cover_image_url,
        cover_image_path=registered.cover_image_path,
        completion_month=registered.completion_month,
        reading_status=registered.reading_status,
        is_favorite=registered.is_favorite,
        rating=None,
        notes=registered.notes,
        created_at=registered.created_at,
        updated_at=registered.updated_at,
    )

    result = repository.update(
        updated_book,
    )

    assert result is True

    loaded = repository.get_by_id(
        registered.id,
    )

    assert loaded is not None
    assert loaded.rating is None


def test_rating_is_independent_from_other_reading_fields(
    repository: BookRepository,
) -> None:
    """評価を読書状態・読了年月・お気に入りと独立して保持できる。"""
    registered = repository.add(
        create_book_item(
            title="評価独立性確認書籍",
            completion_month="2025-05",
            reading_status="unread",
            is_favorite=False,
            rating=5,
        )
    )

    loaded = repository.get_by_id(
        registered.id,
    )

    assert loaded is not None
    assert loaded.completion_month == "2025-05"
    assert loaded.reading_status == "unread"
    assert loaded.is_favorite is False
    assert loaded.rating == 5


def test_search_by_conditions_finds_unset_reading_status(
    repository: BookRepository,
) -> None:
    """未設定の読書状態を検索できる。"""
    matched = repository.add(
        create_book_item(
            title="未設定の書籍",
            reading_status=None,
        )
    )
    repository.add(
        create_book_item(
            title="読書中の書籍",
            reading_status="reading",
        )
    )

    result = repository.search_by_conditions(
        reading_status_filter="unset",
    )

    assert result == [
        matched,
    ]


def test_search_by_conditions_finds_unread_reading_status(
    repository: BookRepository,
) -> None:
    """未読の書籍を検索できる。"""
    matched = repository.add(
        create_book_item(
            title="未読の書籍",
            reading_status="unread",
        )
    )
    repository.add(
        create_book_item(
            title="読書中の書籍",
            reading_status="reading",
        )
    )

    result = repository.search_by_conditions(
        reading_status_filter="unread",
    )

    assert result == [
        matched,
    ]


def test_search_by_conditions_finds_reading_reading_status(
    repository: BookRepository,
) -> None:
    """読書中の書籍を検索できる。"""
    matched = repository.add(
        create_book_item(
            title="読書中の書籍",
            reading_status="reading",
        )
    )
    repository.add(
        create_book_item(
            title="読了した書籍",
            reading_status="completed",
        )
    )

    result = repository.search_by_conditions(
        reading_status_filter="reading",
    )

    assert result == [
        matched,
    ]


def test_search_by_conditions_finds_completed_reading_status(
    repository: BookRepository,
) -> None:
    """読了した書籍を検索できる。"""
    matched = repository.add(
        create_book_item(
            title="読了した書籍",
            reading_status="completed",
        )
    )
    repository.add(
        create_book_item(
            title="未読の書籍",
            reading_status="unread",
        )
    )

    result = repository.search_by_conditions(
        reading_status_filter="completed",
    )

    assert result == [
        matched,
    ]


def test_search_by_conditions_finds_favorites(
    repository: BookRepository,
) -> None:
    """お気に入りの書籍だけを検索できる。"""
    matched = repository.add(
        create_book_item(
            title="お気に入りの書籍",
            is_favorite=True,
        )
    )
    repository.add(
        create_book_item(
            title="通常の書籍",
            is_favorite=False,
        )
    )

    result = repository.search_by_conditions(
        favorite_filter="favorite",
    )

    assert result == [
        matched,
    ]


def test_search_by_conditions_finds_non_favorites(
    repository: BookRepository,
) -> None:
    """お気に入り以外の書籍だけを検索できる。"""
    matched = repository.add(
        create_book_item(
            title="通常の書籍",
            is_favorite=False,
        )
    )
    repository.add(
        create_book_item(
            title="お気に入りの書籍",
            is_favorite=True,
        )
    )

    result = repository.search_by_conditions(
        favorite_filter="not_favorite",
    )

    assert result == [
        matched,
    ]


def test_search_by_conditions_finds_unrated_books(
    repository: BookRepository,
) -> None:
    """未評価の書籍を検索できる。"""
    matched = repository.add(
        create_book_item(
            title="未評価の書籍",
            rating=None,
        )
    )
    repository.add(
        create_book_item(
            title="評価済みの書籍",
            rating=3,
        )
    )

    result = repository.search_by_conditions(
        rating_filter="unrated",
    )

    assert result == [
        matched,
    ]


def test_search_by_conditions_finds_rating_one_or_higher(
    repository: BookRepository,
) -> None:
    """評価1以上の書籍を検索できる。"""
    first = repository.add(
        create_book_item(
            title="評価1",
            rating=1,
        )
    )
    second = repository.add(
        create_book_item(
            title="評価5",
            rating=5,
        )
    )
    repository.add(
        create_book_item(
            title="未評価",
            rating=None,
        )
    )

    result = repository.search_by_conditions(
        rating_filter=1,
    )

    assert result == [
        second,
        first,
    ]


def test_search_by_conditions_finds_rating_three_or_higher(
    repository: BookRepository,
) -> None:
    """評価3以上の書籍を検索できる。"""
    repository.add(
        create_book_item(
            title="評価2",
            rating=2,
        )
    )
    first = repository.add(
        create_book_item(
            title="評価3",
            rating=3,
        )
    )
    second = repository.add(
        create_book_item(
            title="評価5",
            rating=5,
        )
    )

    result = repository.search_by_conditions(
        rating_filter=3,
    )

    assert result == [
        second,
        first,
    ]


def test_search_by_conditions_finds_rating_five(
    repository: BookRepository,
) -> None:
    """評価5の書籍を検索できる。"""
    matched = repository.add(
        create_book_item(
            title="評価5",
            rating=5,
        )
    )
    repository.add(
        create_book_item(
            title="評価4",
            rating=4,
        )
    )

    result = repository.search_by_conditions(
        rating_filter=5,
    )

    assert result == [
        matched,
    ]


def test_search_by_conditions_combines_bibliographic_and_reading_status(
    repository: BookRepository,
) -> None:
    """書誌情報と読書状態をAND条件で検索できる。"""
    matched = repository.add(
        create_book_item(
            title="海辺のカフカ",
            author="村上春樹",
            reading_status="completed",
        )
    )
    repository.add(
        create_book_item(
            title="ノルウェイの森",
            author="村上春樹",
            reading_status="reading",
        )
    )
    repository.add(
        create_book_item(
            title="別の書籍",
            author="別の著者",
            reading_status="completed",
        )
    )

    result = repository.search_by_conditions(
        author="村上",
        reading_status_filter="completed",
    )

    assert result == [
        matched,
    ]


def test_search_by_conditions_combines_reading_filters(
    repository: BookRepository,
) -> None:
    """読書状態・お気に入り・評価をAND条件で検索できる。"""
    matched = repository.add(
        create_book_item(
            title="条件一致",
            reading_status="completed",
            is_favorite=True,
            rating=4,
        )
    )
    repository.add(
        create_book_item(
            title="評価不足",
            reading_status="completed",
            is_favorite=True,
            rating=3,
        )
    )
    repository.add(
        create_book_item(
            title="お気に入り以外",
            reading_status="completed",
            is_favorite=False,
            rating=5,
        )
    )

    result = repository.search_by_conditions(
        reading_status_filter="completed",
        favorite_filter="favorite",
        rating_filter=4,
    )

    assert result == [
        matched,
    ]


def test_search_by_conditions_combines_existing_and_new_conditions(
    repository: BookRepository,
) -> None:
    """既存条件と新しい検索条件をすべてANDで組み合わせられる。"""
    matched = repository.add(
        create_book_item(
            title="海辺のカフカ",
            author="村上春樹",
            publisher="新潮社",
            isbn="9784101001547",
            reading_status="completed",
            is_favorite=True,
            rating=5,
        )
    )
    repository.add(
        create_book_item(
            title="海辺のカフカ",
            author="村上春樹",
            publisher="新潮社",
            isbn="9784101001547",
            reading_status="completed",
            is_favorite=True,
            rating=4,
        )
    )

    result = repository.search_by_conditions(
        title="海辺",
        author="村上",
        publisher="新潮",
        isbn="9784101001547",
        reading_status_filter="completed",
        favorite_filter="favorite",
        rating_filter=5,
    )

    assert result == [
        matched,
    ]


def test_add_stores_multiple_tags(
    repository: BookRepository,
) -> None:
    """複数タグを書籍へ登録して名称順で取得できる。"""
    registered = repository.add(
        create_book_item(
            title="タグ付き書籍",
            tags=("技術書", "Python", "仕事"),
        )
    )

    stored = repository.get_by_id(
        registered.id,  # type: ignore[arg-type]
    )

    assert stored is not None
    assert stored.tags == (
        "Python",
        "仕事",
        "技術書",
    )


def test_add_reuses_same_tag_for_multiple_books(
    repository: BookRepository,
) -> None:
    """同じタグを複数の書籍で共有できる。"""
    first = repository.add(
        create_book_item(
            title="1冊目",
            tags=("小説",),
        )
    )
    second = repository.add(
        create_book_item(
            title="2冊目",
            tags=("小説",),
        )
    )

    tags = repository.get_all_tags()

    assert len(tags) == 1
    assert tags[0].name == "小説"
    assert repository.count_books_by_tag(
        tags[0].id,  # type: ignore[arg-type]
    ) == 2
    assert repository.get_by_id(
        first.id,  # type: ignore[arg-type]
    ).tags == ("小説",)  # type: ignore[union-attr]
    assert repository.get_by_id(
        second.id,  # type: ignore[arg-type]
    ).tags == ("小説",)  # type: ignore[union-attr]


def test_add_does_not_duplicate_same_book_tag_relation(
    repository: BookRepository,
) -> None:
    """同じ書籍とタグの関連を重複登録しない。"""
    registered = repository.add(
        create_book_item(
            title="重複タグ書籍",
            tags=("小説", "小説"),
        )
    )

    stored = repository.get_by_id(
        registered.id,  # type: ignore[arg-type]
    )

    assert stored is not None
    assert stored.tags == ("小説",)


def test_add_rolls_back_book_and_tags_on_tag_error(
    repository: BookRepository,
) -> None:
    """タグ登録失敗時に書籍とタグをすべて戻す。"""
    with pytest.raises(
        sqlite3.DatabaseError,
        match="登録したタグのIDを取得できませんでした。",
    ):
        repository.add(
            create_book_item(
                title="登録失敗書籍",
                tags=("正常タグ", "不正|タグ"),
            )
        )

    assert repository.get_all() == []
    assert repository.get_all_tags() == []


def test_get_all_restores_tags_for_each_book(
    repository: BookRepository,
) -> None:
    """一覧取得時に各書籍のタグを復元する。"""
    first = repository.add(
        create_book_item(
            title="1冊目",
            tags=("小説",),
        )
    )
    second = repository.add(
        create_book_item(
            title="2冊目",
            tags=("仕事", "技術書"),
        )
    )

    result = repository.get_all()

    assert result[0] == replace(
        second,
        tags=("仕事", "技術書"),
    )
    assert result[1] == first


def test_get_all_sorted_restores_tags(
    repository: BookRepository,
) -> None:
    """並べ替え取得時にタグを復元する。"""
    registered = repository.add(
        create_book_item(
            title="タグ付き書籍",
            tags=("小説",),
        )
    )

    result = repository.get_all_sorted(
        sort_by="title",
    )

    assert result == [registered]


@pytest.mark.parametrize(
    "search_method",
    [
        "search_by_title",
        "search_by_author",
        "search_by_publisher",
        "find_by_isbn",
        "find_by_magazine_code",
    ],
)
def test_individual_search_restores_tags(
    repository: BookRepository,
    search_method: str,
) -> None:
    """個別検索で取得した書籍へタグを復元する。"""
    registered = repository.add(
        create_book_item(
            title="検索対象書籍",
            isbn="9784101010014",
            magazine_code="1234507",
            author="検索対象著者",
            publisher="検索対象出版社",
            tags=("検索タグ",),
        )
    )
    arguments = {
        "search_by_title": "検索対象",
        "search_by_author": "検索対象",
        "search_by_publisher": "検索対象",
        "find_by_isbn": "9784101010014",
        "find_by_magazine_code": "1234507",
    }

    method = getattr(repository, search_method)
    result = method(arguments[search_method])

    assert result == [registered]


def test_update_replaces_book_tags(
    repository: BookRepository,
) -> None:
    """書籍更新時にタグの追加と解除ができる。"""
    registered = repository.add(
        create_book_item(
            title="更新対象書籍",
            tags=("解除するタグ", "残すタグ"),
        )
    )
    updated = replace(
        registered,
        tags=("残すタグ", "追加するタグ"),
        updated_at="2026-09-04 12:00:00",
    )

    result = repository.update(updated)
    stored = repository.get_by_id(
        registered.id,  # type: ignore[arg-type]
    )

    assert result is True
    assert stored is not None
    assert stored.tags == (
        "残すタグ",
        "追加するタグ",
    )


def test_update_can_clear_all_book_tags(
    repository: BookRepository,
) -> None:
    """書籍に設定されたすべてのタグを解除できる。"""
    registered = repository.add(
        create_book_item(
            title="更新対象書籍",
            tags=("小説",),
        )
    )
    updated = replace(
        registered,
        tags=(),
        updated_at="2026-09-04 12:00:00",
    )

    result = repository.update(updated)

    assert result is True
    assert repository.get_by_id(
        registered.id,  # type: ignore[arg-type]
    ).tags == ()  # type: ignore[union-attr]
    assert [
        tag.name
        for tag in repository.get_all_tags()
    ] == ["小説"]


def test_update_missing_book_does_not_create_tag(
    repository: BookRepository,
) -> None:
    """存在しない書籍の更新でタグを作成しない。"""
    book = create_book_item(
        title="存在しない書籍",
        tags=("作成されないタグ",),
    )
    book.id = 999

    result = repository.update(book)

    assert result is False
    assert repository.get_all_tags() == []


def test_get_all_tags_returns_tags_in_name_order(
    repository: BookRepository,
) -> None:
    """登録済みタグを名称の昇順で取得する。"""
    repository.add(
        create_book_item(
            title="タグ付き書籍",
            tags=("技術書", "Python", "仕事"),
        )
    )

    result = repository.get_all_tags()

    assert [tag.name for tag in result] == [
        "Python",
        "仕事",
        "技術書",
    ]
    assert all(
        isinstance(tag, Tag)
        for tag in result
    )


def test_get_tag_by_id_and_name(
    repository: BookRepository,
) -> None:
    """IDと名称から同じタグを取得できる。"""
    repository.add(
        create_book_item(tags=("小説",))
    )
    tag = repository.get_tag_by_name("小説")

    assert tag is not None
    assert tag.id is not None
    assert repository.get_tag_by_id(tag.id) == tag


def test_get_tag_returns_none_for_missing_value(
    repository: BookRepository,
) -> None:
    """存在しないIDと名称ではNoneを返す。"""
    assert repository.get_tag_by_id(999) is None
    assert repository.get_tag_by_name("存在しないタグ") is None


def test_rename_tag_updates_all_linked_books(
    repository: BookRepository,
) -> None:
    """タグ名変更を関連するすべての書籍へ反映する。"""
    first = repository.add(
        create_book_item(
            title="1冊目",
            tags=("旧名称",),
        )
    )
    second = repository.add(
        create_book_item(
            title="2冊目",
            tags=("旧名称",),
        )
    )
    tag = repository.get_tag_by_name("旧名称")

    assert tag is not None
    result = repository.rename_tag(
        tag_id=tag.id,  # type: ignore[arg-type]
        name="新名称",
        updated_at="2026-09-04 13:00:00",
    )

    assert result is True
    assert repository.get_tag_by_name("旧名称") is None
    renamed = repository.get_tag_by_name("新名称")
    assert renamed is not None
    assert renamed.updated_at == "2026-09-04 13:00:00"
    assert repository.get_by_id(
        first.id,  # type: ignore[arg-type]
    ).tags == ("新名称",)  # type: ignore[union-attr]
    assert repository.get_by_id(
        second.id,  # type: ignore[arg-type]
    ).tags == ("新名称",)  # type: ignore[union-attr]


def test_rename_tag_returns_false_for_missing_id(
    repository: BookRepository,
) -> None:
    """存在しないタグIDの名称変更ではFalseを返す。"""
    result = repository.rename_tag(
        tag_id=999,
        name="新名称",
        updated_at="2026-09-04 13:00:00",
    )

    assert result is False


def test_rename_tag_rejects_duplicate_name(
    repository: BookRepository,
) -> None:
    """別タグと同じ名称への変更を拒否する。"""
    repository.add(
        create_book_item(
            tags=("既存タグ", "変更対象"),
        )
    )
    target = repository.get_tag_by_name("変更対象")

    assert target is not None
    with pytest.raises(sqlite3.IntegrityError):
        repository.rename_tag(
            tag_id=target.id,  # type: ignore[arg-type]
            name="既存タグ",
            updated_at="2026-09-04 13:00:00",
        )


def test_count_books_by_tag_returns_zero_for_unused_tag(
    repository: BookRepository,
) -> None:
    """未使用タグの書籍数として0を返す。"""
    registered = repository.add(
        create_book_item(tags=("未使用になるタグ",))
    )
    updated = replace(
        registered,
        tags=(),
    )
    repository.update(updated)
    tag = repository.get_tag_by_name("未使用になるタグ")

    assert tag is not None
    assert repository.count_books_by_tag(
        tag.id,  # type: ignore[arg-type]
    ) == 0


def test_delete_tag_removes_relations_from_books(
    repository: BookRepository,
) -> None:
    """タグ削除時にすべての書籍との関連を解除する。"""
    first = repository.add(
        create_book_item(
            title="1冊目",
            tags=("削除対象", "残すタグ"),
        )
    )
    second = repository.add(
        create_book_item(
            title="2冊目",
            tags=("削除対象",),
        )
    )
    target = repository.get_tag_by_name("削除対象")

    assert target is not None
    result = repository.delete_tag(
        target.id,  # type: ignore[arg-type]
    )

    assert result is True
    assert repository.get_by_id(
        first.id,  # type: ignore[arg-type]
    ).tags == ("残すタグ",)  # type: ignore[union-attr]
    assert repository.get_by_id(
        second.id,  # type: ignore[arg-type]
    ).tags == ()  # type: ignore[union-attr]


def test_delete_tag_returns_false_for_missing_id(
    repository: BookRepository,
) -> None:
    """存在しないタグIDの削除ではFalseを返す。"""
    assert repository.delete_tag(999) is False


def test_delete_book_keeps_unused_tag(
    repository: BookRepository,
) -> None:
    """書籍削除後も未使用となったタグを保持する。"""
    registered = repository.add(
        create_book_item(tags=("残るタグ",))
    )
    tag = repository.get_tag_by_name("残るタグ")

    assert tag is not None
    repository.delete(
        registered.id,  # type: ignore[arg-type]
    )

    assert repository.get_tag_by_name("残るタグ") == tag
    assert repository.count_books_by_tag(
        tag.id,  # type: ignore[arg-type]
    ) == 0


def test_search_by_conditions_finds_tagged_books(
    repository: BookRepository,
) -> None:
    """指定したタグが設定された書籍を検索できる。"""
    first = repository.add(
        create_book_item(
            title="1冊目",
            tags=("小説",),
        )
    )
    second = repository.add(
        create_book_item(
            title="2冊目",
            tags=("小説", "歴史"),
        )
    )
    repository.add(
        create_book_item(
            title="3冊目",
            tags=("技術書",),
        )
    )

    result = repository.search_by_conditions(
        tag_name="小説",
    )

    assert result == [
        replace(
            second,
            tags=("小説", "歴史"),
        ),
        first,
    ]


def test_search_by_conditions_finds_untagged_books(
    repository: BookRepository,
) -> None:
    """タグ未設定の書籍だけを検索できる。"""
    matched = repository.add(
        create_book_item(
            title="タグなし",
            tags=(),
        )
    )
    repository.add(
        create_book_item(
            title="タグあり",
            tags=("小説",),
        )
    )

    result = repository.search_by_conditions(
        untagged_only=True,
    )

    assert result == [matched]


def test_search_by_conditions_combines_tag_and_existing_condition(
    repository: BookRepository,
) -> None:
    """タグと既存条件をANDで検索できる。"""
    matched = repository.add(
        create_book_item(
            title="Python入門",
            is_favorite=True,
            tags=("技術書",),
        )
    )
    repository.add(
        create_book_item(
            title="Python応用",
            is_favorite=False,
            tags=("技術書",),
        )
    )
    repository.add(
        create_book_item(
            title="別の書籍",
            is_favorite=True,
            tags=("小説",),
        )
    )

    result = repository.search_by_conditions(
        title="Python",
        favorite_filter="favorite",
        tag_name="技術書",
    )

    assert result == [matched]


def test_search_by_conditions_tag_uses_exact_match(
    repository: BookRepository,
) -> None:
    """タグ名を完全一致で検索する。"""
    exact = repository.add(
        create_book_item(
            title="完全一致",
            tags=("Python",),
        )
    )
    repository.add(
        create_book_item(
            title="部分一致のみ",
            tags=("Python入門",),
        )
    )

    result = repository.search_by_conditions(
        tag_name="Python",
    )

    assert result == [exact]


def test_search_by_conditions_handles_sql_special_tag_name(
    repository: BookRepository,
) -> None:
    """SQL特殊文字を含むタグ名を安全に検索できる。"""
    registered = repository.add(
        create_book_item(
            tags=("O'Reilly, 100%",),
        )
    )

    result = repository.search_by_conditions(
        tag_name="O'Reilly, 100%",
    )

    assert result == [registered]


def test_search_by_conditions_rejects_conflicting_tag_filters(
    repository: BookRepository,
) -> None:
    """タグ名とタグ未設定の同時指定を拒否する。"""
    with pytest.raises(
        ValueError,
        match="タグとタグ未設定を同時に指定できません。",
    ):
        repository.search_by_conditions(
            tag_name="小説",
            untagged_only=True,
        )
