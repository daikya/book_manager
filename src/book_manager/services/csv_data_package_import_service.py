"""Complete CSV data package import orchestration service."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from book_manager.database.connection import create_connection
from book_manager.models.csv_data_package import (
    CsvDataPackageArchiveFingerprint,
    CsvDataPackageImportResult,
    CsvDataPackagePreview,
)
from book_manager.repositories.csv_data_package_restore_repository import (
    CsvDataPackageRestoreRepository,
)
from book_manager.services.backup_service import BackupService
from book_manager.services.csv_data_package_archive_validator import (
    CsvDataPackageArchiveValidator,
)


class CsvDataPackageImportService:
    """バックアップ後、1トランザクションで完全データを復元する。"""

    def __init__(
        self,
        *,
        database_path: Path | str,
        backup_service: BackupService,
        archive_validator: CsvDataPackageArchiveValidator,
        restore_repository: CsvDataPackageRestoreRepository,
    ) -> None:
        """インポートに必要な依存先を保持する。"""
        self._database_path = Path(database_path)
        self._backup_service = backup_service
        self._archive_validator = archive_validator
        self._restore_repository = restore_repository

    def import_preview(
        self,
        preview: CsvDataPackagePreview,
    ) -> CsvDataPackageImportResult:
        """事前検査済みPreviewを安全にDBへ復元する。"""
        if not preview.can_import:
            raise ValueError(
                "事前検査に成功していないデータは"
                "インポートできません。"
            )
        if not self._database_path.is_file():
            raise FileNotFoundError(
                "インポート先のデータベースが存在しません。"
            )

        current_fingerprint = self._archive_validator.validate(
            preview.source_path
        )
        if not self._fingerprints_match(preview, current_fingerprint):
            raise ValueError(
                "事前検査後にCSVデータパッケージが"
                "変更されました。"
            )

        connection = create_connection(self._database_path)
        try:
            if not self._restore_repository.is_database_empty(connection):
                raise ValueError(
                    "完全データは空のデータベースにだけ"
                    "インポートできます。"
                )

            backup_path = self._backup_service.create_backup()
            if backup_path is None:
                raise FileNotFoundError(
                    "インポート前のバックアップを"
                    "作成できませんでした。"
                )

            try:
                connection.execute("BEGIN IMMEDIATE")

                if not self._restore_repository.is_database_empty(connection):
                    raise ValueError(
                        "バックアップ後にデータベースが"
                        "変更されました。"
                    )

                self._restore_repository.restore(connection, preview)
                self._validate_restored_database(connection, preview)
                connection.commit()
            except Exception:
                if connection.in_transaction:
                    connection.rollback()
                raise
        finally:
            connection.close()

        return CsvDataPackageImportResult(
            book_item_count=len(preview.book_items),
            tag_count=len(preview.tags),
            book_item_tag_count=len(preview.book_item_tags),
            reading_history_count=len(preview.reading_histories),
            backup_path=backup_path,
            author_count=len(preview.authors), author_alias_count=len(preview.author_aliases),
            book_item_author_count=len(preview.book_item_authors),
        )

    @staticmethod
    def _fingerprints_match(
        preview: CsvDataPackagePreview,
        current: CsvDataPackageArchiveFingerprint,
    ) -> bool:
        """事前検査時と現在のZIP指紋がすべて一致するか返す。"""
        return (
            Path(preview.source_path) == Path(current.source_path)
            and preview.source_size == current.source_size
            and preview.source_modified_ns == current.source_modified_ns
            and preview.source_sha256 == current.source_sha256
        )

    @staticmethod
    def _validate_restored_database(
        connection: sqlite3.Connection,
        preview: CsvDataPackagePreview,
    ) -> None:
        """コミット前に件数と外部キー整合性を再検証する。"""
        expected_counts = {
            "book_items": len(preview.book_items),
            "tags": len(preview.tags),
            "book_item_tags": len(preview.book_item_tags),
            "reading_histories": len(preview.reading_histories),
            "authors": len(preview.authors), "author_aliases": len(preview.author_aliases),
            "book_item_authors": len(preview.book_item_authors),
        }
        for table_name, expected_count in expected_counts.items():
            row = connection.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()
            if row is None or int(row[0]) != expected_count:
                actual_count = None if row is None else int(row[0])
                raise sqlite3.DatabaseError(
                    "インポート後の件数が一致しません。"
                    f" table={table_name},"
                    f" expected={expected_count},"
                    f" actual={actual_count}"
                )

        foreign_key_error = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchone()
        if foreign_key_error is not None:
            raise sqlite3.IntegrityError(
                "インポート後の外部キー整合性を"
                "確認できませんでした。"
            )
