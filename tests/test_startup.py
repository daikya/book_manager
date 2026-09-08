"""アプリケーション起動時の補助処理のテスト。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

from book_manager.models.data_migration_result import (
    DataMigrationResult,
    DataMigrationStatus,
)
from book_manager.startup import (
    try_create_backup,
    try_migrate_data,
)


def test_try_migrate_data_returns_result(
    tmp_path: Path,
) -> None:
    """移行成功時は結果とNoneを返す。"""
    expected_result = DataMigrationResult(
        status=DataMigrationStatus.NO_LEGACY_DATA,
        source_database_path=None,
        destination_database_path=tmp_path / "books.db",
    )
    migration_service = Mock()
    migration_service.migrate.return_value = expected_result

    result, error = try_migrate_data(migration_service)

    assert result is expected_result
    assert error is None
    migration_service.migrate.assert_called_once_with()


def test_try_migrate_data_returns_error() -> None:
    """移行失敗時はNoneと例外を返す。"""
    expected_error = RuntimeError("migration failed")
    migration_service = Mock()
    migration_service.migrate.side_effect = expected_error

    with patch(
        "book_manager.startup.traceback.print_exc"
    ) as print_exc:
        result, error = try_migrate_data(migration_service)

    assert result is None
    assert error is expected_error
    print_exc.assert_called_once_with()


def test_try_create_backup_returns_none() -> None:
    """バックアップ成功時はNoneを返す。"""
    backup_service = Mock()

    result = try_create_backup(backup_service)

    assert result is None
    backup_service.create_backup_if_needed.assert_called_once_with()


def test_try_create_backup_returns_error() -> None:
    """バックアップ失敗時は例外を返す。"""
    expected_error = RuntimeError("backup failed")
    backup_service = Mock()
    backup_service.create_backup_if_needed.side_effect = (
        expected_error
    )

    with patch(
        "book_manager.startup.traceback.print_exc"
    ) as print_exc:
        result = try_create_backup(backup_service)

    assert result is expected_error
    print_exc.assert_called_once_with()
