"""アプリケーションVersionを取得する。"""

from __future__ import annotations

from importlib import metadata


PACKAGE_NAME = "book-manager"
DEVELOPMENT_VERSION_LABEL = "開発版"


def get_application_version() -> str:
    """パッケージメタデータからVersionを取得する。"""
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        return DEVELOPMENT_VERSION_LABEL
