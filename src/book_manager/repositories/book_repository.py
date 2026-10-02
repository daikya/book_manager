"""Repository for book items."""

import sqlite3
from dataclasses import replace
from pathlib import Path

from book_manager.database.connection import create_connection
from book_manager.models.book_item import BookItem
from book_manager.models.tag import Tag


BOOK_ITEM_COLUMNS = """
    id,
    isbn,
    reference_isbn,
    magazine_code,
    title,
    author,
    publisher,
    publication_format,
    description,
    cover_image_url,
    cover_image_path,
    completion_month,
    reading_status,
    is_favorite,
    rating,
    notes,
    created_at,
    updated_at
"""

SORT_COLUMNS = {
    "registered": "id",
    "title": "title",
    "author": "author",
    "publisher": "publisher",
    "completion_month": "completion_month",
    "reading_status": "reading_status",
    "is_favorite": "is_favorite",
    "rating": "rating",
}

CUSTOM_SORT_EXPRESSIONS = {
    "reading_status": """
        CASE reading_status
            WHEN 'unread' THEN 1
            WHEN 'reading' THEN 2
            WHEN 'completed' THEN 3
            ELSE 0
        END
    """,
    "is_favorite": "COALESCE(is_favorite, 0)",
    "rating": "COALESCE(rating, 0)",
}

