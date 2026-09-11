"""Windows利用者環境変数の永続化を管理する。"""

from __future__ import annotations

import ctypes
import winreg
from collections.abc import Callable
from typing import Any, Protocol


USER_ENVIRONMENT_REGISTRY_KEY = "Environment"
ENVIRONMENT_SETTING_NAME = "Environment"
HWND_BROADCAST = 0xFFFF
WM_SETTINGCHANGE = 0x001A
SMTO_ABORTIFHUNG = 0x0002
SETTING_CHANGE_TIMEOUT_MILLISECONDS = 5_000


class UserEnvironmentStoreError(RuntimeError):
    """Windows利用者環境変数を操作できない場合の例外。"""


class UserEnvironmentStore(Protocol):
    """利用者環境変数を永続化するStoreのProtocol。"""

    def get(self, name: str) -> str | None:
        """指定した利用者環境変数を取得する。"""
        ...

    def set(self, name: str, value: str) -> None:
        """指定した利用者環境変数を保存する。"""
        ...

    def delete(self, name: str) -> None:
        """指定した利用者環境変数を削除する。"""
        ...


class WindowsUserEnvironmentStore:
    """Windowsレジストリの利用者環境変数を管理する。"""

    def __init__(
        self,
        registry: Any = winreg,
        environment_change_notifier: Callable[[], None] | None = None,
    ) -> None:
        """レジストリ操作と環境変更通知を受け取る。"""
        self._registry = registry
        self._environment_change_notifier = (
            environment_change_notifier
            or notify_environment_changed
        )

    def get(self, name: str) -> str | None:
        """Windows利用者環境変数を取得する。"""
        try:
            with self._registry.OpenKey(
                self._registry.HKEY_CURRENT_USER,
                USER_ENVIRONMENT_REGISTRY_KEY,
                0,
                self._registry.KEY_READ,
            ) as key:
                value, _ = self._registry.QueryValueEx(
                    key,
                    name,
                )
        except FileNotFoundError:
            return None
        except OSError as error:
            raise UserEnvironmentStoreError(
                "利用者環境変数を取得できません。"
            ) from error

        if not isinstance(value, str):
            raise UserEnvironmentStoreError(
                "利用者環境変数が文字列ではありません。"
            )

        return value

    def set(self, name: str, value: str) -> None:
        """Windows利用者環境変数を保存する。"""
        try:
            with self._registry.CreateKeyEx(
                self._registry.HKEY_CURRENT_USER,
                USER_ENVIRONMENT_REGISTRY_KEY,
                0,
                self._registry.KEY_SET_VALUE,
            ) as key:
                self._registry.SetValueEx(
                    key,
                    name,
                    0,
                    self._registry.REG_SZ,
                    value,
                )
        except OSError as error:
            raise UserEnvironmentStoreError(
                "利用者環境変数を保存できません。"
            ) from error

        self._environment_change_notifier()

    def delete(self, name: str) -> None:
        """Windows利用者環境変数を削除する。"""
        try:
            with self._registry.OpenKey(
                self._registry.HKEY_CURRENT_USER,
                USER_ENVIRONMENT_REGISTRY_KEY,
                0,
                self._registry.KEY_SET_VALUE,
            ) as key:
                self._registry.DeleteValue(
                    key,
                    name,
                )
        except FileNotFoundError:
            return
        except OSError as error:
            raise UserEnvironmentStoreError(
                "利用者環境変数を削除できません。"
            ) from error

        self._environment_change_notifier()


def notify_environment_changed() -> None:
    """Windowsへ利用者環境変数の変更を通知する。"""
    result = ctypes.c_size_t()

    try:
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            ENVIRONMENT_SETTING_NAME,
            SMTO_ABORTIFHUNG,
            SETTING_CHANGE_TIMEOUT_MILLISECONDS,
            ctypes.byref(result),
        )
    except OSError:
        # 永続化は完了しているため、通知失敗だけでは
        # 利用者環境変数の更新を失敗扱いにしない。
        return
