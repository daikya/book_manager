"""アプリケーション起動時の補助処理。"""

from __future__ import annotations

import traceback

from book_manager.models.data_migration_result import (
    DataMigrationResult,
)
from book_manager.services.backup_service import BackupService
from book_manager.services.data_migration_service import (
    DataMigrationService,
)


def try_migrate_data(
    migration_service: DataMigrationService,
) -> tuple[DataMigrationResult | None, Exception | None]:
    """利用者データ移行を実行し、結果または例外を返す。"""
    try:
        result = migration_service.migrate()
    except Exception as error:
        traceback.print_exc()
        return None, error

    return result, None


def try_create_backup(
    backup_service: BackupService,
) -> Exception | None:
    """自動バックアップを実行し、失敗時の例外を返す。"""
    try:
        backup_service.create_backup_if_needed()
    except Exception as error:
        traceback.print_exc()
        return error

    return None
