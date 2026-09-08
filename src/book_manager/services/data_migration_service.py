"""Version 1.9以前の利用者データを安全に移行するService。"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from book_manager.config.paths import (
    ApplicationPaths,
    ensure_application_directories,
)
from book_manager.database.initializer import initialize_database
from book_manager.database.schema import SCHEMA_VERSION
from book_manager.models.data_migration_result import (
    DataMigrationResult,
    DataMigrationStatus,
)


class DataMigrationError(RuntimeError):
    """利用者データを安全に移行できない場合の例外。"""


class AmbiguousLegacyDatabaseError(DataMigrationError):
    """移行元データベースを一意に決定できない場合の例外。"""


class DataMigrationService:
    """旧保存先から新保存先へ利用者データを複製する。"""

    LEGACY_DATABASE_FILE_NAMES = (
        "books.db",
        "book_manager.db",
    )
    TEMPORARY_DATABASE_SUFFIX = ".migrating"
    BACKUP_DATETIME_FORMAT = "%Y%m%d_%H%M%S"

    def __init__(
        self,
        *,
        application_paths: ApplicationPaths,
        legacy_root_directory: Path,
    ) -> None:
        """DataMigrationServiceを初期化する。

        Args:
            application_paths:
                Version 2.0以降の利用者データ保存先。
            legacy_root_directory:
                Version 1.9以前の保存先を含むルート。
        """
        self._application_paths = application_paths
        self._legacy_root_directory = Path(
            legacy_root_directory,
        ).resolve(strict=False)

    def migrate(self) -> DataMigrationResult:
        """必要に応じて旧利用者データを新保存先へ移行する。

        Returns:
            移行状態、移行件数および警告を保持する結果。

        Raises:
            DataMigrationError:
                移行元または移行先DBが不正、DBが破損、
                対応外Version、または複製に失敗した場合。
            AmbiguousLegacyDatabaseError:
                移行元DBを一意に決定できない場合。
        """
        ensure_application_directories(
            self._application_paths,
        )

        destination_database_path = (
            self._application_paths.database_path
        )

        if destination_database_path.exists():
            self._validate_database(
                destination_database_path,
                role="移行先",
            )
            return DataMigrationResult(
                status=DataMigrationStatus.NOT_NEEDED,
                source_database_path=None,
                destination_database_path=(
                    destination_database_path
                ),
            )

        source_database_path = (
            self._find_legacy_database()
        )

        if source_database_path is None:
            return DataMigrationResult(
                status=DataMigrationStatus.NO_LEGACY_DATA,
                source_database_path=None,
                destination_database_path=(
                    destination_database_path
                ),
            )

        self._validate_distinct_paths(
            source_database_path,
            destination_database_path,
        )
        self._validate_database(
            source_database_path,
            role="移行元",
        )
        self._migrate_database(
            source_database_path,
            destination_database_path,
        )

        warnings: list[str] = []
        migrated_backup_count = self._copy_optional_files(
            source_directory=(
                self._legacy_root_directory
                / "backups"
            ),
            destination_directory=(
                self._application_paths.backup_directory
            ),
            file_kind="バックアップ",
            warnings=warnings,
            backup_files_only=True,
        )
        migrated_cover_count = self._copy_optional_files(
            source_directory=(
                self._legacy_root_directory
                / "cache"
                / "covers"
            ),
            destination_directory=(
                self._application_paths.cover_cache_directory
            ),
            file_kind="表紙画像",
            warnings=warnings,
            backup_files_only=False,
        )

        status = DataMigrationStatus.MIGRATED

        if warnings:
            status = (
                DataMigrationStatus.MIGRATED_WITH_WARNINGS
            )

        return DataMigrationResult(
            status=status,
            source_database_path=source_database_path,
            destination_database_path=(
                destination_database_path
            ),
            migrated_backup_count=migrated_backup_count,
            migrated_cover_count=migrated_cover_count,
            warnings=tuple(warnings),
        )

    def _find_legacy_database(self) -> Path | None:
        """旧データベースを一意に特定する。"""
        legacy_data_directory = (
            self._legacy_root_directory
            / "data"
        )
        candidates = [
            legacy_data_directory / file_name
            for file_name
            in self.LEGACY_DATABASE_FILE_NAMES
            if (
                (legacy_data_directory / file_name).is_file()
                and not (
                    legacy_data_directory
                    / file_name
                ).is_symlink()
            )
        ]

        if len(candidates) > 1:
            raise AmbiguousLegacyDatabaseError(
                "移行元候補のbooks.dbとbook_manager.dbが"
                "両方存在するため、自動移行できません。"
            )

        if not candidates:
            return None

        return candidates[0]

    def _validate_distinct_paths(
        self,
        source_database_path: Path,
        destination_database_path: Path,
    ) -> None:
        """移行元と移行先が異なることを確認する。"""
        if (
            source_database_path.resolve(strict=False)
            == destination_database_path.resolve(strict=False)
        ):
            raise DataMigrationError(
                "移行元と移行先が同じため、"
                "データを移行できません。"
            )

    def _validate_database(
        self,
        database_path: Path,
        *,
        role: str,
    ) -> None:
        """Book Manager用SQLiteデータベースを検証する。"""
        if not database_path.is_file():
            raise DataMigrationError(
                f"{role}データベースが通常ファイルではありません。"
            )

        connection: sqlite3.Connection | None = None

        try:
            database_uri = (
                database_path.resolve().as_uri()
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
                raise DataMigrationError(
                    f"{role}データベースが破損しています。"
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
                raise DataMigrationError(
                    f"{role}データベースは"
                    "Book Manager用ではありません。"
                )

            version_row = connection.execute(
                "PRAGMA user_version"
            ).fetchone()

            if version_row is None:
                raise DataMigrationError(
                    f"{role}データベースの"
                    "スキーマVersionを取得できません。"
                )

            schema_version = int(version_row[0])

            if schema_version > SCHEMA_VERSION:
                raise DataMigrationError(
                    f"{role}データベースの"
                    "スキーマVersionには対応していません。"
                    f" database={schema_version}, "
                    f"application={SCHEMA_VERSION}"
                )
        except DataMigrationError:
            raise
        except sqlite3.DatabaseError as error:
            raise DataMigrationError(
                f"{role}ファイルは正常な"
                "SQLiteデータベースではありません。"
            ) from error
        finally:
            if connection is not None:
                connection.close()

    def _migrate_database(
        self,
        source_database_path: Path,
        destination_database_path: Path,
    ) -> None:
        """一時DBで複製と更新を完了してから正式名へ変更する。"""
        temporary_database_path = (
            destination_database_path.with_name(
                destination_database_path.name
                + self.TEMPORARY_DATABASE_SUFFIX
            )
        )

        if temporary_database_path.exists():
            if not temporary_database_path.is_file():
                raise DataMigrationError(
                    "移行用一時パスが通常ファイルではありません。"
                )
            temporary_database_path.unlink()

        try:
            self._copy_database(
                source_database_path,
                temporary_database_path,
            )
            initialize_database(
                temporary_database_path,
            )
            self._validate_database(
                temporary_database_path,
                role="複製後",
            )
            temporary_database_path.replace(
                destination_database_path,
            )
        except DataMigrationError:
            self._remove_temporary_database(
                temporary_database_path,
            )
            raise
        except Exception as error:
            self._remove_temporary_database(
                temporary_database_path,
            )
            raise DataMigrationError(
                "既存データベースを安全に"
                "移行できませんでした。"
            ) from error

    def _copy_database(
        self,
        source_database_path: Path,
        temporary_database_path: Path,
    ) -> None:
        """SQLite Backup APIで一時DBへ複製する。"""
        source_uri = (
            source_database_path.resolve().as_uri()
            + "?mode=ro"
        )
        source_connection = sqlite3.connect(
            source_uri,
            uri=True,
        )
        destination_connection = sqlite3.connect(
            temporary_database_path,
        )

        try:
            source_connection.backup(
                destination_connection,
            )
        finally:
            destination_connection.close()
            source_connection.close()

    @staticmethod
    def _remove_temporary_database(
        temporary_database_path: Path,
    ) -> None:
        """失敗した移行用一時DBを可能な場合に削除する。"""
        if temporary_database_path.is_file():
            try:
                temporary_database_path.unlink()
            except OSError:
                pass

    def _copy_optional_files(
        self,
        *,
        source_directory: Path,
        destination_directory: Path,
        file_kind: str,
        warnings: list[str],
        backup_files_only: bool,
    ) -> int:
        """バックアップまたは表紙画像を上書きせず複製する。"""
        if not source_directory.is_dir():
            return 0

        copied_count = 0

        for source_path in sorted(source_directory.iterdir()):
            if (
                not source_path.is_file()
                or source_path.is_symlink()
            ):
                continue

            if (
                backup_files_only
                and not self._is_backup_file(source_path)
            ):
                continue

            destination_path = (
                destination_directory
                / source_path.name
            )

            if destination_path.exists():
                continue

            try:
                shutil.copy2(
                    source_path,
                    destination_path,
                )
            except OSError:
                warnings.append(
                    f"{file_kind}「{source_path.name}」を"
                    "コピーできませんでした。"
                )
            else:
                copied_count += 1

        return copied_count

    @classmethod
    def _is_backup_file(
        cls,
        backup_path: Path,
    ) -> bool:
        """既存BackupServiceの命名規則に合うか判定する。"""
        filename = backup_path.name

        if not filename.startswith("books_"):
            return False

        if not filename.endswith(".db"):
            return False

        datetime_text = filename[
            len("books_"):
            -len(".db")
        ]

        try:
            datetime.strptime(
                datetime_text,
                cls.BACKUP_DATETIME_FORMAT,
            )
        except ValueError:
            return False

        return True
