"""Application service for reading history management."""

from collections.abc import Callable
from datetime import datetime

from book_manager.models.reading_history import ReadingHistory
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
