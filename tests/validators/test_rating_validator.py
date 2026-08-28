"""評価値Validatorのテスト。"""

import pytest

from book_manager.validators.rating_validator import (
    validate_rating,
)


@pytest.mark.parametrize(
    "rating",
    [
        None,
        1,
        2,
        3,
        4,
        5,
    ],
)
def test_validate_rating_accepts_valid_value(
    rating: int | None,
) -> None:
    """有効な評価値を許可する。"""
    validate_rating(
        rating,
    )


@pytest.mark.parametrize(
    "rating",
    [
        -1,
        0,
        6,
        10,
        True,
        False,
        1.0,
        "1",
        "",
    ],
)
def test_validate_rating_rejects_invalid_value(
    rating: object,
) -> None:
    """無効な評価値を拒否する。"""
    with pytest.raises(
        ValueError,
        match="評価は1から5の整数で指定してください。",
    ):
        validate_rating(
            rating,  # type: ignore[arg-type]
        )