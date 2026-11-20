"""利用者が貼り付けた1冊分の書誌テキストを、未確認の入力候補へ整理する。"""
from dataclasses import dataclass
import html
import re
import unicodedata

from book_manager.services.book_research import research_isbn
from book_manager.validators.isbn_converter import to_isbn13

FIELDS = {'title': '書籍名', 'author': '著者名', 'publisher': '出版社',
          'isbn': 'ISBN', 'publication_format': '出版形態', 'description': '内容紹介'}
MAX_TEXT_LENGTH = 100_000


@dataclass(frozen=True)
class BookTextCandidate:
    values: dict[str, str]
    warnings: tuple[str, ...]
    product_id: str = ""


def _plain(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # 画像は書影とは限らない。リンクは表示文字だけを残す。
    text = re.sub(r'!\[[^\]]*\]\([^\n]*?\)', '', text)
    text = re.sub(r'\[([^\]\n]*)\]\([^\n]*?\)', r'\1', text)
    text = html.unescape(text).replace('**', '')
    text = re.sub(r'\\[ \t]*\n', '\n', text)
    text = text.replace('\u200e', '').replace('\u200f', '').replace('\ufeff', '')
    if any(ord(c) < 32 and c not in '\n\t' for c in text):
        raise ValueError('貼り付け内容に使用できない制御文字があります。')
    return text


def _clean_line(line: str) -> str:
    return re.sub(r'^\s*(?:[-*•・]\s+|\d+[.)]\s+|#{1,6}\s+)', '', line).strip().strip('|').strip()


def _label_values(lines: list[str], label: str) -> list[str]:
    """独立した項目名、コロン区切り、Markdown表の値を読む。"""
    result = []
    for i, raw in enumerate(lines):
        line = _clean_line(raw)
        match = re.fullmatch(label + r'\s*(?:[:：|]\s*(.*))?', line, re.I)
        if not match:
            continue
        value = (match.group(1) or '').strip()
        if not value:
            value = next((_clean_line(s) for s in lines[i + 1:] if s.strip()), '')
        if value:
            result.append(value)
    return result


def parse_book_text(text: str) -> BookTextCandidate:
    if not text.strip():
        raise ValueError('1冊分の商品情報を貼り付けてください。')
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError('貼り付け内容は10万文字以内にしてください。')
    plain = _plain(text)
    lines = plain.splitlines()
    # 複数版を混ぜて1冊の候補を作らない。
    if (len(re.findall(r'^\s*【[^\n】]+版】\s*$', plain, re.M)) > 1
            or len(re.findall(r'形式\s*[:：]', plain)) > 1):
        raise ValueError('複数の版が含まれています。Audible・Kindle・紙の本は1版ずつ貼り付けてください。')
    values = dict.fromkeys(FIELDS, '')
    warnings = []
    headings = [re.sub(r'^\s*#{1,6}\s+', '', s).strip() for s in lines
                if re.match(r'^\s*#\s+', s)]
    ignored_headings = {'商品の説明', '内容紹介', '商品説明', '商品の詳細', '登録情報'}
    titles = [s for s in headings if s not in ignored_headings]
    if len(titles) > 1:
        raise ValueError('複数の見出しがあり書籍名を特定できません。1冊分に絞ってください。')
    explicit_titles = _label_values(lines, r'(?:書籍名|書名|タイトル)')
    values['title'] = (explicit_titles or titles or [''])[0]
    authors = []
    role_pattern = re.compile(r'([^,、()（）\n]+?)\s*[（(]\s*(?:著|著者)\s*[)）]')
    for i, line in enumerate(lines):
        if re.search(r'形式\s*[:：]', line) or re.search(r'[（(]\s*(?:著|著者)\s*[)）]', line):
            for name in role_pattern.findall(_clean_line(line)):
                name = name.strip()
                if name and name not in authors:
                    authors.append(name)
            if not values['title'] and authors:
                previous = [_clean_line(s) for s in lines[:i] if s.strip()]
                if previous and not previous[-1].startswith('【'):
                    values['title'] = previous[-1]
    values['author'] = '、'.join(authors)
    if not values['author']:
        explicit = _label_values(lines, r'(?:著者名|著者)')
        if explicit:
            values['author'] = explicit[0]
    publishers = _label_values(lines, '出版社')
    if not publishers:
        publishers = re.findall(r'([^,、()（）\n]+?)\s*[（(]\s*出版社\s*[)）]', plain)
    if publishers:
        publisher = publishers[0].strip()
        values['publisher'] = re.sub(r'\s*[（(]\d{4}/\d{1,2}/\d{1,2}[)）]\s*$', '', publisher)
    formats = re.findall(r'形式\s*[:：]\s*([^\n]+)', plain)
    if formats:
        format_ = formats[0].strip()
        if format_.startswith('Audible'):
            values['publication_format'] = 'Audible'
        elif format_.startswith('Kindle'):
            values['publication_format'] = 'Kindle'
        elif format_.startswith('単行本'):
            values['publication_format'] = '単行本'
        elif format_.startswith(('文庫', '新書', '雑誌')):
            values['publication_format'] = next(x for x in ('文庫', '新書', '雑誌') if format_.startswith(x))
        else:
            warnings.append('出版形態を確認できませんでした。必要なら候補欄へ入力してください。')
    isbn_values = _label_values(lines, r'ISBN(?:\s*[-－]\s*(?:10|13))?')
    valid_isbns = []
    for value in isbn_values:
        value = unicodedata.normalize('NFKC', value)
        match = re.match(r'([0-9Xx][0-9Xx \t‐‑‒–—−-]*)', value)
        try:
            isbn = research_isbn(match.group(1).strip() if match else '')
        except ValueError:
            warnings.append('ISBNの形式またはチェックデジットが不正なため候補にしませんでした。')
            continue
        if isbn not in valid_isbns:
            valid_isbns.append(isbn)
    if len({to_isbn13(s) for s in valid_isbns}) > 1:
        warnings.append('異なるISBNが複数あります。対象の版を確認してISBNを入力してください。')
    elif valid_isbns:
        values['isbn'] = next((s for s in valid_isbns if len(s) == 13), valid_isbns[0])
    if not values['isbn']:
        warnings.append('ISBNは未取得です。ASINや商品URLの数字はISBNへ転用しません。')
    # 明示された紹介範囲だけを候補にする。価格・レビュー・商品仕様は混ぜない。
    start = None
    for i, line in enumerate(lines):
        clean = _clean_line(line)
        if (clean in {'商品の説明', '内容紹介', '商品説明', 'すべてのフォーマットとエディションを見る'}
                or re.fullmatch(r'[-―─]{3,}', line.strip())):
            start = i + 1
            break
    if start is not None:
        description = []
        for line in lines[start:]:
            clean = _clean_line(line)
            if (clean.startswith(('image', 'この商品に関する問題を報告する', '商品の詳細',
                                   '登録情報', '本の長さ', '言語', '出版社', 'ASIN',
                                   'ISBN', '発売日', 'カスタマーレビュー', '©', 'Copyright', 'New on Amazon'))
                    or clean in ignored_headings or clean.startswith('【')):
                break
            if clean in {'もっと少なく読む', 'もっと読む', '続きを読む', '閉じる'}:
                continue
            if not clean or re.fullmatch(r'[-―─]{3,}', clean):
                if description and description[-1] != '':description.append('')
                continue
            if clean.startswith(('すべてのフォーマット', '形式:', '形式：')):
                continue
            description.append(line.strip())
        values['description'] = '\n'.join(description).strip()
    for key in ('title', 'author', 'publisher', 'description'):
        if not values[key]:warnings.append(FIELDS[key] + 'を読み取れませんでした。候補欄で補ってください。')
    if not any(values.values()):
        raise ValueError('書誌項目を読み取れませんでした。書籍名・著者・出版社などを含む1冊分を貼り付けてください。')
    warnings.append('読み取り候補です。版・著者の役割・出版社・紹介範囲を確認してください。')
    # 商品IDは追加コピーの混在防止だけに使用し、ISBN・保存項目に転用しない。
    product = re.search(r'https://(?:www\.)?amazon\.co\.jp/[^\s)]*?/dp/([A-Z0-9]{10})(?=[/?#)\s]|$)', text, re.I)
    if product is None:
        product = re.search(r'https://(?:www\.)?amazon\.co\.jp/dp/([A-Z0-9]{10})(?=[/?#)\s]|$)', text, re.I)
    product_id = product.group(1).upper() if product else ''
    return BookTextCandidate(values, tuple(warnings), product_id)


def select_book_text_fields(values: dict[str, str], selected: set[str]) -> dict[str, str]:
    """選択項目だけを検証。空欄による既存値の削除は行わない。"""
    if not selected:
        raise ValueError('反映する項目にチェックを付けてください。')
    if selected - FIELDS.keys():
        raise ValueError('反映対象に不明な項目があります。')
    result = {}
    for key in selected:
        value = values.get(key, '').strip()
        if not value:
            raise ValueError(FIELDS[key] + 'の候補が空欄です。入力するかチェックを外してください。')
        if any((ord(c) < 32 and not (key == 'description' and c in '\n\t')) or ord(c) == 127 for c in value):
            raise ValueError(FIELDS[key] + 'に使用できない改行・制御文字があります。')
        result[key] = research_isbn(value) if key == 'isbn' else value
    return result
