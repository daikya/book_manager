"""読書履歴の日付Validatorのテスト。"""

import pytest

from book_manager.validators.reading_history_validator import (
    validate_reading_date,
    validate_reading_history_dates,
)


@pytest.mark.parametrize(
    "value",
    [
        "0001-01-01",
        "2025-12-31",
        "2026-09-07",
        "2028-02-29",
        "9999-12-31",
    ],
)
def test_validate_reading_date_accepts_valid_value(
    value: str,
) -> None:
    """有効な日付を許可する。"""
    validate_reading_date(
        value,
        field_name="読書開始日",
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "2026-9-7",
        "2026/09/07",
        "20260907",
        "２０２６-０９-０７",
        " 2026-09-07 ",
        "2026-09-07 00:00:00",
    ],
)
def test_validate_reading_date_rejects_invalid_format(
    value: str,
) -> None:
    """YYYY-MM・YYYY-MM-DD以外の形式を拒否する。"""
    with pytest.raises(
        ValueError,
        match="読書開始日はYYYY-MMまたはYYYY-MM-DD形式で入力してください。",
    ):
        validate_reading_date(
            value,
            field_name="読書開始日",
        )


@pytest.mark.parametrize(
    "value",
    [
        "0000-01-01",
        "2025-02-29",
        "2026-02-30",
        "2026-04-31",
        "2026-13-01",
    ],
)
def test_validate_reading_date_rejects_nonexistent_date(
    value: str,
) -> None:
    """実在しない日付を拒否する。"""
    with pytest.raises(
        ValueError,
        match="読書開始日に実在する日付を入力してください。",
    ):
        validate_reading_date(
            value,
            field_name="読書開始日",
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        20260907,
        True,
        (),
    ],
)
def test_validate_reading_date_rejects_non_string(
    value: object,
) -> None:
    """文字列以外の日付を拒否する。"""
    with pytest.raises(
        ValueError,
        match="読了日はYYYY-MMまたはYYYY-MM-DD形式で入力してください。",
    ):
        validate_reading_date(
            value,  # type: ignore[arg-type]
            field_name="読了日",
        )


def test_validate_reading_history_dates_accepts_none_values() -> None:
    """両方の日付が未設定でも日付検証では許可する。"""
    validate_reading_history_dates(None, None)


def test_validate_reading_history_dates_accepts_started_on_only() -> None:
    """読書開始日だけが設定された状態を許可する。"""
    validate_reading_history_dates("2026-09-01", None)


def test_validate_reading_history_dates_accepts_completed_on_only() -> None:
    """読了日だけが設定された状態を許可する。"""
    validate_reading_history_dates(None, "2026-09-07")


def test_validate_reading_history_dates_accepts_same_date() -> None:
    """開始日と読了日が同じ履歴を許可する。"""
    validate_reading_history_dates(
        "2026-09-07",
        "2026-09-07",
    )


def test_validate_reading_history_dates_accepts_ascending_dates() -> None:
    """開始日が読了日より前の履歴を許可する。"""
    validate_reading_history_dates(
        "2026-09-01",
        "2026-09-07",
    )


def test_validate_reading_history_dates_rejects_descending_dates() -> None:
    """開始日が読了日より後の履歴を拒否する。"""
    with pytest.raises(
        ValueError,
        match=(
            "読書開始日は読了日以前の日付を入力してください。"
        ),
    ):
        validate_reading_history_dates(
            "2026-09-08",
            "2026-09-07",
        )


def test_validate_reading_history_dates_uses_completed_on_label() -> None:
    """読了日のエラーでは読了日の項目名を表示する。"""
    with pytest.raises(
        ValueError,
        match="読了日に実在する日付を入力してください。",
    ):
        validate_reading_history_dates(
            "2026-09-01",
            "2026-02-30",
        )


@pytest.mark.parametrize("value", ["0001-01", "2026-05", "2028-02", "9999-12"])
def test_accepts_month_precision(value: str) -> None:
    """月単位の入力を許可する。"""
    validate_reading_date(value, field_name="読了日")


@pytest.mark.parametrize("value", ["2026", "2026-5", "2026/05", "２０２６-０５", " 2026-05", "2026-05 ", "2026-0a"])
def test_rejects_invalid_month_format(value: str) -> None:
    with pytest.raises(ValueError, match="YYYY-MMまたはYYYY-MM-DD"):
        validate_reading_date(value, field_name="読了日")


@pytest.mark.parametrize("value", ["0000-01", "2026-00", "2026-13"])
def test_rejects_nonexistent_month(value: str) -> None:
    with pytest.raises(ValueError, match="実在する日付"):
        validate_reading_date(value, field_name="読了日")


@pytest.mark.parametrize("started, completed", [
    ("2026-05", None), (None, "2026-05"),
    ("2026-05", "2026-05"), ("2026-04", "2026-05"),
    ("2026-05-20", "2026-05"), ("2026-05", "2026-05-10"),
    ("2028-02-29", "2028-02"), ("2026-02-28", "2026-02"),
    ("0001-01", "0001-01-01"), ("9999-12-31", "9999-12"),
])
def test_accepts_overlapping_or_ascending_periods(started, completed) -> None:
    """月の中の日付を推測せず、重なる期間を許可する。"""
    validate_reading_history_dates(started, completed)


@pytest.mark.parametrize("started, completed", [
    ("2026-06", "2026-05-31"), ("2026-06-01", "2026-05"),
    ("2026-06", "2026-05"), ("2027-01", "2026-12"),
    ("2028-03-01", "2028-02"),
])
def test_rejects_reversed_periods(started: str, completed: str) -> None:
    with pytest.raises(ValueError, match="読書開始日は読了日以前"):
        validate_reading_history_dates(started, completed)
