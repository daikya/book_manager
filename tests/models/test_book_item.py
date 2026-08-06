"""Tests for the BookItem model."""

import pytest

from book_manager.models.book_item import BookItem


def test_book_item_can_be_created_with_title_only() -> None:
    """titleだけを指定して生成できることを確認する。"""
    book_item = BookItem(title="吾輩は猫である")

    assert book_item.title == "吾輩は猫である"


def test_book_item_optional_fields_default_to_none() -> None:
    """任意属性の初期値がNoneになることを確認する。"""
    book_item = BookItem(title="吾輩は猫である")

    assert book_item.id is None
    assert book_item.isbn is None
    assert book_item.magazine_code is None
    assert book_item.author is None
    assert book_item.publisher is None
    assert book_item.publication_format is None
    assert book_item.description is None
    assert book_item.cover_image_url is None
    assert book_item.cover_image_path is None
    assert book_item.completion_month is None
    assert book_item.notes is None
    assert book_item.created_at is None
    assert book_item.updated_at is None


def test_book_item_accepts_all_fields() -> None:
    """すべての属性を指定して生成できることを確認する。"""
    book_item = BookItem(
        title="吾輩は猫である",
        id=1,
        isbn="9784101010014",
        magazine_code=None,
        author="夏目漱石",
        publisher="新潮社",
        publication_format="文庫",
        description="猫の視点から人間社会を描いた作品。",
        cover_image_url="https://example.com/cover.jpg",
        cover_image_path="cache/covers/cover.jpg",
        completion_month="2026-07",
        notes="再読。",
        created_at="2026-07-21 15:00:00",
        updated_at="2026-07-21 15:00:00",
    )

    assert book_item.title == "吾輩は猫である"
    assert book_item.id == 1
    assert book_item.isbn == "9784101010014"
    assert book_item.magazine_code is None
    assert book_item.author == "夏目漱石"
    assert book_item.publisher == "新潮社"
    assert book_item.publication_format == "文庫"
    assert book_item.description == "猫の視点から人間社会を描いた作品。"
    assert (
        book_item.cover_image_url
        == "https://example.com/cover.jpg"
    )
    assert (
        book_item.cover_image_path
        == "cache/covers/cover.jpg"
    )
    assert book_item.completion_month == "2026-07"
    assert book_item.notes == "再読。"
    assert book_item.created_at == "2026-07-21 15:00:00"
    assert book_item.updated_at == "2026-07-21 15:00:00"


def test_book_item_requires_title() -> None:
    """titleを省略できないことを確認する。"""
    with pytest.raises(TypeError):
        BookItem()  # type: ignore[call-arg]


def test_book_item_fields_can_be_updated() -> None:
    """定義済み属性を変更できることを確認する。"""
    book_item = BookItem(title="旧書名")

    book_item.title = "新書名"
    book_item.notes = "更新済み。"

    assert book_item.title == "新書名"
    assert book_item.notes == "更新済み。"


def test_book_item_rejects_undefined_attribute() -> None:
    """未定義属性を追加できないことを確認する。"""
    book_item = BookItem(title="吾輩は猫である")

    with pytest.raises(AttributeError):
        book_item.unexpected = "value"  # type: ignore[attr-defined]


def test_book_items_with_same_values_are_equal() -> None:
    """同じ属性値を持つモデル同士が等しいことを確認する。"""
    first = BookItem(
        title="吾輩は猫である",
        author="夏目漱石",
    )
    second = BookItem(
        title="吾輩は猫である",
        author="夏目漱石",
    )

    assert first == second


def test_book_items_with_different_values_are_not_equal() -> None:
    """異なる属性値を持つモデル同士が等しくないことを確認する。"""
    first = BookItem(title="吾輩は猫である")
    second = BookItem(title="坊っちゃん")

    assert first != second