"""提供された3版の例・平文・不明項目の保持を検証する。"""
from pathlib import Path
import pytest
from book_manager.services.book_text_parser import parse_book_text, select_book_text_fields

FIXTURES = Path(__file__).parents[1] / 'fixtures' / 'book_text'


def sample(name):return (FIXTURES / (name + '.md')).read_text(encoding='utf-8')


@pytest.mark.parametrize('name,publisher,format_', [('audible', 'Audible Studios', 'Audible'), ('kindle', 'ダイヤモンド社', 'Kindle'), ('paper', 'ダイヤモンド社', '単行本')])
def test_user_samples_keep_editions_separate(name, publisher, format_):
    result = parse_book_text(sample(name));v = result.values
    assert v['title'] == 'ブティック'
    assert v['author'] == ('池井戸　潤' if name == 'paper' else '池井戸 潤')
    assert v['publisher'] == publisher
    assert v['publication_format'] == format_
    assert v['isbn'] == ''
    assert v['description'].startswith('池井戸潤、2年ぶりの最新長編')
    assert v['description'].endswith('新たな希望とはーー？')
    for noise in ('©', 'image', '出版社', '本の長さ', '485ページ', 'http', 'ナレーション'):
        assert noise not in v['description']
    assert any('ISBNは未取得' in w for w in result.warnings)


def test_markdown_line_breaks_preserved_and_navigation_not_included():
    description = parse_book_text(sample('kindle')).values['description']
    assert len(description.splitlines()) == 5
    assert '\\' not in description and '詳細はこちら' not in description


def test_plain_browser_copy():
    text = '''ブティック
池井戸 潤 (著) 形式: Kindle版
すべてのフォーマットとエディションを見る

内容の1段落。

内容の2段落。
この商品に関する問題を報告する
出版社
ダイヤモンド社
'''
    v = parse_book_text(text).values
    assert v['title'] == 'ブティック' and v['author'] == '池井戸 潤'
    assert v['publisher'] == 'ダイヤモンド社'
    assert v['description'] == '内容の1段落。\n\n内容の2段落。'


def test_multiple_editions_rejected():
    with pytest.raises(ValueError, match='複数の版'):
        parse_book_text(sample('audible') + '\n' + sample('kindle') + '\n' + sample('paper'))


def test_multiple_unmarked_formats_rejected():
    with pytest.raises(ValueError, match='複数の版'):
        parse_book_text('# 本\n甲 (著) 形式: Kindle版\n# 本\n甲 (著) 形式: 単行本')


@pytest.mark.parametrize('text', [
    pytest.param('', id='empty'),
    pytest.param('   ', id='whitespace'),
    pytest.param('https://www.amazon.co.jp/dp/4478124698/', id='url-only'),
    pytest.param('x' * 100001, id='over-text-limit'),
    pytest.param('# 本\n\x00', id='control-character'),
])
def test_unusable_text_rejected(text):
    with pytest.raises(ValueError):parse_book_text(text)


@pytest.mark.parametrize('label,value,expected', [('ISBN-13', '978-4-08-775453-7', '9784087754537'), ('ISBN-10', '4-08-775453-7', '4087754537'), ('ISBN', '9784087754537', '9784087754537')])
def test_only_explicit_valid_isbn_is_used(label, value, expected):
    assert parse_book_text('# 本\n' + label + ': ' + value).values['isbn'] == expected
    assert parse_book_text('# 本\n' + label + '\n' + value).values['isbn'] == expected


def test_isbn_10_13_same_edition_prefers_explicit_13():
    v = parse_book_text('# 本\nISBN-10: 4087754537\nISBN-13: 9784087754537').values
    assert v['isbn'] == '9784087754537'


def test_conflicting_or_invalid_isbn_is_not_applied():
    result = parse_book_text('# 本\nISBN-13: 9784087754537\nISBN-13: 9784087443721')
    assert result.values['isbn'] == '' and any('異なるISBN' in w for w in result.warnings)
    result = parse_book_text('# 本\nISBN-13: 9784087754538')
    assert result.values['isbn'] == '' and any('不正' in w for w in result.warnings)


def test_multiple_authors_do_not_include_translator_or_narrator():
    v = parse_book_text('# 本\n甲 (著), 乙 (著), 丙 (翻訳), 丁 (ナレーション) 形式: Audible版').values
    assert v['author'] == '甲、乙'


def test_missing_description_does_not_guess_from_unmarked_text():
    v = parse_book_text('# 本\n甲 (著)\n価格1,000円\nレビュー本文').values
    assert v['description'] == ''


def test_labeled_plain_and_table_items():
    v = parse_book_text('書籍名: 本\n著者名: 甲\n| 出版社 | 出版社名 (2026/5/13) |\n内容紹介\n本文\n登録情報\nASIN: X').values
    assert v['title'] == '本' and v['author'] == '甲'
    assert v['publisher'] == '出版社名' and v['description'] == '本文'


@pytest.mark.parametrize('selected,values', [(set(), {'title':'本'}), ({'isbn'}, {'isbn':'123'}), ({'title'}, {'title':''}), ({'cover_image_url'}, {'cover_image_url':'https://example.com/'}), ({'author'}, {'author':'甲\n乙'})])
def test_selection_validation(selected, values):
    with pytest.raises(ValueError):select_book_text_fields(values, selected)


def test_only_selected_validated_and_no_blank_deletion():
    assert select_book_text_fields({'title':' 修正した本 ', 'isbn':'bad', 'author':''}, {'title'}) == {'title':'修正した本'}
    assert select_book_text_fields({'description':'段落1\n\n段落2'}, {'description'}) == {'description':'段落1\n\n段落2'}
