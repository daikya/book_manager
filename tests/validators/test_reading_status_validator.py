"""読書ステータスValidatorのテスト。"""

import pytest

from book_manager.validators.reading_status_validator import (
    validate_reading_status,
)


@pytest.mark.parametrize(
    "reading_status",
    [
        None,
        "unread",
        "reading",
        "completed",
    ],
)
def test_validate_reading_status_accepts_valid_value(
    reading_status: str | None,
) -> None:
    """有効な読書ステータスを許可する。"""
    validate_reading_status(
        reading_status,
    )


@pytest.mark.parametrize(
    "reading_status",
    [
        "",
        "finished",
        "done",
        "読了",
        "unknown",
    ],
)
def test_validate_reading_status_rejects_invalid_value(
    reading_status: str,
) -> None:
    """未定義の読書ステータスを拒否する。"""
    with pytest.raises(
        ValueError,
        match="読書ステータスが正しくありません。",
    ):
        validate_reading_status(
            reading_status,
        )