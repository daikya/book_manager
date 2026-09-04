"""Tag model."""

from dataclasses import dataclass


@dataclass(slots=True)
class Tag:
    """書籍の分類に使用するタグを表すデータモデル。"""

    name: str
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
