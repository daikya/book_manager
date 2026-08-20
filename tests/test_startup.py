"""起動補助処理のテスト。"""

from unittest.mock import Mock

from book_manager.startup import try_create_backup


def test_try_create_backup_returns_none_on_success() -> None:
    """バックアップ成功時はNoneを返す。"""
    backup_service = Mock()

    result = try_create_backup(
        backup_service,
    )

    assert result is None

    backup_service.create_backup_if_needed.assert_called_once_with()


def test_try_create_backup_returns_exception_on_failure() -> None:
    """バックアップ失敗時は例外を返す。"""
    backup_service = Mock()

    expected_error = RuntimeError(
        "backup failed"
    )

    backup_service.create_backup_if_needed.side_effect = (
        expected_error
    )

    result = try_create_backup(
        backup_service,
    )

    assert result is expected_error

    backup_service.create_backup_if_needed.assert_called_once_with()