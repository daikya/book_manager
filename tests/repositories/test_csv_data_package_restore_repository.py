"""Tests for the CsvDataPackageRestoreRepository."""

import sqlite3
from pathlib import Path

import pytest

from book_manager.database.connection import create_connection
from book_manager.database.initializer import initialize_database
from book_manager.models.csv_data_package import (
    CsvDataPackageBookItem,
    CsvDataPackageBookItemTag,
    CsvDataPackageIssue,
    CsvDataPackageIssueLevel,
    CsvDataPackageManifest,
    CsvDataPackagePreview,
    CsvDataPackageReadingHistory,
    CsvDataPackageTag,
)
from book_manager.repositories.csv_data_package_restore_repository import (
    CsvDataPackageRestoreRepository,
)


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    """初期化済み一時DBのパスを返す。"""
    path = tmp_path / "test_book_manager.db"
    initialize_database(path)
    return path


def create_preview() -> CsvDataPackagePreview:
    """全テーブルへの復元を確認できるPreviewを生成する。"""
    return CsvDataPackagePreview(
        source_path=Path("package.zip"),
        source_size=100,
        source_modified_ns=200,
        source_sha256="a" * 64,
        manifest=CsvDataPackageManifest(
            application_version="2.6.0",
            database_schema_version=7,
            exported_at="2026-09-30 13:00:00",
            book_item_count=2,
            tag_count=2,
            book_item_tag_count=3,
            reading_history_count=2,
        ),
        book_items=(
            CsvDataPackageBookItem(
                book_key="B000001",
                isbn="9784101010014",
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
                updated_at="2026-09-02 11:00:00",
            ),
            CsvDataPackageBookItem(
                book_key="B000002",
                isbn=None,
                magazine_code="12345-67",
                title="二冊目",
                author=None,
                publisher=None,
                publication_format=None,
                description=None,
                cover_image_url=None,
                completion_month=None,
                reading_status="unread",
                is_favorite=False,
                rating=None,
                notes=None,
                created_at="2026-09-03 10:00:00",
                updated_at="2026-09-03 10:00:00",
            ),
        ),
        tags=(
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
        ),
        book_item_tags=(
            CsvDataPackageBookItemTag("B000001", "T000001"),
            CsvDataPackageBookItemTag("B000001", "T000002"),
            CsvDataPackageBookItemTag("B000002", "T000002"),
        ),
        reading_histories=(
            CsvDataPackageReadingHistory(
                history_key="H000001",
                book_key="B000001",
                started_on="2026-09-01",
                completed_on="2026-09-02",
                notes="読了した。",
                created_at="2026-09-01 10:00:00",
                updated_at="2026-09-02 11:00:00",
            ),
            CsvDataPackageReadingHistory(
                history_key="H000002",
                book_key="B000002",
                started_on=None,
                completed_on=None,
                notes="日付なし",
                created_at="2026-09-03 10:00:00",
                updated_at="2026-09-03 10:00:00",
            ),
        ),
    )


def fetch_all(
    connection: sqlite3.Connection,
    table_name: str,
) -> list[sqlite3.Row]:
    """テスト対象の固定テーブルからID順で全行取得する。"""
    return connection.execute(
        f"SELECT * FROM {table_name} ORDER BY rowid ASC"
    ).fetchall()


def test_is_database_empty_returns_true_for_initialized_database(
    database_path: Path,
) -> None:
    """初期化直後の4テーブルを空と判定する。"""
    connection = create_connection(database_path)
    try:
        assert CsvDataPackageRestoreRepository.is_database_empty(
            connection
        ) is True
    finally:
        connection.close()


@pytest.mark.parametrize(
    "insert_statement",
    [
        """
        INSERT INTO book_items (
            title, created_at, updated_at
        ) VALUES ('書籍', '2026-09-01', '2026-09-01')
        """,
        """
        INSERT INTO tags (
            name, created_at, updated_at
        ) VALUES ('タグ', '2026-09-01', '2026-09-01')
        """,
    ],
)
def test_is_database_empty_detects_existing_root_data(
    database_path: Path,
    insert_statement: str,
) -> None:
    """書籍またはタグだけが存在するDBも空とは判定しない。"""
    connection = create_connection(database_path)
    try:
        with connection:
            connection.execute(insert_statement)
        assert CsvDataPackageRestoreRepository.is_database_empty(
            connection
        ) is False
    finally:
        connection.close()


