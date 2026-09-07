"""読書履歴の日付検証処理。"""

from datetime import date


def validate_reading_date(
    value: str,
    *,
    field_name: str,
) -> None:
    """読書履歴の日付形式と実在日を検証する。

    Args:
        value: 検証する日付文字列。
        field_name: エラーメッセージへ表示する項目名。

    Raises:
        ValueError: 日付形式または実在日が正しくない場合。
    """
    if not isinstance(value, str):
        raise ValueError(
            f"{field_name}はYYYY-MM-DD形式で入力してください。"
        )

    format_is_valid = (
        len(value) == 10
        and value[4] == "-"
        and value[7] == "-"
        and all(
            "0" <= character <= "9"
            for index, character in enumerate(value)
            if index not in (4, 7)
        )
    )

    if not format_is_valid:
        raise ValueError(
            f"{field_name}はYYYY-MM-DD形式で入力してください。"
        )

    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(
            f"{field_name}に実在する日付を入力してください。"
        ) from error


def validate_reading_history_dates(
    started_on: str | None,
    completed_on: str | None,
) -> None:
    """読書開始日、読了日および日付の前後関係を検証する。

    Args:
        started_on: 読書開始日。
        completed_on: 読了日。

    Raises:
        ValueError: 日付または日付の前後関係が正しくない場合。
    """
    if started_on is not None:
        validate_reading_date(
            started_on,
            field_name="読書開始日",
        )

    if completed_on is not None:
        validate_reading_date(
            completed_on,
            field_name="読了日",
        )

    if (
        started_on is not None
        and completed_on is not None
        and started_on > completed_on
    ):
        raise ValueError(
            "読書開始日は読了日以前の日付を入力してください。"
        )
