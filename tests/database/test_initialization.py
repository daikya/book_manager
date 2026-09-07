"""Tests for SQLite database initialization."""

import sqlite3
from pathlib import Path

import pytest

from book_manager.database.connection import create_connection
from book_manager.database.initializer import initialize_database
from book_manager.database.schema import SCHEMA_VERSION


def get_user_version(database_path: Path) -> int:
    """SQLiteのuser_versionを取得する。"""
    connection = sqlite3.connect(database_path)

    try:
        row = connection.execute("PRAGMA user_version").fetchone()

        assert row is not None
        return int(row[0])
    finally:
        connection.close()


def get_schema_object_names(
    database_path: Path,
    object_type: str,
) -> set[str]:
    """指定した種類のスキーマオブジェクト名を取得する。"""
    connection = sqlite3.connect(database_path)

    try:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = ?
            """,
            (object_type,),
        ).fetchall()

        return {str(row[0]) for row in rows}
    finally:
        connection.close()

def get_table_column_names(
    database_path: Path,
    table_name: str,
) -> set[str]:
    """指定されたテーブルの列名を取得する。"""
    connection = sqlite3.connect(database_path)

    try:
        rows = connection.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

        return {
            str(row[1])
            for row in rows
        }
    finally:
        connection.close()

def test_initialize_database_creates_cover_image_columns(
    tmp_path: Path,
) -> None:
    """新規DBに表紙画像関連列を作成する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    column_names = get_table_column_names(
        database_path,
        "book_items",
    )

    assert "cover_image_url" in column_names
    assert "cover_image_path" in column_names

def test_initialize_database_creates_is_favorite_column(
    tmp_path: Path,
) -> None:
    """新規DBにお気に入り列を正しい定義で作成する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    connection = sqlite3.connect(database_path)

    try:
        rows = connection.execute(
            "PRAGMA table_info(book_items)"
        ).fetchall()

        is_favorite_row = next(
            row
            for row in rows
            if row[1] == "is_favorite"
        )

        assert is_favorite_row[2] == "INTEGER"
        assert is_favorite_row[3] == 1
        assert is_favorite_row[4] == "0"

    finally:
        connection.close()


def test_initialize_database_creates_rating_column(
    tmp_path: Path,
) -> None:
    """新規DBに評価列を正しい定義で作成する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    connection = sqlite3.connect(database_path)

    try:
        rows = connection.execute(
            "PRAGMA table_info(book_items)"
        ).fetchall()

        rating_row = next(
            row
            for row in rows
            if row[1] == "rating"
        )

        assert rating_row[2] == "INTEGER"
        assert rating_row[3] == 0
        assert rating_row[4] is None

    finally:
        connection.close()


