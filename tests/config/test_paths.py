"""利用者データ保存先設定のテスト。"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from book_manager.config.paths import (
    APPLICATION_DIRECTORY_NAME,
    APPLICATION_HOME_ENVIRONMENT_VARIABLE,
    DATABASE_FILE_NAME,
    LOG_FILE_NAME,
    LOCAL_APP_DATA_ENVIRONMENT_VARIABLE,
    WINDOW_STATE_FILE_NAME,
    ApplicationPaths,
    create_application_paths,
    ensure_application_directories,
)


def clear_path_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """保存先に関係する環境変数を削除する。"""
    monkeypatch.delenv(
        APPLICATION_HOME_ENVIRONMENT_VARIABLE,
        raising=False,
    )
    monkeypatch.delenv(
        LOCAL_APP_DATA_ENVIRONMENT_VARIABLE,
        raising=False,
    )


def test_create_application_paths_uses_explicit_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """明示指定した利用者データルートを使用する。"""
    environment_home = tmp_path / "environment"
    monkeypatch.setenv(
        APPLICATION_HOME_ENVIRONMENT_VARIABLE,
        str(environment_home),
    )

    explicit_root = tmp_path / "explicit"
    paths = create_application_paths(explicit_root)

    assert paths.root_directory == explicit_root


def test_create_application_paths_uses_book_manager_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BOOK_MANAGER_HOMEをLOCALAPPDATAより優先する。"""
    configured_home = tmp_path / "configured"
    local_app_data = tmp_path / "local"
    monkeypatch.setenv(
        APPLICATION_HOME_ENVIRONMENT_VARIABLE,
        str(configured_home),
    )
    monkeypatch.setenv(
        LOCAL_APP_DATA_ENVIRONMENT_VARIABLE,
        str(local_app_data),
    )

    paths = create_application_paths()

    assert paths.root_directory == configured_home


def test_create_application_paths_uses_local_app_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """既定ではLOCALAPPDATA配下を使用する。"""
    clear_path_environment(monkeypatch)
    local_app_data = tmp_path / "local"
    monkeypatch.setenv(
        LOCAL_APP_DATA_ENVIRONMENT_VARIABLE,
        str(local_app_data),
    )

    paths = create_application_paths()

    assert paths.root_directory == (
        local_app_data
        / APPLICATION_DIRECTORY_NAME
    )


def test_create_application_paths_ignores_blank_book_manager_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """空白だけのBOOK_MANAGER_HOMEを未指定として扱う。"""
    monkeypatch.setenv(
        APPLICATION_HOME_ENVIRONMENT_VARIABLE,
        "   ",
    )
    local_app_data = tmp_path / "local"
    monkeypatch.setenv(
        LOCAL_APP_DATA_ENVIRONMENT_VARIABLE,
        str(local_app_data),
    )

    paths = create_application_paths()

    assert paths.root_directory == (
        local_app_data
        / APPLICATION_DIRECTORY_NAME
    )


def test_create_application_paths_raises_when_root_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """保存先を決定できない場合は例外を発生させる。"""
    clear_path_environment(monkeypatch)

    with pytest.raises(
        RuntimeError,
        match="利用者データの保存先を取得できません。",
    ):
        create_application_paths()


