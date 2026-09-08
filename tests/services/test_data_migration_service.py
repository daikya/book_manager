"""利用者データ移行Serviceのテスト。"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from book_manager.config.paths import create_application_paths
from book_manager.database.initializer import initialize_database
from book_manager.database.schema import SCHEMA_VERSION
from book_manager.models.data_migration_result import (
    DataMigrationStatus,
)
from book_manager.services.data_migration_service import (
    AmbiguousLegacyDatabaseError,
    DataMigrationError,
    DataMigrationService,
)


def create_service(
    tmp_path: Path,
) -> tuple[DataMigrationService, Path, Path]:
    """テスト用の移行Serviceと新旧ルートを生成する。"""
    legacy_root = tmp_path / "legacy"
    destination_root = tmp_path / "destination"
    paths = create_application_paths(destination_root)
    service = DataMigrationService(
        application_paths=paths,
        legacy_root_directory=legacy_root,
    )
    return service, legacy_root, destination_root


def create_book_manager_database(
    database_path: Path,
    *,
    title: str = "移行前の書籍",
) -> None:
    """書籍を1件持つ有効なDBを作成する。"""
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
                    title,
                    "2026-09-08 10:00:00",
                    "2026-09-08 10:00:00",
                ),
            )
    finally:
        connection.close()


def get_book_title(database_path: Path) -> str:
    """DBに保存された先頭書籍のタイトルを返す。"""
    connection = sqlite3.connect(database_path)

    try:
        row = connection.execute(
            """
            SELECT title
            FROM book_items
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()
    finally:
        connection.close()

    assert row is not None
    return str(row[0])


def test_migrate_returns_no_legacy_data_when_source_is_missing(
    tmp_path: Path,
) -> None:
    """旧DBがない場合は新規利用として結果を返す。"""
    service, _, destination_root = create_service(tmp_path)

    result = service.migrate()

    assert result.status is DataMigrationStatus.NO_LEGACY_DATA
    assert result.source_database_path is None
    assert result.destination_database_path == (
        destination_root
        / "data"
        / "books.db"
    )
    assert not result.destination_database_path.exists()


def test_migrate_creates_application_directories(
    tmp_path: Path,
) -> None:
    """移行判定時に必要な保存先ディレクトリを作成する。"""
    service, _, destination_root = create_service(tmp_path)

    service.migrate()

    assert (destination_root / "data").is_dir()
    assert (destination_root / "backups").is_dir()
    assert (destination_root / "cache" / "covers").is_dir()


def test_migrate_returns_not_needed_for_existing_destination(
    tmp_path: Path,
) -> None:
    """新DBが存在する場合は移行しない。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    destination_database = (
        destination_root
        / "data"
        / "books.db"
    )
    legacy_database = legacy_root / "data" / "books.db"
    create_book_manager_database(
        destination_database,
        title="新保存先の書籍",
    )
    create_book_manager_database(
        legacy_database,
        title="旧保存先の書籍",
    )

    result = service.migrate()

    assert result.status is DataMigrationStatus.NOT_NEEDED
    assert result.source_database_path is None
    assert get_book_title(destination_database) == "新保存先の書籍"


def test_migrate_rejects_invalid_existing_destination(
    tmp_path: Path,
) -> None:
    """不正な新DBを旧DBで自動上書きしない。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    legacy_database = legacy_root / "data" / "books.db"
    create_book_manager_database(legacy_database)
    destination_database = (
        destination_root
        / "data"
        / "books.db"
    )
    destination_database.parent.mkdir(parents=True)
    destination_database.write_text(
        "not sqlite",
        encoding="utf-8",
    )

    with pytest.raises(
        DataMigrationError,
        match="移行先ファイルは正常なSQLite",
    ):
        service.migrate()

    assert destination_database.read_text(
        encoding="utf-8",
    ) == "not sqlite"


def test_migrate_copies_books_database(
    tmp_path: Path,
) -> None:
    """books.dbを新保存先へ移行する。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    legacy_database = legacy_root / "data" / "books.db"
    create_book_manager_database(legacy_database)

    result = service.migrate()

    destination_database = (
        destination_root
        / "data"
        / "books.db"
    )
    assert result.status is DataMigrationStatus.MIGRATED
    assert result.source_database_path == legacy_database
    assert result.destination_database_path == destination_database
    assert destination_database.is_file()
    assert get_book_title(destination_database) == "移行前の書籍"


def test_migrate_copies_book_manager_database_as_fallback(
    tmp_path: Path,
) -> None:
    """books.dbがない場合は旧定義のbook_manager.dbを移行する。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    legacy_database = (
        legacy_root
        / "data"
        / "book_manager.db"
    )
    create_book_manager_database(legacy_database)

    result = service.migrate()

    assert result.status is DataMigrationStatus.MIGRATED
    assert result.source_database_path == legacy_database
    assert get_book_title(
        destination_root / "data" / "books.db"
    ) == "移行前の書籍"