class BookRepository:
    """書籍情報と関連するタグの永続化処理を担当する。"""

    def __init__(
        self,
        database_path: Path | str,
    ) -> None:
        """データベースファイルのパスを保持する。"""
        self._database_path = Path(database_path)

    def add(self, book_item: BookItem) -> BookItem:
        """書籍情報を登録し、自動採番されたIDを持つモデルを返す。"""
        return self.add_many((book_item,))[0]

    def add_many(self, books: tuple[BookItem, ...]) -> tuple[BookItem, ...]:
        """全書籍とタグを登録し、途中の例外では全件を取り消す。"""
        if not books:
            return ()
        connection = create_connection(self._database_path)
        try:
            with connection:
                return tuple(
                    self._add_with_connection(connection, book) for book in books
                )
        finally:
            connection.close()

    def _add_with_connection(
        self, connection: sqlite3.Connection, book_item: BookItem,
    ) -> BookItem:
        """呼出元のトランザクション内で書籍とタグを登録する。"""
        query = """
            INSERT INTO book_items (
                isbn,
                reference_isbn,
                magazine_code,
                title,
                author,
                publisher,
                publication_format,
                description,
                cover_image_url,
                cover_image_path,
                completion_month,
                reading_status,
                is_favorite,
                rating,
                notes,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        parameters = (
            book_item.isbn,
            book_item.reference_isbn,
            book_item.magazine_code,
            book_item.title,
            book_item.author,
            book_item.publisher,
            book_item.publication_format,
            book_item.description,
            book_item.cover_image_url,
            book_item.cover_image_path,
            book_item.completion_month,
            book_item.reading_status,
            int(book_item.is_favorite),
            book_item.rating,
            book_item.notes,
            book_item.created_at,
            book_item.updated_at,
        )
        cursor = connection.execute(query, parameters)
        book_id = cursor.lastrowid
        if book_id is None:
            raise sqlite3.DatabaseError("登録した書籍のIDを取得できませんでした。")
        self._replace_book_tags(
            connection, book_id=book_id, tag_names=book_item.tags,
            timestamp=book_item.created_at,
        )
        return replace(book_item, id=book_id)

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

            return self._rows_to_book_items(
                connection,
                [row],
            )[0]
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

            return self._rows_to_book_items(
                connection,
                rows,
            )
        finally:
            connection.close()

    def get_all_sorted(
        self,
        *,
        sort_by: str,
        descending: bool = False,
    ) -> list[BookItem]:
        """指定された項目で全書籍を並べ替えて取得する。"""
        column_name = SORT_COLUMNS.get(
            sort_by,
        )

        if column_name is None:
            raise ValueError(
                "指定された並べ替え項目が正しくありません。"
            )

        direction = (
            "DESC"
            if descending
            else "ASC"
        )

        if sort_by == "registered":
            order_by = (
                f"{column_name} {direction}"
            )
        elif sort_by in CUSTOM_SORT_EXPRESSIONS:
            sort_expression = (
                CUSTOM_SORT_EXPRESSIONS[sort_by]
            )
            order_by = (
                f"{sort_expression} {direction}, "
                "id DESC"
            )
        else:
            order_by = (
                f"{column_name} IS NULL, "
                f"{column_name} {direction}, "
                "id DESC"
            )

        query = f"""
            SELECT
                {BOOK_ITEM_COLUMNS}
            FROM book_items
            ORDER BY {order_by}
        """

        connection = create_connection(
            self._database_path,
        )

        try:
            rows = connection.execute(
                query,
            ).fetchall()

            return self._rows_to_book_items(
                connection,
                rows,
            )
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

            return self._rows_to_book_items(
                connection,
                rows,
            )
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

            return self._rows_to_book_items(
                connection,
                rows,
            )
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

            return self._rows_to_book_items(
                connection,
                rows,
            )
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

            return self._rows_to_book_items(
                connection,
                rows,
            )
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

            return self._rows_to_book_items(
                connection,
                rows,
            )
        finally:
            connection.close()

    def search_by_conditions(
        self,
        *,
        title: str | None = None,
        author: str | None = None,
        publisher: str | None = None,
        isbn: str | None = None,
        magazine_code: str | None = None,
        reading_status_filter: str | None = None,
        favorite_filter: str | None = None,
        rating_filter: str | int | None = None,
        tag_name: str | None = None,
        untagged_only: bool = False,
    ) -> list[BookItem]:
        """複数条件によるAND検索を行う。"""
        if tag_name is not None and untagged_only:
            raise ValueError(
                "タグとタグ未設定を同時に指定できません。"
            )

        conditions: list[str] = []
        parameters: list[str | int] = []

        if title is not None:
            conditions.append(
                "title LIKE ?",
            )
            parameters.append(
                f"%{title}%",
            )

        if author is not None:
            conditions.append(
                "author LIKE ?",
            )
            parameters.append(
                f"%{author}%",
            )

        if publisher is not None:
            conditions.append(
                "publisher LIKE ?",
            )
            parameters.append(
                f"%{publisher}%",
            )

        if isbn is not None:
            conditions.append(
                "isbn = ?",
            )
            parameters.append(
                isbn,
            )

        if magazine_code is not None:
            conditions.append(
                "magazine_code = ?",
            )
            parameters.append(
                magazine_code,
            )

        if reading_status_filter == "unset":
            conditions.append(
                "reading_status IS NULL",
            )
        elif reading_status_filter is not None:
            conditions.append(
                "reading_status = ?",
            )
            parameters.append(
                reading_status_filter,
            )

        if favorite_filter == "favorite":
            conditions.append(
                "is_favorite = ?",
            )
            parameters.append(
                1,
            )
        elif favorite_filter == "not_favorite":
            conditions.append(
                "is_favorite = ?",
            )
            parameters.append(
                0,
            )

        if rating_filter == "unrated":
            conditions.append(
                "rating IS NULL",
            )
        elif isinstance(rating_filter, int):
            conditions.append(
                "rating >= ?",
            )
            parameters.append(
                rating_filter,
            )

        if tag_name is not None:
            conditions.append(
                """
                EXISTS (
                    SELECT 1
                    FROM book_item_tags AS bit
                    INNER JOIN tags AS t
                        ON t.id = bit.tag_id
                    WHERE bit.book_item_id = book_items.id
                      AND t.name = ?
                )
                """
            )
            parameters.append(tag_name)
        elif untagged_only:
            conditions.append(
                """
                NOT EXISTS (
                    SELECT 1
                    FROM book_item_tags AS bit
                    WHERE bit.book_item_id = book_items.id
                )
                """
            )

        if not conditions:
            return self.get_all()

        where_clause = " AND ".join(
            conditions,
        )

        query = f"""
            SELECT
                {BOOK_ITEM_COLUMNS}
            FROM book_items
            WHERE {where_clause}
            ORDER BY id DESC
        """

        connection = create_connection(
            self._database_path,
        )

        try:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

            return self._rows_to_book_items(
                connection,
                rows,
            )
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
                reference_isbn = ?,
                magazine_code = ?,
                title = ?,
                author = ?,
                publisher = ?,
                publication_format = ?,
                description = ?,
                cover_image_url = ?,
                cover_image_path = ?,
                completion_month = ?,
                reading_status = ?,
                is_favorite = ?,
                rating = ?,
                notes = ?,
                updated_at = ?
            WHERE id = ?
        """

        parameters = (
            book_item.isbn,
            book_item.reference_isbn,
            book_item.magazine_code,
            book_item.title,
            book_item.author,
            book_item.publisher,
            book_item.publication_format,
            book_item.description,
            book_item.cover_image_url,
            book_item.cover_image_path,
            book_item.completion_month,
            book_item.reading_status,
            int(book_item.is_favorite),
            book_item.rating,
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

                if cursor.rowcount == 0:
                    return False

                self._replace_book_tags(
                    connection,
                    book_id=book_item.id,
                    tag_names=book_item.tags,
                    timestamp=book_item.updated_at,
                )

            return True
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

    def get_all_tags(self) -> list[Tag]:
        """登録済みタグを名称の昇順で取得する。"""
        query = """
            SELECT
                id,
                name,
                created_at,
                updated_at
            FROM tags
            ORDER BY name ASC
        """
        connection = create_connection(self._database_path)

        try:
            rows = connection.execute(query).fetchall()

            return [
                self._row_to_tag(row)
                for row in rows
            ]
        finally:
            connection.close()

    def get_tag_by_id(
        self,
        tag_id: int,
    ) -> Tag | None:
        """IDを指定してタグを1件取得する。"""
        return self._get_tag(
            "id = ?",
            tag_id,
        )

    def get_tag_by_name(
        self,
        name: str,
    ) -> Tag | None:
        """名称を指定してタグを1件取得する。"""
        return self._get_tag(
            "name = ?",
            name,
        )

    def rename_tag(
        self,
        *,
        tag_id: int,
        name: str,
        updated_at: str,
    ) -> bool:
        """登録済みタグの名称を変更する。"""
        query = """
            UPDATE tags
            SET
                name = ?,
                updated_at = ?
            WHERE id = ?
        """
        connection = create_connection(self._database_path)

        try:
            with connection:
                cursor = connection.execute(
                    query,
                    (
                        name,
                        updated_at,
                        tag_id,
                    ),
                )

            return cursor.rowcount > 0
        finally:
            connection.close()

    def delete_tag(
        self,
        tag_id: int,
    ) -> bool:
        """IDを指定してタグを削除する。"""
        query = """
            DELETE FROM tags
            WHERE id = ?
        """
        connection = create_connection(self._database_path)

        try:
            with connection:
                cursor = connection.execute(
                    query,
                    (tag_id,),
                )

            return cursor.rowcount > 0
        finally:
            connection.close()

    def count_books_by_tag(
        self,
        tag_id: int,
    ) -> int:
        """指定したタグを使用している書籍数を返す。"""
        query = """
            SELECT COUNT(*)
            FROM book_item_tags
            WHERE tag_id = ?
        """
        connection = create_connection(self._database_path)

        try:
            row = connection.execute(
                query,
                (tag_id,),
            ).fetchone()

            if row is None:
                return 0

            return int(row[0])
        finally:
            connection.close()

    def _get_tag(
        self,
        condition: str,
        value: str | int,
    ) -> Tag | None:
        """指定条件に一致するタグを1件取得する。"""
        query = f"""
            SELECT
                id,
                name,
                created_at,
                updated_at
            FROM tags
            WHERE {condition}
        """
        connection = create_connection(self._database_path)

        try:
            row = connection.execute(
                query,
                (value,),
            ).fetchone()

            if row is None:
                return None

            return self._row_to_tag(row)
        finally:
            connection.close()

    @staticmethod
    def _replace_book_tags(
        connection: sqlite3.Connection,
        *,
        book_id: int,
        tag_names: tuple[str, ...],
        timestamp: str | None,
    ) -> None:
        """書籍に設定されたタグ関連を置き換える。"""
        connection.execute(
            """
            DELETE FROM book_item_tags
            WHERE book_item_id = ?
            """,
            (book_id,),
        )

        for tag_name in tag_names:
            connection.execute(
                """
                INSERT OR IGNORE INTO tags (
                    name,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    tag_name,
                    timestamp,
                    timestamp,
                ),
            )
            tag_row = connection.execute(
                """
                SELECT id
                FROM tags
                WHERE name = ?
                """,
                (tag_name,),
            ).fetchone()

            if tag_row is None:
                raise sqlite3.DatabaseError(
                    "登録したタグのIDを取得できませんでした。"
                )

            connection.execute(
                """
                INSERT OR IGNORE INTO book_item_tags (
                    book_item_id,
                    tag_id
                )
                VALUES (?, ?)
                """,
                (
                    book_id,
                    int(tag_row[0]),
                ),
            )

    def _rows_to_book_items(
        self,
        connection: sqlite3.Connection,
        rows: list[sqlite3.Row],
    ) -> list[BookItem]:
        """SQLiteの複数行をタグ付きBookItemへ変換する。"""
        books = [
            self._row_to_book_item(row)
            for row in rows
        ]

        if not books:
            return []

        book_ids = [
            book.id
            for book in books
            if book.id is not None
        ]
        placeholders = ", ".join(
            "?"
            for _ in book_ids
        )
        tag_rows = connection.execute(
            f"""
            SELECT
                bit.book_item_id,
                t.name
            FROM book_item_tags AS bit
            INNER JOIN tags AS t
                ON t.id = bit.tag_id
            WHERE bit.book_item_id IN ({placeholders})
            ORDER BY t.name ASC
            """,
            book_ids,
        ).fetchall()
        tags_by_book_id: dict[int, list[str]] = {}

        for tag_row in tag_rows:
            book_id = int(tag_row["book_item_id"])
            tags_by_book_id.setdefault(
                book_id,
                [],
            ).append(
                str(tag_row["name"])
            )

        return [
            replace(
                book,
                tags=tuple(
                    tags_by_book_id.get(
                        book.id,
                        [],
                    )
                ),
            )
            for book in books
        ]

    @staticmethod
    def _row_to_tag(
        row: sqlite3.Row,
    ) -> Tag:
        """SQLiteの行をTagへ変換する。"""
        return Tag(
            id=row["id"],
            name=row["name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_book_item(
        row: sqlite3.Row,
    ) -> BookItem:
        """SQLiteの行をBookItemへ変換する。"""
        return BookItem(
            id=row["id"],
            isbn=row["isbn"],
            reference_isbn=row["reference_isbn"],
            magazine_code=row["magazine_code"],
            title=row["title"],
            author=row["author"],
            publisher=row["publisher"],
            publication_format=row["publication_format"],
            description=row["description"],
            cover_image_url=row["cover_image_url"],
            cover_image_path=row["cover_image_path"],
            completion_month=row["completion_month"],
            reading_status=row["reading_status"],
            is_favorite=bool(row["is_favorite"]),
            rating=row["rating"],
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
