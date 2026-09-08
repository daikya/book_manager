"""Repository for reading histories."""

import sqlite3
from dataclasses import replace
from pathlib import Path

from book_manager.database.connection import create_connection
from book_manager.models.reading_history import ReadingHistory
from book_manager.models.reading_statistics import (
    ReadingStatisticsSummary,
)


READING_HISTORY_COLUMNS = """
    id,
    book_item_id,
    started_on,
    completed_on,
    notes,
    created_at,
    updated_at
"""


class ReadingHistoryRepository:
    """読書履歴の永続化処理を担当する。"""

    def __init__(
        self,
        database_path: Path | str,
    ) -> None:
        """データベースファイルのパスを保持する。"""
        self._database_path = Path(database_path)

    def add(
        self,
        reading_history: ReadingHistory,
    ) -> ReadingHistory:
        """読書履歴を登録し、自動採番されたIDを持つモデルを返す。"""
        query = """
            INSERT INTO reading_histories (
                book_item_id,
                started_on,
                completed_on,
                notes,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """
        parameters = (
            reading_history.book_item_id,
            reading_history.started_on,
            reading_history.completed_on,
            reading_history.notes,
            reading_history.created_at,
            reading_history.updated_at,
        )
        connection = create_connection(self._database_path)

        try:
            with connection:
                cursor = connection.execute(
                    query,
                    parameters,
                )

            reading_history_id = cursor.lastrowid

            if reading_history_id is None:
                raise sqlite3.DatabaseError(
                    "登録した読書履歴のIDを取得できませんでした。"
                )

            return replace(
                reading_history,
                id=reading_history_id,
            )
        finally:
            connection.close()

    def get_by_id(
        self,
        reading_history_id: int,
    ) -> ReadingHistory | None:
        """IDを指定して読書履歴を1件取得する。"""
        query = f"""
            SELECT
                {READING_HISTORY_COLUMNS}
            FROM reading_histories
            WHERE id = ?
        """
        connection = create_connection(self._database_path)

        try:
            row = connection.execute(
                query,
                (reading_history_id,),
            ).fetchone()

            if row is None:
                return None

            return self._row_to_reading_history(row)
        finally:
            connection.close()

    def get_by_book_id(
        self,
        book_item_id: int,
    ) -> list[ReadingHistory]:
        """指定された書籍の読書履歴を新しい順で取得する。"""
        query = f"""
            SELECT
                {READING_HISTORY_COLUMNS}
            FROM reading_histories
            WHERE book_item_id = ?
            ORDER BY
                COALESCE(
                    completed_on,
                    started_on,
                    substr(created_at, 1, 10)
                ) DESC,
                id DESC
        """
        connection = create_connection(self._database_path)

        try:
            rows = connection.execute(
                query,
                (book_item_id,),
            ).fetchall()

            return [
                self._row_to_reading_history(row)
                for row in rows
            ]
        finally:
            connection.close()

    def update(
        self,
        reading_history: ReadingHistory,
    ) -> bool:
        """IDを指定して読書履歴の入力項目と更新日時を更新する。"""
        if reading_history.id is None:
            raise ValueError(
                "更新する読書履歴のIDが設定されていません。"
            )

        query = """
            UPDATE reading_histories
            SET
                started_on = ?,
                completed_on = ?,
                notes = ?,
                updated_at = ?
            WHERE id = ?
        """
        parameters = (
            reading_history.started_on,
            reading_history.completed_on,
            reading_history.notes,
            reading_history.updated_at,
            reading_history.id,
        )
        connection = create_connection(self._database_path)

        try:
            with connection:
                cursor = connection.execute(
                    query,
                    parameters,
                )

            return cursor.rowcount > 0
        finally:
            connection.close()

    def delete(
        self,
        reading_history_id: int,
    ) -> bool:
        """IDを指定して読書履歴を削除する。"""
        query = """
            DELETE FROM reading_histories
            WHERE id = ?
        """
        connection = create_connection(self._database_path)

        try:
            with connection:
                cursor = connection.execute(
                    query,
                    (reading_history_id,),
                )

            return cursor.rowcount > 0
        finally:
            connection.close()

    def get_statistics_summary(
        self,
    ) -> ReadingStatisticsSummary:
        """読書履歴の全体集計を取得する。"""
        query = """
            SELECT
                COUNT(*) AS total_history_count,
                COUNT(DISTINCT book_item_id)
                    AS books_with_history_count,
                COUNT(completed_on)
                    AS completed_history_count,
                (
                    SELECT COUNT(*)
                    FROM (
                        SELECT book_item_id
                        FROM reading_histories
                        GROUP BY book_item_id
                        HAVING COUNT(*) >= 2
                    ) AS reread_books
                ) AS reread_book_count
            FROM reading_histories
        """
        connection = create_connection(self._database_path)

        try:
            row = connection.execute(query).fetchone()

            if row is None:
                raise sqlite3.DatabaseError(
                    "読書履歴の集計結果を取得できませんでした。"
                )

            return ReadingStatisticsSummary(
                total_history_count=row["total_history_count"],
                books_with_history_count=(
                    row["books_with_history_count"]
                ),
                completed_history_count=(
                    row["completed_history_count"]
                ),
                reread_book_count=row["reread_book_count"],
            )
        finally:
            connection.close()

    def get_completed_years(self) -> list[int]:
        """読了記録が存在する年を新しい順で取得する。"""
        query = """
            SELECT DISTINCT
                CAST(
                    substr(completed_on, 1, 4)
                    AS INTEGER
                ) AS year
            FROM reading_histories
            WHERE completed_on IS NOT NULL
            ORDER BY year DESC
        """
        connection = create_connection(self._database_path)

        try:
            rows = connection.execute(query).fetchall()

            return [row["year"] for row in rows]
        finally:
            connection.close()

    def get_monthly_completed_counts(
        self,
        year: int,
    ) -> dict[int, int]:
        """指定年について月ごとの読了数を取得する。"""
        query = """
            SELECT
                CAST(
                    substr(completed_on, 6, 2)
                    AS INTEGER
                ) AS month,
                COUNT(*) AS completed_count
            FROM reading_histories
            WHERE substr(completed_on, 1, 4) = ?
            GROUP BY month
            ORDER BY month ASC
        """
        year_text = f"{year:04d}"
        connection = create_connection(self._database_path)

        try:
            rows = connection.execute(
                query,
                (year_text,),
            ).fetchall()

            return {
                row["month"]: row["completed_count"]
                for row in rows
            }
        finally:
            connection.close()

    @staticmethod
    def _row_to_reading_history(
        row: sqlite3.Row,
    ) -> ReadingHistory:
        """SQLiteの行をReadingHistoryへ変換する。"""
        return ReadingHistory(
            id=row["id"],
            book_item_id=row["book_item_id"],
            started_on=row["started_on"],
            completed_on=row["completed_on"],
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