def test_migrate_rejects_ambiguous_legacy_databases(
    tmp_path: Path,
) -> None:
    """旧DB候補が2件ある場合は自動選択しない。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    create_book_manager_database(
        legacy_root / "data" / "books.db"
    )
    create_book_manager_database(
        legacy_root / "data" / "book_manager.db"
    )

    with pytest.raises(
        AmbiguousLegacyDatabaseError,
        match="両方存在するため",
    ):
        service.migrate()

    assert not (
        destination_root / "data" / "books.db"
    ).exists()


def test_migrate_rejects_non_sqlite_source(
    tmp_path: Path,
) -> None:
    """SQLiteでない旧DBを移行しない。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    legacy_database = legacy_root / "data" / "books.db"
    legacy_database.parent.mkdir(parents=True)
    legacy_database.write_text("not sqlite", encoding="utf-8")

    with pytest.raises(
        DataMigrationError,
        match="移行元ファイルは正常なSQLite",
    ):
        service.migrate()

    assert not (
        destination_root / "data" / "books.db"
    ).exists()


def test_migrate_rejects_database_for_another_application(
    tmp_path: Path,
) -> None:
    """Book Manager用でないSQLite DBを移行しない。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    legacy_database = legacy_root / "data" / "books.db"
    legacy_database.parent.mkdir(parents=True)
    connection = sqlite3.connect(legacy_database)

    try:
        connection.execute("CREATE TABLE sample (id INTEGER)")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        DataMigrationError,
        match="Book Manager用ではありません。",
    ):
        service.migrate()

    assert not (
        destination_root / "data" / "books.db"
    ).exists()


def test_migrate_rejects_newer_schema_version(
    tmp_path: Path,
) -> None:
    """対応Versionより新しい旧DBを移行しない。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    legacy_database = legacy_root / "data" / "books.db"
    create_book_manager_database(legacy_database)
    connection = sqlite3.connect(legacy_database)

    try:
        connection.execute(
            f"PRAGMA user_version = {SCHEMA_VERSION + 1}"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        DataMigrationError,
        match="スキーマVersionには対応していません。",
    ):
        service.migrate()

    assert not (
        destination_root / "data" / "books.db"
    ).exists()


def test_migrate_does_not_modify_legacy_database(
    tmp_path: Path,
) -> None:
    """移行元DBの内容とVersionを変更しない。"""
    service, legacy_root, _ = create_service(tmp_path)
    legacy_database = legacy_root / "data" / "books.db"
    create_book_manager_database(legacy_database)
    before_bytes = legacy_database.read_bytes()

    service.migrate()

    assert legacy_database.is_file()
    assert legacy_database.read_bytes() == before_bytes


def test_migrate_can_run_multiple_times(
    tmp_path: Path,
) -> None:
    """2回目は新DBを上書きせず移行不要になる。"""
    service, legacy_root, _ = create_service(tmp_path)
    legacy_database = legacy_root / "data" / "books.db"
    create_book_manager_database(legacy_database)

    first_result = service.migrate()
    second_result = service.migrate()

    assert first_result.status is DataMigrationStatus.MIGRATED
    assert second_result.status is DataMigrationStatus.NOT_NEEDED


def test_migrate_uses_current_schema_version(
    tmp_path: Path,
) -> None:
    """複製後DBを現在のスキーマVersionとして利用できる。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    legacy_database = legacy_root / "data" / "books.db"
    create_book_manager_database(legacy_database)

    service.migrate()

    connection = sqlite3.connect(
        destination_root / "data" / "books.db"
    )

    try:
        version_row = connection.execute(
            "PRAGMA user_version"
        ).fetchone()
    finally:
        connection.close()

    assert version_row is not None
    assert version_row[0] == SCHEMA_VERSION


def test_migrate_removes_temporary_database_after_failure(
    tmp_path: Path,
) -> None:
    """DB複製失敗時は移行用一時ファイルを残さない。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    legacy_database = legacy_root / "data" / "books.db"
    create_book_manager_database(legacy_database)
    temporary_database = (
        destination_root
        / "data"
        / "books.db.migrating"
    )

    def fail_copy(
        source_path: Path,
        destination_path: Path,
    ) -> None:
        del source_path
        destination_path.write_text(
            "partial",
            encoding="utf-8",
        )
        raise sqlite3.OperationalError("copy failed")

    with patch.object(
        service,
        "_copy_database",
        side_effect=fail_copy,
    ):
        with pytest.raises(
            DataMigrationError,
            match="安全に移行できませんでした。",
        ):
            service.migrate()

    assert not temporary_database.exists()
    assert not (
        destination_root / "data" / "books.db"
    ).exists()
    assert legacy_database.is_file()


