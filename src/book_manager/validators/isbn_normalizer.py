"""ISBN normalization functions."""


def normalize_isbn(isbn: str) -> str:
    """ISBNから空白とハイフン類を除去する。

    ISBN-10末尾の小文字xは、大文字Xへ変換する。

    Args:
        isbn: 正規化前のISBN。

    Returns:
        正規化済みのISBN。

    Raises:
        TypeError: isbnが文字列でない場合。
    """
    if not isinstance(isbn, str):
        raise TypeError(
            "ISBNは文字列で指定してください。"
        )

    normalized = isbn.strip()

    removable_characters = (
        " ",
        "　",
        "-",
        "‐",
        "-",
        "‒",
        "–",
        "—",
        "−",
    )

    for character in removable_characters:
        normalized = normalized.replace(
            character,
            "",
        )

    if normalized.endswith("x"):
        normalized = (
            normalized[:-1] + "X"
        )

    return normalized