def test_initialize_database_migrates_version_1_to_7(
    tmp_path: Path,
) -> None:
    """Version 1のDBをVersion 7へ移行する。"""
    database_path = tmp_path / "test_book_manager.db"

    connection = sqlite3.connect(database_path)

    try:
        with connection:
            connection.execute(
                """
                CREATE TABLE book_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    isbn TEXT,
                    magazine_code TEXT,
                    title TEXT NOT NULL,
                    author TEXT,
                    publisher TEXT,
                    publication_format TEXT,
                    description TEXT,
                    completion_month TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO book_items (
                    title,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    "移行前の書籍",
                    "2026-08-06 10:00:00",
                    "2026-08-06 10:00:00",
                ),
            )
            connection.execute(
                "PRAGMA user_version = 1"
            )
    finally:
        connection.close()

    initialize_database(database_path)

    assert get_user_version(database_path) == SCHEMA_VERSION

    column_names = get_table_column_names(
        database_path,
        "book_items",
    )

    assert "cover_image_url" in column_names
    assert "cover_image_path" in column_names
    assert "reading_status" in column_names
    assert "is_favorite" in column_names
    assert "rating" in column_names

    connection = sqlite3.connect(database_path)

    try:
        row = connection.execute(
            """
            SELECT
                title,
                cover_image_url,
                cover_image_path,
                reading_status,
                is_favorite,
                rating
            FROM book_items
            """
        ).fetchone()

        assert row == (
            "移行前の書籍",
            None,
            None,
            None,
            0,
            None,
        )
    finally:
        connection.close()

def test_initialize_database_migrates_version_2_to_7(
    tmp_path: Path,
) -> None:
    """Version 2のDBをVersion 7へ移行する。"""
    database_path = tmp_path / "test_book_manager.db"

    connection = sqlite3.connect(database_path)

    try:
        with connection:
            connection.execute(
                """
                CREATE TABLE book_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    isbn TEXT,
                    magazine_code TEXT,
                    title TEXT NOT NULL,
                    author TEXT,
                    publisher TEXT,
                    publication_format TEXT,
                    description TEXT,
                    cover_image_url TEXT,
                    cover_image_path TEXT,
                    completion_month TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                INSERT INTO book_items (
                    title,
                    completion_month,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    "吾輩は猫である",
                    "2025-05",
                    "2026-08-25 10:00:00",
                    "2026-08-25 10:00:00",
                ),
            )

            connection.execute(
                "PRAGMA user_version = 2"
            )

    finally:
        connection.close()

    initialize_database(database_path)

    assert get_user_version(database_path) == SCHEMA_VERSION

    column_names = get_table_column_names(
        database_path,
        "book_items",
    )

    assert "reading_status" in column_names
    assert "is_favorite" in column_names
    assert "rating" in column_names

    connection = sqlite3.connect(database_path)

    try:
        row = connection.execute(
            """
            SELECT
                title,
                completion_month,
                reading_status,
                is_favorite,
                rating
            FROM book_items
            """
        ).fetchone()

        assert row is not None
        assert row[0] == "吾輩は猫である"
        assert row[1] == "2025-05"
        assert row[2] is None
        assert row[3] == 0
        assert row[4] == None

    finally:
        connection.close()

def test_initialize_database_migrates_version_3_to_7(
    tmp_path: Path,
) -> None:
    """Version 3のDBをVersion 7へ移行する。"""
    database_path = tmp_path / "test_book_manager.db"

    connection = sqlite3.connect(database_path)

    try:
        with connection:
            connection.execute(
                """
                CREATE TABLE book_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    isbn TEXT,
                    magazine_code TEXT,
                    title TEXT NOT NULL,
                    author TEXT,
                    publisher TEXT,
                    publication_format TEXT,
                    description TEXT,
                    cover_image_url TEXT,
                    cover_image_path TEXT,
                    completion_month TEXT,
                    reading_status TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                INSERT INTO book_items (
                    title,
                    completion_month,
                    reading_status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "再読する書籍",
                    "2025-05",
                    "reading",
                    "2026-08-27 10:00:00",
                    "2026-08-27 10:00:00",
                ),
            )

            connection.execute(
                "PRAGMA user_version = 3"
            )

    finally:
        connection.close()

    initialize_database(database_path)

    assert get_user_version(database_path) == SCHEMA_VERSION

    column_names = get_table_column_names(
        database_path,
        "book_items",
    )

    assert "is_favorite" in column_names
    assert "rating" in column_names

    connection = sqlite3.connect(database_path)

    try:
        row = connection.execute(
            """
            SELECT
                title,
                completion_month,
                reading_status,
                is_favorite,
                rating
            FROM book_items
            """
        ).fetchone()

        assert row == (
            "再読する書籍",
            "2025-05",
            "reading",
            0,
            None,
        )

    finally:
        connection.close()

def test_initialize_database_migrates_version_4_to_7(
    tmp_path: Path,
) -> None:
    """Version 4のDBをVersion 7へ移行する。"""
    database_path = tmp_path / "test_book_manager.db"

    connection = sqlite3.connect(database_path)

    try:
        with connection:
            connection.execute(
                """
                CREATE TABLE book_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    isbn TEXT,
                    magazine_code TEXT,
                    title TEXT NOT NULL,
                    author TEXT,
                    publisher TEXT,
                    publication_format TEXT,
                    description TEXT,
                    cover_image_url TEXT,
                    cover_image_path TEXT,
                    completion_month TEXT,
                    reading_status TEXT,
                    is_favorite INTEGER NOT NULL DEFAULT 0,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                INSERT INTO book_items (
                    title,
                    completion_month,
                    reading_status,
                    is_favorite,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "評価前の書籍",
                    "2026-08",
                    "completed",
                    1,
                    "2026-08-28 10:00:00",
                    "2026-08-28 10:00:00",
                ),
            )

            connection.execute(
                "PRAGMA user_version = 4"
            )

    finally:
        connection.close()

    initialize_database(database_path)

    assert get_user_version(database_path) == SCHEMA_VERSION

    column_names = get_table_column_names(
        database_path,
        "book_items",
    )

    assert "rating" in column_names

    connection = sqlite3.connect(database_path)

    try:
        row = connection.execute(
            """
            SELECT
                title,
                completion_month,
                reading_status,
                is_favorite,
                rating
            FROM book_items
            """
        ).fetchone()

        assert row == (
            "評価前の書籍",
            "2026-08",
            "completed",
            1,
            None,
        )

    finally:
        connection.close()


