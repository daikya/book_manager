"""Repository for restoring complete CSV data packages."""

import sqlite3

from book_manager.validators.author_name_normalizer import author_search_key

from book_manager.models.csv_data_package import CsvDataPackagePreview


class CsvDataPackageRestoreRepository:
    """共有SQLite接続を使って完全データを復元する。"""

    TABLE_NAMES = (
        "book_items",
        "tags",
        "book_item_tags",
        "reading_histories",
        "authors", "author_aliases", "book_item_authors",
    )

    @classmethod
    def is_database_empty(
        cls,
        connection: sqlite3.Connection,
    ) -> bool:
        """移行対象7テーブルがすべて空か返す。"""
        row = connection.execute('SELECT ' + ' + '.join(
            f'(SELECT COUNT(*) FROM {table})' for table in cls.TABLE_NAMES)).fetchone()
        if row is None:
            raise sqlite3.DatabaseError(
                "移行対象テーブルの件数を取得できませんでした。"
            )
        return int(row[0]) == 0

    def restore(
        self,
        connection: sqlite3.Connection,
        preview: CsvDataPackagePreview,
    ) -> None:
        """検査済みデータを新しい主キーで7テーブルへ登録する。"""
        if not preview.can_import:
            raise ValueError(
                "事前検査に成功していないデータは"
                "復元できません。"
            )
        if not self.is_database_empty(connection):
            raise ValueError(
                "完全データは空のデータベースにだけ"
                "復元できます。"
            )

        book_ids = self._insert_books(connection, preview)
        tag_ids = self._insert_tags(connection, preview)
        self._insert_book_item_tags(
            connection,
            preview,
            book_ids=book_ids,
            tag_ids=tag_ids,
        )
        self._insert_reading_histories(
            connection,
            preview,
            book_ids=book_ids,
        )

        author_ids = {}
        for author in preview.authors:
            cursor = connection.execute(
                'INSERT INTO authors(name,name_key,disambiguation_note,created_at,updated_at) VALUES (?,?,?,?,?)',
                (author.name, author_search_key(author.name), author.disambiguation_note, author.created_at, author.updated_at))
            author_ids[author.author_key] = cursor.lastrowid
        for alias in preview.author_aliases:
            connection.execute('INSERT INTO author_aliases(author_id,name,name_key) VALUES (?,?,?)',
                               (self._resolve_id(author_ids, alias.author_key, '別名の著者'), alias.name, author_search_key(alias.name)))
        for relation in preview.book_item_authors:
            connection.execute('INSERT INTO book_item_authors(book_item_id,author_id,position) VALUES (?,?,?)',
                               (self._resolve_id(book_ids, relation.book_key, '著者関連の書籍'),
                                self._resolve_id(author_ids, relation.author_key, '書籍関連の著者'), relation.position))

    @staticmethod
    def _insert_books(
        connection: sqlite3.Connection,
        preview: CsvDataPackagePreview,
    ) -> dict[str, int]:
        """書籍を登録してbook_keyと新IDの対応表を返す。"""
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)
        """
        book_ids: dict[str, int] = {}

        for book in preview.book_items:
            cursor = connection.execute(
                query,
                (
                    book.isbn,
                    book.reference_isbn,
                    book.magazine_code,
                    book.title,
                    book.author,
                    book.publisher,
                    book.publication_format,
                    book.description,
                    book.cover_image_url,
                    book.completion_month,
                    book.reading_status,
                    int(book.is_favorite),
                    book.rating,
                    book.notes,
                    book.created_at,
                    book.updated_at,
                ),
            )
            book_id = cursor.lastrowid
            if book_id is None:
                raise sqlite3.DatabaseError(
                    "復元した書籍のIDを取得できませんでした。"
                )
            book_ids[book.book_key] = book_id

        return book_ids

    @staticmethod
    def _insert_tags(
        connection: sqlite3.Connection,
        preview: CsvDataPackagePreview,
    ) -> dict[str, int]:
        """タグを登録してtag_keyと新IDの対応表を返す。"""
        query = """
            INSERT INTO tags (
                name,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?)
        """
        tag_ids: dict[str, int] = {}

        for tag in preview.tags:
            cursor = connection.execute(
                query,
                (
                    tag.name,
                    tag.created_at,
                    tag.updated_at,
                ),
            )
            tag_id = cursor.lastrowid
            if tag_id is None:
                raise sqlite3.DatabaseError(
                    "復元したタグのIDを取得できませんでした。"
                )
            tag_ids[tag.tag_key] = tag_id

        return tag_ids

    @classmethod
    def _insert_book_item_tags(
        cls,
        connection: sqlite3.Connection,
        preview: CsvDataPackagePreview,
        *,
        book_ids: dict[str, int],
        tag_ids: dict[str, int],
    ) -> None:
        """新しく採番されたIDで書籍タグ関連を登録する。"""
        query = """
            INSERT INTO book_item_tags (
                book_item_id,
                tag_id
            )
            VALUES (?, ?)
        """
        for relation in preview.book_item_tags:
            connection.execute(
                query,
                (
                    cls._resolve_id(
                        book_ids,
                        relation.book_key,
                        "書籍タグ関連の書籍",
                    ),
                    cls._resolve_id(
                        tag_ids,
                        relation.tag_key,
                        "書籍タグ関連のタグ",
                    ),
                ),
            )

    @classmethod
    def _insert_reading_histories(
        cls,
        connection: sqlite3.Connection,
        preview: CsvDataPackagePreview,
        *,
        book_ids: dict[str, int],
    ) -> None:
        """新しく採番された書籍IDで読書履歴を登録する。"""
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
        for history in preview.reading_histories:
            connection.execute(
                query,
                (
                    cls._resolve_id(
                        book_ids,
                        history.book_key,
                        "読書履歴の書籍",
                    ),
                    history.started_on,
                    history.completed_on,
                    history.notes,
                    history.created_at,
                    history.updated_at,
                ),
            )

    @staticmethod
    def _resolve_id(
        ids: dict[str, int],
        package_key: str,
        relation_name: str,
    ) -> int:
        """パッケージ内キーに対応する新IDを返す。"""
        try:
            return ids[package_key]
        except KeyError as error:
            raise sqlite3.DatabaseError(
                f"{relation_name}が存在しません: {package_key}"
            ) from error
