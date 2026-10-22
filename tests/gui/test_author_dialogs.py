"""管理著者ダイアログの選択・キャンセル・順序・同名確認を表示なしで検証。"""
from unittest.mock import Mock, patch
from types import SimpleNamespace
import pytest

from book_manager.gui.author_dialogs import AuthorSelectionDialog, AuthorEditDialog, AuthorManagementDialog, state_store
from book_manager.models.author import Author
from book_manager.config.window_state_store import WindowStateStore

MODULE='book_manager.gui.author_dialogs'


def selection():
    d=AuthorSelectionDialog.__new__(AuthorSelectionDialog)
    d.window=Mock();d._service=Mock();d._service.get.return_value=Author('著者',id=1)
    d._selected_ids=[1,2];d._authors={1:Author('同名',id=1),2:Author('同名',id=2)}
    d._candidates=Mock();d._selected=Mock();d._selected.get_children.return_value=();d.result=None
    return d


def test_apply_returns_ids_without_persisting_relations():
    d=selection();d._apply()
    assert d.result==(1,2)
    d._service.set_book_authors.assert_not_called();d.window.destroy.assert_called_once()


def test_cancel_default_does_not_change_input_list():
    d=selection();original=(1,2);d._selected_ids=list(original)
    d._candidates.selection.return_value=('3',);d._add()
    assert original==(1,2) and d.result is None
    d._service.set_book_authors.assert_not_called()


def test_duplicate_selected_author_not_added_twice():
    d=selection();d._candidates.selection.return_value=('1',);d._add()
    assert d._selected_ids==[1,2]


def test_order_move_and_remove():
    d=selection();d._selected.selection.return_value=('2',);d._move(-1)
    assert d._selected_ids==[2,1]
    d._remove();assert d._selected_ids==[1]


def test_move_beyond_boundary_preserves_order():
    d=selection();d._selected.selection.return_value=('1',);d._move(-1)
    assert d._selected_ids==[1,2]


def test_same_name_ids_render_separately():
    d=selection();d._render_selected()
    assert [c.kwargs['iid'] for c in d._selected.insert.call_args_list]==['1','2']
    assert [c.kwargs['values'][1] for c in d._selected.insert.call_args_list]==['同名','同名']


def test_deleted_author_cannot_be_applied():
    d=selection();d._service.get.return_value=None
    with patch(f'{MODULE}.messagebox.showwarning') as warning:d._apply()
    assert d.result is None;d.window.destroy.assert_not_called();warning.assert_called_once()


def editor():
    d=AuthorEditDialog.__new__(AuthorEditDialog)
    d.window=Mock();d._service=Mock();d._author=None;d.result=None
    d._name=Mock();d._name.get.return_value='山田太郎'
    d._aliases=Mock();d._aliases.get.return_value='山田 太郎\n\n山田,太郎'
    d._note=Mock();d._note.get.return_value='経済学'
    return d


def test_new_author_homonym_requires_confirmation_and_can_cancel():
    d=editor();d._service.search.return_value=[SimpleNamespace(match_kind='exact')]
    with patch(f'{MODULE}.messagebox.askyesno',return_value=False):d._save()
    d._service.create.assert_not_called();d.window.destroy.assert_not_called();assert d.result is None


def test_new_author_homonym_can_be_registered_as_separate_person():
    d=editor();d._service.search.return_value=[SimpleNamespace(match_kind='normalized')]
    with patch(f'{MODULE}.messagebox.askyesno',return_value=True):d._save()
    d._service.create.assert_called_once_with(name='山田太郎',aliases=('山田 太郎','山田,太郎'),disambiguation_note='経済学')
    d.window.destroy.assert_called_once()


def test_editor_validation_failure_keeps_dialog_open():
    d=editor();d._service.search.return_value=[];d._service.create.side_effect=ValueError('invalid')
    with patch(f'{MODULE}.messagebox.showerror'),patch(f'{MODULE}.logger'):d._save()
    d.window.destroy.assert_not_called();assert d.result is None


def test_edit_calls_same_author_id():
    d=editor();d._author=Author('山田太郎',id=17)
    d._save();assert d._service.update.call_args.kwargs['author_id']==17
    d._service.create.assert_not_called()


def test_linked_author_cannot_be_deleted():
    d=AuthorManagementDialog.__new__(AuthorManagementDialog)
    d.window=Mock();d._service=Mock();d._selected=Mock(return_value=Author('同名',id=1))
    d._service.linked_book_ids.return_value=(5,)
    with patch(f'{MODULE}.messagebox.showwarning'):d._delete()
    d._service.delete.assert_not_called()


def test_each_dialog_has_independent_persistent_store(tmp_path):
    base=WindowStateStore(tmp_path/'window_state.json')
    assert state_store(base,'author_edit').path==tmp_path/'author_edit_window_state.json'
    assert state_store(base,'author_management').path!=state_store(base,'author_selection').path
    assert state_store(None,'author_edit') is None
