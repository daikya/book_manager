"""表記違いの比較と巻・版の誤一致防止。"""

import pytest

from book_manager.metadata.candidate_matching import (
    candidate_match, normalize_comparison, prepare_search_terms, rank_candidates,
)
from book_manager.models.book_search_candidate import BookSearchCandidate


def candidate(title="本", **kwargs):
    return BookSearchCandidate(source="Google Books", title=title, **kwargs)


@pytest.mark.parametrize("author", ["小路幸也", "小路 幸也", "小路　幸也"])
def test_japanese_name_spacing(author):
    result = candidate(author="小路幸也")
    assert candidate_match(result, author=author)[1] == "著者: 一致"
    assert prepare_search_terms(author=author)["author"] == "小路幸也"


def test_latin_author_query_keeps_spaces():
    assert prepare_search_terms(author=" J. R. R. Tolkien ")["author"] == "J. R. R. Tolkien"


@pytest.mark.parametrize("query", ["イエロー・サブマリン", "イエロー サブマリン", "イエロー－サブマリン"])
def test_title_separators(query):
    assert candidate_match(candidate("イエロー・サブマリン"), title=query)[1] == "書籍名: 一致"


def test_nfkc_case_and_publisher_legal_name():
    result = candidate("Ｐｙｔｈｏｎ　入門", publisher="株式会社 集英社")
    score, label = candidate_match(result, title="python入門", publisher="集英社")
    assert score[0] == 2
    assert label == "書籍名: 一致 / 出版社: 一致"
    assert normalize_comparison("集英社（株）", publisher=True) == "集英社"


@pytest.mark.parametrize("value", ["三体 3", "三体 20", "三体 2 下巻"])
def test_different_number_is_not_fuzzy_match(value):
    assert candidate_match(candidate(value), title="三体 2")[1] == "書籍名: 巻数等を確認"


def test_upper_lower_and_long_vowel_are_not_equated():
    assert candidate_match(candidate("物語 下巻"), title="物語 上巻")[0][0] == 0
    assert normalize_comparison("コート") != normalize_comparison("コト")


def test_partial_and_fuzzy_are_only_hints():
    assert "部分一致" in candidate_match(candidate("Python入門 改訂版"), title="Python入門")[1]
    assert "近似" in candidate_match(candidate("プログラミング入門"), title="プログラミングの入門")[1]
    assert "要確認" in candidate_match(candidate(author="別の著者"), author="小路幸也")[1]


def test_ranking_stable_and_keeps_distinct_volumes_and_missing_isbn():
    unrelated = candidate("別の本", source_id="other")
    a = candidate("イエロー・サブマリン", source_id="a", author="小路幸也")
    b = candidate("イエロー サブマリン", source_id="b", author="小路 幸也")
    result = rank_candidates([unrelated, a, b], title="イエロー・サブマリン", author="小路幸也")
    assert result == [a, b, unrelated]
    assert result[0] is a
    assert a.title == "イエロー・サブマリン"
    assert b.author == "小路 幸也"
    assert b.isbn_candidates == ()


def test_subtitle_can_match_without_lowering_main_title_match():
    result = candidate("本", subtitle="ある副題")
    assert candidate_match(result, title="本")[1] == "書籍名: 一致"
    assert candidate_match(result, title="本 ある副題")[1] == "書籍名: 一致"


def test_missing_metadata_is_visible():
    assert candidate_match(candidate(), publisher="集英社")[1] == "出版社: 情報なし"


@pytest.mark.parametrize("kwargs,error", [
    ({}, ValueError), ({"publisher": "　"}, ValueError),
    ({"publisher": None}, TypeError), ({"publisher": 3}, TypeError),
    ({"title": '":\\'}, ValueError),
])
def test_invalid_conditions(kwargs, error):
    with pytest.raises(error):
        prepare_search_terms(**kwargs)
