"""比較画面の選択可能項目と初期選択を検証する。"""
from book_manager.gui.metadata_comparison_dialog import build_comparison_fields
from book_manager.models.fetched_book_data import FetchedBookData


def rows(current, fetched, reference=False):
    return {row.key: row for row in build_comparison_fields(
        current, fetched, use_reference_isbn=reference,
    )}


def test_empty_current_selects_available_fields():
    result = rows({}, FetchedBookData(isbn="isbn", title="書籍", description="紹介"))
    assert result["title"].selected
    assert result["description"].selected
    assert not result["cover_image_url"].selectable


def test_existing_values_are_not_selected():
    result = rows({"title": "元書籍", "description": "元紹介"},
                  FetchedBookData(isbn="isbn", title="新書籍", description="新紹介"))
    assert result["title"].selectable
    assert not result["title"].selected
    assert result["description"].selectable
    assert not result["description"].selected


def test_identical_values_are_not_selectable():
    result = rows({"title": "同じ"}, FetchedBookData(isbn="isbn", title="同じ"))
    assert not result["title"].selectable


def test_reference_only_allows_description_and_cover():
    result = rows({}, FetchedBookData(
        isbn="isbn", title="書籍", author="著者", publisher="出版元",
        publication_format="文庫", description="紹介", cover_image_url="https://cover",
    ), reference=True)
    assert {key for key, row in result.items() if row.selectable} == {
        "description", "cover_image_url",
    }


def test_blank_fetched_values_cannot_erase_current_values():
    result = rows({"title": "元書籍", "author": "元著者"},
                  FetchedBookData(isbn="isbn", title="", author="  "))
    assert not result["title"].selectable
    assert not result["author"].selectable
    assert result["title"].fetched is None


def test_description_line_breaks_are_preserved():
    result = rows({"description": "元\n紹介"},
                  FetchedBookData(isbn="isbn", description="新\n紹介"))
    assert result["description"].current == "元\n紹介"
    assert result["description"].fetched == "新\n紹介"


def test_reference_existing_description_is_initially_kept():
    result = rows({"description": "元紹介"},
                  FetchedBookData(isbn="isbn", description="新紹介"), reference=True)
    assert result["description"].selectable
    assert not result["description"].selected
