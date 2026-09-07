"""Reading history model."""

from dataclasses import dataclass


@dataclass(slots=True)
class ReadingHistory:
    """一回分の読書履歴を表すデータモデル。"""

    book_item_id: int
    id: int | None = None
    started_on: str | None = None
    completed_on: str | None = None
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
