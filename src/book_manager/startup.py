"""アプリケーション起動時の補助処理。"""

from __future__ import annotations

import traceback

from book_manager.services.backup_service import BackupService


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