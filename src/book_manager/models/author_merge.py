"""確認画面と保存時の再検査で共有する著者統合の計画。"""
from dataclasses import dataclass
from book_manager.models.author import Author


@dataclass(frozen=True, slots=True)
class AuthorMergeBook:
    id: int
    title: str
    original_author: str | None
    before_ids: tuple[int, ...]
    after_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class AuthorMergePlan:
    source: Author
    target: Author
    aliases: tuple[str, ...]
    books: tuple[AuthorMergeBook, ...]

    @property
    def suggested_note(self) -> str:
        target = self.target.disambiguation_note or ''
        source = self.source.disambiguation_note or ''
        if not source or source == target:
            return target
        addition = f'【統合元 ID:{self.source.id} {self.source.name}】\n{source}'
        return f'{target}\n\n{addition}' if target else addition