def test_initialize_database_migrates_version_5_to_7(
    tmp_path: Path,
) -> None:
    """Version 5のDBをVersion 7へ移行する。"""
    database_path = tmp_path / "test_book_manager.db"

    connection = sqlite3.connect(database_path)

    try:
        with connection:
            connection.execute(
                """
                CREATE TABLE book_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    isbn TEXT,
                    magazine_code TEXT,
                    title TEXT NOT NULL,
                    author TEXT,
                    publisher TEXT,
                    publication_format TEXT,
                    description TEXT,
                    cover_image_url TEXT,
                    cover_image_path TEXT,
                    completion_month TEXT,
                    reading_status TEXT,
                    is_favorite INTEGER NOT NULL DEFAULT 0,
                    rating INTEGER,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO book_items (
                    title,
                    reading_status,
                    is_favorite,
                    rating,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "タグ機能追加前の書籍",
                    "completed",
                    1,
                    5,
                    "2026-09-03 10:00:00",
                    "2026-09-03 10:00:00",
                ),
            )
            connection.execute(
                "PRAGMA user_version = 5"
            )
    finally:
        connection.close()

    initialize_database(database_path)

    assert get_user_version(database_path) == SCHEMA_VERSION

    table_names = get_schema_object_names(
        database_path,
        "table",
    )

    assert "tags" in table_names
    assert "book_item_tags" in table_names

    connection = sqlite3.connect(database_path)

    try:
        row = connection.execute(
            """
            SELECT
                title,
                reading_status,
                is_favorite,
                rating
            FROM book_items
            """
        ).fetchone()

        assert row == (
            "タグ機能追加前の書籍",
            "completed",
            1,
            5,
        )

        tag_count = connection.execute(
            "SELECT COUNT(*) FROM tags"
        ).fetchone()
        relation_count = connection.execute(
            "SELECT COUNT(*) FROM book_item_tags"
        ).fetchone()

        assert tag_count is not None
        assert tag_count[0] == 0
        assert relation_count is not None
        assert relation_count[0] == 0
    finally:
        connection.close()


def test_initialize_database_migrates_version_6_to_7(
    tmp_path: Path,
) -> None:
    """Version 6のDBをVersion 7へ移行する。"""
    database_path = tmp_path / "test_book_manager.db"
    connection = sqlite3.connect(database_path)

    try:
        with connection:
            connection.execute(
                """
                CREATE TABLE book_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    isbn TEXT,
                    magazine_code TEXT,
                    title TEXT NOT NULL,
                    author TEXT,
                    publisher TEXT,
                    publication_format TEXT,
                    description TEXT,
                    cover_image_url TEXT,
                    cover_image_path TEXT,
                    completion_month TEXT,
                    reading_status TEXT,
                    is_favorite INTEGER NOT NULL DEFAULT 0,
                    rating INTEGER,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE book_item_tags (
                    book_item_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (book_item_id, tag_id),
                    FOREIGN KEY (book_item_id)
                        REFERENCES book_items (id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (tag_id)
                        REFERENCES tags (id)
                        ON DELETE CASCADE
                )
                """
            )
            book_cursor = connection.execute(
                """
                INSERT INTO book_items (
                    title,
                    completion_month,
                    reading_status,
                    is_favorite,
                    rating,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "読書履歴追加前の書籍",
                    "2026-08",
                    "completed",
                    1,
                    5,
                    "2026-09-06 10:00:00",
                    "2026-09-06 10:00:00",
                ),
            )
            tag_cursor = connection.execute(
                """
                INSERT INTO tags (
                    name,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    "小説",
                    "2026-09-06 10:00:00",
                    "2026-09-06 10:00:00",
                ),
            )
            connection.execute(
                """
                INSERT INTO book_item_tags (
                    book_item_id,
                    tag_id
                )
                VALUES (?, ?)
                """,
                (
                    book_cursor.lastrowid,
                    tag_cursor.lastrowid,
                ),
            )
            connection.execute("PRAGMA user_version = 6")
    finally:
        connection.close()

    initialize_database(database_path)

    assert get_user_version(database_path) == SCHEMA_VERSION
    assert "reading_histories" in get_schema_object_names(
        database_path,
        "table",
    )

    connection = sqlite3.connect(database_path)

    try:
        book_row = connection.execute(
            """
            SELECT
                title,
                completion_month,
                reading_status,
                is_favorite,
                rating
            FROM book_items
            """
        ).fetchone()
        tag_row = connection.execute(
            """
            SELECT t.name
            FROM tags AS t
            INNER JOIN book_item_tags AS bit
                ON bit.tag_id = t.id
            """
        ).fetchone()
        history_count = connection.execute(
            "SELECT COUNT(*) FROM reading_histories"
        ).fetchone()

        assert book_row == (
            "読書履歴追加前の書籍",
            "2026-08",
            "completed",
            1,
            5,
        )
        assert tag_row == ("小説",)
        assert history_count is not None
        assert history_count[0] == 0
    finally:
        connection.close()


def test_initialize_database_creates_parent_directory(
    tmp_path: Path,
) -> None:
    """親ディレクトリが存在しなくても作成できることを確認する。"""
    database_path = (
        tmp_path
        / "data"
        / "nested"
        / "test_book_manager.db"
    )

    initialize_database(database_path)

    assert database_path.parent.is_dir()


def test_initialize_database_creates_database_file(
    tmp_path: Path,
) -> None:
    """SQLiteデータベースファイルが作成されることを確認する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    assert database_path.is_file()


def test_initialize_database_creates_book_items_table(
    tmp_path: Path,
) -> None:
    """book_itemsテーブルが作成されることを確認する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    table_names = get_schema_object_names(
        database_path,
        "table",
    )

    assert "book_items" in table_names


def test_initialize_database_creates_tag_tables(
    tmp_path: Path,
) -> None:
    """タグマスタと書籍タグ関連テーブルを作成する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    table_names = get_schema_object_names(
        database_path,
        "table",
    )

    assert "tags" in table_names
    assert "book_item_tags" in table_names


def test_initialize_database_creates_expected_tag_columns(
    tmp_path: Path,
) -> None:
    """タグ関連テーブルを正しい列構成で作成する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    assert get_table_column_names(
        database_path,
        "tags",
    ) == {
        "id",
        "name",
        "created_at",
        "updated_at",
    }
    assert get_table_column_names(
        database_path,
        "book_item_tags",
    ) == {
        "book_item_id",
        "tag_id",
    }


def test_initialize_database_creates_reading_histories_table(
    tmp_path: Path,
) -> None:
    """読書履歴テーブルを作成する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    table_names = get_schema_object_names(
        database_path,
        "table",
    )

    assert "reading_histories" in table_names


def test_initialize_database_creates_expected_reading_history_columns(
    tmp_path: Path,
) -> None:
    """読書履歴テーブルを正しい列構成で作成する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    assert get_table_column_names(
        database_path,
        "reading_histories",
    ) == {
        "id",
        "book_item_id",
        "started_on",
        "completed_on",
        "notes",
        "created_at",
        "updated_at",
    }


def test_initialize_database_creates_reading_history_foreign_key(
    tmp_path: Path,
) -> None:
    """読書履歴テーブルへ書籍の外部キーを作成する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)
    connection = sqlite3.connect(database_path)

    try:
        rows = connection.execute(
            "PRAGMA foreign_key_list(reading_histories)"
        ).fetchall()
    finally:
        connection.close()

    foreign_keys = {
        (
            str(row[2]),
            str(row[3]),
            str(row[4]),
            str(row[6]),
        )
        for row in rows
    }

    assert foreign_keys == {
        (
            "book_items",
            "book_item_id",
            "id",
            "CASCADE",
        ),
    }


def test_initialize_database_creates_tag_foreign_keys(
    tmp_path: Path,
) -> None:
    """書籍タグ関連テーブルへ外部キーを作成する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    connection = sqlite3.connect(database_path)

    try:
        rows = connection.execute(
            "PRAGMA foreign_key_list(book_item_tags)"
        ).fetchall()
    finally:
        connection.close()

    foreign_keys = {
        (
            str(row[2]),
            str(row[3]),
            str(row[4]),
            str(row[6]),
        )
        for row in rows
    }

    assert foreign_keys == {
        (
            "book_items",
            "book_item_id",
            "id",
            "CASCADE",
        ),
        (
            "tags",
            "tag_id",
            "id",
            "CASCADE",
        ),
    }


def test_initialize_database_creates_expected_indexes(
    tmp_path: Path,
) -> None:
    """必要なインデックスが作成されることを確認する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    index_names = get_schema_object_names(
        database_path,
        "index",
    )

    expected_index_names = {
        "idx_book_items_title",
        "idx_book_items_isbn",
        "idx_book_items_magazine_code",
        "idx_book_item_tags_tag_id",
        "idx_reading_histories_book_item_id",
    }

    assert expected_index_names <= index_names


def test_deleting_book_cascades_only_tag_relation(
    tmp_path: Path,
) -> None:
    """書籍削除時に関連だけを削除してタグを保持する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)
    connection = create_connection(database_path)

    try:
        with connection:
            book_cursor = connection.execute(
                """
                INSERT INTO book_items (
                    title,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    "タグ付き書籍",
                    "2026-09-04 10:00:00",
                    "2026-09-04 10:00:00",
                ),
            )
            tag_cursor = connection.execute(
                """
                INSERT INTO tags (
                    name,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    "小説",
                    "2026-09-04 10:00:00",
                    "2026-09-04 10:00:00",
                ),
            )
            connection.execute(
                """
                INSERT INTO book_item_tags (
                    book_item_id,
                    tag_id
                )
                VALUES (?, ?)
                """,
                (
                    book_cursor.lastrowid,
                    tag_cursor.lastrowid,
                ),
            )
            connection.execute(
                "DELETE FROM book_items WHERE id = ?",
                (book_cursor.lastrowid,),
            )

        relation_count = connection.execute(
            "SELECT COUNT(*) FROM book_item_tags"
        ).fetchone()
        tag_count = connection.execute(
            "SELECT COUNT(*) FROM tags"
        ).fetchone()

        assert relation_count is not None
        assert relation_count[0] == 0
        assert tag_count is not None
        assert tag_count[0] == 1
    finally:
        connection.close()


def test_deleting_tag_cascades_tag_relation(
    tmp_path: Path,
) -> None:
    """タグ削除時に書籍との関連を削除する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)
    connection = create_connection(database_path)

    try:
        with connection:
            book_cursor = connection.execute(
                """
                INSERT INTO book_items (
                    title,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    "タグ付き書籍",
                    "2026-09-04 10:00:00",
                    "2026-09-04 10:00:00",
                ),
            )
            tag_cursor = connection.execute(
                """
                INSERT INTO tags (
                    name,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    "技術書",
                    "2026-09-04 10:00:00",
                    "2026-09-04 10:00:00",
                ),
            )
            connection.execute(
                """
                INSERT INTO book_item_tags (
                    book_item_id,
                    tag_id
                )
                VALUES (?, ?)
                """,
                (
                    book_cursor.lastrowid,
                    tag_cursor.lastrowid,
                ),
            )
            connection.execute(
                "DELETE FROM tags WHERE id = ?",
                (tag_cursor.lastrowid,),
            )

        relation_count = connection.execute(
            "SELECT COUNT(*) FROM book_item_tags"
        ).fetchone()
        book_count = connection.execute(
            "SELECT COUNT(*) FROM book_items"
        ).fetchone()

        assert relation_count is not None
        assert relation_count[0] == 0
        assert book_count is not None
        assert book_count[0] == 1
    finally:
        connection.close()


