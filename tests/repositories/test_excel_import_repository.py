"""Excel登録の実DB検証。通常利用のDBにはアクセスしない。"""
from dataclasses import replace
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from book_manager.database.initializer import initialize_database
from book_manager.models.book_item import BookItem
from book_manager.models.excel_import import (
    ExcelImportIssue, ExcelImportOptions, ExcelImportPreview, ExcelImportRecord,
)
from book_manager.repositories.excel_import_repository import (
    ExcelImportCounts, ExcelImportRepository,
)


class ExcelImportRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        path = Path(self.directory.name) / "books.db"
        initialize_database(path)
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.addCleanup(self.connection.close)
        self.repository = ExcelImportRepository()

    def preview(self, *records):
        return ExcelImportPreview(
            source_path=Path("source.xlsx"), source_sha256="test",
            sheet_name="読書", header_row=1,
            options=ExcelImportOptions((("title", 1),)), records=tuple(records),
        )

    def execute(self, preview):
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            result = self.repository.import_preview(self.connection, preview)
            self.connection.commit()
            return result
        except BaseException:
            self.connection.rollback()
            raise

    def counts(self):
        return tuple(self.connection.execute(
            f"SELECT COUNT(*) FROM {name}"
        ).fetchone()[0] for name in (
            "book_items", "tags", "book_item_tags", "reading_histories",
        ))

    def test_registers_books_tags_and_month_history(self):
        result = self.execute(self.preview(
            ExcelImportRecord(2, BookItem(title="音声版", reference_isbn="9784101010014",
                tags=("読書", "音声"), completion_month="2020-02", reading_status="completed"),
                started_on="2020-01", completed_on="2020-02", history_notes="感想"),
            ExcelImportRecord(3, BookItem(title="紙版", tags=("読書",))),
        ))
        self.assertEqual(result, ExcelImportCounts(2, 2, 3, 1))
        self.assertEqual(self.counts(), (2, 2, 3, 1))
        self.assertEqual(self.connection.execute(
            "SELECT started_on, completed_on, notes FROM reading_histories"
        ).fetchone(), ("2020-01", "2020-02", "感想"))
        self.assertEqual(self.connection.execute(
            "SELECT isbn, reference_isbn FROM book_items ORDER BY id"
        ).fetchone(), (None, "9784101010014"))
        self.assertEqual(self.connection.execute("PRAGMA integrity_check").fetchone(), ("ok",))
        self.assertEqual(self.connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_duplicate_isbn_and_title_are_separate_books(self):
        record = ExcelImportRecord(2, BookItem(title="同名", isbn="9784101010014"))
        self.execute(self.preview(record))
        self.execute(self.preview(record, replace(record, row_number=3)))
        self.assertEqual(self.counts(), (3, 0, 0, 0))

    def test_existing_tag_is_reused_without_timestamp_update(self):
        self.connection.execute("INSERT INTO tags (name, created_at, updated_at) VALUES ('既存', 'old', 'old')")
        self.connection.commit()
        result = self.execute(self.preview(ExcelImportRecord(2, BookItem(title="新規", tags=("既存",)))))
        self.assertEqual(result, ExcelImportCounts(1, 0, 1, 0))
        self.assertEqual(self.connection.execute("SELECT updated_at FROM tags").fetchone(), ("old",))

    def test_repeated_tag_in_one_book_has_one_relation(self):
        result = self.execute(self.preview(ExcelImportRecord(2, BookItem(title="本", tags=("タグ", "タグ")))))
        self.assertEqual(result, ExcelImportCounts(1, 1, 1, 0))

    def test_history_notes_only_creates_history(self):
        self.execute(self.preview(ExcelImportRecord(2, BookItem(title="本"), history_notes="感想のみ")))
        self.assertEqual(self.counts(), (1, 0, 0, 1))

    def test_start_only_creates_history(self):
        self.execute(self.preview(ExcelImportRecord(2, BookItem(title="本"), started_on="2021-03")))
        self.assertEqual(self.counts(), (1, 0, 0, 1))

    def test_book_fields_preserved_and_preview_not_mutated(self):
        book = BookItem(title="本", author="著者", publisher="出版社", publication_format="文庫",
            description="内容\n紹介", notes="備考", is_favorite=True, rating=4,
            cover_image_url="https://example.invalid/cover", completion_month="2022-03")
        self.execute(self.preview(ExcelImportRecord(2, book)))
        self.assertEqual(self.connection.execute(
            "SELECT author, publisher, publication_format, description, notes, is_favorite, rating, completion_month FROM book_items"
        ).fetchone(), ("著者", "出版社", "文庫", "内容\n紹介", "備考", 1, 4, "2022-03"))
        self.assertIsNone(book.id)
        self.assertIsNone(book.created_at)

    def test_empty_preview_rejected(self):
        with self.assertRaises(ValueError):
            self.execute(self.preview())
        self.assertEqual(self.counts(), (0, 0, 0, 0))

    def test_preview_with_error_rejected(self):
        preview = replace(self.preview(ExcelImportRecord(2, BookItem(title="本"))),
            errors=(ExcelImportIssue(3, "不正な行"),))
        with self.assertRaises(ValueError):
            self.execute(preview)
        self.assertEqual(self.counts(), (0, 0, 0, 0))

    def test_active_transaction_required(self):
        with self.assertRaises(ValueError):
            self.repository.import_preview(self.connection, self.preview(ExcelImportRecord(2, BookItem(title="本"))))
        self.assertEqual(self.counts(), (0, 0, 0, 0))

    def test_repository_does_not_commit(self):
        self.connection.execute("BEGIN IMMEDIATE")
        self.repository.import_preview(self.connection, self.preview(ExcelImportRecord(2, BookItem(title="本"))))
        self.assertTrue(self.connection.in_transaction)
        self.connection.rollback()
        self.assertEqual(self.counts(), (0, 0, 0, 0))

    def test_later_history_failure_rolls_back_all_new_data(self):
        self.execute(self.preview(ExcelImportRecord(2, BookItem(title="以前の本", tags=("既存",)))))
        before = self.counts()
        self.connection.execute("""CREATE TRIGGER reject_history BEFORE INSERT ON reading_histories
            BEGIN SELECT RAISE(ABORT, 'test failure'); END""")
        self.connection.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.execute(self.preview(
                ExcelImportRecord(2, BookItem(title="最初", tags=("新規",))),
                ExcelImportRecord(3, BookItem(title="次", tags=("別タグ",)), completed_on="2022-03"),
            ))
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.connection.execute("SELECT title FROM book_items").fetchall(), [("以前の本",)])


if __name__ == "__main__":
    unittest.main()
