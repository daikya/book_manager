"""Tests for the ReadingHistory model."""

import pytest

from book_manager.models.reading_history import ReadingHistory


def test_reading_history_can_be_created_with_book_item_id_only() -> None:
    """book_item_idだけを指定して生成できる。"""
    history = ReadingHistory(book_item_id=1)

    assert history.book_item_id == 1


def test_reading_history_optional_fields_default_to_none() -> None:
    """任意属性の初期値がNoneになる。"""
    history = ReadingHistory(book_item_id=1)

    assert history.id is None
    assert history.started_on is None
    assert history.completed_on is None
    assert history.notes is None
    assert history.created_at is None
    assert history.updated_at is None


def test_reading_history_accepts_all_fields() -> None:
    """すべての属性を指定して生成できる。"""
    history = ReadingHistory(
        book_item_id=10,
        id=3,
        started_on="2026-09-01",
        completed_on="2026-09-07",
        notes="再読で新しい発見があった。",
        created_at="2026-09-07 10:00:00",
        updated_at="2026-09-07 11:00:00",
    )

    assert history.book_item_id == 10
    assert history.id == 3
    assert history.started_on == "2026-09-01"
    assert history.completed_on == "2026-09-07"
    assert history.notes == "再読で新しい発見があった。"
    assert history.created_at == "2026-09-07 10:00:00"
    assert history.updated_at == "2026-09-07 11:00:00"


def test_reading_history_requires_book_item_id() -> None:
    """book_item_idを省略できない。"""
    with pytest.raises(TypeError):
        ReadingHistory()  # type: ignore[call-arg]


def test_reading_history_fields_can_be_updated() -> None:
    """定義済み属性を変更できる。"""
    history = ReadingHistory(
        book_item_id=1,
        started_on="2026-09-01",
    )

    history.completed_on = "2026-09-07"
    history.notes = "読了した。"

    assert history.completed_on == "2026-09-07"
    assert history.notes == "読了した。"


def test_reading_history_rejects_undefined_attribute() -> None:
    """未定義属性を追加できない。"""
    history = ReadingHistory(book_item_id=1)

    with pytest.raises(AttributeError):
        history.unexpected = "value"  # type: ignore[attr-defined]


def test_reading_histories_with_same_values_are_equal() -> None:
    """同じ属性値を持つモデル同士が等しい。"""
    first = ReadingHistory(
        book_item_id=1,
        started_on="2026-09-01",
    )
    second = ReadingHistory(
        book_item_id=1,
        started_on="2026-09-01",
    )

    assert first == second


def test_reading_histories_with_different_values_are_not_equal() -> None:
    """異なる属性値を持つモデル同士が等しくない。"""
    first = ReadingHistory(book_item_id=1)
    second = ReadingHistory(book_item_id=2)

    assert first != second
