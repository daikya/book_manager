"""Tests for the CsvDataPackageRepository."""

import sqlite3
from pathlib import Path

import pytest

from book_manager.database.connection import create_connection
from book_manager.database.initializer import initialize_database
from book_manager.models.csv_data_package import (
    CsvDataPackageBookItem,
    CsvDataPackageBookItemTag,
    CsvDataPackageReadingHistory,
    CsvDataPackageSnapshot,
    CsvDataPackageTag,
)
from book_manager.repositories.csv_data_package_repository import (
    CsvDataPackageRepository,
)


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    """初期化済みの一時DBパスを返す。"""
    path = tmp_path / "test_book_manager.db"
    initialize_database(path)
    return path


@pytest.fixture
def repository(database_path: Path) -> CsvDataPackageRepository:
    """初期化済みDBを使用するRepositoryを返す。"""
    return CsvDataPackageRepository(database_path)


def insert_complete_test_data(database_path: Path) -> None:
    """全テーブルへ順序と関連を検証できるデータを登録する。"""
    connection = create_connection(database_path)

    try:
        with connection:
            connection.executemany(
                """
                INSERT INTO book_items (
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
                    reading_status,
                    is_favorite,
                    rating,
                    notes,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        20,
                        None,
                        "12345-67",
                        "二冊目",
                        None,
                        "出版社B",
                        "雑誌",
                        None,
                        None,
                        "cache/covers/second.jpg",
                        None,
                        "reading",
                        0,
                        None,
                        None,
                        "2026-09-02 10:00:00",
                        "2026-09-03 10:00:00",
                    ),
                    (
                        10,
                        "9784000000000",
                        None,
                        "一冊目",
                        "著者A",
                        "出版社A",
                        "単行本",
                        "内容紹介",
                        "https://example.com/cover.jpg",
                        "cache/covers/first.jpg",
                        "2026-09",
                        "completed",
                        1,
                        5,
                        "備考",
                        "2026-09-01 10:00:00",
                        "2026-09-04 10:00:00",
                    ),
                ],
            )
            connection.executemany(
                """
                INSERT INTO tags (
                    id,
                    name,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        8,
                        "再読",
                        "2026-09-02 10:00:00",
                        "2026-09-02 10:00:00",
                    ),
                    (
                        3,
                        "技術書",
                        "2026-09-01 10:00:00",
                        "2026-09-01 10:00:00",
                    ),
                ],
            )
            connection.executemany(
                """
                INSERT INTO book_item_tags (
                    book_item_id,
                    tag_id
                )
                VALUES (?, ?)
                """,
                [
                    (20, 8),
                    (10, 8),
                    (10, 3),
                ],
            )
            connection.executemany(
                """
                INSERT INTO reading_histories (
                    id,
                    book_item_id,
                    started_on,
                    completed_on,
                    notes,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        12,
                        20,
                        None,
                        None,
                        "二冊目のメモ",
                        "2026-09-05 10:00:00",
                        "2026-09-05 10:00:00",
                    ),
                    (
                        4,
                        10,
                        "2026-09-01",
                        "2026-09-04",
                        "読了した。",
                        "2026-09-01 10:00:00",
                        "2026-09-04 10:00:00",
                    ),
                ],
            )
    finally:
        connection.close()


def test_repository_accepts_path(tmp_path: Path) -> None:
    """Pathを使用してRepositoryを生成できる。"""
    database_path = tmp_path / "test.db"

    repository = CsvDataPackageRepository(database_path)

    assert repository._database_path == database_path


def test_repository_accepts_string_path(tmp_path: Path) -> None:
    """文字列パスを使用してRepositoryを生成できる。"""
    database_path = tmp_path / "test.db"

    repository = CsvDataPackageRepository(str(database_path))

    assert repository._database_path == database_path


def test_export_snapshot_returns_empty_data(
    repository: CsvDataPackageRepository,
) -> None:
    """4テーブルが空の場合に空のスナップショットを返す。"""
    snapshot = repository.export_snapshot()

    assert snapshot == CsvDataPackageSnapshot()


def test_export_snapshot_maps_books_in_id_order(
    database_path: Path,
    repository: CsvDataPackageRepository,
) -> None:
    """書籍をID昇順で取得して連番キーへ変換する。"""
    insert_complete_test_data(database_path)

    snapshot = repository.export_snapshot()

    assert snapshot.book_items == (
        CsvDataPackageBookItem(
            book_key="B000001",
            isbn="9784000000000",
            magazine_code=None,
            title="一冊目",
            author="著者A",
            publisher="出版社A",
            publication_format="単行本",
            description="内容紹介",
            cover_image_url="https://example.com/cover.jpg",
            completion_month="2026-09",
            reading_status="completed",
            is_favorite=True,
            rating=5,
            notes="備考",
            created_at="2026-09-01 10:00:00",
            updated_at="2026-09-04 10:00:00",
        ),
        CsvDataPackageBookItem(
            book_key="B000002",
            isbn=None,
            magazine_code="12345-67",
            title="二冊目",
            author=None,
            publisher="出版社B",
            publication_format="雑誌",
            description=None,
            cover_image_url=None,
            completion_month=None,
            reading_status="reading",
            is_favorite=False,
            rating=None,
            notes=None,
            created_at="2026-09-02 10:00:00",
            updated_at="2026-09-03 10:00:00",
        ),
    )


def test_export_snapshot_excludes_cover_image_path(
    database_path: Path,
    repository: CsvDataPackageRepository,
) -> None:
    """ローカル表紙画像パスをスナップショットへ含めない。"""
    insert_complete_test_data(database_path)

    snapshot = repository.export_snapshot()

    assert not hasattr(snapshot.book_items[0], "cover_image_path")
    assert not hasattr(snapshot.book_items[1], "cover_image_path")


def test_export_snapshot_maps_tags_and_relations(
    database_path: Path,
    repository: CsvDataPackageRepository,
) -> None:
    """タグをID昇順のキーへ変換して書籍との関連を維持する。"""
    insert_complete_test_data(database_path)

    snapshot = repository.export_snapshot()

    assert snapshot.tags == (
        CsvDataPackageTag(
            tag_key="T000001",
            name="技術書",
            created_at="2026-09-01 10:00:00",
            updated_at="2026-09-01 10:00:00",
        ),
        CsvDataPackageTag(
            tag_key="T000002",
            name="再読",
            created_at="2026-09-02 10:00:00",
            updated_at="2026-09-02 10:00:00",
        ),
    )
    assert snapshot.book_item_tags == (
        CsvDataPackageBookItemTag("B000001", "T000001"),
        CsvDataPackageBookItemTag("B000001", "T000002"),
        CsvDataPackageBookItemTag("B000002", "T000002"),
    )


def test_export_snapshot_maps_reading_histories(
    database_path: Path,
    repository: CsvDataPackageRepository,
) -> None:
    """読書履歴をID昇順のキーへ変換して対象書籍を維持する。"""
    insert_complete_test_data(database_path)

    snapshot = repository.export_snapshot()

    assert snapshot.reading_histories == (
        CsvDataPackageReadingHistory(
            history_key="H000001",
            book_key="B000001",
            started_on="2026-09-01",
            completed_on="2026-09-04",
            notes="読了した。",
            created_at="2026-09-01 10:00:00",
            updated_at="2026-09-04 10:00:00",
        ),
        CsvDataPackageReadingHistory(
            history_key="H000002",
            book_key="B000002",
            started_on=None,
            completed_on=None,
            notes="二冊目のメモ",
            created_at="2026-09-05 10:00:00",
            updated_at="2026-09-05 10:00:00",
        ),
    )


def test_export_snapshot_detects_orphan_book_tag_relation(
    database_path: Path,
    repository: CsvDataPackageRepository,
) -> None:
    """外部キー無効時に作られた孤立タグ関連を検出する。"""
    connection = sqlite3.connect(database_path)

    try:
        with connection:
            connection.execute(
                """
                INSERT INTO tags (
                    id,
                    name,
                    created_at,
                    updated_at
                )
                VALUES (1, '孤立タグ', '2026-09-01', '2026-09-01')
                """
            )
            connection.execute(
                """
                INSERT INTO book_item_tags (
                    book_item_id,
                    tag_id
                )
                VALUES (999, 1)
                """
            )
    finally:
        connection.close()

    with pytest.raises(sqlite3.DatabaseError, match="ID: 999"):
        repository.export_snapshot()


def test_export_snapshot_detects_orphan_reading_history(
    database_path: Path,
    repository: CsvDataPackageRepository,
) -> None:
    """外部キー無効時に作られた孤立読書履歴を検出する。"""
    connection = sqlite3.connect(database_path)

    try:
        with connection:
            connection.execute(
                """
                INSERT INTO reading_histories (
                    book_item_id,
                    notes,
                    created_at,
                    updated_at
                )
                VALUES (999, '孤立履歴', '2026-09-01', '2026-09-01')
                """
            )
    finally:
        connection.close()

    with pytest.raises(sqlite3.DatabaseError, match="ID: 999"):
        repository.export_snapshot()
