"""SQLiteデータベースのバックアップ処理。"""

from __future__ import annotations

import os
import re
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from book_manager.database.connection import create_connection
from book_manager.database.initializer import initialize_database
from book_manager.database.schema import SCHEMA_VERSION


@dataclass(frozen=True)
class BackupStatus:
    """管理対象ファイルの存在情報。DBの整合性は保証しない。"""

    backup_directory: Path
    backup_count: int
    latest_backup_path: Path | None
    latest_backup_datetime: datetime | None


class BackupService:
    """SQLiteデータベースの自動バックアップを管理する。"""

    BACKUP_FILE_PREFIX = "books_"
    BACKUP_FILE_SUFFIX = ".db"
    BACKUP_DATETIME_FORMAT = "%Y%m%d_%H%M%S"
    MAX_SAME_SECOND_SEQUENCE = 999

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

    def create_backup(
        self,
        *,
        protected_paths: set[Path] | None = None,
    ) -> Path | None:
        """現在のデータベースを無条件でバックアップする。

        Args:
            protected_paths:
                世代整理で削除しないバックアップファイル。

        Returns:
            バックアップを作成した場合はそのPath。
            元DBが存在しない場合はNone。
        """
        if not self._database_path.is_file():
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

        self._remove_old_backups(
            protected_paths=protected_paths,
        )

        return backup_path

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

        return self.create_backup()

    def get_backup_status(self) -> BackupStatus:
        """バックアップの件数と最新ファイルを読み取り専用で返す。"""
        backup_files = self._get_backup_files()
        latest = backup_files[-1] if backup_files else None
        return BackupStatus(
            backup_directory=self._backup_directory,
            backup_count=len(backup_files),
            latest_backup_path=latest,
            latest_backup_datetime=(
                self._get_backup_datetime(latest)
                if latest is not None
                else None
            ),
        )

    def restore_backup(
        self,
        backup_path: Path,
    ) -> None:
        """指定されたバックアップからデータベースを復元する。

        復元元を検証したあと、現在のデータベースを
        強制バックアップしてから復元する。

        Args:
            backup_path:
                復元元SQLiteデータベース。

        Raises:
            FileNotFoundError:
                復元元または現在のDBが存在しない場合。
            ValueError:
                復元元DBが不正な場合。
            RuntimeError:
                対応していないスキーマVersionの場合。
        """
        resolved_backup_path = Path(
            backup_path,
        )

        self._validate_restore_source(
            resolved_backup_path,
        )

        safety_backup_path = self.create_backup(
            protected_paths={
                resolved_backup_path.resolve(),
            },
        )

        if safety_backup_path is None:
            raise FileNotFoundError(
                "復元前のデータベースが存在しません。"
            )

        source_uri = (
            resolved_backup_path
            .resolve()
            .as_uri()
            + "?mode=ro"
        )

        source_connection = sqlite3.connect(
            source_uri,
            uri=True,
        )
        destination_connection = create_connection(
            self._database_path,
        )

        try:
            source_connection.backup(
                destination_connection,
            )
        finally:
            destination_connection.close()
            source_connection.close()

        initialize_database(
            self._database_path,
        )

        self._validate_restore_source(
            self._database_path,
        )

    def _validate_restore_source(
        self,
        backup_path: Path,
    ) -> None:
        """復元元データベースが利用可能か検証する。

        Args:
            backup_path:
                復元元SQLiteデータベース。

        Raises:
            FileNotFoundError:
                復元元ファイルが存在しない場合。
            ValueError:
                SQLiteデータベースとして不正、
                データベースが破損している、
                またはBook Manager用DBではない場合。
            RuntimeError:
                復元元DBのスキーマVersionが、
                現在のアプリケーションより新しい場合。
        """
        resolved_backup_path = Path(
            backup_path,
        )

        if not resolved_backup_path.is_file():
            raise FileNotFoundError(
                "復元元データベースが存在しません。"
            )

        connection: sqlite3.Connection | None = None

        try:
            database_uri = (
                resolved_backup_path
                .resolve()
                .as_uri()
                + "?mode=ro"
            )

            connection = sqlite3.connect(
                database_uri,
                uri=True,
            )

            integrity_row = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()

            if (
                integrity_row is None
                or str(integrity_row[0]).lower() != "ok"
            ):
                raise ValueError(
                    "復元元データベースが破損しています。"
                )

            book_items_row = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'book_items'
                """
            ).fetchone()

            if book_items_row is None:
                raise ValueError(
                    "復元元データベースは"
                    "Book Manager用ではありません。"
                )

            version_row = connection.execute(
                "PRAGMA user_version"
            ).fetchone()

            if version_row is None:
                raise ValueError(
                    "復元元データベースの"
                    "スキーマVersionを取得できませんでした。"
                )

            backup_schema_version = int(
                version_row[0],
            )

            if backup_schema_version > SCHEMA_VERSION:
                raise RuntimeError(
                    "このバックアップのスキーマVersionは、"
                    "現在のアプリケーションでは対応していません。"
                    f" backup={backup_schema_version}, "
                    f"application={SCHEMA_VERSION}"
                )

        except sqlite3.DatabaseError as error:
            raise ValueError(
                "復元元ファイルは正常な"
                "SQLiteデータベースではありません。"
            ) from error
        finally:
            if connection is not None:
                connection.close()

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
            key=self._get_backup_sort_key,
        )

    def _create_backup_path(self) -> Path:
        """既存ファイルを上書きせず今回の保存先を排他的に確保する。"""
        timestamp = self._now_provider().strftime(
            self.BACKUP_DATETIME_FORMAT,
        )

        stem = (
            f"{self.BACKUP_FILE_PREFIX}"
            f"{timestamp}"
        )

        for sequence in range(self.MAX_SAME_SECOND_SEQUENCE + 1):
            suffix = "" if sequence == 0 else f"_{sequence:03d}"
            backup_path = self._backup_directory / (
                f"{stem}{suffix}{self.BACKUP_FILE_SUFFIX}"
            )
            try:
                descriptor = os.open(
                    backup_path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
            except FileExistsError:
                continue
            os.close(descriptor)
            return backup_path

        raise RuntimeError(
            "同じ秒のバックアップファイル名をこれ以上確保できません。"
        )

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

    def _remove_old_backups(
        self,
        *,
        protected_paths: set[Path] | None = None,
    ) -> None:
        """保持数を超えた古いバックアップを削除する。

        Args:
            protected_paths:
                世代整理で削除しないバックアップファイル。
        """
        backup_files = self._get_backup_files()

        excess_count = (
            len(backup_files)
            - self._max_backups
        )

        if excess_count <= 0:
            return

        protected_resolved_paths = {
            path.resolve()
            for path in (
                protected_paths
                or set()
            )
        }

        removable_backup_files = [
            backup_path
            for backup_path in backup_files
            if backup_path.resolve()
            not in protected_resolved_paths
        ]

        for backup_path in removable_backup_files[:excess_count]:
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

        match = re.fullmatch(
            r"(\d{8}_\d{6})(?:_(\d{3}))?",
            datetime_text,
        )
        if match is None or match.group(2) == "000":
            return None

        try:
            backup_datetime = datetime.strptime(
                match.group(1),
                cls.BACKUP_DATETIME_FORMAT,
            )
        except ValueError:
            return None

        if (
            backup_datetime.strftime(cls.BACKUP_DATETIME_FORMAT)
            != match.group(1)
        ):
            return None
        return backup_datetime

    @classmethod
    def _get_backup_sort_key(cls, path: Path) -> tuple[datetime, int]:
        """日時が同じ場合は後から確保した連番を新しいものとする。"""
        backup_datetime = cls._get_backup_datetime(path)
        if backup_datetime is None:
            raise ValueError("管理対象外のバックアップです。")
        stem = path.name[
            len(cls.BACKUP_FILE_PREFIX):-len(cls.BACKUP_FILE_SUFFIX)
        ]
        sequence = int(stem[-3:]) if len(stem) > 15 else 0
        return backup_datetime, sequence
