"""アプリケーション設定の表示内容を表すModel。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from book_manager.models.backup_settings import BackupSettings


@dataclass(frozen=True, slots=True)
class ApplicationSettingsSnapshot:
    """設定画面へ表示する非秘密情報を保持する不変Model。"""

    google_books_api_key_is_configured: bool
    application_name: str
    application_version: str
    root_directory: Path
    database_path: Path
    backup_directory: Path
    cover_cache_directory: Path
    log_path: Path


@dataclass(frozen=True, slots=True)
class BackupSettingsSnapshot:
    """バックアップの表示状態。存在することは復元可能性の保証ではない。"""

    active_settings: BackupSettings
    saved_settings: BackupSettings
    backup_directory: Path
    backup_count: int
    latest_backup_path: Path | None
    latest_backup_datetime: datetime | None

    @property
    def changes_pending_restart(self) -> bool:
        """保存した設定が次回起動から適用されるか。"""
        return self.active_settings != self.saved_settings
