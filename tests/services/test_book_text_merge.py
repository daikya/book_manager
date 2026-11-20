"""隠れた商品詳細からのISBN補完、同版照合、相違の扱いを検証する。"""
from pathlib import Path
import pytest
from book_manager.services.book_text_parser import parse_book_text, BookTextCandidate
from book_manager.services.book_text_merge import check_book_text_identity, extend_book_text_identity, plan_book_text_merge

DATA = Path(__file__).parents[1] / 'fixtures' / 'book_text'


def sample(name):return parse_book_text((DATA/(name+'.md')).read_text(encoding='utf-8'))


@pytest.mark.parametrize('name,isbn', [('hakone_hardcover', '9784163917726'), ('hakone_bunko', '9784167925529')])
def test_real_slide_patterns_supplement_isbn_without_losing_publisher(name, isbn):
    first, second = sample(name+'_1'), sample(name+'_2')
    assert first.values['isbn'] == '' and second.values['publisher'] == ''
    assert second.values['isbn'] == isbn
    assert check_book_text_identity(first, second) is True
    merged, conflicts = plan_book_text_merge(first.values, second.values)
    assert merged['publisher'] == '文藝春秋' and merged['isbn'] == isbn
    assert conflicts == {}
    assert 'もっと少なく読む' not in merged['description']
    assert merged['description'] == first.values['description']


def test_three_kindle_slides_keep_publisher_and_do_not_create_isbn():
    base = sample('hakone_kindle_1');values = dict(base.values)
    assert base.product_id == 'B0HFYPKHWF'  # 全巻セットの商品IDにはしない。
    for i in (2, 3):
        added = sample(f'hakone_kindle_{i}')
        assert check_book_text_identity(base, added)
        values, conflicts = plan_book_text_merge(values, added.values)
        assert conflicts == {}
        base = extend_book_text_identity(base, added)
    assert values['publisher'] == '文藝春秋' and values['isbn'] == ''
    assert values['publication_format'] == 'Kindle'


@pytest.mark.parametrize('left,right', [('hakone_hardcover_1','hakone_bunko_2'), ('hakone_kindle_1','hakone_hardcover_2')])
def test_different_editions_are_rejected(left, right):
    with pytest.raises(ValueError):check_book_text_identity(sample(left), sample(right))


def test_same_title_format_but_different_product_or_isbn_rejected():
    base = parse_book_text('# 本\n甲 (著) 形式: 文庫\nISBN-13: 9784167925529\n[商品](https://www.amazon.co.jp/dp/4167925524/)')
    wrong_id = parse_book_text('# 本\n甲 (著) 形式: 文庫\n[商品](https://www.amazon.co.jp/dp/4163917721/)')
    with pytest.raises(ValueError, match='商品ID'):check_book_text_identity(base, wrong_id)
    wrong_isbn = parse_book_text('# 本\n甲 (著) 形式: 文庫\nISBN-13: 9784163917726')
    with pytest.raises(ValueError, match='ISBN'):check_book_text_identity(base, wrong_isbn)


def test_metadata_identity_is_separate_from_manually_corrected_values():
    first, second = sample('hakone_hardcover_1'), sample('hakone_hardcover_2')
    corrected = dict(first.values, title='手で修正した題名', description='手で修正した説明')
    assert check_book_text_identity(first, second)
    merged, conflicts = plan_book_text_merge(corrected, second.values)
    assert merged['title'] == corrected['title'] and merged['description'] == corrected['description']
    assert conflicts['title'] == (corrected['title'], second.values['title'])
    assert conflicts['description'] == (corrected['description'], second.values['description'])
    assert merged['isbn'] == '9784163917726'


def test_isbn_equivalence_and_repeat_merge():
    first = parse_book_text('# 本\nISBN-10: 4163917721')
    added = parse_book_text('# 本\nISBN-13: 9784163917726')
    assert check_book_text_identity(first, added)
    merged, conflicts = plan_book_text_merge(first.values, added.values)
    assert merged['isbn'] == '4163917721' and not conflicts
    merged2, conflicts = plan_book_text_merge(merged, added.values)
    assert merged2 == merged and not conflicts


def test_missing_identity_requires_user_confirmation():
    first = parse_book_text('# 本\n甲 (著) 形式: 文庫')
    added = parse_book_text('ISBN-13: 9784167925529')
    assert check_book_text_identity(first, added) is False


def test_second_addition_remembers_previously_added_identity():
    first = parse_book_text('# 本\n甲 (著) 形式: 文庫')
    added = parse_book_text('# 本\n甲 (著) 形式: 文庫\nISBN-13: 9784167925529')
    extended = extend_book_text_identity(first, added)
    with pytest.raises(ValueError, match='ISBN'):
        check_book_text_identity(extended, parse_book_text('# 本\n甲 (著) 形式: 文庫\nISBN-13: 9784163917726'))
    assert first.values['isbn'] == ''


@pytest.mark.parametrize('noise', ['もっと少なく読む', 'もっと読む', '続きを読む'])
def test_read_more_controls_excluded_but_real_prose_preserved(noise):
    parsed = parse_book_text('# 本\n甲 (著) 形式: Audible版\n---\nもっと読むことが好きな主人公。\n'+noise+'\n©2024\n出版社\nAudible Studios')
    assert parsed.values['description'] == 'もっと読むことが好きな主人公。'


def test_three_audible_slides_keep_author_and_publisher_without_narrator():
    head = '# 俺たちの箱根駅伝 上\n池井戸 潤 (著), 浅木 俊之 (ナレーション), Audible Studios (出版社) 形式: Audible版\n[商品](https://www.amazon.co.jp/book/dp/B0D175WRJ9/)\n---\n紹介本文。\nもっと少なく読む\n©Jun Ikeido\n'
    parts = ['1. 著者\n池井戸 潤\n2. ナレーター\n浅木 俊之\n',
             '1. 出版社\nAudible Studios\n2. ASIN\nB0D175WRJ9\n',
             '1. フォマット\nオーディオブック\n']
    base = parse_book_text(head + parts[0]);values = dict(base.values)
    for part in parts[1:]:
        added = parse_book_text(head + part)
        assert check_book_text_identity(base, added)
        values, conflicts = plan_book_text_merge(values, added.values)
        assert not conflicts
        base = extend_book_text_identity(base, added)
    assert values['author'] == '池井戸 潤' and values['publisher'] == 'Audible Studios'
    assert values['description'] == '紹介本文。' and values['isbn'] == ''
