"""Reading statistics models."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReadingStatisticsSummary:
    """読書履歴の全体集計を表すデータモデル。"""

    total_history_count: int
    books_with_history_count: int
    completed_history_count: int
    reread_book_count: int


@dataclass(frozen=True, slots=True)
class MonthlyReadingCount:
    """一か月分の読了記録数を表すデータモデル。"""

    year: int
    month: int
    completed_count: int
