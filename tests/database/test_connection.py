"""Tests for SQLite connection utilities."""

import sqlite3
from pathlib import Path

import pytest

from book_manager.database.connection import create_connection


def test_create_connection_returns_sqlite_connection(
    tmp_path: Path,
) -> None:
    """SQLite接続を生成できることを確認する。"""
    database_path = tmp_path / "test_book_manager.db"

    connection = create_connection(database_path)

    try:
        assert isinstance(connection, sqlite3.Connection)
    finally:
        connection.close()


def test_create_connection_sets_row_factory(
    tmp_path: Path,
) -> None:
    """row_factoryにsqlite3.Rowが設定されることを確認する。"""
    database_path = tmp_path / "test_book_manager.db"

    connection = create_connection(database_path)

    try:
        assert connection.row_factory is sqlite3.Row
    finally:
        connection.close()


def test_create_connection_enables_foreign_keys(
    tmp_path: Path,
) -> None:
    """外部キー制約が有効になることを確認する。"""
    database_path = tmp_path / "test_book_manager.db"

    connection = create_connection(database_path)

    try:
        row = connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()

        assert row is not None
        assert row[0] == 1
    finally:
        connection.close()


def test_create_connection_can_execute_sql(
    tmp_path: Path,
) -> None:
    """生成した接続でSQLを実行できることを確認する。"""
    database_path = tmp_path / "test_book_manager.db"

    connection = create_connection(database_path)

    try:
        result = connection.execute("SELECT 1 AS value").fetchone()

        assert result is not None
        assert result["value"] == 1
    finally:
        connection.close()


def test_create_connection_can_store_and_read_japanese_text(
    tmp_path: Path,
) -> None:
    """日本語を保存および取得できることを確認する。"""
    database_path = tmp_path / "test_book_manager.db"

    connection = create_connection(database_path)

    try:
        with connection:
            connection.execute(
                """
                CREATE TABLE sample (
                    id INTEGER PRIMARY KEY,
                    text_value TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO sample (text_value)
                VALUES (?)
                """,
                ("吾輩は猫である",),
            )

        result = connection.execute(
            """
            SELECT text_value
            FROM sample
            """
        ).fetchone()

        assert result is not None
        assert result["text_value"] == "吾輩は猫である"
    finally:
        connection.close()


def test_connection_can_be_closed_by_caller(
    tmp_path: Path,
) -> None:
    """呼び出し元が接続を閉じられることを確認する。"""
    database_path = tmp_path / "test_book_manager.db"

    connection = create_connection(database_path)
    connection.close()

    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")


def test_create_connection_raises_error_for_missing_parent_directory(
    tmp_path: Path,
) -> None:
    """存在しない親ディレクトリでは接続に失敗することを確認する。"""
    database_path = (
        tmp_path
        / "missing"
        / "directory"
        / "test_book_manager.db"
    )

    with pytest.raises(sqlite3.OperationalError):
        create_connection(database_path)
