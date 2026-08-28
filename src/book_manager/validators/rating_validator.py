"""評価値の検証処理。"""


def validate_rating(
    rating: int | None,
) -> None:
    """評価値を検証する。

    Args:
        rating:
            検証する評価値。
            Noneの場合は未評価として許可する。

    Raises:
        ValueError:
            評価値が1から5の整数ではない場合。
    """
    if rating is None:
        return

    if (
        isinstance(rating, bool)
        or not isinstance(rating, int)
        or rating < 1
        or rating > 5
    ):
        raise ValueError(
            "評価は1から5の整数で指定してください。"
        )