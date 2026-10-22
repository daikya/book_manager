"""表記違いの検索と同姓同名を混同しないことを検証する。"""
import pytest

from book_manager.models.author import Author
from book_manager.services.author_matching import author_search_key, find_author_candidates


@pytest.mark.parametrize('query', ['小路幸也', '小路 幸也', '小路　幸也', ' 小路\t幸也 ', '小路\u00a0幸也'])
def test_spaces_find_candidate_without_changing_stored_name(query):
    author = Author('小路 幸也', id=1)
    assert find_author_candidates([author], query)[0].author is author
    assert author.name == '小路 幸也'


def test_homonyms_remain_separate_and_stable():
    first = Author('山田太郎', id=1, disambiguation_note='経済学')
    second = Author('山田太郎', id=2, disambiguation_note='小説家')
    results = find_author_candidates([second, first], '山田 太郎')
    assert [item.author.id for item in results] == [2, 1]
    assert all(item.match_kind == 'normalized' for item in results)


def test_alias_can_be_shared_by_distinct_people():
    authors = [Author('甲', id=1, aliases=('山田太郎',)), Author('乙', id=2, aliases=('山田太郎',))]
    assert [item.author.id for item in find_author_candidates(authors, '山田太郎')] == [1, 2]


def test_alias_is_not_another_author_and_name_is_not_split():
    author = Author('小路,幸也,1961-', aliases=('小路幸也',), id=1)
    results = find_author_candidates([author], '小路幸也')
    assert len(results) == 1
    assert results[0].matched_text == '小路幸也'
    assert results[0].author.name == '小路,幸也,1961-'


def test_best_alias_match_wins_over_primary_partial_match():
    author = Author('山田太郎・作品集', aliases=('山田太郎',))
    result, = find_author_candidates([author], '山田太郎')
    assert result.match_kind == 'exact'
    assert result.matched_text == '山田太郎'


def test_order_exact_normalized_partial_note():
    note = Author('別人', id=4, disambiguation_note='山田太郎という筆名について')
    partial = Author('山田太郎二世', id=3)
    normalized = Author('山田 太郎', id=2)
    exact = Author('山田太郎', id=1)
    assert [item.author.id for item in find_author_candidates([note, partial, normalized, exact], '山田太郎')] == [1, 2, 3, 4]


@pytest.mark.parametrize('query', ['', ' ', '　', '\t\n'])
def test_empty_query_returns_no_candidates(query):
    assert find_author_candidates([Author('小路幸也')], query) == []


@pytest.mark.parametrize('query', [None, 1, True, ['小路幸也']])
def test_invalid_query_is_rejected(query):
    with pytest.raises(TypeError):
        find_author_candidates([], query)


def test_nfkc_and_casefold_used_only_for_search():
    author = Author('Ｊ．Ｋ．Ｒｏｗｌｉｎｇ')
    result, = find_author_candidates([author], 'j.k.rowling')
    assert result.match_kind == 'normalized'
    assert result.author.name == 'Ｊ．Ｋ．Ｒｏｗｌｉｎｇ'


@pytest.mark.parametrize(('first', 'second'), [('山田一郎', '山田二郎'), ('小路幸也', '小路,幸也,1961-'), ('ジョン・スミス', 'ジョンスミス'), ('Anne-Marie', 'AnneMarie'), ('髙橋', '高橋'), ('渡邊', '渡辺')])
def test_punctuation_digits_and_kanji_not_automatically_equated(first, second):
    assert author_search_key(first) != author_search_key(second)


def test_notes_find_distinguishing_information():
    first = Author('山田太郎', id=1, disambiguation_note='経済学・○○大学')
    second = Author('山田太郎', id=2, disambiguation_note='小説家')
    results = find_author_candidates([first, second], '経済学')
    assert len(results) == 1
    assert results[0].author.id == 1
    assert results[0].match_kind == 'note'


def test_does_not_infer_multiple_authors_from_delimiters():
    author = Author('甲／乙,丙 著', id=1)
    result, = find_author_candidates([author], '乙')
    assert result.author.name == '甲／乙,丙 著'
    assert result.match_kind == 'partial'


def test_same_author_matches_multiple_aliases_once():
    author = Author('小路幸也', aliases=('小路 幸也', '小路　幸也'))
    assert len(find_author_candidates([author], '小路幸也')) == 1


def test_input_and_aliases_are_not_mutated():
    authors = [Author('山田 太郎', id=2, aliases=('別名',)), Author('山田太郎', id=1)]
    before = list(authors)
    find_author_candidates(authors, '山田太郎')
    assert authors == before


def test_unrelated_name_returns_no_candidate():
    assert find_author_candidates([Author('小路幸也')], '夏目漱石') == []
