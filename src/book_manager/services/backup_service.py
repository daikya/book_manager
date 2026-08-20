"""SQLiteデータベースのバックアップ処理。"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from book_manager.database.connection import create_connection


class BackupService:
    """SQLiteデータベースの自動バックアップを管理する。"""

    BACKUP_FILE_PREFIX = "books_"
    BACKUP_FILE_SUFFIX = ".db"
    BACKUP_DATETIME_FORMAT = "%Y%m%d_%H%M%S"

    def __init__(
        self,
        *,
        database_path: Path,
        backup_directory: Path,
        now_provider: Callable[[], datetime] = datetime.now,
        backup_interval: timedelta = timedelta(hours=24),
        max_backups: int = 10,
    ) -> None:
        """BackupServiceを初期化する。

        Args:
            database_path:
                バックアップ対象のSQLiteデータベース。
            backup_directory:
                バックアップファイルの保存先。
            now_provider:
                現在日時を取得する関数。
            backup_interval:
                自動バックアップを作成する間隔。
            max_backups:
                保持するバックアップの最大世代数。

        Raises:
            ValueError:
                backup_intervalまたはmax_backupsが不正な場合。
        """
        if backup_interval <= timedelta(0):
            raise ValueError(
                "バックアップ間隔は0より大きい必要があります。"
            )

        if max_backups <= 0:
            raise ValueError(
                "バックアップ保持数は1以上である必要があります。"
            )

        self._database_path = Path(database_path)
        self._backup_directory = Path(backup_directory)
        self._now_provider = now_provider
        self._backup_interval = backup_interval
        self._max_backups = max_backups

    def create_backup_if_needed(self) -> Path | None:
        """必要な場合のみデータベースをバックアップする。

        Returns:
            バックアップを作成した場合はそのPath。
            バックアップ不要または元DBが存在しない場合はNone。
        """
        if not self._database_path.is_file():
            return None

        if not self._is_backup_needed():
            return None

        self._backup_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        backup_path = self._create_backup_path()

        try:
            self._create_backup(
                backup_path,
            )
        except Exception:
            if backup_path.exists():
                backup_path.unlink()

            raise

        self._remove_old_backups()

        return backup_path

    def _is_backup_needed(self) -> bool:
        """新しいバックアップが必要か判定する。"""
        backup_files = self._get_backup_files()

        if not backup_files:
            return True

        latest_backup_datetime = self._get_backup_datetime(
            backup_files[-1],
        )

        if latest_backup_datetime is None:
            return True

        elapsed = (
            self._now_provider()
            - latest_backup_datetime
        )

        return elapsed >= self._backup_interval

    def _get_backup_files(self) -> list[Path]:
        """管理対象のバックアップファイルを取得する。"""
        if not self._backup_directory.is_dir():
            return []

        backup_files = [
            path
            for path in self._backup_directory.iterdir()
            if (
                path.is_file()
                and path.name.startswith(
                    self.BACKUP_FILE_PREFIX
                )
                and path.name.endswith(
                    self.BACKUP_FILE_SUFFIX
                )
                and self._get_backup_datetime(path) is not None
            )
        ]

        return sorted(
            backup_files,
            key=lambda path: (
                self._get_backup_datetime(path)
                or datetime.min
            ),
        )

    def _create_backup_path(self) -> Path:
        """新しいバックアップファイルのPathを生成する。"""
        timestamp = self._now_provider().strftime(
            self.BACKUP_DATETIME_FORMAT,
        )

        filename = (
            f"{self.BACKUP_FILE_PREFIX}"
            f"{timestamp}"
            f"{self.BACKUP_FILE_SUFFIX}"
        )

        return self._backup_directory / filename

    def _create_backup(
        self,
        backup_path: Path,
    ) -> None:
        """SQLite Backup APIでバックアップを作成する。"""
        source_connection = create_connection(
            self._database_path,
        )

        backup_connection = sqlite3.connect(
            backup_path,
        )

        try:
            source_connection.backup(
                backup_connection,
            )
        finally:
            backup_connection.close()
            source_connection.close()

    def _remove_old_backups(self) -> None:
        """保持数を超えた古いバックアップを削除する。"""
        backup_files = self._get_backup_files()

        excess_count = (
            len(backup_files)
            - self._max_backups
        )

        if excess_count <= 0:
            return

        for backup_path in backup_files[:excess_count]:
            backup_path.unlink()

    @classmethod
    def _get_backup_datetime(
        cls,
        backup_path: Path,
    ) -> datetime | None:
        """バックアップファイル名から作成日時を取得する。"""
        filename = backup_path.name

        if not filename.startswith(
            cls.BACKUP_FILE_PREFIX
        ):
            return None

        if not filename.endswith(
            cls.BACKUP_FILE_SUFFIX
        ):
            return None

        datetime_text = filename[
            len(cls.BACKUP_FILE_PREFIX):
            -len(cls.BACKUP_FILE_SUFFIX)
        ]

        try:
            return datetime.strptime(
                datetime_text,
                cls.BACKUP_DATETIME_FORMAT,
            )
        except ValueError:
            return None