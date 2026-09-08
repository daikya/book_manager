"""Tests for reading statistics models."""

from dataclasses import FrozenInstanceError

import pytest

from book_manager.models.reading_statistics import (
    MonthlyReadingCount,
    ReadingStatisticsSummary,
)


def test_reading_statistics_summary_stores_values() -> None:
    """全体集計の各値を保持する。"""
    summary = ReadingStatisticsSummary(
        total_history_count=12,
        books_with_history_count=8,
        completed_history_count=10,
        reread_book_count=3,
    )

    assert summary.total_history_count == 12
    assert summary.books_with_history_count == 8
    assert summary.completed_history_count == 10
    assert summary.reread_book_count == 3


def test_reading_statistics_summary_accepts_zero_values() -> None:
    """履歴がない場合の0件を保持できる。"""
    summary = ReadingStatisticsSummary(
        total_history_count=0,
        books_with_history_count=0,
        completed_history_count=0,
        reread_book_count=0,
    )

    assert summary == ReadingStatisticsSummary(
        total_history_count=0,
        books_with_history_count=0,
        completed_history_count=0,
        reread_book_count=0,
    )


def test_reading_statistics_summary_compares_by_value() -> None:
    """同じ集計値を持つModelは等価になる。"""
    first = ReadingStatisticsSummary(12, 8, 10, 3)
    second = ReadingStatisticsSummary(12, 8, 10, 3)

    assert first == second


def test_reading_statistics_summary_is_frozen() -> None:
    """生成後に全体集計値を変更できない。"""
    summary = ReadingStatisticsSummary(12, 8, 10, 3)

    with pytest.raises(FrozenInstanceError):
        summary.total_history_count = 13  # type: ignore[misc]


def test_reading_statistics_summary_uses_slots() -> None:
    """全体集計Modelが動的属性を持たない。"""
    summary = ReadingStatisticsSummary(12, 8, 10, 3)

    assert not hasattr(summary, "__dict__")


def test_monthly_reading_count_stores_values() -> None:
    """対象年・月・読了記録数を保持する。"""
    monthly_count = MonthlyReadingCount(
        year=2026,
        month=9,
        completed_count=4,
    )

    assert monthly_count.year == 2026
    assert monthly_count.month == 9
    assert monthly_count.completed_count == 4


def test_monthly_reading_count_accepts_zero_count() -> None:
    """読了記録がない月の0件を保持できる。"""
    monthly_count = MonthlyReadingCount(
        year=2026,
        month=2,
        completed_count=0,
    )

    assert monthly_count.completed_count == 0


def test_monthly_reading_count_compares_by_value() -> None:
    """同じ月別集計値を持つModelは等価になる。"""
    first = MonthlyReadingCount(2026, 9, 4)
    second = MonthlyReadingCount(2026, 9, 4)

    assert first == second


def test_monthly_reading_count_is_frozen() -> None:
    """生成後に月別集計値を変更できない。"""
    monthly_count = MonthlyReadingCount(2026, 9, 4)

    with pytest.raises(FrozenInstanceError):
        monthly_count.completed_count = 5  # type: ignore[misc]


def test_monthly_reading_count_uses_slots() -> None:
    """月別集計Modelが動的属性を持たない。"""
    monthly_count = MonthlyReadingCount(2026, 9, 4)

    assert not hasattr(monthly_count, "__dict__")
