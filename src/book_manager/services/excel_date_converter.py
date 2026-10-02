"""Excel移行用の日付・年月の変換。外部通信とDB操作は行わない。"""
from calendar import monthrange
from datetime import date, datetime
import re
import unicodedata

from book_manager.validators.reading_history_validator import validate_reading_date


_ERAS = {
    "昭和": (1926, date(1926, 12, 25), date(1989, 1, 7)),
    "平成": (1989, date(1989, 1, 8), date(2019, 4, 30)),
    "令和": (2019, date(2019, 5, 1), date.max),
}


def normalize_excel_reading_date(
    value: object,
    *,
    field_name: str = "読書日付",
) -> str | None:
    """セル値をYYYY-MMまたはYYYY-MM-DDへ変換し、未設定はNoneとする。

    date・datetimeは完全日付とする。文字列の年月には日を補わない。
    数値は日付シリアルと推測せず拒否する。数式文字列は評価しない。
    和暦は元号の期間と重なる年月、または期間内の完全日付だけ許可する。
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str):
        raise ValueError(
            f"{field_name}の数値などを日付として推測できません。"
            "Excelの日付セル、または年月・日付の文字列で指定してください。"
        )
    text = unicodedata.normalize("NFKC", value).strip()
    if not text:
        return None
    if text.startswith("="):
        raise ValueError(
            f"{field_name}の数式は評価しません。"
            "Excelで再計算して保存し、保存済みの計算値を読み込んでください。"
        )
    text = re.sub(r"\s+", "", text)
    era = re.fullmatch(
        r"(昭和|平成|令和)(元|[0-9]+)年([0-9]{1,2})月(?:([0-9]{1,2})日)?",
        text,
    )
    if era:
        era_name, era_year_text, month_text, day_text = era.groups()
        era_year = 1 if era_year_text == "元" else int(era_year_text)
        if era_year < 1:
            raise ValueError(f"{field_name}の和暦年は1以上で指定してください。")
        base_year, first, last = _ERAS[era_name]
        result = _format_and_validate(
            base_year + era_year - 1, int(month_text),
            int(day_text) if day_text else None, field_name,
        )
        lower = date.fromisoformat(result if day_text else result + "-01")
        upper = lower if day_text else date(
            lower.year, lower.month, monthrange(lower.year, lower.month)[1],
        )
        if upper < first or lower > last:
            raise ValueError(f"{field_name}が{era_name}の期間外です。")
        return result
    match = re.fullmatch(
        r"([0-9]{4})[-/.]([0-9]{1,2})(?:[-/.]([0-9]{1,2}))?",
        text,
    ) or re.fullmatch(
        r"([0-9]{4})年([0-9]{1,2})月(?:([0-9]{1,2})日)?",
        text,
    )
    if not match:
        raise ValueError(
            f"{field_name}は西暦の年月・日付、または「平成21年10月」"
            "などの和暦で指定してください。年だけの値は取り込めません。"
        )
    year, month, day = match.groups()
    return _format_and_validate(
        int(year), int(month), int(day) if day else None, field_name,
    )


def _format_and_validate(year: int, month: int, day: int | None, field_name: str) -> str:
    result = f"{year:04d}-{month:02d}"
    if day is not None:
        result += f"-{day:02d}"
    validate_reading_date(result, field_name=field_name)
    return result
