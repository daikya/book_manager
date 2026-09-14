"""アプリケーション設定Serviceのテスト。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from book_manager.config.backup_settings_store import (
    BackupSettingsStore,
    BackupSettingsStoreError,
)
from book_manager.config.paths import ApplicationPaths
from book_manager.config.user_environment import (
    UserEnvironmentStoreError,
)
from book_manager.models.backup_settings import BackupSettings
from book_manager.services.application_settings_service import (
    GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE,
    ApplicationSettingsService,
    ApplicationSettingsValidationError,
    BackupSettingsError,
    DirectoryOpenError,
    UserEnvironmentUpdateError,
)
from book_manager.services.backup_service import BackupStatus


def create_application_paths(tmp_path: Path) -> ApplicationPaths:
    """テスト用のアプリケーションパスを生成する。"""
    root_directory = tmp_path / "book_manager"
    data_directory = root_directory / "data"
    cache_directory = root_directory / "cache"
    log_directory = root_directory / "logs"

    return ApplicationPaths(
        root_directory=root_directory,
        data_directory=data_directory,
        database_path=data_directory / "books.db",
        backup_directory=root_directory / "backups",
        cache_directory=cache_directory,
        cover_cache_directory=cache_directory / "covers",
        log_directory=log_directory,
        log_path=log_directory / "book_manager.log",
    )


def create_service(
    tmp_path: Path,
    *,
    environment: dict[str, str] | None = None,
    user_environment_store: MagicMock | None = None,
    directory_opener: MagicMock | None = None,
) -> tuple[
    ApplicationSettingsService,
    dict[str, str],
    MagicMock,
    MagicMock,
]:
    """テスト用Serviceと依存オブジェクトを生成する。"""
    actual_environment = (
        environment
        if environment is not None
        else {}
    )
    if user_environment_store is None:
        actual_store = MagicMock()
        actual_store.get.return_value = None
    else:
        actual_store = user_environment_store
    actual_opener = (
        directory_opener
        if directory_opener is not None
        else MagicMock()
    )

    service = ApplicationSettingsService(
        application_paths=create_application_paths(tmp_path),
        application_name="Book Manager",
        application_version="2.1.0",
        user_environment_store=actual_store,
        environment=actual_environment,
        directory_opener=actual_opener,
    )

    return (
        service,
        actual_environment,
        actual_store,
        actual_opener,
    )


def test_get_snapshot_holds_application_information_and_paths(
    tmp_path: Path,
) -> None:
    """Snapshotへアプリ情報と各パスを設定する。"""
    service, _, _, _ = create_service(tmp_path)
    paths = create_application_paths(tmp_path)

    snapshot = service.get_snapshot()

    assert snapshot.application_name == "Book Manager"
    assert snapshot.application_version == "2.1.0"
    assert snapshot.root_directory == paths.root_directory
    assert snapshot.database_path == paths.database_path
    assert snapshot.backup_directory == paths.backup_directory
    assert (
        snapshot.cover_cache_directory
        == paths.cover_cache_directory
    )
    assert snapshot.log_path == paths.log_path


def test_get_snapshot_detects_key_in_current_environment(
    tmp_path: Path,
) -> None:
    """現在プロセスのAPIキーを設定済みとして扱う。"""
    environment = {
        GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE: "current-key",
    }
    service, _, store, _ = create_service(
        tmp_path,
        environment=environment,
    )

    snapshot = service.get_snapshot()

    assert snapshot.google_books_api_key_is_configured is True
    store.get.assert_not_called()


def test_get_snapshot_detects_key_in_user_environment(
    tmp_path: Path,
) -> None:
    """永続化済みのAPIキーを設定済みとして扱う。"""
    store = MagicMock()
    store.get.return_value = "stored-key"
    service, _, _, _ = create_service(
        tmp_path,
        user_environment_store=store,
    )

    snapshot = service.get_snapshot()

    assert snapshot.google_books_api_key_is_configured is True
    store.get.assert_called_once_with(
        GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE,
    )


def test_get_snapshot_treats_blank_values_as_unconfigured(
    tmp_path: Path,
) -> None:
    """空白だけのAPIキーを未設定として扱う。"""
    store = MagicMock()
    store.get.return_value = "  "
    service, _, _, _ = create_service(
        tmp_path,
        environment={
            GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE: " ",
        },
        user_environment_store=store,
    )

    snapshot = service.get_snapshot()

    assert snapshot.google_books_api_key_is_configured is False


def test_get_snapshot_wraps_store_error(
    tmp_path: Path,
) -> None:
    """設定状態の取得失敗を専用例外へ変換する。"""
    store = MagicMock()
    store.get.side_effect = UserEnvironmentStoreError
    service, _, _, _ = create_service(
        tmp_path,
        user_environment_store=store,
    )

    with pytest.raises(
        UserEnvironmentUpdateError,
        match="設定状態を確認できません",
    ):
        service.get_snapshot()


def test_save_google_books_api_key_trims_and_saves_value(
    tmp_path: Path,
) -> None:
    """APIキーの前後空白を除去して永続化する。"""
    service, environment, store, _ = create_service(tmp_path)

    saved_value = service.save_google_books_api_key(
        "  test-api-key  ",
    )

    assert saved_value == "test-api-key"
    store.set.assert_called_once_with(
        GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE,
        "test-api-key",
    )
    assert environment == {
        GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE: "test-api-key",
    }


@pytest.mark.parametrize(
    ("api_key", "message"),
    (
        ("", "入力してください"),
        ("   ", "入力してください"),
        ("key\nvalue", "改行は使用できません"),
        ("key\rvalue", "改行は使用できません"),
        ("key\x00value", "NUL文字は使用できません"),
    ),
)
def test_save_google_books_api_key_rejects_invalid_value(
    tmp_path: Path,
    api_key: str,
    message: str,
) -> None:
    """保存できないAPIキーを拒否する。"""
    service, environment, store, _ = create_service(tmp_path)

    with pytest.raises(
        ApplicationSettingsValidationError,
        match=message,
    ):
        service.save_google_books_api_key(api_key)

    assert environment == {}
    store.set.assert_not_called()


def test_save_google_books_api_key_rejects_non_string(
    tmp_path: Path,
) -> None:
    """文字列以外のAPIキーを拒否する。"""
    service, environment, store, _ = create_service(tmp_path)

    with pytest.raises(
        ApplicationSettingsValidationError,
        match="文字列で入力してください",
    ):
        service.save_google_books_api_key(  # type: ignore[arg-type]
            123,
        )

    assert environment == {}
    store.set.assert_not_called()


def test_save_failure_preserves_current_environment_and_secret(
    tmp_path: Path,
) -> None:
    """保存失敗時に現在値を維持する。

    例外へ秘密値を含めないことも確認する。
    """
    environment = {
        GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE: "existing-key",
    }
    store = MagicMock()
    store.get.return_value = None
    store.set.side_effect = UserEnvironmentStoreError
    service, _, _, _ = create_service(
        tmp_path,
        environment=environment,
        user_environment_store=store,
    )
    secret_value = "new-secret-key"

    with pytest.raises(
        UserEnvironmentUpdateError,
        match="保存できません",
    ) as error_info:
        service.save_google_books_api_key(secret_value)

    assert secret_value not in str(error_info.value)
    assert environment == {
        GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE: "existing-key",
    }


def test_delete_google_books_api_key_removes_both_values(
    tmp_path: Path,
) -> None:
    """永続領域と現在プロセスからAPIキーを削除する。"""
    environment = {
        GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE: "test-api-key",
    }
    service, _, store, _ = create_service(
        tmp_path,
        environment=environment,
    )

    service.delete_google_books_api_key()

    store.delete.assert_called_once_with(
        GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE,
    )
    assert GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE not in (
        environment
    )


def test_delete_failure_preserves_current_environment(
    tmp_path: Path,
) -> None:
    """永続領域の削除失敗時に現在値を維持する。"""
    environment = {
        GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE: "existing-key",
    }
    store = MagicMock()
    store.get.return_value = None
    store.delete.side_effect = UserEnvironmentStoreError
    service, _, _, _ = create_service(
        tmp_path,
        environment=environment,
        user_environment_store=store,
    )

    with pytest.raises(
        UserEnvironmentUpdateError,
        match="削除できません",
    ):
        service.delete_google_books_api_key()

    assert environment == {
        GOOGLE_BOOKS_API_KEY_ENVIRONMENT_VARIABLE: "existing-key",
    }


def test_open_directory_creates_and_opens_directory(
    tmp_path: Path,
) -> None:
    """存在しないフォルダーを作成して開く。"""
    service, _, _, opener = create_service(tmp_path)
    directory = tmp_path / "new" / "directory"

    service.open_directory(directory)

    assert directory.is_dir()
    opener.assert_called_once_with(directory)


def test_open_directory_opens_existing_directory(
    tmp_path: Path,
) -> None:
    """作成済みフォルダーをそのまま開く。"""
    service, _, _, opener = create_service(tmp_path)
    directory = tmp_path / "existing"
    directory.mkdir()

    service.open_directory(directory)

    opener.assert_called_once_with(directory)


def test_open_directory_rejects_relative_path(
    tmp_path: Path,
) -> None:
    """カレントディレクトリ依存の相対パスを拒否する。"""
    service, _, _, opener = create_service(tmp_path)

    with pytest.raises(
        DirectoryOpenError,
        match="絶対パスが必要です",
    ):
        service.open_directory(Path("relative"))

    opener.assert_not_called()


def test_open_directory_wraps_creation_error(
    tmp_path: Path,
) -> None:
    """フォルダー作成失敗を専用例外へ変換する。"""
    service, _, _, opener = create_service(tmp_path)
    blocking_file = tmp_path / "file"
    blocking_file.write_text("test", encoding="utf-8")

    with pytest.raises(
        DirectoryOpenError,
        match="フォルダーを開けません",
    ):
        service.open_directory(blocking_file / "directory")

    opener.assert_not_called()


def test_open_directory_wraps_opener_error(
    tmp_path: Path,
) -> None:
    """OSのフォルダー起動失敗を専用例外へ変換する。"""
    opener = MagicMock(side_effect=OSError)
    service, _, _, _ = create_service(
        tmp_path,
        directory_opener=opener,
    )
    directory = tmp_path / "existing"
    directory.mkdir()

    with pytest.raises(
        DirectoryOpenError,
        match="フォルダーを開けません",
    ):
        service.open_directory(directory)


def create_backup_settings_service(
    tmp_path: Path,
) -> tuple[ApplicationSettingsService, MagicMock, BackupSettingsStore]:
    """バックアップ設定のテスト用Service。"""
    paths = create_application_paths(tmp_path)
    store = BackupSettingsStore(paths.backup_settings_path)
    backup_service = MagicMock()
    backup_service.get_backup_status.return_value = BackupStatus(
        backup_directory=paths.backup_directory,
        backup_count=0,
        latest_backup_path=None,
        latest_backup_datetime=None,
    )
    service = ApplicationSettingsService(
        application_paths=paths,
        application_name="Book Manager",
        application_version="2.1.0",
        user_environment_store=MagicMock(),
        environment={},
        backup_service=backup_service,
        backup_settings_store=store,
        active_backup_settings=BackupSettings(),
    )
    return service, backup_service, store


def test_get_backup_settings_snapshot_with_no_backups(tmp_path: Path) -> None:
    service, _, _ = create_backup_settings_service(tmp_path)

    snapshot = service.get_backup_settings_snapshot()

    assert snapshot.active_settings == BackupSettings()
    assert snapshot.saved_settings == BackupSettings()
    assert snapshot.backup_count == 0
    assert snapshot.latest_backup_path is None


def test_backup_settings_are_saved_but_not_applied_until_restart(
    tmp_path: Path,
) -> None:
    service, backup_service, store = create_backup_settings_service(tmp_path)

    result = service.save_backup_settings(" 48 ", " 3 ")
    snapshot = service.get_backup_settings_snapshot()

    assert result == BackupSettings(48, 3)
    assert store.load() == result
    assert snapshot.saved_settings == result
    assert snapshot.active_settings == BackupSettings()
    assert snapshot.changes_pending_restart is True
    backup_service.create_backup.assert_not_called()


@pytest.mark.parametrize(
    ("hours", "count"),
    [
        ("0", "10"),
        ("169", "10"),
        ("24", "1"),
        ("24", "101"),
        ("24.0", "10"),
        ("+24", "10"),
        ("１２", "10"),
        ("", "10"),
    ],
)
def test_rejects_invalid_backup_settings_without_writing(
    tmp_path: Path, hours: str, count: str,
) -> None:
    service, _, store = create_backup_settings_service(tmp_path)

    with pytest.raises(ApplicationSettingsValidationError):
        service.save_backup_settings(hours, count)

    assert store.load() == BackupSettings()
    assert not create_application_paths(tmp_path).backup_settings_path.exists()


def test_save_backup_settings_wraps_write_failure(tmp_path: Path) -> None:
    paths = create_application_paths(tmp_path)
    store = MagicMock()
    store.save.side_effect = BackupSettingsStoreError("denied")
    service, backup_service, _ = create_backup_settings_service(tmp_path)
    service._backup_settings_store = store

    with pytest.raises(BackupSettingsError, match="保存できません"):
        service.save_backup_settings("24", "10")

    backup_service.create_backup.assert_not_called()
    assert not paths.backup_settings_path.exists()


def test_get_backup_settings_snapshot_reports_latest(tmp_path: Path) -> None:
    service, backup_service, _ = create_backup_settings_service(tmp_path)
    directory = create_application_paths(tmp_path).backup_directory
    latest = directory / "books_20260914_090000.db"
    backup_service.get_backup_status.return_value = BackupStatus(
        backup_directory=directory,
        backup_count=2,
        latest_backup_path=latest,
        latest_backup_datetime=datetime(2026, 9, 14, 9),
    )

    snapshot = service.get_backup_settings_snapshot()

    assert snapshot.backup_count == 2
    assert snapshot.latest_backup_path == latest


def test_create_backup_now_does_not_check_interval(tmp_path: Path) -> None:
    service, backup_service, _ = create_backup_settings_service(tmp_path)
    new_file = tmp_path / "books.db"
    backup_service.create_backup.return_value = new_file

    assert service.create_backup_now() == new_file
    backup_service.create_backup.assert_called_once_with()


def test_create_backup_now_propagates_no_database(tmp_path: Path) -> None:
    service, backup_service, _ = create_backup_settings_service(tmp_path)
    backup_service.create_backup.return_value = None

    assert service.create_backup_now() is None


def test_create_backup_now_wraps_failure(tmp_path: Path) -> None:
    service, backup_service, _ = create_backup_settings_service(tmp_path)
    backup_service.create_backup.side_effect = OSError("disk full")

    with pytest.raises(BackupSettingsError):
        service.create_backup_now()