def test_restore_inserts_all_tables_with_new_ids(
    database_path: Path,
) -> None:
    """新しい主キーで4テーブルと参照関係を復元する。"""
    setup_connection = create_connection(database_path)
    try:
        with setup_connection:
            setup_connection.execute(
                """
                INSERT INTO book_items (
                    title, created_at, updated_at
                ) VALUES ('採番用', '2026-01-01', '2026-01-01')
                """
            )
            setup_connection.execute("DELETE FROM book_items")
            setup_connection.execute(
                """
                INSERT INTO tags (
                    name, created_at, updated_at
                ) VALUES ('採番用', '2026-01-01', '2026-01-01')
                """
            )
            setup_connection.execute("DELETE FROM tags")
    finally:
        setup_connection.close()

    connection = create_connection(database_path)
    try:
        connection.execute("BEGIN")
        CsvDataPackageRestoreRepository().restore(
            connection,
            create_preview(),
        )
        connection.commit()

        books = fetch_all(connection, "book_items")
        tags = fetch_all(connection, "tags")
        relations = fetch_all(connection, "book_item_tags")
        histories = fetch_all(connection, "reading_histories")

        assert [row["id"] for row in books] == [2, 3]
        assert [row["id"] for row in tags] == [2, 3]
        assert [row["title"] for row in books] == ["一冊目", "二冊目"]
        assert [row["name"] for row in tags] == ["技術書", "再読"]
        assert [
            (row["book_item_id"], row["tag_id"])
            for row in relations
        ] == [(2, 2), (2, 3), (3, 3)]
        assert [row["book_item_id"] for row in histories] == [2, 3]
    finally:
        connection.close()


def test_restore_preserves_book_fields_and_excludes_cache_path(
    database_path: Path,
) -> None:
    """書籍項目を保持し、表紙キャッシュパスをNULLにする。"""
    connection = create_connection(database_path)
    try:
        connection.execute("BEGIN")
        CsvDataPackageRestoreRepository().restore(
            connection,
            create_preview(),
        )
        row = connection.execute(
            "SELECT * FROM book_items WHERE title = '一冊目'"
        ).fetchone()

        assert row is not None
        assert row["isbn"] == "9784101010014"
        assert row["cover_image_url"] == "https://example.com/cover.jpg"
        assert row["cover_image_path"] is None
        assert row["reading_status"] == "completed"
        assert row["is_favorite"] == 1
        assert row["rating"] == 5
        assert row["created_at"] == "2026-09-01 10:00:00"
        assert row["updated_at"] == "2026-09-02 11:00:00"
    finally:
        connection.rollback()
        connection.close()


def test_restore_preserves_tag_and_history_fields(
    database_path: Path,
) -> None:
    """タグと読書履歴の日時および任意値を保持する。"""
    connection = create_connection(database_path)
    try:
        connection.execute("BEGIN")
        CsvDataPackageRestoreRepository().restore(
            connection,
            create_preview(),
        )
        tag = connection.execute(
            "SELECT * FROM tags WHERE name = '技術書'"
        ).fetchone()
        histories = fetch_all(connection, "reading_histories")

        assert tag is not None
        assert tag["created_at"] == "2026-09-01 10:00:00"
        assert histories[0]["started_on"] == "2026-09-01"
        assert histories[0]["completed_on"] == "2026-09-02"
        assert histories[0]["notes"] == "読了した。"
        assert histories[0]["updated_at"] == "2026-09-02 11:00:00"
        assert histories[1]["started_on"] is None
        assert histories[1]["completed_on"] is None
    finally:
        connection.rollback()
        connection.close()


def test_restore_does_not_commit_transaction(
    database_path: Path,
) -> None:
    """Repositoryが共有接続のトランザクションを確定しない。"""
    connection = create_connection(database_path)
    observer = create_connection(database_path)
    try:
        connection.execute("BEGIN")
        CsvDataPackageRestoreRepository().restore(
            connection,
            create_preview(),
        )

        assert connection.in_transaction is True
        assert connection.execute(
            "SELECT COUNT(*) FROM book_items"
        ).fetchone()[0] == 2
        assert observer.execute(
            "SELECT COUNT(*) FROM book_items"
        ).fetchone()[0] == 0

        connection.rollback()
        assert connection.execute(
            "SELECT COUNT(*) FROM book_items"
        ).fetchone()[0] == 0
    finally:
        observer.close()
        connection.close()


