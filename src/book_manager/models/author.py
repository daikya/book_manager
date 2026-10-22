"""名前の一致とは独立したIDを持つ著者と、その検索候補。"""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class Author:
    """同名の別人も許可する。既存書籍の著者名文字列とは別に管理する。"""

    name: str
    id: int | None = None
    aliases: tuple[str, ...] = ()
    disambiguation_note: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def __post_init__(self) -> None:
        if self.id is not None and (type(self.id) is not int or self.id < 1):
            raise ValueError('著者IDは1以上の整数で指定してください。')
        if not isinstance(self.aliases, tuple):
            raise TypeError('著者の別名はタプルで指定してください。')
        for text in (self.name, *self.aliases):
            if not isinstance(text, str):
                raise TypeError('著者名・別名は文字列で指定してください。')
            if not text.strip() or len(text) > 200:
                raise ValueError('著者名・別名は1文字以上200文字以内で入力してください。')
            if any(ord(character) < 32 or 127 <= ord(character) <= 159 for character in text):
                raise ValueError('著者名・別名に制御文字は使用できません。')
        note = self.disambiguation_note
        if note is not None:
            if not isinstance(note, str):
                raise TypeError('識別メモは文字列で指定してください。')
            if len(note) > 2000:
                raise ValueError('識別メモは2000文字以内で入力してください。')
            if any((ord(character) < 32 and character not in '\r\n\t')
                   or 127 <= ord(character) <= 159 for character in note):
                raise ValueError('識別メモに使用できない制御文字があります。')


@dataclass(frozen=True, slots=True)
class AuthorCandidate:
    """候補の一致根拠。人物の同一性や関連付けの確定を意味しない。"""

    author: Author
    match_kind: Literal['exact', 'normalized', 'partial', 'note']
    matched_text: str
