"""アプリケーションで使用する保存先を管理する。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


APPLICATION_DIRECTORY_NAME = "book_manager"
APPLICATION_HOME_ENVIRONMENT_VARIABLE = "BOOK_MANAGER_HOME"
LOCAL_APP_DATA_ENVIRONMENT_VARIABLE = "LOCALAPPDATA"
DATABASE_FILE_NAME = "books.db"


@dataclass(frozen=True, slots=True)
class ApplicationPaths:
    """アプリケーションが使用するパスをまとめた不変Model。"""

    root_directory: Path
    data_directory: Path
    database_path: Path
    backup_directory: Path
    cache_directory: Path
    cover_cache_directory: Path


def create_application_paths(
    root_directory: Path | None = None,
) -> ApplicationPaths:
    """利用者データの保存先を決定する。

    保存先は、明示指定、BOOK_MANAGER_HOME、LOCALAPPDATAの順で
    決定する。この関数はディレクトリやファイルを作成しない。

    Args:
        root_directory:
            明示的に使用する利用者データルート。

    Returns:
        用途ごとの絶対パスを保持するApplicationPaths。

    Raises:
        RuntimeError:
            利用者データルートを決定できない場合。
        ValueError:
            指定された利用者データルートが絶対パスでない場合。
    """
    resolved_root_directory = _resolve_root_directory(
        root_directory,
    )
    data_directory = resolved_root_directory / "data"
    cache_directory = resolved_root_directory / "cache"

    return ApplicationPaths(
        root_directory=resolved_root_directory,
        data_directory=data_directory,
        database_path=(
            data_directory
            / DATABASE_FILE_NAME
        ),
        backup_directory=(
            resolved_root_directory
            / "backups"
        ),
        cache_directory=cache_directory,
        cover_cache_directory=(
            cache_directory
            / "covers"
        ),
    )


def ensure_application_directories(
    paths: ApplicationPaths,
) -> None:
    """アプリケーションが使用するディレクトリを作成する。

    Args:
        paths:
            作成対象を保持するApplicationPaths。
    """
    directories = (
        paths.root_directory,
        paths.data_directory,
        paths.backup_directory,
        paths.cache_directory,
        paths.cover_cache_directory,
    )

    for directory in directories:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )


def _resolve_root_directory(
    root_directory: Path | None,
) -> Path:
    """優先順位に従って利用者データルートを解決する。"""
    if root_directory is not None:
        return _normalize_absolute_path(
            Path(root_directory),
        )

    configured_home = os.getenv(
        APPLICATION_HOME_ENVIRONMENT_VARIABLE,
        "",
    ).strip()

    if configured_home:
        return _normalize_absolute_path(
            Path(configured_home),
        )

    local_app_data = os.getenv(
        LOCAL_APP_DATA_ENVIRONMENT_VARIABLE,
        "",
    ).strip()

    if not local_app_data:
        raise RuntimeError(
            "利用者データの保存先を取得できません。"
        )

    return _normalize_absolute_path(
        Path(local_app_data)
        / APPLICATION_DIRECTORY_NAME,
    )


def _normalize_absolute_path(
    path: Path,
) -> Path:
    """絶対パスを正規化する。"""
    expanded_path = path.expanduser()

    if not expanded_path.is_absolute():
        raise ValueError(
            "利用者データの保存先には"
            "絶対パスを指定してください。"
        )

    return expanded_path.resolve(strict=False)
