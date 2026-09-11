"""Windows利用者環境変数Storeのテスト。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from book_manager.config.user_environment import (
    USER_ENVIRONMENT_REGISTRY_KEY,
    UserEnvironmentStoreError,
    WindowsUserEnvironmentStore,
)


GOOGLE_BOOKS_API_KEY = "GOOGLE_BOOKS_API_KEY"


def create_registry() -> SimpleNamespace:
    """テスト用のレジストリ操作を生成する。"""
    key = MagicMock()
    key_context = MagicMock()
    key_context.__enter__.return_value = key

    return SimpleNamespace(
        HKEY_CURRENT_USER=object(),
        KEY_READ=1,
        KEY_SET_VALUE=2,
        REG_SZ=1,
        OpenKey=MagicMock(return_value=key_context),
        CreateKeyEx=MagicMock(return_value=key_context),
        QueryValueEx=MagicMock(),
        SetValueEx=MagicMock(),
        DeleteValue=MagicMock(),
        key=key,
    )


def test_get_returns_user_environment_value() -> None:
    """登録済みの利用者環境変数を取得する。"""
    registry = create_registry()
    registry.QueryValueEx.return_value = (
        "test-api-key",
        registry.REG_SZ,
    )
    store = WindowsUserEnvironmentStore(
        registry=registry,
        environment_change_notifier=MagicMock(),
    )

    value = store.get(GOOGLE_BOOKS_API_KEY)

    assert value == "test-api-key"
    registry.OpenKey.assert_called_once_with(
        registry.HKEY_CURRENT_USER,
        USER_ENVIRONMENT_REGISTRY_KEY,
        0,
        registry.KEY_READ,
    )
    registry.QueryValueEx.assert_called_once_with(
        registry.key,
        GOOGLE_BOOKS_API_KEY,
    )


def test_get_returns_none_when_value_does_not_exist() -> None:
    """未登録の利用者環境変数にはNoneを返す。"""
    registry = create_registry()
    registry.OpenKey.side_effect = FileNotFoundError
    store = WindowsUserEnvironmentStore(
        registry=registry,
        environment_change_notifier=MagicMock(),
    )

    assert store.get(GOOGLE_BOOKS_API_KEY) is None


def test_get_rejects_non_string_value() -> None:
    """文字列以外の利用者環境変数を拒否する。"""
    registry = create_registry()
    registry.QueryValueEx.return_value = (
        123,
        registry.REG_SZ,
    )
    store = WindowsUserEnvironmentStore(
        registry=registry,
        environment_change_notifier=MagicMock(),
    )

    with pytest.raises(
        UserEnvironmentStoreError,
        match="文字列ではありません",
    ):
        store.get(GOOGLE_BOOKS_API_KEY)


def test_get_wraps_registry_error() -> None:
    """取得時のレジストリエラーを専用例外へ変換する。"""
    registry = create_registry()
    registry.OpenKey.side_effect = PermissionError
    store = WindowsUserEnvironmentStore(
        registry=registry,
        environment_change_notifier=MagicMock(),
    )

    with pytest.raises(
        UserEnvironmentStoreError,
        match="取得できません",
    ):
        store.get(GOOGLE_BOOKS_API_KEY)


def test_set_saves_value_and_notifies_windows() -> None:
    """利用者環境変数を保存して変更を通知する。"""
    registry = create_registry()
    notifier = MagicMock()
    store = WindowsUserEnvironmentStore(
        registry=registry,
        environment_change_notifier=notifier,
    )

    store.set(
        GOOGLE_BOOKS_API_KEY,
        "test-api-key",
    )

    registry.CreateKeyEx.assert_called_once_with(
        registry.HKEY_CURRENT_USER,
        USER_ENVIRONMENT_REGISTRY_KEY,
        0,
        registry.KEY_SET_VALUE,
    )
    registry.SetValueEx.assert_called_once_with(
        registry.key,
        GOOGLE_BOOKS_API_KEY,
        0,
        registry.REG_SZ,
        "test-api-key",
    )
    notifier.assert_called_once_with()


def test_set_wraps_registry_error_without_exposing_value() -> None:
    """保存失敗時にAPIキーを例外へ含めない。"""
    registry = create_registry()
    registry.SetValueEx.side_effect = PermissionError
    notifier = MagicMock()
    store = WindowsUserEnvironmentStore(
        registry=registry,
        environment_change_notifier=notifier,
    )
    secret_value = "secret-api-key"

    with pytest.raises(
        UserEnvironmentStoreError,
        match="保存できません",
    ) as error_info:
        store.set(
            GOOGLE_BOOKS_API_KEY,
            secret_value,
        )

    assert secret_value not in str(error_info.value)
    notifier.assert_not_called()


def test_delete_removes_value_and_notifies_windows() -> None:
    """利用者環境変数を削除して変更を通知する。"""
    registry = create_registry()
    notifier = MagicMock()
    store = WindowsUserEnvironmentStore(
        registry=registry,
        environment_change_notifier=notifier,
    )

    store.delete(GOOGLE_BOOKS_API_KEY)

    registry.OpenKey.assert_called_once_with(
        registry.HKEY_CURRENT_USER,
        USER_ENVIRONMENT_REGISTRY_KEY,
        0,
        registry.KEY_SET_VALUE,
    )
    registry.DeleteValue.assert_called_once_with(
        registry.key,
        GOOGLE_BOOKS_API_KEY,
    )
    notifier.assert_called_once_with()


def test_delete_ignores_missing_value() -> None:
    """未登録の利用者環境変数を安全に削除できる。"""
    registry = create_registry()
    registry.DeleteValue.side_effect = FileNotFoundError
    notifier = MagicMock()
    store = WindowsUserEnvironmentStore(
        registry=registry,
        environment_change_notifier=notifier,
    )

    store.delete(GOOGLE_BOOKS_API_KEY)

    notifier.assert_not_called()


def test_delete_wraps_registry_error() -> None:
    """削除時のレジストリエラーを専用例外へ変換する。"""
    registry = create_registry()
    registry.DeleteValue.side_effect = PermissionError
    notifier = MagicMock()
    store = WindowsUserEnvironmentStore(
        registry=registry,
        environment_change_notifier=notifier,
    )

    with pytest.raises(
        UserEnvironmentStoreError,
        match="削除できません",
    ):
        store.delete(GOOGLE_BOOKS_API_KEY)

    notifier.assert_not_called()
