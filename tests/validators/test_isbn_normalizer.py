"""Tests for ISBN normalization."""

import pytest

from book_manager.validators.isbn_normalizer import (
    normalize_isbn,
)


@pytest.mark.parametrize(
    ("isbn", "expected"),
    [
        (
            "978-4-16-391773-3",
            "9784163917733",
        ),
        (
            "4-10-101001-3",
            "4101010013",
        ),
        (
            " 9784163917733 ",
            "9784163917733",
        ),
        (
            "978 416 391773 3",
            "9784163917733",
        ),
        (
            "978　416　391773　3",
            "9784163917733",
        ),
        (
            "978‐4‐16‐391773‐3",
            "9784163917733",
        ),
        (
            "978-4-16-391773-3",
            "9784163917733",
        ),
        (
            "978–4–16–391773–3",
            "9784163917733",
        ),
        (
            "978—4—16—391773—3",
            "9784163917733",
        ),
        (
            "978−4−16−391773−3",
            "9784163917733",
        ),
        (
            "080442957x",
            "080442957X",
        ),
    ],
)
def test_normalize_isbn_returns_normalized_value(
    isbn: str,
    expected: str,
) -> None:
    result = normalize_isbn(isbn)

    assert result == expected


def test_normalize_isbn_returns_empty_string_for_whitespace_only() -> None:
    """空白だけの場合は空文字列になることを確認する。"""
    result = normalize_isbn(" 　")

    assert result == ""


def test_normalize_isbn_does_not_change_uppercase_x() -> None:
    """末尾の大文字Xを維持することを確認する。"""
    result = normalize_isbn("080442957X")

    assert result == "080442957X"


def test_normalize_isbn_does_not_convert_x_except_at_end() -> None:
    """末尾以外の小文字xは変換しないことを確認する。"""
    result = normalize_isbn("08044x9570")

    assert result == "08044x9570"


def test_normalize_isbn_rejects_non_string() -> None:
    """文字列以外を拒否することを確認する。"""
    with pytest.raises(
        TypeError,
        match="ISBNは文字列で指定してください。",
    ):
        normalize_isbn(9784163917733)  # type: ignore[arg-type]