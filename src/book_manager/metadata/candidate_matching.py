"""検索語と候補の比較。保存用データには適用しない。"""

import re
import unicodedata
from difflib import SequenceMatcher

from book_manager.models.book_search_candidate import BookSearchCandidate


_FIELDS = (("title", "書籍名"), ("author", "著者"), ("publisher", "出版社"))
_IGNORED = str.maketrans("", "", "・･·‐‑‒–—―−-")


def prepare_search_terms(
    *, title: str = "", author: str = "", publisher: str = "",
) -> dict[str, str]:
    """API用キーワードを整える。フィールド演算子は組み立てない。"""
    values = []
    for key, value in (("title", title), ("author", author), ("publisher", publisher)):
        if not isinstance(value, str):
            raise TypeError("書籍名・著者名・出版社は文字列で指定してください。")
        value = unicodedata.normalize("NFKC", value)
        for character in ('"', "\\", ":", "-", "|", "{", "}"):
            value = value.replace(character, " ")
        value = " ".join(value.split())
        # Latin names retain word boundaries for keyword retrieval.
        if key == "author" and re.fullmatch(r"[\u3040-\u30ff\u3400-\u9fff々〆ヶ\s]+", value):
            value = "".join(value.split())
        values.append(value)
    if not any(values):
        raise ValueError("書籍名・著者名・出版社のいずれかを入力してください。")
    return dict(zip(("title", "author", "publisher"), values))


def normalize_comparison(value: str | None, *, publisher: bool = False) -> str:
    text = unicodedata.normalize("NFKC", value or "").casefold()
    text = "".join(text.split()).translate(_IGNORED)
    if publisher:
        text = re.sub(r"^(?:株式会社|有限会社|\(株\)|\(有\))", "", text)
        text = re.sub(r"(?:株式会社|有限会社|\(株\)|\(有\))$", "", text)
    return text


def _edition_tokens(text: str) -> list[str]:
    return re.findall(r"\d+|[上下中]巻|[上下中]$", text)


def _level(query: str, value: str | None, *, field: str) -> tuple[int, str]:
    left = normalize_comparison(query, publisher=field == "publisher")
    right = normalize_comparison(value, publisher=field == "publisher")
    if not right:
        return 0, "情報なし"
    if not left:
        return 0, "要確認"
    if left == right:
        return 3, "一致"
    if field == "title" and _edition_tokens(left) and _edition_tokens(left) != _edition_tokens(right):
        return 0, "巻数等を確認"
    if left in right or right in left:
        return 2, "部分一致"
    if field == "title" and len(left) >= 4 and len(right) >= 4:
        if SequenceMatcher(None, left, right).ratio() >= 0.75:
            return 1, "近似"
    return 0, "要確認"


def candidate_match(
    candidate: BookSearchCandidate, *, title: str = "", author: str = "",
    publisher: str = "",
) -> tuple[tuple[int, int, int], str]:
    """指定項目ごとの目安と順位キーを返す。同一作品とは断定しない。"""
    queries = dict(title=title, author=author, publisher=publisher)
    levels, labels = [], []
    for field, label in _FIELDS:
        if not queries[field].strip():
            continue
        value = getattr(candidate, field)
        if field == "title" and candidate.subtitle:
            # Main title exact match takes precedence over title + subtitle.
            options = (value, value + " " + candidate.subtitle)
            level, status = max((_level(queries[field], v, field=field) for v in options), key=lambda x: x[0])
        else:
            level, status = _level(queries[field], value, field=field)
        levels.append(level)
        labels.append(f"{label}: {status}")
    return (sum(x == 3 for x in levels), sum(x >= 2 for x in levels), sum(levels)), " / ".join(labels)


def rank_candidates(
    candidates: list[BookSearchCandidate], **conditions: str,
) -> list[BookSearchCandidate]:
    """候補の原文・ID・ISBNを保持したまま安定ソートする。"""
    return sorted(candidates, key=lambda c: candidate_match(c, **conditions)[0], reverse=True)
