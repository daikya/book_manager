"""Magazine code validation functions."""


def validate_magazine_code(
    magazine_code: str,
) -> None:
    """雑誌コードを検証する。

    Args:
        magazine_code: 正規化済みの雑誌コード。

    Raises:
        ValueError: 桁数または文字種が正しくない場合。
    """
    if len(magazine_code) not in (5, 7):
        raise ValueError(
            "雑誌コードは5桁または7桁で入力してください。"
        )

    if not all(
        "0" <= character <= "9"
        for character in magazine_code
    ):
        raise ValueError(
            "雑誌コードは半角数字で入力してください。"
        )