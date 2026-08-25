"""Tests for SQLite database initialization."""

import sqlite3
from pathlib import Path

import pytest

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

def test_initialize_database_migrates_version_1_to_2(
    tmp_path: Path,
) -> None:
    """Version 1のDBへ表紙画像関連列を追加する。"""
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

    connection = sqlite3.connect(database_path)

    try:
        row = connection.execute(
            """
            SELECT
                title,
                cover_image_url,
                cover_image_path
            FROM book_items
            """
        ).fetchone()

        assert row == (
            "移行前の書籍",
            None,
            None,
        )
    finally:
        connection.close()

def test_initialize_database_migrates_version_2_to_3(
    tmp_path: Path,
) -> None:
    """Version 2のDBへ読書ステータス列を追加する。"""
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

    connection = sqlite3.connect(database_path)

    try:
        row = connection.execute(
            """
            SELECT
                title,
                completion_month,
                reading_status
            FROM book_items
            """
        ).fetchone()

        assert row is not None
        assert row[0] == "吾輩は猫である"
        assert row[1] == "2025-05"
        assert row[2] is None

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
    }

    assert expected_index_names <= index_names


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