"""アプリケーションへ同梱する静的資源のパスを解決する。"""

from __future__ import annotations

import sys
from pathlib import Path


ASSETS_DIRECTORY_NAME = "assets"
WINDOWS_ASSETS_DIRECTORY_NAME = "windows"
APPLICATION_ICON_FILE_NAME = "book_manager.ico"
APPLICATION_ICON_PNG_FILE_NAME = "book_manager.png"


def get_resource_root() -> Path:
    """ソース版またはPyInstaller版の資源ルートを返す。

    PyInstaller版では、同梱データが展開される`_MEIPASS`を
    使用する。ソース版では、srcレイアウトのプロジェクト
    ルートを使用する。
    """
    if getattr(sys, "frozen", False):
        bundle_root = getattr(sys, "_MEIPASS", None)

        if bundle_root is None:
            raise RuntimeError(
                "配布版の資源ルートを取得できません。"
            )

        return Path(bundle_root).resolve(strict=False)

    return Path(__file__).resolve().parents[3]


def get_application_icon_path() -> Path:
    """Windows用アプリケーションアイコンのパスを返す。"""
    return (
        get_resource_root()
        / ASSETS_DIRECTORY_NAME
        / WINDOWS_ASSETS_DIRECTORY_NAME
        / APPLICATION_ICON_FILE_NAME
    )


def get_application_icon_png_path() -> Path:
    """PNG形式のアプリケーションアイコンのパスを返す。"""
    return (
        get_resource_root()
        / ASSETS_DIRECTORY_NAME
        / WINDOWS_ASSETS_DIRECTORY_NAME
        / APPLICATION_ICON_PNG_FILE_NAME
    )
