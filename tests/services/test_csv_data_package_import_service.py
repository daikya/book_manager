"""Tests for the CsvDataPackageImportService."""

import sqlite3
from pathlib import Path
from unittest.mock import Mock

import pytest

from book_manager.database.connection import create_connection
from book_manager.database.initializer import initialize_database
from book_manager.models.csv_data_package import (
    CsvDataPackageArchiveFingerprint,
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
from book_manager.services.csv_data_package_import_service import (
    CsvDataPackageImportService,
)


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    """初期化済み一時DBのパスを返す。"""
    path = tmp_path / "test_book_manager.db"
    initialize_database(path)
    return path


def create_preview(
    source_path: Path,
    *,
    empty: bool = False,
) -> CsvDataPackagePreview:
    """インポートService用の正常Previewを生成する。"""
    if empty:
        book_items = ()
        tags = ()
        relations = ()
        histories = ()
    else:
        book_items = (
            CsvDataPackageBookItem(
                book_key="B000001",
                isbn="9784101010014",
                magazine_code=None,
                title="テスト書籍",
                author="著者",
                publisher="出版社",
                publication_format="単行本",
                description="内容紹介",
                cover_image_url="https://example.com/cover.jpg",
                completion_month="2026-09",
                reading_status="completed",
                is_favorite=True,
                rating=5,
                notes="備考",
                created_at="2026-09-01 10:00:00",
                updated_at="2026-09-02 10:00:00",
            ),
        )
        tags = (
            CsvDataPackageTag(
                tag_key="T000001",
                name="技術書",
                created_at="2026-09-01 10:00:00",
                updated_at="2026-09-01 10:00:00",
            ),
        )
        relations = (
            CsvDataPackageBookItemTag("B000001", "T000001"),
        )
        histories = (
            CsvDataPackageReadingHistory(
                history_key="H000001",
                book_key="B000001",
                started_on="2026-09-01",
                completed_on="2026-09-02",
                notes="読了した。",
                created_at="2026-09-01 10:00:00",
                updated_at="2026-09-02 10:00:00",
            ),
        )

    return CsvDataPackagePreview(
        source_path=source_path,
        source_size=100,
        source_modified_ns=200,
        source_sha256="a" * 64,
        manifest=CsvDataPackageManifest(
            application_version="2.6.0",
            database_schema_version=7,
            exported_at="2026-09-30 13:00:00",
            book_item_count=len(book_items),
            tag_count=len(tags),
            book_item_tag_count=len(relations),
            reading_history_count=len(histories),
        ),
        book_items=book_items,
        tags=tags,
        book_item_tags=relations,
        reading_histories=histories,
    )


def create_fingerprint(
    preview: CsvDataPackagePreview,
    **overrides: object,
) -> CsvDataPackageArchiveFingerprint:
    """Previewと一致する現在指紋を生成する。"""
    values: dict[str, object] = {
        "source_path": preview.source_path,
        "source_size": preview.source_size,
        "source_modified_ns": preview.source_modified_ns,
        "source_sha256": preview.source_sha256,
    }
    values.update(overrides)
    return CsvDataPackageArchiveFingerprint(
        **values  # type: ignore[arg-type]
    )


def create_service(
    database_path: Path,
    preview: CsvDataPackagePreview,
    *,
    backup_path: Path | None = None,
    restore_repository: CsvDataPackageRestoreRepository | None = None,
) -> tuple[CsvDataPackageImportService, Mock, Mock]:
    """一致する指紋と成功バックアップを持つServiceを返す。"""
    backup_service = Mock()
    backup_service.create_backup.return_value = (
        backup_path
        if backup_path is not None
        else database_path.parent / "backup.db"
    )
    archive_validator = Mock()
    archive_validator.validate.return_value = create_fingerprint(preview)
    service = CsvDataPackageImportService(
        database_path=database_path,
        backup_service=backup_service,
        archive_validator=archive_validator,
        restore_repository=(
            restore_repository
            if restore_repository is not None
            else CsvDataPackageRestoreRepository()
        ),
    )
    return service, backup_service, archive_validator


def table_counts(database_path: Path) -> tuple[int, int, int, int]:
    """移行対象4テーブルの件数を返す。"""
    connection = create_connection(database_path)
    try:
        return tuple(
            connection.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]
            for table_name in (
                "book_items",
                "tags",
                "book_item_tags",
                "reading_histories",
            )
        )  # type: ignore[return-value]
    finally:
        connection.close()


def test_import_preview_restores_and_commits_complete_data(
    database_path: Path,
    tmp_path: Path,
) -> None:
    """バックアップ後、4テーブルを1トランザクションで復元する。"""
    preview = create_preview(tmp_path / "package.zip")
    backup_path = tmp_path / "backups" / "before.db"
    service, backup_service, archive_validator = create_service(
        database_path,
        preview,
        backup_path=backup_path,
    )

    result = service.import_preview(preview)

    archive_validator.validate.assert_called_once_with(preview.source_path)
    backup_service.create_backup.assert_called_once_with()
    assert table_counts(database_path) == (1, 1, 1, 1)
    assert result.book_item_count == 1
    assert result.tag_count == 1
    assert result.book_item_tag_count == 1
    assert result.reading_history_count == 1
    assert result.backup_path == backup_path


