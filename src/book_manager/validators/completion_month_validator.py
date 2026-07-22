"""Completion month validation functions."""


def validate_completion_month(
    completion_month: str,
) -> None:
    """読了年月を検証する。

    Args:
        completion_month: YYYY-MM形式の読了年月。

    Raises:
        ValueError: 形式、年、または月が正しくない場合。
    """
    if (
        len(completion_month) != 7
        or completion_month[4] != "-"
    ):
        raise ValueError(
            "読了年月はYYYY-MM形式で入力してください。"
        )

    year_text = completion_month[:4]
    month_text = completion_month[5:]

    year_is_ascii_digits = all(
        "0" <= character <= "9"
        for character in year_text
    )
    month_is_ascii_digits = all(
        "0" <= character <= "9"
        for character in month_text
    )

    if not (
        year_is_ascii_digits
        and month_is_ascii_digits
    ):
        raise ValueError(
            "読了年月はYYYY-MM形式で入力してください。"
        )

    year = int(year_text)
    month = int(month_text)

    if year == 0:
        raise ValueError(
            "読了年月の年は0001から9999で入力してください。"
        )

    if not 1 <= month <= 12:
        raise ValueError(
            "読了年月の月は01から12で入力してください。"
        )