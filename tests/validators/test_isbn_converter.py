"""Tests for ISBN conversion."""

import pytest

from book_manager.validators.isbn_converter import (
    convert_isbn10_to_isbn13,
    to_isbn13,
)
from book_manager.validators.isbn_validator import (
    validate_isbn,
)


@pytest.mark.parametrize(
    ("isbn10", "expected"),
    [
        (
            "4101010013",
            "9784101010014",
        ),
        (
            "4101109184",
            "9784101109183",
        ),
        (
            "080442957X",
            "9780804429573",
        ),
    ],
)
def test_convert_isbn10_to_isbn13(
    isbn10: str,
    expected: str,
) -> None:
    """ISBN-10をISBN-13へ変換できることを確認する。"""
    result = convert_isbn10_to_isbn13(
        isbn10,
    )

    assert result == expected


@pytest.mark.parametrize(
    "isbn10",
    [
        "4101010014",
        "0804429579",
    ],
)
def test_convert_isbn10_to_isbn13_rejects_invalid_isbn10(
    isbn10: str,
) -> None:
    """不正なISBN-10を拒否することを確認する。"""
    with pytest.raises(
        ValueError,
        match="ISBNのチェックデジットが正しくありません。",
    ):
        convert_isbn10_to_isbn13(isbn10)


def test_convert_isbn10_to_isbn13_rejects_isbn13() -> None:
    """ISBN-13をISBN-10変換関数へ渡せないことを確認する。"""
    with pytest.raises(
        ValueError,
        match="ISBN-10を指定してください。",
    ):
        convert_isbn10_to_isbn13(
            "9784101010014",
        )


@pytest.mark.parametrize(
    "isbn13",
    [
        "9784101010014",
        "9784163917733",
    ],
)
def test_to_isbn13_returns_isbn13_unchanged(
    isbn13: str,
) -> None:
    """ISBN-13は変更せず返すことを確認する。"""
    result = to_isbn13(isbn13)

    assert result == isbn13


@pytest.mark.parametrize(
    ("isbn10", "expected"),
    [
        (
            "4101010013",
            "9784101010014",
        ),
        (
            "080442957X",
            "9780804429573",
        ),
    ],
)
def test_to_isbn13_converts_isbn10(
    isbn10: str,
    expected: str,
) -> None:
    """ISBN-10をISBN-13へ変換することを確認する。"""
    result = to_isbn13(isbn10)

    assert result == expected


@pytest.mark.parametrize(
    "isbn",
    [
        "",
        "123456789",
        "9784101010015",
        "080442957x",
    ],
)
def test_to_isbn13_rejects_invalid_isbn(
    isbn: str,
) -> None:
    """不正なISBNを拒否することを確認する。"""
    with pytest.raises(ValueError):
        to_isbn13(isbn)


@pytest.mark.parametrize(
    "isbn10",
    [
        "4101010013",
        "4101109184",
        "080442957X",
    ],
)
def test_converted_isbn13_is_valid(
    isbn10: str,
) -> None:
    """変換後のISBN-13が検証を通ることを確認する。"""
    converted = convert_isbn10_to_isbn13(
        isbn10,
    )

    result = validate_isbn(converted)

    assert result is None