def test_deleting_book_cascades_reading_histories(
    tmp_path: Path,
) -> None:
    """書籍削除時に関連する読書履歴を削除する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)
    connection = create_connection(database_path)

    try:
        with connection:
            book_cursor = connection.execute(
                """
                INSERT INTO book_items (
                    title,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    "履歴付き書籍",
                    "2026-09-07 10:00:00",
                    "2026-09-07 10:00:00",
                ),
            )
            connection.execute(
                """
                INSERT INTO reading_histories (
                    book_item_id,
                    started_on,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    book_cursor.lastrowid,
                    "2026-09-01",
                    "2026-09-07 10:00:00",
                    "2026-09-07 10:00:00",
                ),
            )
            connection.execute(
                "DELETE FROM book_items WHERE id = ?",
                (book_cursor.lastrowid,),
            )

        history_count = connection.execute(
            "SELECT COUNT(*) FROM reading_histories"
        ).fetchone()

        assert history_count is not None
        assert history_count[0] == 0
    finally:
        connection.close()


def test_reading_history_rejects_all_empty_values(
    tmp_path: Path,
) -> None:
    """日付とメモがすべてNULLの履歴を拒否する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)
    connection = create_connection(database_path)

    try:
        with connection:
            book_cursor = connection.execute(
                """
                INSERT INTO book_items (
                    title,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    "テスト書籍",
                    "2026-09-07 10:00:00",
                    "2026-09-07 10:00:00",
                ),
            )

        with pytest.raises(sqlite3.IntegrityError):
            with connection:
                connection.execute(
                    """
                    INSERT INTO reading_histories (
                        book_item_id,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        book_cursor.lastrowid,
                        "2026-09-07 10:00:00",
                        "2026-09-07 10:00:00",
                    ),
                )
    finally:
        connection.close()