def test_migrate_replaces_stale_temporary_database(
    tmp_path: Path,
) -> None:
    """前回失敗時の通常ファイルを新しい一時DBへ置き換える。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    legacy_database = legacy_root / "data" / "books.db"
    create_book_manager_database(legacy_database)
    temporary_database = (
        destination_root
        / "data"
        / "books.db.migrating"
    )
    temporary_database.parent.mkdir(parents=True)
    temporary_database.write_text("stale", encoding="utf-8")

    result = service.migrate()

    assert result.status is DataMigrationStatus.MIGRATED
    assert not temporary_database.exists()


def test_migrate_copies_valid_backup_files(
    tmp_path: Path,
) -> None:
    """命名規則に合う旧バックアップを複製する。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    create_book_manager_database(
        legacy_root / "data" / "books.db"
    )
    backup_directory = legacy_root / "backups"
    backup_directory.mkdir()
    valid_backup = backup_directory / "books_20260908_100000.db"
    valid_backup.write_bytes(b"backup")
    (backup_directory / "memo.txt").write_text(
        "not backup",
        encoding="utf-8",
    )
    (backup_directory / "books_invalid.db").write_bytes(
        b"invalid name"
    )

    result = service.migrate()

    copied_backup = (
        destination_root
        / "backups"
        / valid_backup.name
    )
    assert result.migrated_backup_count == 1
    assert copied_backup.read_bytes() == b"backup"
    assert not (
        destination_root / "backups" / "memo.txt"
    ).exists()


def test_migrate_does_not_overwrite_existing_backup(
    tmp_path: Path,
) -> None:
    """新保存先の同名バックアップを上書きしない。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    create_book_manager_database(
        legacy_root / "data" / "books.db"
    )
    backup_name = "books_20260908_100000.db"
    source_backup = legacy_root / "backups" / backup_name
    source_backup.parent.mkdir()
    source_backup.write_bytes(b"legacy")
    destination_backup = (
        destination_root
        / "backups"
        / backup_name
    )
    destination_backup.parent.mkdir(parents=True)
    destination_backup.write_bytes(b"destination")

    result = service.migrate()

    assert result.migrated_backup_count == 0
    assert destination_backup.read_bytes() == b"destination"


def test_migrate_copies_cover_images(
    tmp_path: Path,
) -> None:
    """旧表紙画像キャッシュを複製する。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    create_book_manager_database(
        legacy_root / "data" / "books.db"
    )
    cover_directory = legacy_root / "cache" / "covers"
    cover_directory.mkdir(parents=True)
    first_cover = cover_directory / "first.jpg"
    second_cover = cover_directory / "second.png"
    first_cover.write_bytes(b"first")
    second_cover.write_bytes(b"second")

    result = service.migrate()

    destination_cover_directory = (
        destination_root
        / "cache"
        / "covers"
    )
    assert result.migrated_cover_count == 2
    assert (
        destination_cover_directory
        / first_cover.name
    ).read_bytes() == b"first"
    assert (
        destination_cover_directory
        / second_cover.name
    ).read_bytes() == b"second"


def test_migrate_does_not_overwrite_existing_cover(
    tmp_path: Path,
) -> None:
    """新保存先の同名表紙画像を上書きしない。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    create_book_manager_database(
        legacy_root / "data" / "books.db"
    )
    source_cover = (
        legacy_root
        / "cache"
        / "covers"
        / "cover.jpg"
    )
    source_cover.parent.mkdir(parents=True)
    source_cover.write_bytes(b"legacy")
    destination_cover = (
        destination_root
        / "cache"
        / "covers"
        / "cover.jpg"
    )
    destination_cover.parent.mkdir(parents=True)
    destination_cover.write_bytes(b"destination")

    result = service.migrate()

    assert result.migrated_cover_count == 0
    assert destination_cover.read_bytes() == b"destination"


def test_migrate_returns_warning_when_optional_copy_fails(
    tmp_path: Path,
) -> None:
    """任意ファイルの失敗を警告として返しDB移行を維持する。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    create_book_manager_database(
        legacy_root / "data" / "books.db"
    )
    source_cover = (
        legacy_root
        / "cache"
        / "covers"
        / "cover.jpg"
    )
    source_cover.parent.mkdir(parents=True)
    source_cover.write_bytes(b"cover")

    with patch(
        "book_manager.services.data_migration_service.shutil.copy2",
        side_effect=OSError("copy failed"),
    ):
        result = service.migrate()

    assert (
        result.status
        is DataMigrationStatus.MIGRATED_WITH_WARNINGS
    )
    assert result.migrated_cover_count == 0
    assert result.warnings == (
        "表紙画像「cover.jpg」をコピーできませんでした。",
    )
    assert (
        destination_root / "data" / "books.db"
    ).is_file()


def test_migrate_ignores_optional_subdirectories(
    tmp_path: Path,
) -> None:
    """バックアップとキャッシュのサブディレクトリを移行しない。"""
    service, legacy_root, destination_root = create_service(
        tmp_path,
    )
    create_book_manager_database(
        legacy_root / "data" / "books.db"
    )
    nested_backup = legacy_root / "backups" / "nested"
    nested_backup.mkdir(parents=True)
    (nested_backup / "books_20260908_100000.db").write_bytes(
        b"backup"
    )
    nested_cover = legacy_root / "cache" / "covers" / "nested"
    nested_cover.mkdir(parents=True)
    (nested_cover / "cover.jpg").write_bytes(b"cover")

    result = service.migrate()

    assert result.migrated_backup_count == 0
    assert result.migrated_cover_count == 0
    assert not (
        destination_root / "backups" / "nested"
    ).exists()
    assert not (
        destination_root / "cache" / "covers" / "nested"
    ).exists()