@pytest.mark.parametrize(
    "environment_variable",
    [
        APPLICATION_HOME_ENVIRONMENT_VARIABLE,
        LOCAL_APP_DATA_ENVIRONMENT_VARIABLE,
    ],
)
def test_create_application_paths_rejects_relative_environment_path(
    environment_variable: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """環境変数の相対パスを拒否する。"""
    clear_path_environment(monkeypatch)
    monkeypatch.setenv(
        environment_variable,
        "relative/directory",
    )

    with pytest.raises(
        ValueError,
        match="絶対パスを指定してください。",
    ):
        create_application_paths()


def test_create_application_paths_rejects_relative_explicit_root() -> None:
    """明示指定された相対パスを拒否する。"""
    with pytest.raises(
        ValueError,
        match="絶対パスを指定してください。",
    ):
        create_application_paths(
            Path("relative/directory"),
        )


def test_create_application_paths_returns_expected_paths(
    tmp_path: Path,
) -> None:
    """用途ごとのパスを正しく生成する。"""
    root_directory = tmp_path / "application"

    paths = create_application_paths(root_directory)

    assert paths == ApplicationPaths(
        root_directory=root_directory,
        data_directory=root_directory / "data",
        database_path=(
            root_directory
            / "data"
            / DATABASE_FILE_NAME
        ),
        backup_directory=(
            root_directory
            / "backups"
        ),
        cache_directory=(
            root_directory
            / "cache"
        ),
        cover_cache_directory=(
            root_directory
            / "cache"
            / "covers"
        ),
        log_directory=(
            root_directory
            / "logs"
        ),
        log_path=(
            root_directory
            / "logs"
            / LOG_FILE_NAME
        ),
    )


def test_create_application_paths_returns_absolute_paths(
    tmp_path: Path,
) -> None:
    """生成するすべてのパスが絶対パスになる。"""
    paths = create_application_paths(
        tmp_path / "application",
    )

    assert all(
        path.is_absolute()
        for path in (
            paths.root_directory,
            paths.data_directory,
            paths.database_path,
            paths.backup_directory,
            paths.cache_directory,
            paths.cover_cache_directory,
            paths.log_directory,
            paths.log_path,
        )
    )

    assert paths.backup_settings_path.is_absolute()
    assert paths.window_state_path.is_absolute()


def test_backup_settings_path_uses_user_data_root(
    tmp_path: Path,
) -> None:
    """設定はインストール先でなく利用者データ領域に置く。"""
    paths = create_application_paths(tmp_path / "application")

    assert paths.backup_settings_path == (
        tmp_path / "application" / "backup_settings.json"
    )
    assert not paths.backup_settings_path.exists()


def test_window_state_path_uses_user_data_root(
    tmp_path: Path,
) -> None:
    """状態はインストール先でなく利用者データ領域に置く。"""
    paths = create_application_paths(tmp_path / "application")

    assert paths.window_state_path == (
        tmp_path / "application" / WINDOW_STATE_FILE_NAME
    )
    assert not paths.window_state_path.exists()


def test_create_application_paths_does_not_create_directories(
    tmp_path: Path,
) -> None:
    """パス生成時にはファイルシステムを変更しない。"""
    root_directory = tmp_path / "application"

    paths = create_application_paths(root_directory)

    assert paths.root_directory == root_directory
    assert not root_directory.exists()


def test_create_application_paths_does_not_depend_on_current_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """カレントディレクトリを変更しても結果が変わらない。"""
    local_app_data = tmp_path / "local"
    first_current_directory = tmp_path / "first"
    second_current_directory = tmp_path / "second"
    first_current_directory.mkdir()
    second_current_directory.mkdir()
    clear_path_environment(monkeypatch)
    monkeypatch.setenv(
        LOCAL_APP_DATA_ENVIRONMENT_VARIABLE,
        str(local_app_data),
    )

    monkeypatch.chdir(first_current_directory)
    first_paths = create_application_paths()
    monkeypatch.chdir(second_current_directory)
    second_paths = create_application_paths()

    assert first_paths == second_paths


def test_application_paths_is_immutable(
    tmp_path: Path,
) -> None:
    """ApplicationPathsを生成後に変更できない。"""
    paths = create_application_paths(
        tmp_path / "application",
    )

    with pytest.raises(FrozenInstanceError):
        paths.database_path = tmp_path / "changed.db"  # type: ignore[misc]


def test_ensure_application_directories_creates_all_directories(
    tmp_path: Path,
) -> None:
    """必要なディレクトリをすべて作成する。"""
    paths = create_application_paths(
        tmp_path / "application",
    )

    ensure_application_directories(paths)

    assert paths.root_directory.is_dir()
    assert paths.data_directory.is_dir()
    assert paths.backup_directory.is_dir()
    assert paths.cache_directory.is_dir()
    assert paths.cover_cache_directory.is_dir()
    assert paths.log_directory.is_dir()
    assert not paths.database_path.exists()
    assert not paths.log_path.exists()


def test_ensure_application_directories_can_run_multiple_times(
    tmp_path: Path,
) -> None:
    """ディレクトリ作成処理を繰り返し実行できる。"""
    paths = create_application_paths(
        tmp_path / "application",
    )

    ensure_application_directories(paths)
    ensure_application_directories(paths)

    assert paths.cover_cache_directory.is_dir()
    assert paths.log_directory.is_dir()


def test_ensure_application_directories_raises_for_conflicting_file(
    tmp_path: Path,
) -> None:
    """作成先に同名ファイルがある場合は例外を通知する。"""
    root_directory = tmp_path / "application"
    root_directory.mkdir()
    conflicting_path = root_directory / "data"
    conflicting_path.write_text(
        "not a directory",
        encoding="utf-8",
    )
    paths = create_application_paths(root_directory)

    with pytest.raises(FileExistsError):
        ensure_application_directories(paths)
