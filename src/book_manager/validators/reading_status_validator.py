"""読書ステータスの検証処理。"""

ALLOWED_READING_STATUSES = {
    "unread",
    "reading",
    "completed",
}


def validate_reading_status(
    reading_status: str | None,
) -> None:
    """読書ステータスを検証する。

    Args:
        reading_status:
            検証する読書ステータス。
            Noneの場合は未設定として許可する。

    Raises:
        ValueError:
            許可されていない読書ステータスの場合。
    """
    if reading_status is None:
        return

    if reading_status not in ALLOWED_READING_STATUSES:
        raise ValueError(
            "読書ステータスが正しくありません。"
        )