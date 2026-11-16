"""雑誌コードの入力正規化・表示・検証。"""
import re


def normalize_magazine_code(value: str | None) -> str | None:
    """5桁・7桁、または5桁-2桁を受け付け、保存時は数字だけにする。"""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if re.fullmatch(r"[0-9]{5}-[0-9]{2}", value):
        value = value.replace("-", "")
    return value


def validate_magazine_code(magazine_code: str) -> None:
    """半角数字5桁・7桁、または5桁-2桁を検証する。"""
    value = normalize_magazine_code(magazine_code)
    if value is None or len(value) not in (5, 7):
        raise ValueError("雑誌コードは5桁または7桁で入力してください。")
    if not re.fullmatch(r"[0-9]+", value):
        raise ValueError("雑誌コードは半角数字で入力してください。")


def format_magazine_code(value: str | None) -> str:
    """7桁は読みやすい5桁-2桁で表示する。既存のその他の値は保持する。"""
    normalized = normalize_magazine_code(value)
    if normalized and re.fullmatch(r"[0-9]{7}", normalized):
        return normalized[:5] + "-" + normalized[5:]
    return value or ""
