"""アプリケーション設定の表示内容を表すModel。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
