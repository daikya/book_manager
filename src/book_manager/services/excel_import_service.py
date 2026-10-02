"""Excel取込前の再検査、必須バックアップ、一括登録を管理する。"""
from dataclasses import dataclass
from pathlib import Path
import sqlite3

from book_manager.database.connection import create_connection
from book_manager.models.excel_import import ExcelImportPreview
from book_manager.repositories.excel_import_repository import (
    ExcelImportCounts, ExcelImportRepository,
)
from book_manager.services.backup_service import BackupService
from book_manager.services.excel_import_preflight_service import ExcelImportPreflightService


@dataclass(frozen=True, slots=True)
class ExcelImportResult:
    counts: ExcelImportCounts
    backup_path: Path


class ExcelImportService:
    """利用者が確認したPreviewだけを登録する。API検索は行わない。"""

    TABLE_NAMES = ("book_items", "tags", "book_item_tags", "reading_histories")

    def __init__(self, *, database_path: Path | str,
                 backup_service: BackupService,
                 preflight_service: ExcelImportPreflightService,
                 repository: ExcelImportRepository | None = None):
        self._database_path = Path(database_path)
        self._backup_service = backup_service
        self._preflight_service = preflight_service
        self._repository = repository or ExcelImportRepository()

    def import_preview(self, preview: ExcelImportPreview) -> ExcelImportResult:
        """確認時の内容を再現できない場合は、登録せず再確認を求める。"""
        if not preview.can_import:
            raise ValueError("事前検査に成功していないExcelは登録できません。")
        if not self._database_path.is_file():
            raise FileNotFoundError("取込先のデータベースが存在しません。")
        current = self._preflight_service.preview_file(
            preview.source_path, options=preview.options, header_row=preview.header_row,
        )
        if current != preview or not current.can_import:
            raise ValueError("確認後にExcelまたは登録予定が変更されました。事前検査からやり直してください。")

        connection = create_connection(self._database_path)
        try:
            # 書き込み予約後、別の読み取り接続でBackup APIを実行する。
            # バックアップからコミットまで、他の接続による書き込みを防ぐ。
            connection.execute("BEGIN IMMEDIATE")
            before = self._counts(connection)
            backup_path = self._backup_service.create_backup()
            if backup_path is None or not Path(backup_path).is_file():
                raise FileNotFoundError("取込前のバックアップを作成できませんでした。")
            counts = self._repository.import_preview(connection, current)
            expected = tuple(old + added for old, added in zip(before, (
                counts.books, counts.tags, counts.book_item_tags, counts.reading_histories,
            ), strict=True))
            if self._counts(connection) != expected:
                raise sqlite3.DatabaseError("Excel取込後の件数が一致しません。")
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise sqlite3.IntegrityError("Excel取込後の外部キー整合性を確認できませんでした。")
            if [row[0] for row in connection.execute("PRAGMA integrity_check")] != ["ok"]:
                raise sqlite3.DatabaseError("Excel取込後のDB整合性を確認できませんでした。")
            connection.commit()
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()
        return ExcelImportResult(counts=counts, backup_path=Path(backup_path))

    @classmethod
    def _counts(cls, connection: sqlite3.Connection) -> tuple[int, ...]:
        return tuple(int(connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]) for table in cls.TABLE_NAMES)
