"""ISBN conversion functions."""

from book_manager.validators.isbn_validator import (
    validate_isbn,
)


def convert_isbn10_to_isbn13(
    isbn10: str,
) -> str:
    """ISBN-10をISBN-13へ変換する。

    Args:
        isbn10: 正規化済みのISBN-10。

    Returns:
        変換後のISBN-13。

    Raises:
        ValueError: ISBN-10が正しくない場合。
    """
    validate_isbn(isbn10)

    if len(isbn10) != 10:
        raise ValueError(
            "ISBN-10を指定してください。"
        )

    isbn13_body = "978" + isbn10[:9]

    weighted_sum = sum(
        int(character) * (
            1
            if index % 2 == 0
            else 3
        )
        for index, character in enumerate(
            isbn13_body
        )
    )

    check_digit = (
        10 - weighted_sum % 10
    ) % 10

    return isbn13_body + str(check_digit)


def to_isbn13(isbn: str) -> str:
    """ISBNを問い合わせ用ISBN-13へ変換する。

    ISBN-13の場合は、そのまま返す。

    Args:
        isbn: 正規化済みのISBN-10またはISBN-13。

    Returns:
        問い合わせ用ISBN-13。

    Raises:
        ValueError: ISBNが正しくない場合。
    """
    validate_isbn(isbn)

    if len(isbn) == 13:
        return isbn

    return convert_isbn10_to_isbn13(isbn)