"""Tests for magazine code validation."""

import pytest

from book_manager.validators.magazine_code_validator import (
    validate_magazine_code,
)


@pytest.mark.parametrize(
    "magazine_code",
    [
        "12345",
        "00001",
        "1234507",
        "0000001",
    ],
)
def test_validate_magazine_code_accepts_valid_value(
    magazine_code: str,
) -> None:
    result = validate_magazine_code(magazine_code)

    assert result is None


@pytest.mark.parametrize(
    "magazine_code",
    [
        "",
        "1234",
        "123456",
        "12345678",
    ],
)
def test_validate_magazine_code_rejects_invalid_length(
    magazine_code: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "雑誌コードは5桁または7桁で入力してください。"
        ),
    ):
        validate_magazine_code(magazine_code)


@pytest.mark.parametrize(
    "magazine_code",
    [
        "12A45",
        "12-45",
        "12 45",
        "１２３４５",
        "1234!",
        "123A507",
        "123 507",
        "１２３４５０７",
    ],
)
def test_validate_magazine_code_rejects_non_ascii_digits(
    magazine_code: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="雑誌コードは半角数字で入力してください。",
    ):
        validate_magazine_code(magazine_code)


def test_validate_magazine_code_accepts_leading_zero(
) -> None:
    result = validate_magazine_code("00001")

    assert result is None