def test_reading_history_rejects_descending_dates(
    tmp_path: Path,
) -> None:
    """読書開始日が読了日より後の履歴を拒否する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)
    connection = create_connection(database_path)

    try:
        with connection:
            book_cursor = connection.execute(
                """
                INSERT INTO book_items (
                    title,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    "テスト書籍",
                    "2026-09-07 10:00:00",
                    "2026-09-07 10:00:00",
                ),
            )

        with pytest.raises(sqlite3.IntegrityError):
            with connection:
                connection.execute(
                    """
                    INSERT INTO reading_histories (
                        book_item_id,
                        started_on,
                        completed_on,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        book_cursor.lastrowid,
                        "2026-09-08",
                        "2026-09-07",
                        "2026-09-07 10:00:00",
                        "2026-09-07 10:00:00",
                    ),
                )
    finally:
        connection.close()


def test_initialize_database_sets_user_version(
    tmp_path: Path,
) -> None:
    """user_versionが現行スキーマVersionになることを確認する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    assert get_user_version(database_path) == SCHEMA_VERSION


def test_initialize_database_can_run_multiple_times(
    tmp_path: Path,
) -> None:
    """初期化処理を複数回実行できることを確認する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)
    initialize_database(database_path)

    assert get_user_version(database_path) == SCHEMA_VERSION


def test_initialize_database_preserves_existing_data(
    tmp_path: Path,
) -> None:
    """再初期化しても既存データが削除されないことを確認する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    connection = sqlite3.connect(database_path)

    try:
        with connection:
            connection.execute(
                """
                INSERT INTO book_items (
                    title,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    "吾輩は猫である",
                    "2026-07-21 12:00:00",
                    "2026-07-21 12:00:00",
                ),
            )
    finally:
        connection.close()

    initialize_database(database_path)

    connection = sqlite3.connect(database_path)

    try:
        row = connection.execute(
            """
            SELECT title
            FROM book_items
            """
        ).fetchone()

        assert row is not None
        assert row[0] == "吾輩は猫である"
    finally:
        connection.close()


def test_initialize_database_accepts_current_user_version(
    tmp_path: Path,
) -> None:
    """現行user_versionのデータベースを再初期化できることを確認する。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    assert get_user_version(database_path) == SCHEMA_VERSION

    initialize_database(database_path)

    assert get_user_version(database_path) == SCHEMA_VERSION


def test_initialize_database_rejects_newer_user_version(
    tmp_path: Path,
) -> None:
    """新しいuser_versionを未対応として拒否することを確認する。"""
    database_path = tmp_path / "test_book_manager.db"

    connection = sqlite3.connect(database_path)

    try:
        connection.execute(
            f"PRAGMA user_version = {SCHEMA_VERSION + 1}"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        RuntimeError,
        match="対応していません",
    ):
        initialize_database(database_path)


def test_initialize_database_does_not_lower_newer_user_version(
    tmp_path: Path,
) -> None:
    """未対応Versionを検出した際にuser_versionを変更しないことを確認する。"""
    database_path = tmp_path / "test_book_manager.db"
    newer_version = SCHEMA_VERSION + 1

    connection = sqlite3.connect(database_path)

    try:
        connection.execute(
            f"PRAGMA user_version = {newer_version}"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(RuntimeError):
        initialize_database(database_path)

    assert get_user_version(database_path) == newer_version

def test_initialize_database_uses_zero_as_default_is_favorite(
    tmp_path: Path,
) -> None:
    """お気に入り未指定時のデフォルト値を0とする。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    connection = sqlite3.connect(database_path)

    try:
        with connection:
            connection.execute(
                """
                INSERT INTO book_items (
                    title,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    "テスト書籍",
                    "2026-08-27 10:00:00",
                    "2026-08-27 10:00:00",
                ),
            )

        row = connection.execute(
            """
            SELECT is_favorite
            FROM book_items
            """
        ).fetchone()

        assert row is not None
        assert row[0] == 0

    finally:
        connection.close()


def test_initialize_database_uses_null_as_default_rating(
    tmp_path: Path,
) -> None:
    """評価未指定時のデフォルト値をNULLとする。"""
    database_path = tmp_path / "test_book_manager.db"

    initialize_database(database_path)

    connection = sqlite3.connect(database_path)

    try:
        with connection:
            connection.execute(
                """
                INSERT INTO book_items (
                    title,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    "テスト書籍",
                    "2026-08-28 10:00:00",
                    "2026-08-28 10:00:00",
                ),
            )

        row = connection.execute(
            """
            SELECT rating
            FROM book_items
            """
        ).fetchone()

        assert row is not None
        assert row[0] is None

    finally:
        connection.close()
