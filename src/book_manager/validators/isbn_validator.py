"""ISBN validation functions."""


def validate_isbn(isbn: str) -> None:
    """ISBN-10またはISBN-13を検証する。

    Args:
        isbn: 正規化済みのISBN。

    Raises:
        ValueError: ISBNの桁数、形式、またはチェックデジットが
            正しくない場合。
    """
    if len(isbn) == 10:
        _validate_isbn10(isbn)
        return

    if len(isbn) == 13:
        _validate_isbn13(isbn)
        return

    raise ValueError(
        "ISBNは10桁または13桁で入力してください。"
    )


def _validate_isbn10(isbn: str) -> None:
    """ISBN-10を検証する。"""
    first_nine_are_digits = all(
        "0" <= character <= "9"
        for character in isbn[:9]
    )

    last_character_is_valid = (
        "0" <= isbn[-1] <= "9"
        or isbn[-1] == "X"
    )

    if not (
        first_nine_are_digits
        and last_character_is_valid
    ):
        raise ValueError(
            "ISBNの形式が正しくありません。"
        )

    values = [
        int(character)
        for character in isbn[:9]
    ]

    check_digit = (
        10
        if isbn[-1] == "X"
        else int(isbn[-1])
    )
    values.append(check_digit)

    weighted_sum = sum(
        value * weight
        for value, weight in zip(
            values,
            range(10, 0, -1),
            strict=True,
        )
    )

    if weighted_sum % 11 != 0:
        raise ValueError(
            "ISBNのチェックデジットが正しくありません。"
        )


def _validate_isbn13(isbn: str) -> None:
    """ISBN-13を検証する。"""
    if not all(
        "0" <= character <= "9"
        for character in isbn
    ):
        raise ValueError(
            "ISBNの形式が正しくありません。"
        )

    digits = [
        int(character)
        for character in isbn
    ]

    weighted_sum = sum(
        digit * (
            1
            if index % 2 == 0
            else 3
        )
        for index, digit in enumerate(
            digits[:12]
        )
    )

    expected_check_digit = (
        10 - weighted_sum % 10
    ) % 10

    if digits[-1] != expected_check_digit:
        raise ValueError(
            "ISBNのチェックデジットが正しくありません。"
        )