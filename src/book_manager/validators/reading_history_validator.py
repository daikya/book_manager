"""読書履歴の年月・年月日の検証処理。"""

from calendar import monthrange
from datetime import date


def _reading_date_range(value: str, *, field_name: str) -> tuple[date, date]:
    """検証用の期間を返す。入力値の補完や変更は行わない。"""
    format_error = f"{field_name}はYYYY-MMまたはYYYY-MM-DD形式で入力してください。"
    if not isinstance(value, str):
        raise ValueError(format_error)
    if not (
        len(value) in (7, 10)
        and value[4] == "-"
        and (len(value) == 7 or value[7] == "-")
        and all(
            "0" <= character <= "9"
            for index, character in enumerate(value)
            if index not in (4, 7)
        )
    ):
        raise ValueError(format_error)
    try:
        if len(value) == 10:
            exact_date = date.fromisoformat(value)
            return exact_date, exact_date
        year, month = int(value[:4]), int(value[5:7])
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])
        return first_day, last_day
    except ValueError as error:
        raise ValueError(
            f"{field_name}に実在する日付を入力してください。"
        ) from error


def validate_reading_date(value: str, *, field_name: str) -> None:
    """ASCIIのYYYY-MMまたはYYYY-MM-DD形式と実在日を検証する。"""
    _reading_date_range(value, field_name=field_name)


def validate_reading_history_dates(
    started_on: str | None,
    completed_on: str | None,
) -> None:
    """開始と読了の期間が明らかに逆転する場合だけ拒否する。"""
    started_range = (
        _reading_date_range(started_on, field_name="読書開始日")
        if started_on is not None else None
    )
    completed_range = (
        _reading_date_range(completed_on, field_name="読了日")
        if completed_on is not None else None
    )
    if (
        started_range is not None
        and completed_range is not None
        and started_range[0] > completed_range[1]
    ):
        raise ValueError(
            "読書開始日は読了日以前の日付を入力してください。"
        )
