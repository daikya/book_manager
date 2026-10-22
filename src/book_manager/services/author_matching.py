"""著者の表記違いを検索する。ID統合・DB更新・名前の自動分割は行わない。"""
from collections.abc import Iterable

from book_manager.models.author import Author, AuthorCandidate
from book_manager.validators.author_name_normalizer import author_search_key


def find_author_candidates(authors: Iterable[Author], query: str) -> list[AuthorCandidate]:
    """表示名・別名・識別メモから候補を返す。同名の著者は全件残す。

    順序は文字列の完全一致、正規化後の一致、部分一致、識別メモの一致。
    同順位は入力順を維持する。空検索は全件返却せず空リストを返す。
    データ量に応じた候補取得は、後続のRepository側で対応する。
    """
    key = author_search_key(query)
    if not key:
        return []
    query = query.strip()
    candidates = []
    priorities = {'exact': 0, 'normalized': 1, 'partial': 2, 'note': 3}
    for author in authors:
        if not isinstance(author, Author):
            raise TypeError('著者候補にはAuthorを指定してください。')
        best = None
        for text in (author.name, *author.aliases):
            target = author_search_key(text)
            if text.strip() == query:
                match = AuthorCandidate(author, 'exact', text)
            elif target == key:
                match = AuthorCandidate(author, 'normalized', text)
            elif key in target:
                match = AuthorCandidate(author, 'partial', text)
            else:
                continue
            if best is None or priorities[match.match_kind] < priorities[best.match_kind]:
                best = match
        if best is None and author.disambiguation_note:
            if key in author_search_key(author.disambiguation_note):
                best = AuthorCandidate(author, 'note', author.disambiguation_note)
        if best is not None:
            candidates.append(best)
    return sorted(candidates, key=lambda candidate: priorities[candidate.match_kind])
