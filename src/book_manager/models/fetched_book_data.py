"""外部サービスから取得した書誌情報のモデル。"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class FetchedBookData:
    """外部サービスから取得した未確認の書誌情報を表す。"""

    isbn: str
    title: str | None = None
    author: str | None = None
    publisher: str | None = None
    publication_date: str | None = None
    publication_format: str | None = None
    description: str | None = None
    cover_image_url: str | None = None
    sources: tuple[str, ...] = ()
    raw_data: dict[str, Any] = field(default_factory=dict)