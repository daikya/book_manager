"""追加確定まで候補・チェックを保持し、異版混在を防ぐ。"""
from unittest.mock import Mock, patch
from pathlib import Path
import pytest
from book_manager.gui.book_text_merge_dialog import BookTextMergeDialog
from test_book_text_import_dialog import editor, MODULE

DATA = Path(__file__).parents[1] / 'fixtures' / 'book_text'


def slide(name):return (DATA/(name+'.md')).read_text(encoding='utf-8')


def prepared():
    d = editor();d._source.value = slide('hakone_hardcover_1');d._parse()
    d._source.value = slide('hakone_hardcover_2')
    return d


def test_add_isbn_without_losing_publisher_or_checkbox_choices():
    d = prepared();d._current['isbn'] = ''
    d._selected['publisher'].set(False)
    d._merge()
    assert d._variables['isbn'].get() == '9784163917726'
    assert d._variables['publisher'].get() == '文藝春秋'
    assert d._selected['publisher'].get() is False and d._selected['isbn'].get() is True
    assert 'ISBNは未取得' not in d._warnings.get()
    assert '出版社を読み取れません' not in d._warnings.get()
    d._apply();assert d.result['isbn'] == '9784163917726' and 'publisher' not in d.result


@pytest.mark.parametrize('adopted', [frozenset(), frozenset({'description'})])
def test_conflict_choice_keeps_or_replaces_whole_description(adopted):
    d = prepared();d._description.value = '手で修正した内容紹介'
    with patch(f'{MODULE}.BookTextMergeDialog') as dialog:
        dialog.return_value.show.return_value = adopted;d._merge()
        assert dialog.call_args.kwargs['conflicts']['description'][0] == '手で修正した内容紹介'
    expected = '手で修正した内容紹介' if not adopted else '「東京箱根間往復大学駅伝競走」――通称・箱根駅伝。\n白熱のレースとその舞台裏を描く感動長編。'
    assert d._description.value == expected
    assert d._variables['isbn'].get() == '9784163917726'
    d.window.grab_set.assert_called_once()


def test_conflict_cancel_rolls_back_entire_addition():
    d = prepared();d._description.value = '手で修正'
    before = d._candidate_values();choices = {k:v.get() for k,v in d._selected.items()};identity = d._identity
    with patch(f'{MODULE}.BookTextMergeDialog') as dialog:
        dialog.return_value.show.return_value = None;d._merge()
    assert d._candidate_values() == before and d._identity is identity
    assert {k:v.get() for k,v in d._selected.items()} == choices
    assert d._source.value == slide('hakone_hardcover_1')
    d._apply_button.configure.assert_called_with(state='normal')


@pytest.mark.parametrize('source', ['hakone_bunko_2', 'hakone_kindle_2'])
def test_other_edition_is_rejected_without_touching_candidates(source):
    d = prepared();before = d._candidate_values();d._source.value = slide(source)
    with patch(f'{MODULE}.messagebox.showerror') as error, patch(f'{MODULE}.BookTextMergeDialog') as dialog:
        d._merge();error.assert_called_once();dialog.assert_not_called()
    assert d._candidate_values() == before
    d._apply_button.configure.assert_called_with(state='disabled')


def test_invalid_addition_keeps_manual_corrections():
    d = prepared();d._variables['publisher'].set('修正済み出版社');d._source.value = ''
    with patch(f'{MODULE}.messagebox.showerror'):
        d._merge()
    assert d._variables['publisher'].get() == '修正済み出版社' and d._variables['isbn'].get() == ''


@pytest.mark.parametrize('confirmed', [True, False])
def test_isbn_only_addition_requires_confirmation(confirmed):
    d = prepared();d._source.value = 'ISBN-13: 9784163917726'
    with patch(f'{MODULE}.messagebox.askyesno', return_value=confirmed) as question:
        d._merge();question.assert_called_once()
    assert d._variables['isbn'].get() == ('9784163917726' if confirmed else '')


def test_add_without_initial_read_is_blocked():
    d = editor()
    with patch(f'{MODULE}.messagebox.showinfo') as info:
        d._merge();info.assert_called_once()
    assert d._identity is None


def test_merge_confirmation_defaults_to_keep_and_cancel_is_distinct():
    module = 'book_manager.gui.book_text_merge_dialog'
    with patch(f'{module}.tk') as tk, patch(f'{module}.ttk'), patch(f'{module}.ScrolledText'), patch(f'{module}.restore_dialog_window') as restore:
        d = BookTextMergeDialog(Mock(), conflicts={'description':('旧紹介','新紹介')})
        assert d.result is None
        assert tk.BooleanVar.call_args.kwargs['value'] is False
        assert restore.call_args.kwargs['default_size'] == (900, 600)
        tk.BooleanVar.return_value.get.return_value = False
        d._confirm();assert d.result == frozenset()
