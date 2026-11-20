"""同じ版の追加コピーを照合し、空欄補完と確認すべき相違を分ける。"""
import re
import unicodedata

from book_manager.services.book_text_parser import BookTextCandidate, FIELDS
from book_manager.services.book_research import research_isbn
from book_manager.validators.isbn_converter import to_isbn13


def _title(value: str) -> str:
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', value))


def _isbn(value: str) -> str:
    try:
        return to_isbn13(research_isbn(value))
    except ValueError:
        return value.strip()


def check_book_text_identity(base: BookTextCandidate, added: BookTextCandidate) -> bool:
    """既知の相違は拒否。同じ版を識別する手掛かりが不足ならFalse。"""
    pairs = [('title', '書籍名', _title), ('publication_format', '出版形態', lambda s:s.strip()),
             ('isbn', 'ISBN', _isbn)]
    for key, label, normalize in pairs:
        old, new = base.values.get(key, ''), added.values.get(key, '')
        if old.strip() and new.strip() and normalize(old) != normalize(new):
            raise ValueError(label + 'が異なるため追加できません。別の書籍・版は「新しく読み取る」を使用してください。')
    if base.product_id and added.product_id and base.product_id != added.product_id:
        raise ValueError('商品IDが異なるため追加できません。同じ版の商品ページか確認してください。')
    if base.product_id and added.product_id:
        return True
    if base.values.get('isbn') and added.values.get('isbn'):
        return True
    return all(base.values.get(k, '').strip() and added.values.get(k, '').strip()
               for k in ('title', 'publication_format'))


def extend_book_text_identity(base: BookTextCandidate, added: BookTextCandidate) -> BookTextCandidate:
    """候補欄の手修正と分離して、原文から得た照合用情報を保持する。"""
    values = {k:base.values.get(k, '') or added.values.get(k, '') for k in FIELDS}
    return BookTextCandidate(values, (), base.product_id or added.product_id)


def plan_book_text_merge(existing: dict[str, str], added: dict[str, str]):
    """空欄だけを補完。異なる非空値は既存を保持して比較対象へ返す。"""
    merged = dict(existing)
    conflicts = {}
    for key in FIELDS:
        old, new = existing.get(key, ''), added.get(key, '')
        if not new.strip():
            continue
        if not old.strip():
            merged[key] = new
        elif (old.strip() != new.strip()
              and not (key == 'isbn' and _isbn(old) == _isbn(new))):
            conflicts[key] = (old, new)
    return merged, conflicts
