"""Excel移行用の日付変換の検証。"""
from datetime import date, datetime

import pytest

from book_manager.services.excel_date_converter import normalize_excel_reading_date
from book_manager.validators.reading_history_validator import validate_reading_history_dates


@pytest.mark.parametrize("value,expected", [
    (None, None), ("", None), ("　 ", None),
    (date(2026, 5, 20), "2026-05-20"),
    (datetime(2026, 5, 20, 12, 30), "2026-05-20"),
    ("2026-05", "2026-05"), ("2026/5", "2026-05"),
    ("2026.5", "2026-05"), ("2026年5月", "2026-05"),
    ("２０２６年５月", "2026-05"), (" 2026 / 5 ", "2026-05"),
    ("2026-5-20", "2026-05-20"), ("2026/5/20", "2026-05-20"),
    ("2026年5月20日", "2026-05-20"), ("2024/2/29", "2024-02-29"),
    ("平成21年10月", "2009-10"), ("平成元年1月", "1989-01"),
    ("昭和64年1月", "1989-01"), ("平成31年4月30日", "2019-04-30"),
    ("令和元年5月1日", "2019-05-01"), ("令和１年５月", "2019-05"),
    ("昭和64年1月7日", "1989-01-07"),
    ("平成元年1月8日", "1989-01-08"),
])
def test_normalize_excel_reading_date(value, expected):
    assert normalize_excel_reading_date(value) == expected


@pytest.mark.parametrize("value", [
    45000, 45000.0, True, 202605, "2026", "202605", "200305",
    "2026-00", "2026-13", "0000-01", "2026-02-29", "2024-02-30",
    "2026-01-00", "2026年5月20", "不明", "平成0年1月",
    "平成元年1月7日", "昭和64年1月8日", "昭和64年2月",
    "平成31年5月", "令和元年4月", "令和元年4月30日",
    "=DATE(2026,5,20)", "99999-01", "令和10000年1月",
])
def test_normalize_rejects_ambiguous_or_invalid_value(value):
    with pytest.raises(ValueError):
        normalize_excel_reading_date(value, field_name="読了日")


def test_month_precision_survives_history_validation():
    started = normalize_excel_reading_date("2026年5月20日")
    completed = normalize_excel_reading_date("2026年5月")
    validate_reading_history_dates(started, completed)
    assert started == "2026-05-20"
    assert completed == "2026-05"


def test_converted_reverse_dates_are_rejected():
    started = normalize_excel_reading_date("令和8年6月")
    completed = normalize_excel_reading_date("令和8年5月")
    with pytest.raises(ValueError):
        validate_reading_history_dates(started, completed)