def test_restore_rejects_preview_with_errors(
    database_path: Path,
) -> None:
    """事前検査エラーを持つPreviewを復元しない。"""
    valid_preview = create_preview()
    invalid_preview = CsvDataPackagePreview(
        source_path=valid_preview.source_path,
        source_size=valid_preview.source_size,
        source_modified_ns=valid_preview.source_modified_ns,
        source_sha256=valid_preview.source_sha256,
        manifest=valid_preview.manifest,
        book_items=valid_preview.book_items,
        issues=(
            CsvDataPackageIssue(
                level=CsvDataPackageIssueLevel.ERROR,
                file_name="book_items.csv",
                message="入力エラー",
            ),
        ),
    )
    connection = create_connection(database_path)
    try:
        with pytest.raises(ValueError, match="事前検査"):
            CsvDataPackageRestoreRepository().restore(
                connection,
                invalid_preview,
            )
        assert CsvDataPackageRestoreRepository.is_database_empty(connection)
    finally:
        connection.close()


def test_restore_rejects_non_empty_database(
    database_path: Path,
) -> None:
    """タグだけが存在するDBへの完全復元も拒否する。"""
    connection = create_connection(database_path)
    try:
        with connection:
            connection.execute(
                """
                INSERT INTO tags (
                    name, created_at, updated_at
                ) VALUES ('既存タグ', '2026-09-01', '2026-09-01')
                """
            )

        with pytest.raises(ValueError, match="空のデータベース"):
            CsvDataPackageRestoreRepository().restore(
                connection,
                create_preview(),
            )
        assert connection.execute(
            "SELECT COUNT(*) FROM book_items"
        ).fetchone()[0] == 0
    finally:
        connection.close()


def test_restore_failure_remains_rollbackable(
    database_path: Path,
) -> None:
    """途中のDB制約違反後も呼出側が全変更を戻せる。"""
    preview = create_preview()
    duplicate_tags_preview = CsvDataPackagePreview(
        source_path=preview.source_path,
        source_size=preview.source_size,
        source_modified_ns=preview.source_modified_ns,
        source_sha256=preview.source_sha256,
        manifest=preview.manifest,
        book_items=preview.book_items,
        tags=(preview.tags[0], preview.tags[0]),
    )
    connection = create_connection(database_path)
    try:
        connection.execute("BEGIN")
        with pytest.raises(sqlite3.IntegrityError):
            CsvDataPackageRestoreRepository().restore(
                connection,
                duplicate_tags_preview,
            )

        assert connection.in_transaction is True
        assert connection.execute(
            "SELECT COUNT(*) FROM book_items"
        ).fetchone()[0] == 2
        connection.rollback()
        assert CsvDataPackageRestoreRepository.is_database_empty(connection)
    finally:
        if connection.in_transaction:
            connection.rollback()
        connection.close()


def test_restore_rejects_missing_relation_key(
    database_path: Path,
) -> None:
    """Previewが改変され参照キーが欠落した場合も検出する。"""
    preview = create_preview()
    broken_preview = CsvDataPackagePreview(
        source_path=preview.source_path,
        source_size=preview.source_size,
        source_modified_ns=preview.source_modified_ns,
        source_sha256=preview.source_sha256,
        manifest=preview.manifest,
        book_items=preview.book_items,
        tags=preview.tags,
        book_item_tags=(
            CsvDataPackageBookItemTag("B999999", "T000001"),
        ),
    )
    connection = create_connection(database_path)
    try:
        connection.execute("BEGIN")
        with pytest.raises(sqlite3.DatabaseError, match="B999999"):
            CsvDataPackageRestoreRepository().restore(
                connection,
                broken_preview,
            )
        connection.rollback()
        assert CsvDataPackageRestoreRepository.is_database_empty(connection)
    finally:
        if connection.in_transaction:
            connection.rollback()
        connection.close()


def test_restore_preserves_null_status_and_duplicate_isbn(
    database_path: Path,
) -> None:
    """同じISBNの別書籍をNULL状態と個別の関連・履歴ごと復元する。"""
    from dataclasses import replace

    preview = create_preview()
    preview = replace(
        preview,
        book_items=tuple(
            replace(book, isbn="9784101010014", reading_status=None)
            for book in preview.book_items
        ),
    )
    connection = create_connection(database_path)
    try:
        with connection:
            CsvDataPackageRestoreRepository().restore(connection, preview)
        books = fetch_all(connection, "book_items")
        assert len(books) == 2
        assert all(row["isbn"] == "9784101010014" for row in books)
        assert all(row["reading_status"] is None for row in books)
        histories = fetch_all(connection, "reading_histories")
        assert [row["book_item_id"] for row in histories] == [
            row["id"] for row in books
        ]
        assert len(fetch_all(connection, "book_item_tags")) == 3
    finally:
        connection.close()
