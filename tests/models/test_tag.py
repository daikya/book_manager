"""Tests for the Tag model."""

import pytest

from book_manager.models.tag import Tag


def test_tag_can_be_created_with_name_only() -> None:
    """nameだけを指定して生成できる。"""
    tag = Tag(name="小説")

    assert tag.name == "小説"


def test_tag_optional_fields_default_to_none() -> None:
    """任意属性の初期値がNoneになる。"""
    tag = Tag(name="小説")

    assert tag.id is None
    assert tag.created_at is None
    assert tag.updated_at is None


def test_tag_accepts_all_fields() -> None:
    """すべての属性を指定して生成できる。"""
    tag = Tag(
        name="技術書",
        id=1,
        created_at="2026-09-04 10:00:00",
        updated_at="2026-09-04 11:00:00",
    )

    assert tag.name == "技術書"
    assert tag.id == 1
    assert tag.created_at == "2026-09-04 10:00:00"
    assert tag.updated_at == "2026-09-04 11:00:00"


def test_tag_requires_name() -> None:
    """nameを省略できない。"""
    with pytest.raises(TypeError):
        Tag()  # type: ignore[call-arg]


def test_tag_fields_can_be_updated() -> None:
    """定義済み属性を変更できる。"""
    tag = Tag(name="旧名称")

    tag.name = "新名称"

    assert tag.name == "新名称"


def test_tag_rejects_undefined_attribute() -> None:
    """未定義属性を追加できない。"""
    tag = Tag(name="小説")

    with pytest.raises(AttributeError):
        tag.unexpected = "value"  # type: ignore[attr-defined]


def test_tags_with_same_values_are_equal() -> None:
    """同じ属性値を持つモデル同士が等しい。"""
    first = Tag(name="小説")
    second = Tag(name="小説")

    assert first == second


def test_tags_with_different_values_are_not_equal() -> None:
    """異なる属性値を持つモデル同士が等しくない。"""
    first = Tag(name="小説")
    second = Tag(name="技術書")

    assert first != second
