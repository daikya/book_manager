"""Application service for reading history management."""

from collections.abc import Callable
from datetime import datetime

from book_manager.models.reading_history import ReadingHistory
from book_manager.models.reading_statistics import (
    MonthlyReadingCount,
    ReadingStatisticsSummary,
)
from book_manager.repositories.book_repository import BookRepository
from book_manager.repositories.reading_history_repository import (
    ReadingHistoryRepository,
)
from book_manager.validators.reading_history_validator import (
    validate_reading_history_dates,
)


class ReadingHistoryService:
    """読書履歴に関するアプリケーションロジックを担当する。"""

    def __init__(
        self,
        repository: ReadingHistoryRepository,
        book_repository: BookRepository,
        now_provider: Callable[[], datetime] = datetime.now,
    ) -> None:
        """ReadingHistoryServiceを初期化する。"""
        self._repository = repository
        self._book_repository = book_repository
        self._now_provider = now_provider

    def add_history(
        self,
        *,
        book_item_id: int,
        started_on: str | None = None,
        completed_on: str | None = None,
        notes: str | None = None,
    ) -> ReadingHistory:
        """指定された書籍へ一回分の読書履歴を登録する。"""
        if self._book_repository.get_by_id(book_item_id) is None:
            raise ValueError(
                "対象の書籍が見つかりません。"
            )

        normalized_started_on = self._normalize_optional_text(
            started_on,
        )
        normalized_completed_on = self._normalize_optional_text(
            completed_on,
        )
        normalized_notes = self._normalize_optional_text(notes)

        self._validate_history_values(
            started_on=normalized_started_on,
            completed_on=normalized_completed_on,
            notes=normalized_notes,
        )
        current_timestamp = self._current_timestamp()

        return self._repository.add(
            ReadingHistory(
                book_item_id=book_item_id,
                started_on=normalized_started_on,
                completed_on=normalized_completed_on,
                notes=normalized_notes,
                created_at=current_timestamp,
                updated_at=current_timestamp,
            )
        )

    def get_history(
        self,
        reading_history_id: int,
    ) -> ReadingHistory | None:
        """IDを指定して読書履歴を1件取得する。"""
        return self._repository.get_by_id(reading_history_id)

    def get_histories_for_book(
        self,
        book_item_id: int,
    ) -> list[ReadingHistory]:
        """指定された書籍の読書履歴を取得する。"""
        if self._book_repository.get_by_id(book_item_id) is None:
            raise ValueError(
                "対象の書籍が見つかりません。"
            )

        return self._repository.get_by_book_id(book_item_id)

    def update_history(
        self,
        reading_history: ReadingHistory,
    ) -> bool:
        """既存の読書履歴を更新する。"""
        if reading_history.id is None:
            raise ValueError(
                "更新対象のReadingHistoryにはidが必要です。"
            )

        existing = self._repository.get_by_id(
            reading_history.id
        )

        if existing is None:
            return False

        normalized_started_on = self._normalize_optional_text(
            reading_history.started_on,
        )
        normalized_completed_on = self._normalize_optional_text(
            reading_history.completed_on,
        )
        normalized_notes = self._normalize_optional_text(
            reading_history.notes,
        )

        self._validate_history_values(
            started_on=normalized_started_on,
            completed_on=normalized_completed_on,
            notes=normalized_notes,
        )
        normalized_history = ReadingHistory(
            id=existing.id,
            book_item_id=existing.book_item_id,
            started_on=normalized_started_on,
            completed_on=normalized_completed_on,
            notes=normalized_notes,
            created_at=existing.created_at,
            updated_at=self._current_timestamp(),
        )

        return self._repository.update(normalized_history)

    def delete_history(
        self,
        reading_history_id: int,
    ) -> bool:
        """IDを指定して読書履歴を削除する。"""
        return self._repository.delete(reading_history_id)

    def get_statistics_summary(
        self,
    ) -> ReadingStatisticsSummary:
        """読書履歴の全体集計を取得する。"""
        summary = self._repository.get_statistics_summary()
        self._validate_statistics_summary(summary)

        return summary

    def get_completed_years(self) -> list[int]:
        """読了記録が存在する年を新しい順で取得する。"""
        years = self._repository.get_completed_years()

        for year in years:
            self._validate_statistics_year(year)

        return years

    def get_monthly_reading_counts(
        self,
        year: int,
    ) -> list[MonthlyReadingCount]:
        """指定年の月別読了数を1月から12月まで取得する。"""
        self._validate_statistics_year(year)
        stored_counts = (
            self._repository.get_monthly_completed_counts(year)
        )
        self._validate_monthly_counts(stored_counts)

        return [
            MonthlyReadingCount(
                year=year,
                month=month,
                completed_count=stored_counts.get(month, 0),
            )
            for month in range(1, 13)
        ]

    @staticmethod
    def _normalize_optional_text(
        value: str | None,
    ) -> str | None:
        """任意入力の文字列を正規化する。"""
        if value is None:
            return None

        normalized_value = value.strip()

        if normalized_value == "":
            return None

        return normalized_value

    @staticmethod
    def _validate_history_values(
        *,
        started_on: str | None,
        completed_on: str | None,
        notes: str | None,
    ) -> None:
        """正規化済みの読書履歴入力値を検証する。"""
        validate_reading_history_dates(
            started_on,
            completed_on,
        )

        if (
            started_on is None
            and completed_on is None
            and notes is None
        ):
            raise ValueError(
                "読書開始日、読了日、読書メモのいずれかを"
                "入力してください。"
            )

    def _current_timestamp(self) -> str:
        """現在日時を保存用文字列として取得する。"""
        return self._now_provider().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    @classmethod
    def _validate_statistics_summary(
        cls,
        summary: ReadingStatisticsSummary,
    ) -> None:
        """全体集計が0以上の整数で構成されることを確認する。"""
        counts = (
            summary.total_history_count,
            summary.books_with_history_count,
            summary.completed_history_count,
            summary.reread_book_count,
        )

        if any(not cls._is_nonnegative_integer(value) for value in counts):
            raise ValueError(
                "読書履歴の集計結果が不正です。"
            )

    @staticmethod
    def _validate_statistics_year(year: int) -> None:
        """集計対象年が有効な整数であることを確認する。"""
        if (
            isinstance(year, bool)
            or not isinstance(year, int)
            or not 1 <= year <= 9999
        ):
            raise ValueError(
                "集計対象年は1から9999までの整数で"
                "指定してください。"
            )

    @classmethod
    def _validate_monthly_counts(
        cls,
        monthly_counts: dict[int, int],
    ) -> None:
        """Repositoryから取得した月別集計を検証する。"""
        for month, count in monthly_counts.items():
            if (
                isinstance(month, bool)
                or not isinstance(month, int)
                or not 1 <= month <= 12
                or not cls._is_nonnegative_integer(count)
            ):
                raise ValueError(
                    "月別読了数の集計結果が不正です。"
                )

    @staticmethod
    def _is_nonnegative_integer(value: object) -> bool:
        """値がboolではない0以上の整数か判定する。"""
        return (
            not isinstance(value, bool)
            and isinstance(value, int)
            and value >= 0
        )
