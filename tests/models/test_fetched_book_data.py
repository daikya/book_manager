"""Tests for the FetchedBookData model."""

import pytest

from book_manager.models.fetched_book_data import FetchedBookData


def test_fetched_book_data_can_be_created_with_isbn_only() -> None:
    """isbnだけを指定して生成できることを確認する。"""
    fetched_data = FetchedBookData(
        isbn="9784163917733",
    )

    assert fetched_data.isbn == "9784163917733"


def test_fetched_book_data_optional_fields_have_default_values() -> None:
    """任意属性の初期値を確認する。"""
    fetched_data = FetchedBookData(
        isbn="9784163917733",
    )

    assert fetched_data.title is None
    assert fetched_data.author is None
    assert fetched_data.publisher is None
    assert fetched_data.publication_date is None
    assert fetched_data.publication_format is None
    assert fetched_data.description is None
    assert fetched_data.cover_image_url is None
    assert fetched_data.sources == ()
    assert fetched_data.raw_data == {}


def test_fetched_book_data_accepts_all_fields() -> None:
    """すべての属性を指定して生成できることを確認する。"""
    raw_data = {
        "Google Books": {
            "response": {
                "totalItems": 1,
            },
        },
    }

    fetched_data = FetchedBookData(
        isbn="9784163917733",
        title="テスト書籍",
        author="著者A、著者B",
        publisher="テスト出版社",
        publication_date="2023-10-27",
        publication_format="単行本",
        description="テスト書籍の内容紹介。",
        cover_image_url="https://example.com/cover.jpg",
        sources=("Google Books", "openBD"),
        raw_data=raw_data,
    )

    assert fetched_data.isbn == "9784163917733"
    assert fetched_data.title == "テスト書籍"
    assert fetched_data.author == "著者A、著者B"
    assert fetched_data.publisher == "テスト出版社"
    assert fetched_data.publication_date == "2023-10-27"
    assert fetched_data.publication_format == "単行本"
    assert fetched_data.description == "テスト書籍の内容紹介。"
    assert (
        fetched_data.cover_image_url
        == "https://example.com/cover.jpg"
    )
    assert fetched_data.sources == (
        "Google Books",
        "openBD",
    )
    assert fetched_data.raw_data == raw_data


def test_fetched_book_data_requires_isbn() -> None:
    """isbnを省略できないことを確認する。"""
    with pytest.raises(TypeError):
        FetchedBookData()  # type: ignore[call-arg]


def test_fetched_book_data_fields_can_be_updated() -> None:
    """定義済み属性を変更できることを確認する。"""
    fetched_data = FetchedBookData(
        isbn="9784163917733",
        title="旧書名",
    )

    fetched_data.title = "新書名"
    fetched_data.publisher = "新出版社"

    assert fetched_data.title == "新書名"
    assert fetched_data.publisher == "新出版社"


def test_fetched_book_data_rejects_undefined_attribute() -> None:
    """未定義属性を追加できないことを確認する。"""
    fetched_data = FetchedBookData(
        isbn="9784163917733",
    )

    with pytest.raises(AttributeError):
        fetched_data.unexpected = "value"  # type: ignore[attr-defined]


def test_fetched_book_data_with_same_values_are_equal() -> None:
    """同じ属性値を持つモデル同士が等しいことを確認する。"""
    first = FetchedBookData(
        isbn="9784163917733",
        title="テスト書籍",
        author="著者A",
    )
    second = FetchedBookData(
        isbn="9784163917733",
        title="テスト書籍",
        author="著者A",
    )

    assert first == second


def test_fetched_book_data_with_different_values_are_not_equal() -> None:
    """異なる属性値を持つモデル同士が等しくないことを確認する。"""
    first = FetchedBookData(
        isbn="9784163917733",
        title="テスト書籍A",
    )
    second = FetchedBookData(
        isbn="9784163917733",
        title="テスト書籍B",
    )

    assert first != second


def test_raw_data_is_not_shared_between_instances() -> None:
    """raw_dataがインスタンス間で共有されないことを確認する。"""
    first = FetchedBookData(
        isbn="9784163917733",
    )
    second = FetchedBookData(
        isbn="9784101109180",
    )

    first.raw_data["Google Books"] = {
        "response": {},
    }

    assert second.raw_data == {}