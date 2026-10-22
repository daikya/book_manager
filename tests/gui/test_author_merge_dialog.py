"""統合の確認取消・エラーと比較表示。"""
from unittest.mock import Mock,patch
from types import SimpleNamespace
from book_manager.gui.author_merge_dialog import AuthorMergeDialog,describe_plan
from book_manager.models.author import Author
from book_manager.models.author_merge import AuthorMergePlan,AuthorMergeBook


def plan():
    return AuthorMergePlan(Author('同名',id=1,disambiguation_note='元'),
        Author('同名',id=2,disambiguation_note='先'),('旧名',),
        (AuthorMergeBook(3,'本','原表記',(1,2),(2,)),))


def dialog():
    obj=AuthorMergeDialog.__new__(AuthorMergeDialog)
    obj._plan=plan();obj.window=Mock();obj._service=Mock();obj._note=Mock()
    obj._note.get.return_value='編集したメモ';obj._save_button=Mock();obj.result=None
    return obj


def test_comparison_shows_identity_notes_and_link_order():
    text=describe_plan(plan())
    for value in ('ID:1','ID:2','統合元（削除）','統合先（保持）','原表記','(1, 2) → (2,)','旧名'):
        assert value in text


def test_cancel_final_confirmation_does_not_write():
    obj=dialog()
    with patch('book_manager.gui.author_merge_dialog.messagebox.askyesno',return_value=False):obj._save()
    obj._service.merge.assert_not_called();obj.window.destroy.assert_not_called()


def test_confirm_passes_reviewed_plan_and_edited_note():
    obj=dialog();expected=obj._plan
    with patch('book_manager.gui.author_merge_dialog.messagebox.askyesno',return_value=True):obj._save()
    obj._service.merge.assert_called_once_with(expected,disambiguation_note='編集したメモ')
    obj.window.destroy.assert_called_once_with()


def test_stale_plan_requires_new_preview():
    obj=dialog();obj._service.merge.side_effect=ValueError('変更')
    with patch('book_manager.gui.author_merge_dialog.messagebox.askyesno',return_value=True),patch('book_manager.gui.author_merge_dialog.show_error') as error:obj._save();error.assert_called_once()
    assert obj._plan is None
    obj._save_button.configure.assert_called_once_with(state='disabled')
    obj.window.destroy.assert_not_called()


def test_no_preview_cannot_merge():
    obj=dialog();obj._plan=None;obj._save()
    obj._service.merge.assert_not_called()


def search_dialog():
    obj=dialog()
    obj._source=Author('山田 太郎',id=1)
    obj._query=Mock();obj._query.get.return_value='山田 太郎'
    obj._target_tree=Mock();obj._target_tree.get_children.return_value=()
    obj._target_count=Mock();obj._details=Mock()
    obj._service.list_authors.return_value=[
        obj._source,Author('山田太郎',id=2,disambiguation_note='経済学'),
        Author('筆名',id=3,aliases=('山田 太郎',),disambiguation_note='小説家'),
        Author('無関係',id=4,disambiguation_note='別分野'),
    ]
    return obj


def test_search_matches_spaces_aliases_and_excludes_source():
    obj=search_dialog();obj._refresh_targets()
    inserted=[call.kwargs for call in obj._target_tree.insert.call_args_list]
    assert {row['iid'] for row in inserted}=={'2','3'}
    assert any('経済学' in row['values'] for row in inserted)
    assert any('小説家' in row['values'] for row in inserted)
    assert obj._plan is None
    obj._save_button.configure.assert_called_with(state='disabled')


def test_empty_search_shows_all_other_people():
    obj=search_dialog();obj._query.get.return_value='';obj._refresh_targets()
    assert {call.kwargs['iid'] for call in obj._target_tree.insert.call_args_list}=={'2','3','4'}


def test_note_search_and_zero_results_clear_old_plan():
    obj=search_dialog();obj._query.get.return_value='別分野';obj._refresh_targets()
    assert obj._target_tree.insert.call_args.kwargs['iid']=='4'
    obj._target_tree.insert.reset_mock();obj._query.get.return_value='不存在';obj._refresh_targets()
    obj._target_tree.insert.assert_not_called()
    assert obj._plan is None
    obj._target_count.set.assert_called_with('候補：0人（統合元は除外）')


def test_select_uses_id_and_loads_comparison():
    obj=search_dialog();obj._target_tree.selection.return_value=('2',)
    obj._service.preview_merge.return_value=plan();obj._preview()
    obj._service.preview_merge.assert_called_once_with(1,2)
    assert obj._plan==plan()
    obj._save_button.configure.assert_called_with(state='normal')


def test_no_selection_clears_comparison_and_cannot_save():
    obj=search_dialog();obj._target_tree.selection.return_value=();obj._preview()
    assert obj._plan is None
    obj._service.preview_merge.assert_not_called()


def test_repeated_selection_event_preserves_edited_note():
    obj=search_dialog();obj._target_tree.selection.return_value=('2',)
    obj._on_target_selected()
    obj._note.delete.assert_not_called()
    obj._service.preview_merge.assert_not_called()
