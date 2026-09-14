"""アプリケーション設定の参照と変更を提供するService。"""

from __future__ import annotations

import os
from collections.abc import Callable, MutableMapping
from pathlib import Path

from book_manager.config.backup_settings_store import (
    BackupSettingsStore,
    BackupSettingsStoreError,
)
from book_manager.config.paths import ApplicationPaths
from book_manager.config.user_environment import (
    UserEnvironmentStore,
    UserEnvironmentStoreError,
)
from book_manager.models.application_settings import (
    ApplicationSettingsSnapshot,
    BackupSettingsSnapshot,
)
from book_manager.models.backup_settings import BackupSettings
from book_manager.services.backup_service import BackupService


GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE = (
    "GOOGLE_BOOKS_API_KEY"
)


class ApplicationSettingsError(RuntimeError):
    """アプリケーション設定処理の基底例外。"""


class ApplicationSettingsValidationError(
    ApplicationSettingsError,
):
    """設定値が不正な場合の例外。"""


class UserEnvironmentUpdateError(ApplicationSettingsError):
    """利用者環境変数を更新できない場合の例外。"""


class DirectoryOpenError(ApplicationSettingsError):
    """利用者データ関連フォルダーを開けない場合の例外。

    """


class BackupSettingsError(ApplicationSettingsError):
    """バックアップ設定・作成処理が失敗した場合。"""


