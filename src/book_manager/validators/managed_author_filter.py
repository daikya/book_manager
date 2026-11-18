"""管理著者IDの検索条件を検証する。"""
from collections.abc import Sequence


def normalize_managed_author_filter(*, author_id=None, author_ids=(), mode='any'):
    """単一IDの旧APIと複数IDを受け付け、重複のないID列を返す。"""
    if mode not in ('any', 'all'):
        raise ValueError('管理著者の検索方法はanyまたはallで指定してください。')
    if not isinstance(author_ids, Sequence) or isinstance(author_ids, (str, bytes)):
        raise ValueError('管理著者IDは整数の列で指定してください。')
    if author_id is not None and author_ids:
        raise ValueError('単一の管理著者IDと複数IDは同時に指定できません。')
    values = (author_id,) if author_id is not None else author_ids
    if any(type(value) is not int or value <= 0 for value in values):
        raise ValueError('管理著者IDは正の整数で指定してください。')
    return tuple(dict.fromkeys(values))
