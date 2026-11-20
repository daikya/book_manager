"""候補修正・取消・原文変更と、親フォームへの限定反映を検証する。"""
from unittest.mock import Mock, patch
from pathlib import Path
import tkinter as tk
import pytest
from book_manager.gui.book_text_import_dialog import BookTextImportDialog
from book_manager.gui.book_research_dialog import BookResearchDialog
from book_manager.gui.book_manager_application import BookManagerApplication
from book_manager.gui.long_text_dialog import FormTextValue
from book_manager.services.book_text_parser import FIELDS

MODULE = 'book_manager.gui.book_text_import_dialog'
SAMPLE = (Path(__file__).parents[1] / 'fixtures' / 'book_text' / 'audible.md').read_text(encoding='utf-8')


class Value:
    def __init__(self, value=''):self.value = value
    def get(self):return self.value
    def set(self, value):self.value = value


def editor():
    d = BookTextImportDialog.__new__(BookTextImportDialog)
    d.result = None;d.window = Mock();d._current = {'title':'既存書籍', 'isbn':'9784087754537'}
    d._identity = None;d._merge_store = None;d._additional_button = Mock()
    d._parsed_source = None;d._apply_button = Mock();d._warnings = Value()
    d._source = FormTextValue(SAMPLE);d._description = FormTextValue()
    d._variables = {k:Value() for k in FIELDS if k != 'description'}
    d._selected = {k:Value(False) for k in FIELDS}
    return d


def test_parse_preserves_existing_values_by_default():
    d = editor();d._parse()
    assert d._variables['title'].get() == 'ブティック'
    assert d._variables['author'].get() == '池井戸 潤'
    assert d._selected['title'].get() is False
    assert d._selected['isbn'].get() is False
    assert d._selected['author'].get() is True
    assert d._current == {'title':'既存書籍', 'isbn':'9784087754537'}
    assert d.result is None


def test_manual_correction_and_only_checked_fields_returned():
    d = editor();d._parse()
    for v in d._selected.values():v.set(False)
    d._selected['publisher'].set(True);d._variables['publisher'].set('確認して修正した出版社')
    d._apply()
    assert d.result == {'publisher':'確認して修正した出版社'}
    d.window.destroy.assert_called_once()


def test_changed_source_cannot_apply_old_candidates():
    d = editor();d._parse();d._source.insert('1.0', '変更')
    with patch(f'{MODULE}.messagebox.showwarning') as warning:
        d._apply();warning.assert_called_once()
    assert d.result is None;d.window.destroy.assert_not_called()


def test_parse_error_invalidates_previous_candidates():
    d = editor();d._parse();d._source.value = SAMPLE + '\n形式: Kindle版'
    with patch(f'{MODULE}.messagebox.showerror') as error:
        d._parse();error.assert_called_once()
    assert d._parsed_source is None
    assert all(v.get() == '' for v in d._variables.values())
    assert d._description.value == '' and not any(v.get() for v in d._selected.values())
    d._apply_button.configure.assert_called_with(state='disabled')


def test_invalid_selected_isbn_keeps_dialog_open():
    d = editor();d._parse();d._variables['isbn'].set('123');d._selected['isbn'].set(True)
    with patch(f'{MODULE}.messagebox.showerror') as error:
        d._apply();error.assert_called_once()
    assert d.result is None;d.window.destroy.assert_not_called()


def test_clipboard_failure_keeps_source():
    d = editor();d.window.clipboard_get.side_effect = tk.TclError('empty')
    with patch(f'{MODULE}.messagebox.showerror'):
        d._paste_clipboard()
    assert d._source.value == SAMPLE


def test_clipboard_paste_requires_new_parse():
    d = editor();d._parse();d.window.clipboard_get.return_value = '# 別の本'
    d._paste_clipboard()
    assert d._source.value == '# 別の本' and d._parsed_source == SAMPLE
    d._apply_button.configure.assert_called_with(state='disabled')


def test_dialog_restores_own_geometry():
    with patch(f'{MODULE}.tk'), patch(f'{MODULE}.ttk'), patch(f'{MODULE}.ScrolledText'), patch(f'{MODULE}.restore_dialog_window') as restore:
        store = Mock();store.path = Path('/tmp/window_state.json');d = BookTextImportDialog(Mock(), current={'title':'本'}, state_store=store)
        assert restore.call_args.args[2] is store
        assert restore.call_args.kwargs['default_size'] == (940, 680)
        assert d.result is None


def app():
    a = BookManagerApplication.__new__(BookManagerApplication)
    a._root = Mock();a._service = Mock();a._selected_book_id = 7
    for name, value in [('isbn','9784087754537'), ('reference_isbn','9784087443721'), ('title','既存書籍'), ('author','既存著者'), ('publisher','既存出版社'), ('publication_format','単行本')]:
        setattr(a, f'_{name}_var', Value(value))
    a._description_text = FormTextValue('既存紹介');a._notes_text = FormTextValue('備考')
    a._current_cover_image_url = 'https://example.com/cover.jpg';a._current_cover_image_path = 'cache/cover.jpg'
    a._managed_author_ids = (3,);a._edit_status_var = Value();a._replace_text = lambda t,v:setattr(t,'value',v)
    return a


def test_parent_applies_only_selected_fields_and_does_not_save():
    a = app()
    with patch('book_manager.gui.book_manager_application.BookResearchDialog') as dialog:
        dialog.return_value.show.return_value = {'title':'修正書籍', 'description':'新紹介\n次の段落'}
        a._on_book_research()
    assert a._title_var.get() == '修正書籍' and a._description_text.value == '新紹介\n次の段落'
    assert a._isbn_var.get() == '9784087754537' and a._reference_isbn_var.get() == '9784087443721'
    assert a._author_var.get() == '既存著者' and a._publisher_var.get() == '既存出版社'
    assert a._managed_author_ids == (3,) and a._notes_text.value == '備考'
    assert a._current_cover_image_path == 'cache/cover.jpg'
    a._service.assert_not_called();assert not a._service.method_calls


def test_cancel_keeps_entire_form():
    a = app();before = a._metadata_form_snapshot()
    with patch('book_manager.gui.book_manager_application.BookResearchDialog') as dialog:
        dialog.return_value.show.return_value = None;a._on_book_research()
    assert a._metadata_form_snapshot() == before


def test_changed_target_rejects_apply():
    a = app()
    def changed():
        a._selected_book_id = 8
        return {'title':'反映しない'}
    with patch('book_manager.gui.book_manager_application.BookResearchDialog') as dialog, patch('book_manager.gui.book_manager_application.messagebox.showwarning') as warning:
        dialog.return_value.show.side_effect = changed;a._on_book_research();warning.assert_called_once()
    assert a._title_var.get() == '既存書籍'


@pytest.mark.parametrize('result', [None, {'title':'新しい書籍'}])
def test_nested_paste_returns_only_on_apply(result):
    d = BookResearchDialog.__new__(BookResearchDialog)
    d.window = Mock();d.result = None;d._current = {'title':'旧書籍'};d._paste_state_store = None
    with patch('book_manager.gui.book_research_dialog.BookTextImportDialog') as child:
        child.return_value.show.return_value = result;d._paste_book_text()
    assert d.result == result
    if result is None:
        d.window.destroy.assert_not_called();d.window.grab_set.assert_called_once()
    else:d.window.destroy.assert_called_once()
