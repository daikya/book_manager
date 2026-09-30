"""Repository for exporting complete CSV data packages."""

import sqlite3
from pathlib import Path

from book_manager.database.connection import create_connection
from book_manager.models.csv_data_package import (
    BOOK_KEY_PREFIX,
    HISTORY_KEY_PREFIX,
    TAG_KEY_PREFIX,
    CsvDataPackageBookItem,
    CsvDataPackageBookItemTag,
    CsvDataPackageReadingHistory,
    CsvDataPackageSnapshot,
    CsvDataPackageTag,
    create_package_key,
)


class CsvDataPackageRepository:
    """完全データを一貫した読取トランザクションで取得する。"""

    def __init__(
        self,
        database_path: Path | str,
    ) -> None:
        """データベースファイルのパスを保持する。"""
        self._database_path = Path(database_path)

    def export_snapshot(self) -> CsvDataPackageSnapshot:
        """4テーブルを取得してパッケージ内キーへ変換する。"""
        connection = create_connection(self._database_path)

        try:
            connection.execute("BEGIN")

            book_rows = connection.execute(
                """
                SELECT
                    id,
                    isbn,
                    magazine_code,
                    title,
                    author,
                    publisher,
                    publication_format,
                    description,
                    cover_image_url,
                    completion_month,
                    reading_status,
                    is_favorite,
                    rating,
                    notes,
                    created_at,
                    updated_at
                FROM book_items
                ORDER BY id ASC
                """
            ).fetchall()
            tag_rows = connection.execute(
                """
                SELECT
                    id,
                    name,
                    created_at,
                    updated_at
                FROM tags
                ORDER BY id ASC
                """
            ).fetchall()
            relation_rows = connection.execute(
                """
                SELECT
                    book_item_id,
                    tag_id
                FROM book_item_tags
                ORDER BY
                    book_item_id ASC,
                    tag_id ASC
                """
            ).fetchall()
            history_rows = connection.execute(
                """
                SELECT
                    id,
                    book_item_id,
                    started_on,
                    completed_on,
                    notes,
                    created_at,
                    updated_at
                FROM reading_histories
                ORDER BY id ASC
                """
            ).fetchall()

            return self._create_snapshot(
                book_rows=book_rows,
                tag_rows=tag_rows,
                relation_rows=relation_rows,
                history_rows=history_rows,
            )
        finally:
            if connection.in_transaction:
                connection.rollback()
            connection.close()

    @staticmethod
    def _create_snapshot(
        *,
        book_rows: list[sqlite3.Row],
        tag_rows: list[sqlite3.Row],
        relation_rows: list[sqlite3.Row],
        history_rows: list[sqlite3.Row],
    ) -> CsvDataPackageSnapshot:
        """DB行をパッケージ用Modelへ変換する。"""
        book_keys = {
            int(row["id"]): create_package_key(
                BOOK_KEY_PREFIX,
                sequence,
            )
            for sequence, row in enumerate(book_rows, start=1)
        }
        tag_keys = {
            int(row["id"]): create_package_key(
                TAG_KEY_PREFIX,
                sequence,
            )
            for sequence, row in enumerate(tag_rows, start=1)
        }

        book_items = tuple(
            CsvDataPackageBookItem(
                book_key=book_keys[int(row["id"])],
                isbn=row["isbn"],
                magazine_code=row["magazine_code"],
                title=row["title"],
                author=row["author"],
                publisher=row["publisher"],
                publication_format=row["publication_format"],
                description=row["description"],
                cover_image_url=row["cover_image_url"],
                completion_month=row["completion_month"],
                reading_status=row["reading_status"],
                is_favorite=bool(row["is_favorite"]),
                rating=row["rating"],
                notes=row["notes"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in book_rows
        )
        tags = tuple(
            CsvDataPackageTag(
                tag_key=tag_keys[int(row["id"])],
                name=row["name"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in tag_rows
        )
        book_item_tags = tuple(
            CsvDataPackageBookItemTag(
                book_key=CsvDataPackageRepository._resolve_key(
                    book_keys,
                    int(row["book_item_id"]),
                    "書籍タグ関連の書籍",
                ),
                tag_key=CsvDataPackageRepository._resolve_key(
                    tag_keys,
                    int(row["tag_id"]),
                    "書籍タグ関連のタグ",
                ),
            )
            for row in relation_rows
        )
        reading_histories = tuple(
            CsvDataPackageReadingHistory(
                history_key=create_package_key(
                    HISTORY_KEY_PREFIX,
                    sequence,
                ),
                book_key=CsvDataPackageRepository._resolve_key(
                    book_keys,
                    int(row["book_item_id"]),
                    "読書履歴の書籍",
                ),
                started_on=row["started_on"],
                completed_on=row["completed_on"],
                notes=row["notes"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for sequence, row in enumerate(history_rows, start=1)
        )

        return CsvDataPackageSnapshot(
            book_items=book_items,
            tags=tags,
            book_item_tags=book_item_tags,
            reading_histories=reading_histories,
        )

    @staticmethod
    def _resolve_key(
        keys: dict[int, str],
        source_id: int,
        relation_name: str,
    ) -> str:
        """参照元IDに対応するパッケージ内キーを返す。"""
        try:
            return keys[source_id]
        except KeyError as error:
            raise sqlite3.DatabaseError(
                f"{relation_name}が存在しません。ID: {source_id}"
            ) from error