def test_import_preview_preserves_data_fields(
    database_path: Path,
    tmp_path: Path,
) -> None:
    """コミット後も日時、表紙URL、関連、読書履歴を保持する。"""
    preview = create_preview(tmp_path / "package.zip")
    service, _, _ = create_service(database_path, preview)

    service.import_preview(preview)

    connection = create_connection(database_path)
    try:
        book = connection.execute("SELECT * FROM book_items").fetchone()
        relation = connection.execute(
            "SELECT * FROM book_item_tags"
        ).fetchone()
        history = connection.execute(
            "SELECT * FROM reading_histories"
        ).fetchone()

        assert book is not None
        assert relation is not None
        assert history is not None
        assert book["cover_image_url"] == "https://example.com/cover.jpg"
        assert book["cover_image_path"] is None
        assert book["created_at"] == "2026-09-01 10:00:00"
        assert relation["book_item_id"] == book["id"]
        assert history["book_item_id"] == book["id"]
        assert history["completed_on"] == "2026-09-02"
    finally:
        connection.close()


def test_import_preview_accepts_empty_package(
    database_path: Path,
    tmp_path: Path,
) -> None:
    """0件でもバックアップとトランザクションを完了する。"""
    preview = create_preview(tmp_path / "empty.zip", empty=True)
    service, backup_service, _ = create_service(database_path, preview)

    result = service.import_preview(preview)

    backup_service.create_backup.assert_called_once_with()
    assert table_counts(database_path) == (0, 0, 0, 0)
    assert result.book_item_count == 0


def test_import_preview_rejects_preflight_errors(
    database_path: Path,
    tmp_path: Path,
) -> None:
    """事前検査エラー時は再検査もバックアップもしない。"""
    preview = create_preview(tmp_path / "package.zip")
    invalid_preview = CsvDataPackagePreview(
        source_path=preview.source_path,
        source_size=preview.source_size,
        source_modified_ns=preview.source_modified_ns,
        source_sha256=preview.source_sha256,
        manifest=preview.manifest,
        issues=(
            CsvDataPackageIssue(
                level=CsvDataPackageIssueLevel.ERROR,
                file_name="book_items.csv",
                message="入力エラー",
            ),
        ),
    )
    service, backup_service, archive_validator = create_service(
        database_path,
        invalid_preview,
    )

    with pytest.raises(ValueError, match="事前検査"):
        service.import_preview(invalid_preview)

    archive_validator.validate.assert_not_called()
    backup_service.create_backup.assert_not_called()
    assert table_counts(database_path) == (0, 0, 0, 0)


