"""著者情報を利用者が調べて識別メモへ残すための入力支援。"""
from urllib.parse import urlencode, urlsplit

from book_manager.models.author import Author

SOURCE_PREFIX = '情報元URL: '


def research_author_name(value: str) -> str:
    """編集中の表示名を検証し、検索・コピー用に前後だけ空白を除く。"""
    Author(name=value)
    return value.strip()


def amazon_author_search_url(name: str) -> str:
    """名前を安全にエンコードしたAmazonの書籍検索URL。"""
    return 'https://www.amazon.co.jp/s?' + urlencode({
        'i': 'stripbooks', 'k': research_author_name(name),
    })


def validate_author_source_url(value: str) -> str:
    """ブラウザーで開く情報元URLをHTTP(S)に限定する。"""
    url = value.strip()
    if any(ord(c) < 32 or ord(c) == 127 for c in url):
        raise ValueError('URLに改行・制御文字は使用できません。')
    try:
        parts = urlsplit(url)
        _ = parts.port  # 不正なポート番号もここで拒否する。
    except ValueError as error:
        raise ValueError('情報元URLの形式が正しくありません。') from error
    if (parts.scheme not in ('http', 'https') or not parts.hostname
            or parts.username is not None or parts.password is not None
            or any(c.isspace() for c in parts.netloc)):
        raise ValueError('情報元にはHTTP/HTTPSのURLを入力してください。')
    return url


def append_author_note(current: str, text: str) -> str:
    """既存メモを保持して末尾へ追記する。保存可能な2000文字まで。"""
    text = text.replace('\r\n', '\n').replace('\r', '\n').strip()
    if not text:
        return current
    result = current + ('\n' if current and not current.endswith('\n') else '') + text
    Author(name='入力検査', disambiguation_note=result)
    return result


def append_author_source(current: str, url: str) -> str:
    line = SOURCE_PREFIX + validate_author_source_url(url)
    if line in current.splitlines():
        return current
    return append_author_note(current, line)


def author_source_from_note(note: str) -> str:
    """最後に追記された有効な情報元URLを再表示する。"""
    for line in reversed(note.splitlines()):
        if line.startswith(SOURCE_PREFIX):
            try:
                return validate_author_source_url(line[len(SOURCE_PREFIX):])
            except ValueError:
                continue
    return ''