class ApplicationSettingsService:
    """設定画面で使用する設定処理を提供する。"""

    def __init__(
        self,
        application_paths: ApplicationPaths,
        application_name: str,
        application_version: str,
        user_environment_store: UserEnvironmentStore,
        environment: MutableMapping[str, str] | None = None,
        directory_opener: Callable[[Path], None] | None = None,
        backup_service: BackupService | None = None,
        backup_settings_store: BackupSettingsStore | None = None,
        active_backup_settings: BackupSettings | None = None,
    ) -> None:
        """設定表示値と外部操作を受け取る。"""
        self._application_paths = application_paths
        self._application_name = application_name
        self._application_version = application_version
        self._user_environment_store = user_environment_store
        self._environment = (
            environment
            if environment is not None
            else os.environ
        )
        self._directory_opener = (
            directory_opener
            or _open_directory_with_default_application
        )
        self._backup_service = backup_service
        self._backup_settings_store = (
            backup_settings_store
            if backup_settings_store is not None
            else BackupSettingsStore(application_paths.backup_settings_path)
        )
        self._active_backup_settings = active_backup_settings

    def get_backup_settings_snapshot(self) -> BackupSettingsSnapshot:
        """保存値・起動時有効値と管理対象バックアップの存在情報を返す。"""
        backup_service = self._require_backup_service()
        try:
            saved_settings = self._backup_settings_store.load()
            status = backup_service.get_backup_status()
        except (BackupSettingsStoreError, OSError) as error:
            raise BackupSettingsError(
                "バックアップ設定またはバックアップの状態を確認できません。"
            ) from error

        if self._active_backup_settings is None:
            raise BackupSettingsError("有効なバックアップ設定を取得できません。")

        return BackupSettingsSnapshot(
            active_settings=self._active_backup_settings,
            saved_settings=saved_settings,
            backup_directory=status.backup_directory,
            backup_count=status.backup_count,
            latest_backup_path=status.latest_backup_path,
            latest_backup_datetime=status.latest_backup_datetime,
        )

    def save_backup_settings(
        self,
        interval_hours: str,
        max_backups: str,
    ) -> BackupSettings:
        """値を保存する。起動中のBackupServiceは変更しない。"""
        hours = self._parse_integer(interval_hours, "自動バックアップ間隔")
        generations = self._parse_integer(max_backups, "保持世代数")
        try:
            settings = BackupSettings(
                backup_interval_hours=hours,
                max_backups=generations,
            )
        except ValueError as error:
            raise ApplicationSettingsValidationError(str(error)) from error

        try:
            self._backup_settings_store.save(settings)
        except BackupSettingsStoreError as error:
            raise BackupSettingsError("バックアップ設定を保存できません。") from error
        return settings

    def create_backup_now(self) -> Path | None:
        """起動中の設定で、間隔に関係なくバックアップを作成する。"""
        try:
            return self._require_backup_service().create_backup()
        except (OSError, ValueError, RuntimeError) as error:
            raise BackupSettingsError(
                "バックアップを作成または整理できませんでした。"
            ) from error

    def _require_backup_service(self) -> BackupService:
        if self._backup_service is None:
            raise BackupSettingsError("バックアップ処理を利用できません。")
        return self._backup_service

    @staticmethod
    def _parse_integer(value: str, field_name: str) -> int:
        if not isinstance(value, str):
            raise ApplicationSettingsValidationError(
                f"{field_name}は整数で入力してください。"
            )
        stripped = value.strip()
        if not stripped or not stripped.isascii() or not stripped.isdecimal():
            raise ApplicationSettingsValidationError(
                f"{field_name}は整数で入力してください。"
            )
        return int(stripped)

    def get_snapshot(self) -> ApplicationSettingsSnapshot:
        """設定画面へ表示する現在の設定内容を返す。"""
        return ApplicationSettingsSnapshot(
            google_books_api_key_is_configured=(
                self._is_google_books_api_key_configured()
            ),
            application_name=self._application_name,
            application_version=self._application_version,
            root_directory=(
                self._application_paths.root_directory
            ),
            database_path=self._application_paths.database_path,
            backup_directory=(
                self._application_paths.backup_directory
            ),
            cover_cache_directory=(
                self._application_paths.cover_cache_directory
            ),
            log_path=self._application_paths.log_path,
        )

    def save_google_books_api_key(self, api_key: str) -> str:
        """Google Books APIキーを保存する。

        現在のプロセス環境にも反映する。
        """
        normalized_api_key = self._normalize_api_key(api_key)

        try:
            self._user_environment_store.set(
                GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE,
                normalized_api_key,
            )
        except UserEnvironmentStoreError as error:
            raise UserEnvironmentUpdateError(
                "Google Books APIキーを保存できません。"
            ) from error

        self._environment[
            GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE
        ] = normalized_api_key

        return normalized_api_key

    def delete_google_books_api_key(self) -> None:
        """Google Books APIキーを削除する。

        永続領域と現在のプロセス環境から削除する。
        """
        try:
            self._user_environment_store.delete(
                GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE,
            )
        except UserEnvironmentStoreError as error:
            raise UserEnvironmentUpdateError(
                "Google Books APIキーを削除できません。"
            ) from error

        self._environment.pop(
            GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE,
            None,
        )

    def open_directory(self, directory: Path) -> None:
        """絶対パスのフォルダーを作成して開く。"""
        normalized_directory = Path(directory).expanduser()

        if not normalized_directory.is_absolute():
            raise DirectoryOpenError(
                "開くフォルダーには絶対パスが必要です。"
            )

        try:
            normalized_directory.mkdir(
                parents=True,
                exist_ok=True,
            )
            self._directory_opener(normalized_directory)
        except OSError as error:
            raise DirectoryOpenError(
                "フォルダーを開けません。"
            ) from error

    def _is_google_books_api_key_configured(self) -> bool:
        """現在環境または利用者環境の設定有無を返す。"""
        current_value = self._environment.get(
            GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE,
            "",
        )

        if current_value.strip():
            return True

        try:
            stored_value = self._user_environment_store.get(
                GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE,
            )
        except UserEnvironmentStoreError as error:
            raise UserEnvironmentUpdateError(
                "Google Books APIキーの設定状態を"
                "確認できません。"
            ) from error

        return bool(stored_value and stored_value.strip())

    @staticmethod
    def _normalize_api_key(api_key: str) -> str:
        """保存可能なAPIキーへ正規化する。"""
        if not isinstance(api_key, str):
            raise ApplicationSettingsValidationError(
                "Google Books APIキーは文字列で"
                "入力してください。"
            )

        normalized_api_key = api_key.strip()

        if not normalized_api_key:
            raise ApplicationSettingsValidationError(
                "Google Books APIキーを入力してください。"
            )

        if "\n" in normalized_api_key or "\r" in normalized_api_key:
            raise ApplicationSettingsValidationError(
                "Google Books APIキーに改行は使用できません。"
            )

        if "\x00" in normalized_api_key:
            raise ApplicationSettingsValidationError(
                "Google Books APIキーにNUL文字は使用できません。"
            )

        return normalized_api_key


def _open_directory_with_default_application(
    directory: Path,
) -> None:
    """Windowsの既定アプリケーションで開く。"""
    os.startfile(directory)  # type: ignore[attr-defined]
