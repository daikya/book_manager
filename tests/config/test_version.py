"""アプリケーションVersion取得処理のテスト。"""

from __future__ import annotations

from importlib import metadata
from unittest.mock import patch

import pytest

from book_manager.config.version import (
    DEVELOPMENT_VERSION_LABEL,
    PACKAGE_NAME,
    get_application_version,
)


def test_get_application_version_returns_package_version() -> None:
    """パッケージメタデータのVersionを返す。"""
    with patch(
        "book_manager.config.version.metadata.version",
        return_value="2.1.0",
    ) as get_version:
        result = get_application_version()

    assert result == "2.1.0"
    get_version.assert_called_once_with(PACKAGE_NAME)


def test_get_application_version_returns_development_label() -> None:
    """パッケージメタデータがない場合は開発版を返す。"""
    with patch(
        "book_manager.config.version.metadata.version",
        side_effect=metadata.PackageNotFoundError,
    ):
        result = get_application_version()

    assert result == DEVELOPMENT_VERSION_LABEL


def test_get_application_version_does_not_hide_other_errors() -> None:
    """メタデータ未検出以外のエラーを隠さない。"""
    with patch(
        "book_manager.config.version.metadata.version",
        side_effect=RuntimeError("metadata error"),
    ):
        with pytest.raises(
            RuntimeError,
            match="metadata error",
        ):
            get_application_version()