def test_import_preview_rejects_missing_database(
    tmp_path: Path,
) -> None:
    """存在しないDBを暗黙に新規作成しない。"""
    database_path = tmp_path / "missing.db"
    preview = create_preview(tmp_path / "package.zip")
    service, backup_service, archive_validator = create_service(
        database_path,
        preview,
    )

    with pytest.raises(FileNotFoundError, match="データベース"):
        service.import_preview(preview)

    assert not database_path.exists()
    archive_validator.validate.assert_not_called()
    backup_service.create_backup.assert_not_called()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_size", 101),
        ("source_modified_ns", 201),
        ("source_sha256", "b" * 64),
        ("source_path", Path("other.zip")),
    ],
)
def test_import_preview_rejects_changed_package(
    database_path: Path,
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    """事前検査後に指紋が変化したZIPを拒否する。"""
    preview = create_preview(tmp_path / "package.zip")
    service, backup_service, archive_validator = create_service(
        database_path,
        preview,
    )
    archive_validator.validate.return_value = create_fingerprint(
        preview,
        **{field: value},
    )

    with pytest.raises(ValueError, match="変更されました"):
        service.import_preview(preview)

    backup_service.create_backup.assert_not_called()
    assert table_counts(database_path) == (0, 0, 0, 0)


def test_import_preview_rejects_non_empty_database_before_backup(
    database_path: Path,
    tmp_path: Path,
) -> None:
    """既存データがある場合はバックアップ作成前に拒否する。"""
    connection = create_connection(database_path)
    try:
        with connection:
            connection.execute(
                """
                INSERT INTO tags (
                    name, created_at, updated_at
                ) VALUES ('既存', '2026-09-01', '2026-09-01')
                """
            )
    finally:
        connection.close()
    preview = create_preview(tmp_path / "package.zip")
    service, backup_service, _ = create_service(database_path, preview)

    with pytest.raises(ValueError, match="空のデータベース"):
        service.import_preview(preview)

    backup_service.create_backup.assert_not_called()
    assert table_counts(database_path) == (0, 1, 0, 0)


def test_import_preview_rejects_missing_backup(
    database_path: Path,
    tmp_path: Path,
) -> None:
    """BackupServiceがパスを返さない場合は復元を開始しない。"""
    preview = create_preview(tmp_path / "package.zip")
    service, backup_service, _ = create_service(database_path, preview)
    backup_service.create_backup.return_value = None

    with pytest.raises(FileNotFoundError, match="バックアップ"):
        service.import_preview(preview)

    assert table_counts(database_path) == (0, 0, 0, 0)


def test_import_preview_preserves_database_when_backup_fails(
    database_path: Path,
    tmp_path: Path,
) -> None:
    """バックアップ例外時にDBを変更しない。"""
    preview = create_preview(tmp_path / "package.zip")
    service, backup_service, _ = create_service(database_path, preview)
    backup_service.create_backup.side_effect = RuntimeError(
        "バックアップ失敗"
    )

    with pytest.raises(RuntimeError, match="バックアップ失敗"):
        service.import_preview(preview)

    assert table_counts(database_path) == (0, 0, 0, 0)


def test_import_preview_rechecks_empty_database_after_backup(
    database_path: Path,
    tmp_path: Path,
) -> None:
    """バックアップ中にDBが変化した場合は復元せず拒否する。"""
    preview = create_preview(tmp_path / "package.zip")
    service, backup_service, _ = create_service(database_path, preview)

    def change_database() -> Path:
        connection = create_connection(database_path)
        try:
            with connection:
                connection.execute(
                    """
                    INSERT INTO tags (
                        name, created_at, updated_at
                    ) VALUES ('割込', '2026-09-01', '2026-09-01')
                    """
                )
        finally:
            connection.close()
        return tmp_path / "backup.db"

    backup_service.create_backup.side_effect = change_database

    with pytest.raises(ValueError, match="バックアップ後"):
        service.import_preview(preview)

    assert table_counts(database_path) == (0, 1, 0, 0)


def test_import_preview_rolls_back_restore_failure(
    database_path: Path,
    tmp_path: Path,
) -> None:
    """復元途中の例外時に全テーブルをロールバックする。"""
    preview = create_preview(tmp_path / "package.zip")
    restore_repository = Mock(spec=CsvDataPackageRestoreRepository)
    restore_repository.is_database_empty.return_value = True

    def fail_after_insert(
        connection: sqlite3.Connection,
        _: CsvDataPackagePreview,
    ) -> None:
        connection.execute(
            """
            INSERT INTO book_items (
                title, created_at, updated_at
            ) VALUES ('途中', '2026-09-01', '2026-09-01')
            """
        )
        raise RuntimeError("復元失敗")

    restore_repository.restore.side_effect = fail_after_insert
    service, _, _ = create_service(
        database_path,
        preview,
        restore_repository=restore_repository,
    )

    with pytest.raises(RuntimeError, match="復元失敗"):
        service.import_preview(preview)

    assert table_counts(database_path) == (0, 0, 0, 0)


def test_import_preview_rolls_back_count_mismatch(
    database_path: Path,
    tmp_path: Path,
) -> None:
    """復元後件数がPreviewと異なる場合は全件を戻す。"""
    preview = create_preview(tmp_path / "package.zip")
    restore_repository = Mock(spec=CsvDataPackageRestoreRepository)
    restore_repository.is_database_empty.return_value = True

    def insert_nothing(
        _: sqlite3.Connection,
        __: CsvDataPackagePreview,
    ) -> None:
        return None

    restore_repository.restore.side_effect = insert_nothing
    service, _, _ = create_service(
        database_path,
        preview,
        restore_repository=restore_repository,
    )

    with pytest.raises(sqlite3.DatabaseError, match="件数"):
        service.import_preview(preview)

    assert table_counts(database_path) == (0, 0, 0, 0)


def test_validate_restored_database_detects_foreign_key_error(
    database_path: Path,
    tmp_path: Path,
) -> None:
    """外部キー違反をコミット前検査で検出する。"""
    preview = create_preview(tmp_path / "package.zip", empty=True)
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            """
            INSERT INTO book_item_tags (
                book_item_id, tag_id
            ) VALUES (999, 999)
            """
        )
        broken_preview = CsvDataPackagePreview(
            source_path=preview.source_path,
            source_size=preview.source_size,
            source_modified_ns=preview.source_modified_ns,
            source_sha256=preview.source_sha256,
            manifest=preview.manifest,
            book_item_tags=(
                CsvDataPackageBookItemTag("B999999", "T999999"),
            ),
        )

        with pytest.raises(sqlite3.IntegrityError, match="外部キー"):
            CsvDataPackageImportService._validate_restored_database(
                connection,
                broken_preview,
            )
    finally:
        connection.rollback()
        connection.close()
