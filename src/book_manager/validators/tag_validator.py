"""タグ名の検証処理。"""

MAX_TAG_NAME_LENGTH = 30
TAG_SEPARATOR = "|"


def validate_tag_name(tag_name: str) -> None:
    """タグ名を検証する。

    Args:
        tag_name:
            検証する正規化済みタグ名。

    Raises:
        ValueError:
            タグ名の型、文字数または文字が正しくない場合。
    """
    if not isinstance(tag_name, str):
        raise ValueError(
            "タグ名は文字列で指定してください。"
        )

    if tag_name.strip() == "":
        raise ValueError(
            "タグ名を入力してください。"
        )

    if len(tag_name) > MAX_TAG_NAME_LENGTH:
        raise ValueError(
            "タグ名は30文字以内で入力してください。"
        )

    if (
        TAG_SEPARATOR in tag_name
        or "\r" in tag_name
        or "\n" in tag_name
    ):
        raise ValueError(
            "タグ名に「|」または改行は使用できません。"
        )
