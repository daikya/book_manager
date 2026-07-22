"""Tests for ISBN validation."""

import pytest

from book_manager.validators.isbn_validator import (
    validate_isbn,
)


@pytest.mark.parametrize(
    "isbn",
    [
        "4101010013",
        "080442957X",
    ],
)
def test_validate_isbn_accepts_valid_isbn10(
    isbn: str,
) -> None:
    result = validate_isbn(isbn)

    assert result is None


@pytest.mark.parametrize(
    "isbn",
    [
        "9784101010014",
        "9784163917733",
    ],
)
def test_validate_isbn_accepts_valid_isbn13(
    isbn: str,
) -> None:
    result = validate_isbn(isbn)

    assert result is None


@pytest.mark.parametrize(
    "isbn",
    [
        "",
        "123456789",
        "12345678901",
        "123456789012",
        "12345678901234",
    ],
)
def test_validate_isbn_rejects_invalid_length(
    isbn: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="ISBNは10桁または13桁で入力してください。",
    ):
        validate_isbn(isbn)


@pytest.mark.parametrize(
    "isbn",
    [
        "A101010013",
        "41010100A3",
        "080442957x",
        "080442957A",
        "４１０１０１００１３",
    ],
)
def test_validate_isbn10_rejects_invalid_characters(
    isbn: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="ISBNの形式が正しくありません。",
    ):
        validate_isbn(isbn)


@pytest.mark.parametrize(
    "isbn",
    [
        "978410101001A",
        "97841010100-4",
        "97841010100 4",
        "９７８４１０１０１００１４",
    ],
)
def test_validate_isbn13_rejects_invalid_characters(
    isbn: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="ISBNの形式が正しくありません。",
    ):
        validate_isbn(isbn)


@pytest.mark.parametrize(
    "isbn",
    [
        "4101010014",
        "0804429579",
        "9784101010015",
        "9784163917734",
    ],
)
def test_validate_isbn_rejects_invalid_check_digit(
    isbn: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="ISBNのチェックデジットが正しくありません。",
    ):
        validate_isbn(isbn)


def test_validate_isbn10_accepts_uppercase_x(
) -> None:
    result = validate_isbn("080442957X")

    assert result is None


def test_validate_isbn10_rejects_lowercase_x(
) -> None:
    with pytest.raises(
        ValueError,
        match="ISBNの形式が正しくありません。",
    ):
        validate_isbn("080442957x")