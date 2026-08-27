"""Book item model."""

from dataclasses import dataclass


@dataclass(slots=True)
class BookItem:
    """書籍情報を表すデータモデル。"""

    title: str
    id: int | None = None
    isbn: str | None = None
    magazine_code: str | None = None
    author: str | None = None
    publisher: str | None = None
    publication_format: str | None = None
    description: str | None = None
    cover_image_url: str | None = None
    cover_image_path: str | None = None
    completion_month: str | None = None
    reading_status: str | None = None
    is_favorite: bool = False
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None