"""実Excel・実SQLite・実バックアップを使う取込Serviceの検証。"""
from contextlib import closing
from dataclasses import replace
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from openpyxl import Workbook
from book_manager.database.initializer import initialize_database
from book_manager.models.book_item import BookItem
from book_manager.models.excel_import import ExcelImportIssue, ExcelImportOptions
from book_manager.repositories.excel_import_repository import ExcelImportRepository
from book_manager.services.backup_service import BackupService
from book_manager.services.excel_import_preflight_service import ExcelImportPreflightService
from book_manager.services.excel_import_service import ExcelImportService


class ExcelImportServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.database = self.root / "books.db"
        self.source = self.root / "source.xlsx"
        initialize_database(self.database)
        self.write_excel()
        # 外部API・DB照会を持たない準備処理。検査と登録は本物を使用する。
        preparer = Mock(spec=["prepare_book"])
        preparer.prepare_book.side_effect = lambda **values: BookItem(**values)
        self.preflight = ExcelImportPreflightService(book_service=preparer)
        self.backup = BackupService(database_path=self.database, backup_directory=self.root / "backups")
        self.service = ExcelImportService(database_path=self.database,
            backup_service=self.backup, preflight_service=self.preflight)
        self.preview = self.preflight.preview_file(self.source, options=ExcelImportOptions((
            ("title", 1), ("tags", 2), ("completed_on", 3),
        )))

    def write_excel(self, title="移行した本"):
        workbook = Workbook()
        workbook.active.append(["書籍名", "タグ", "読了日"])
        workbook.active.append([title, "読書|音声", "2022年3月"])
        workbook.save(self.source)
        workbook.close()

    def query(self, path, sql):
        with closing(sqlite3.connect(
            path.resolve().as_uri() + "?mode=ro", uri=True,
        )) as connection:
            return connection.execute(sql).fetchall()

    def test_query_closes_connection_explicitly(self):
        from unittest.mock import patch
        connection = Mock()
        connection.execute.return_value.fetchall.return_value = [(0,)]
        with patch("sqlite3.connect", return_value=connection):
            self.assertEqual(self.query(self.database, "SELECT 0"), [(0,)])
        connection.close.assert_called_once_with()

    def test_query_closes_connection_when_query_fails(self):
        from unittest.mock import patch
        connection = Mock()
        connection.execute.side_effect = sqlite3.DatabaseError("照会失敗")
        with patch("sqlite3.connect", return_value=connection):
            with self.assertRaises(sqlite3.DatabaseError):
                self.query(self.database, "SELECT 0")
        connection.close.assert_called_once_with()

    def test_success_and_backup_contains_pre_import_database(self):
        result = self.service.import_preview(self.preview)
        self.assertEqual(result.counts.books, 1)
        self.assertEqual(result.counts.tags, 2)
        self.assertEqual(result.counts.book_item_tags, 2)
        self.assertEqual(result.counts.reading_histories, 1)
        self.assertEqual(self.query(result.backup_path, "SELECT COUNT(*) FROM book_items"), [(0,)])
        self.assertEqual(self.query(self.database, "SELECT completed_on FROM reading_histories"), [("2022-03",)])

    def test_existing_data_kept_and_second_import_backup_has_first_book(self):
        self.service.import_preview(self.preview)
        result = self.service.import_preview(self.preview)
        self.assertEqual(result.counts.tags, 0)
        self.assertEqual(self.query(self.database, "SELECT COUNT(*) FROM book_items"), [(2,)])
        self.assertEqual(self.query(result.backup_path, "SELECT COUNT(*) FROM book_items"), [(1,)])

    def test_changed_excel_rejected_without_backup_or_registration(self):
        self.write_excel("変更された本")
        with self.assertRaises(ValueError):
            self.service.import_preview(self.preview)
        self.assertFalse((self.root / "backups").exists())
        self.assertEqual(self.query(self.database, "SELECT COUNT(*) FROM book_items"), [(0,)])

    def test_mutated_preview_book_rejected(self):
        self.preview.records[0].book.title = "確認後の変更"
        with self.assertRaises(ValueError):
            self.service.import_preview(self.preview)
        self.assertFalse((self.root / "backups").exists())

    def test_modified_history_rejected(self):
        altered = replace(self.preview, records=(replace(self.preview.records[0], completed_on="2023-04"),))
        with self.assertRaises(ValueError):
            self.service.import_preview(altered)

    def test_error_preview_rejected(self):
        altered = replace(self.preview, errors=(ExcelImportIssue(2, "エラー"),))
        with self.assertRaises(ValueError):
            self.service.import_preview(altered)

    def test_missing_database_does_not_create_empty_file(self):
        self.database.unlink()
        with self.assertRaises(FileNotFoundError):
            self.service.import_preview(self.preview)
        self.assertFalse(self.database.exists())

    def test_missing_source_rejected(self):
        self.source.unlink()
        with self.assertRaises(FileNotFoundError):
            self.service.import_preview(self.preview)
        self.assertFalse((self.root / "backups").exists())

    def test_backup_failure_prevents_registration(self):
        backup = Mock(spec=["create_backup"])
        backup.create_backup.side_effect = OSError("保存できない")
        service = ExcelImportService(database_path=self.database,
            backup_service=backup, preflight_service=self.preflight)
        with self.assertRaises(OSError):
            service.import_preview(self.preview)
        self.assertEqual(self.query(self.database, "SELECT COUNT(*) FROM book_items"), [(0,)])

    def test_missing_backup_result_prevents_registration(self):
        backup = Mock(spec=["create_backup"])
        backup.create_backup.return_value = None
        service = ExcelImportService(database_path=self.database,
            backup_service=backup, preflight_service=self.preflight)
        with self.assertRaises(FileNotFoundError):
            service.import_preview(self.preview)
        self.assertEqual(self.query(self.database, "SELECT COUNT(*) FROM book_items"), [(0,)])

    def test_repository_failure_rolls_back_but_keeps_backup(self):
        repository = Mock(spec=["import_preview"])
        def insert_then_fail(connection, preview):
            ExcelImportRepository().import_preview(connection, preview)
            raise sqlite3.DatabaseError("登録後の失敗")
        repository.import_preview.side_effect = insert_then_fail
        service = ExcelImportService(database_path=self.database,
            backup_service=self.backup, preflight_service=self.preflight, repository=repository)
        with self.assertRaises(sqlite3.DatabaseError):
            service.import_preview(self.preview)
        for table in ("book_items", "tags", "book_item_tags", "reading_histories"):
            self.assertEqual(self.query(self.database, f"SELECT COUNT(*) FROM {table}"), [(0,)])
        self.assertEqual(len(list((self.root / "backups").glob("*.db"))), 1)

    def test_inconsistent_count_rolls_back(self):
        repository = Mock(spec=["import_preview"])
        def wrong_count(connection, preview):
            actual = ExcelImportRepository().import_preview(connection, preview)
            return replace(actual, books=99)
        repository.import_preview.side_effect = wrong_count
        service = ExcelImportService(database_path=self.database,
            backup_service=self.backup, preflight_service=self.preflight, repository=repository)
        with self.assertRaises(sqlite3.DatabaseError):
            service.import_preview(self.preview)
        self.assertEqual(self.query(self.database, "SELECT COUNT(*) FROM book_items"), [(0,)])


if __name__ == "__main__":
    unittest.main()
