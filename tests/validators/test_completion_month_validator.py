"""Tests for completion month validation."""

import pytest

from book_manager.validators.completion_month_validator import (
    validate_completion_month,
)


@pytest.mark.parametrize(
    "completion_month",
    [
        "0001-01",
        "1999-12",
        "2026-07",
        "9999-12",
    ],
)
def test_validate_completion_month_accepts_valid_value(
    completion_month: str,
) -> None:
    result = validate_completion_month(
        completion_month
    )

    assert result is None


@pytest.mark.parametrize(
    "completion_month",
    [
        "",
        "202607",
        "2026/07",
        "2026-7",
        "26-07",
        "2026--07",
        "2026-007",
    ],
)
def test_validate_completion_month_rejects_invalid_format(
    completion_month: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="読了年月はYYYY-MM形式で入力してください。",
    ):
        validate_completion_month(
            completion_month
        )


@pytest.mark.parametrize(
    "completion_month",
    [
        "20A6-07",
        "2026-0A",
        "２０２６-０７",
        "2026－07",
        "2026 07",
        "2026-\n7",
        "2026-\t7",
    ],
)
def test_validate_completion_month_rejects_invalid_characters(
    completion_month: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="読了年月はYYYY-MM形式で入力してください。",
    ):
        validate_completion_month(
            completion_month
        )


def test_validate_completion_month_rejects_year_zero(
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "読了年月の年は0001から9999で入力してください。"
        ),
    ):
        validate_completion_month("0000-01")


@pytest.mark.parametrize(
    "completion_month",
    [
        "2026-00",
        "2026-13",
        "2026-99",
    ],
)
def test_validate_completion_month_rejects_invalid_month(
    completion_month: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "読了年月の月は01から12で入力してください。"
        ),
    ):
        validate_completion_month(
            completion_month
        )


def test_validate_completion_month_accepts_minimum_value(
) -> None:
    result = validate_completion_month("0001-01")

    assert result is None


def test_validate_completion_month_accepts_maximum_value(
) -> None:
    result = validate_completion_month("9999-12")

    assert result is None