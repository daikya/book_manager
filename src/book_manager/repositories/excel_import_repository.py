"""検査済みExcelデータを共有トランザクションで登録する。"""
from dataclasses import dataclass
from datetime import datetime
import sqlite3

from book_manager.models.excel_import import ExcelImportPreview


@dataclass(frozen=True, slots=True)
class ExcelImportCounts:
    """今回新しく登録したデータの件数。"""
    books: int
    tags: int
    book_item_tags: int
    reading_histories: int


class ExcelImportRepository:
    """接続・バックアップ・コミットは呼び出し元Serviceが管理する。"""

    def import_preview(
        self,
        connection: sqlite3.Connection,
        preview: ExcelImportPreview,
    ) -> ExcelImportCounts:
        """事前検査済みの各行を別の書籍として登録する。

        呼び出し元はBEGIN後に呼び出し、例外時は必ずROLLBACKする。
        同じISBNや書籍名を持つ行も統合せず、それぞれ登録する。
        """
        if not preview.can_import:
            raise ValueError("事前検査に成功していないExcelは登録できません。")
        if not connection.in_transaction:
            raise ValueError("Excel登録には開始済みのトランザクションが必要です。")

        timestamp = datetime.now().isoformat(timespec="seconds")
        tags_created = relations_created = histories_created = 0
        for record in preview.records:
            book = record.book
            cursor = connection.execute(
                """INSERT INTO book_items (
                    isbn, reference_isbn, magazine_code, title, author,
                    publisher, publication_format, description, cover_image_url,
                    cover_image_path, completion_month, reading_status,
                    is_favorite, rating, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (book.isbn, book.reference_isbn, book.magazine_code, book.title,
                 book.author, book.publisher, book.publication_format,
                 book.description, book.cover_image_url, book.cover_image_path,
                 book.completion_month, book.reading_status,
                 int(book.is_favorite), book.rating, book.notes,
                 timestamp, timestamp),
            )
            book_id = cursor.lastrowid
            if book_id is None:
                raise sqlite3.DatabaseError("登録した書籍のIDを取得できませんでした。")

            for name in dict.fromkeys(book.tags):
                existing = connection.execute(
                    "SELECT id FROM tags WHERE name = ?", (name,),
                ).fetchone()
                if existing is None:
                    tag_cursor = connection.execute(
                        "INSERT INTO tags (name, created_at, updated_at) VALUES (?, ?, ?)",
                        (name, timestamp, timestamp),
                    )
                    tag_id = tag_cursor.lastrowid
                    if tag_id is None:
                        raise sqlite3.DatabaseError("登録したタグのIDを取得できませんでした。")
                    tags_created += 1
                else:
                    tag_id = existing[0]
                connection.execute(
                    "INSERT INTO book_item_tags (book_item_id, tag_id) VALUES (?, ?)",
                    (book_id, tag_id),
                )
                relations_created += 1

            if record.has_history:
                connection.execute(
                    """INSERT INTO reading_histories (
                        book_item_id, started_on, completed_on, notes,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)""",
                    (book_id, record.started_on, record.completed_on,
                     record.history_notes, timestamp, timestamp),
                )
                histories_created += 1

        return ExcelImportCounts(
            books=len(preview.records), tags=tags_created,
            book_item_tags=relations_created, reading_histories=histories_created,
        )
