"""利用者が確認して選択する書籍検索候補。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BookSearchCandidate:
    """ISBNなし・複数ISBNの候補も保持し、自動選択しない。

    is_ebook=Falseだけでは紙の版と断定できない。
    文庫・単行本などの出版形態はタイトルから推測しない。
    """

    source: str
    title: str
    source_id: str | None = None
    subtitle: str | None = None
    author: str | None = None
    publisher: str | None = None
    publication_date: str | None = None
    cover_image_url: str | None = None
    isbn_candidates: tuple[str, ...] = ()
    is_ebook: bool | None = None
