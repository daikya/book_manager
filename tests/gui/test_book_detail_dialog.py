"""書籍詳細のデータ欠落・副作用・画像異常を確認する。"""
from dataclasses import fields, asdict
from unittest.mock import Mock, patch
from PIL import Image
import pytest

from book_manager.models.book_item import BookItem
from book_manager.models.author import Author
from book_manager.models.reading_history import ReadingHistory
from book_manager.gui.book_detail_dialog import LABELS, detail_sections, load_cover
from book_manager.gui.book_manager_application import BookManagerApplication


def test_all_book_fields_and_related_information_are_preserved():
    assert set(LABELS) == {field.name for field in fields(BookItem)}
    book = BookItem(title='長い題名', id=42, description='あいう\n' * 10000,
                    notes='備考全文', reading_status='completed', tags=('タグA', 'タグB'), rating=5,
                    reference_isbn='9784087754537', is_favorite=True)
    before = asdict(book)
    sections = dict(detail_sections(book, [Author(name='同名', id=7)],
        [ReadingHistory(book_item_id=42, id=9, notes='履歴メモ', completed_on='2026-11-26')]))
    assert sections['内容紹介'] == book.description
    assert sections['備考'] == '備考全文'
    assert sections['読書状態'] == '読了'
    assert sections['管理著者'] == '同名 [ID:7]'
    assert '履歴メモ' in sections['読書履歴']
    assert '2026-11-26' in sections['読書履歴']
    assert sections['お気に入り'] == 'はい'
    assert sections['タグ'] == 'タグA ／ タグB'
    assert asdict(book) == before


def test_empty_values_remain_readable():
    values = dict(detail_sections(BookItem(title='本')))
    assert values['評価'] == '未設定'
    assert values['管理著者'] == '未設定'
    assert values['読書履歴'] == '登録なし'
    assert values['お気に入り'] == 'いいえ'


def test_large_cover_keeps_aspect_ratio_and_source_unchanged(tmp_path):
    path = tmp_path / 'cover.png'
    Image.new('RGB', (800, 1200), 'blue').save(path)
    before = path.read_bytes()
    image = load_cover(path)
    assert image.size == (320, 480)
    assert path.read_bytes() == before


def test_missing_and_corrupt_cover_do_not_block_text(tmp_path):
    assert load_cover(None) is None
    assert load_cover(tmp_path / 'missing.png') is None
    path = tmp_path / 'bad.png'
    path.write_text('not an image')
    assert load_cover(path) is None


def app():
    a = BookManagerApplication.__new__(BookManagerApplication)
    a._root = Mock()
    a._selected_book_id = 42
    a._service = Mock()
    a._author_service = Mock()
    a._reading_history_service = Mock()
    return a


def test_dialog_uses_saved_book_and_never_fetches_or_updates():
    a = app()
    book = BookItem(title='保存済み', id=42, cover_image_path='cache/covers/a.png')
    a._service.get_book.return_value = book
    with patch('book_manager.gui.book_manager_application.BookDetailDialog') as dialog:
        a._on_show_book_detail()
        assert dialog.call_args.kwargs['book'] is book
        dialog.return_value.show.assert_called_once()
    a._service.fetch_cover_image.assert_not_called()
    a._service.update_book.assert_not_called()
    a._reading_history_service.get_histories_for_book.assert_called_once_with(42)


@pytest.mark.parametrize('selected,book', [(None, None), (42, None)])
def test_no_selection_or_deleted_book_does_not_open(selected, book):
    a = app(); a._selected_book_id = selected
    a._service.get_book.return_value = book
    with patch('book_manager.gui.book_manager_application.messagebox.showwarning') as warning, \
         patch('book_manager.gui.book_manager_application.BookDetailDialog') as dialog:
        a._on_show_book_detail()
        warning.assert_called_once()
        dialog.assert_not_called()


def test_history_order_uses_dates_and_does_not_mutate_input():
    from book_manager.gui.book_detail_dialog import ordered_histories, history_date
    latest = ReadingHistory(42, id=2, started_on='2026-11-26')
    older = ReadingHistory(42, id=1, completed_on='2025-04-10')
    original = [latest, older]
    assert ordered_histories(original) == [older, latest]
    assert original == [latest, older]
    assert history_date('2026-11-26') == '2026/11/26'
    assert history_date(None) == '未設定'


@pytest.mark.parametrize('key,note', [('1', '長いメモ\n' * 1000), ('2', None), (None, None)])
def test_history_selection_shows_full_note_and_resets_scroll(key, note):
    from book_manager.gui.book_detail_dialog import BookDetailDialog
    d = BookDetailDialog.__new__(BookDetailDialog)
    d._history_tree = Mock()
    d._history_tree.selection.return_value = (key,) if key else ()
    d._history_items = {key: ReadingHistory(42, id=1, notes=note)} if key else {}
    d._history_caption = Mock(); d._history_note = Mock(); d._history_metadata = Mock()
    d._on_history_selected()
    expected = note or ('メモは登録されていません。' if key else '読書履歴は登録されていません。')
    d._history_note.insert.assert_called_once_with('1.0', expected)
    d._history_note.yview_moveto.assert_called_once_with(0)
    assert d._history_note.configure.call_args.kwargs == {'state': 'disabled'}
