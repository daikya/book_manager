"""Repository for book items."""

import sqlite3
from dataclasses import replace
from pathlib import Path

from book_manager.database.connection import create_connection
from book_manager.models.book_item import BookItem


BOOK_ITEM_COLUMNS = """
    id,
    isbn,
    magazine_code,
    title,
    author,
    publisher,
    publication_format,
    description,
    cover_image_url,
    cover_image_path,
    completion_month,
    notes,
    created_at,
    updated_at
"""

class BookRepository:
    """book_itemsテーブルの永続化処理を担当する。"""

    def __init__(
        self,
        database_path: Path | str,
    ) -> None:
        """データベースファイルのパスを保持する。"""
        self._database_path = Path(database_path)

    def add(
        self,
        book_item: BookItem,
    ) -> BookItem:
        """書籍情報を登録し、自動採番されたIDを持つモデルを返す。"""
        query = """
            INSERT INTO book_items (
                isbn,
                magazine_code,
                title,
                author,
                publisher,
                publication_format,
                description,
                cover_image_url,
                cover_image_path,
                completion_month,
                notes,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        parameters = (
            book_item.isbn,
            book_item.magazine_code,
            book_item.title,
            book_item.author,
            book_item.publisher,
            book_item.publication_format,
            book_item.description,
            book_item.cover_image_url,
            book_item.cover_image_path,
            book_item.completion_month,
            book_item.notes,
            book_item.created_at,
            book_item.updated_at,
        )
        connection = create_connection(self._database_path)

        try:
            with connection:
                cursor = connection.execute(
                    query,
                    parameters,
                )

            book_id = cursor.lastrowid

            if book_id is None:
                raise sqlite3.DatabaseError(
                    "登録した書籍のIDを取得できませんでした。"
                )

            return replace(
                book_item,
                id=book_id,
            )
        finally:
            connection.close()

    def get_by_id(
        self,
        book_id: int,
    ) -> BookItem | None:
        """IDを指定して書籍情報を1件取得する。"""
        query = f"""
            SELECT
                {BOOK_ITEM_COLUMNS}
            FROM book_items
            WHERE id = ?
        """

        connection = create_connection(self._database_path)

        try:
            row = connection.execute(
                query,
                (book_id,),
            ).fetchone()

            if row is None:
                return None

            return self._row_to_book_item(row)
        finally:
            connection.close()

    def get_all(self) -> list[BookItem]:
        """すべての書籍情報をIDの降順で取得する。"""
        query = f"""
            SELECT
                {BOOK_ITEM_COLUMNS}
            FROM book_items
            ORDER BY id DESC
        """

        connection = create_connection(self._database_path)

        try:
            rows = connection.execute(query).fetchall()

            return [
                self._row_to_book_item(row)
                for row in rows
            ]
        finally:
            connection.close()

    def search_by_title(
        self,
        keyword: str,
    ) -> list[BookItem]:
        """書籍名の部分一致検索を行う。"""
        query = f"""
            SELECT
                {BOOK_ITEM_COLUMNS}
            FROM book_items
            WHERE title LIKE ?
            ORDER BY id DESC
        """

        connection = create_connection(self._database_path)

        try:
            rows = connection.execute(
                query,
                (f"%{keyword}%",),
            ).fetchall()

            return [
                self._row_to_book_item(row)
                for row in rows
            ]
        finally:
            connection.close()

    def search_by_author(
        self,
        keyword: str,
    ) -> list[BookItem]:
        """著者名の部分一致検索を行う。"""
        query = f"""
            SELECT
                {BOOK_ITEM_COLUMNS}
            FROM book_items
            WHERE author LIKE ?
            ORDER BY id DESC
        """

        connection = create_connection(
            self._database_path,
        )

        try:
            rows = connection.execute(
                query,
                (f"%{keyword}%",),
            ).fetchall()

            return [
                self._row_to_book_item(row)
                for row in rows
            ]
        finally:
            connection.close()
    def search_by_publisher(
        self,
        keyword: str,
    ) -> list[BookItem]:
        """出版社名の部分一致検索を行う。"""
        query = f"""
            SELECT
                {BOOK_ITEM_COLUMNS}
            FROM book_items
            WHERE publisher LIKE ?
            ORDER BY id DESC
        """

        connection = create_connection(
            self._database_path,
        )

        try:
            rows = connection.execute(
                query,
                (f"%{keyword}%",),
            ).fetchall()

            return [
                self._row_to_book_item(row)
                for row in rows
            ]
        finally:
            connection.close()

    def find_by_isbn(
        self,
        isbn: str,
    ) -> list[BookItem]:
        """ISBNが完全一致する書籍情報を取得する。"""
        query = f"""
            SELECT
                {BOOK_ITEM_COLUMNS}
            FROM book_items
            WHERE isbn = ?
            ORDER BY id DESC
        """

        connection = create_connection(self._database_path)

        try:
            rows = connection.execute(
                query,
                (isbn,),
            ).fetchall()

            return [
                self._row_to_book_item(row)
                for row in rows
            ]
        finally:
            connection.close()

    def find_by_magazine_code(
        self,
        magazine_code: str,
    ) -> list[BookItem]:
        """雑誌コードが完全一致する書籍情報を取得する。"""
        query = f"""
            SELECT
                {BOOK_ITEM_COLUMNS}
            FROM book_items
            WHERE magazine_code = ?
            ORDER BY id DESC
        """

        connection = create_connection(self._database_path)

        try:
            rows = connection.execute(
                query,
                (magazine_code,),
            ).fetchall()

            return [
                self._row_to_book_item(row)
                for row in rows
            ]
        finally:
            connection.close()

    def update(
        self,
        book_item: BookItem,
    ) -> bool:
        """既存の書籍情報を更新する。"""
        if book_item.id is None:
            raise ValueError(
                "更新対象のBookItemにはidが必要です。"
            )

        query = """
            UPDATE book_items
            SET
                isbn = ?,
                magazine_code = ?,
                title = ?,
                author = ?,
                publisher = ?,
                publication_format = ?,
                description = ?,
                cover_image_url = ?,
                cover_image_path = ?,
                completion_month = ?,
                notes = ?,
                updated_at = ?
            WHERE id = ?
        """

        parameters = (
            book_item.isbn,
            book_item.magazine_code,
            book_item.title,
            book_item.author,
            book_item.publisher,
            book_item.publication_format,
            book_item.description,
            book_item.cover_image_url,
            book_item.cover_image_path,
            book_item.completion_month,
            book_item.notes,
            book_item.updated_at,
            book_item.id,
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
        book_id: int,
    ) -> bool:
        """IDを指定して書籍情報を削除する。"""
        query = """
            DELETE FROM book_items
            WHERE id = ?
        """

        connection = create_connection(self._database_path)

        try:
            with connection:
                cursor = connection.execute(
                    query,
                    (book_id,),
                )

            return cursor.rowcount > 0
        finally:
            connection.close()

    @staticmethod
    def _row_to_book_item(
        row: sqlite3.Row,
    ) -> BookItem:
        """SQLiteの行をBookItemへ変換する。"""
        return BookItem(
            id=row["id"],
            isbn=row["isbn"],
            magazine_code=row["magazine_code"],
            title=row["title"],
            author=row["author"],
            publisher=row["publisher"],
            publication_format=row["publication_format"],
            description=row["description"],
            cover_image_url=row["cover_image_url"],
            cover_image_path=row["cover_image_path"],
            completion_month=row["completion_month"],
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )