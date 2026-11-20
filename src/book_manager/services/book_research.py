"""書籍情報をブラウザーで調べるための検索語。通信やDB更新は行わない。"""
from urllib.parse import urlencode

from book_manager.validators.isbn_normalizer import normalize_isbn
from book_manager.validators.isbn_validator import validate_isbn


def research_isbn(value: str) -> str:
    """区切りを除いてチェックデジットまで確認したISBNを返す。"""
    isbn = normalize_isbn(value)
    validate_isbn(isbn)
    return isbn


def research_book_title(value: str) -> str:
    title = value.strip()
    if not title:
        raise ValueError('書籍名を入力してください。')
    if any(ord(c) < 32 or ord(c) == 127 for c in title):
        raise ValueError('書籍名に改行・制御文字は使用できません。')
    return title


def book_search_query(*, isbn: str = '', title: str = '', author: str = '') -> str:
    """所有書籍のISBNを優先。空欄時だけ書籍名と著者名を使用する。"""
    if isbn.strip():
        return research_isbn(isbn)
    title = research_book_title(title)
    author = author.strip()
    if any(ord(c) < 32 or ord(c) == 127 for c in author):
        raise ValueError('著者名に改行・制御文字は使用できません。')
    return ' '.join(part for part in (title, author) if part)


def amazon_book_search_url(**values: str) -> str:
    return 'https://www.amazon.co.jp/s?' + urlencode({
        'i': 'stripbooks', 'k': book_search_query(**values),
    })
