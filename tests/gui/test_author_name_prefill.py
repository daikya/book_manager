"""書籍の原著者名を新規登録へ引き継ぎ、検索語や既存名と混同しない。"""
from unittest.mock import Mock,patch
import pytest
from book_manager.gui.author_dialogs import AuthorEditDialog,AuthorManagementDialog,AuthorSelectionDialog
from book_manager.models.author import Author

MODULE='book_manager.gui.author_dialogs'


@pytest.mark.parametrize('original',['石黒 成治','木原 浩勝','甲,乙／丙',''])
def test_selection_passes_original_not_edited_search(original):
    obj=AuthorSelectionDialog.__new__(AuthorSelectionDialog)
    obj.window=Mock();obj._service=Mock();obj._get_book=Mock();obj._base_store=None
    obj._initial_name=original
    obj._query=Mock();obj._query.get.return_value='変更した検索語'
    obj._refresh=Mock()
    with patch(f'{MODULE}.AuthorManagementDialog') as management:
        obj._manage()
        assert management.call_args.kwargs['initial_name']==original
    obj._service.create.assert_not_called()


def test_management_passes_prefill_only_for_new_author():
    obj=AuthorManagementDialog.__new__(AuthorManagementDialog)
    obj.window=Mock();obj._service=Mock();obj._base_store=None
    obj._initial_name='書籍の 原著者名'
    with patch(f'{MODULE}.AuthorEditDialog') as editor:
        editor.return_value.show.return_value=None
        obj._new()
        assert editor.call_args.kwargs['initial_name']=='書籍の 原著者名'
        author=Author('既存の名前',id=5)
        obj._open_editor(author)
        assert editor.call_args.kwargs['author']==author
        assert editor.call_args.kwargs['initial_name']==''
    obj._service.create.assert_not_called()


@pytest.mark.parametrize('author,initial,expected',[
    (None,'石黒 成治','石黒 成治'),
    (None,'甲,乙／丙','甲,乙／丙'),
    (None,'',''),
    (Author('編集対象',id=5),'書籍の名前','編集対象'),
])
def test_editor_initial_value_can_be_reviewed_before_save(author,initial,expected):
    with patch(f'{MODULE}.tk') as tk,patch(f'{MODULE}.ttk'),patch(f'{MODULE}.restore_dialog_window'):
        service=Mock()
        dialog=AuthorEditDialog(Mock(),service,author=author,initial_name=initial)
        assert tk.StringVar.call_args.args[1]==expected
        assert dialog.result is None
        service.create.assert_not_called();service.update.assert_not_called()
