"""整理画面の選択取消・確認取消・確定を検証する。"""
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
from book_manager.gui.author_link_review_dialog import AuthorLinkReviewDialog


@pytest.fixture
def dialog():
    obj = AuthorLinkReviewDialog.__new__(AuthorLinkReviewDialog)
    obj.window = Mock()
    obj._service = Mock()
    obj._get_book = Mock()
    obj._base_store = None
    obj._tree = Mock()
    obj._tree.selection.return_value = ('10',)
    obj._books = {10:dict(id=10,title='本',author='山田 太郎')}
    obj._service.get.return_value = SimpleNamespace(id=2,name='山田太郎',disambiguation_note='小説家')
    obj._refresh = Mock()
    return obj


@pytest.mark.parametrize('result', [None, ()])
def test_selection_cancel_does_not_save(dialog,result):
    with patch('book_manager.gui.author_link_review_dialog.AuthorSelectionDialog') as choose:
        choose.return_value.show.return_value = result
        dialog._choose()
        assert choose.call_args.kwargs['query'] == '山田 太郎'
    dialog._service.link_unassigned_book.assert_not_called()


def test_confirmation_cancel_does_not_save(dialog):
    with patch('book_manager.gui.author_link_review_dialog.AuthorSelectionDialog') as choose, patch('book_manager.gui.author_link_review_dialog.messagebox.askyesno',return_value=False):
        choose.return_value.show.return_value = (2,)
        dialog._choose()
    dialog._service.link_unassigned_book.assert_not_called()


def test_confirmation_saves_snapshot_and_refreshes(dialog):
    with patch('book_manager.gui.author_link_review_dialog.AuthorSelectionDialog') as choose, patch('book_manager.gui.author_link_review_dialog.messagebox.askyesno',return_value=True):
        choose.return_value.show.return_value = (2,)
        dialog._choose()
    dialog._service.link_unassigned_book.assert_called_once_with(10,(2,),expected_title='本',expected_author='山田 太郎')
    dialog._refresh.assert_called_once_with()


def test_stale_selection_displays_error_without_refresh(dialog):
    dialog._service.link_unassigned_book.side_effect = ValueError('変更されました')
    with patch('book_manager.gui.author_link_review_dialog.AuthorSelectionDialog') as choose, patch('book_manager.gui.author_link_review_dialog.messagebox.askyesno',return_value=True), patch('book_manager.gui.author_link_review_dialog.show_error') as error:
        choose.return_value.show.return_value = (2,)
        dialog._choose()
        error.assert_called_once()
    dialog._refresh.assert_not_called()


def test_main_form_cancel_keeps_unsaved_notes():
    from book_manager.gui.book_manager_application import BookManagerApplication
    app = BookManagerApplication.__new__(BookManagerApplication)
    app._root = Mock()
    app._author_service = Mock()
    app._selected_book_id = None
    for name in ('title','author','publisher','isbn','reference_isbn','magazine_code','tags','publication_format','completion_month'):
        var = Mock();var.get.return_value = ''
        setattr(app, '_' + name + '_var', var)
    app._description_text = Mock();app._description_text.get.return_value = ''
    app._notes_text = Mock();app._notes_text.get.return_value = '未保存の備考'
    app._clear_form = Mock()
    with patch('book_manager.gui.book_manager_application.messagebox.askyesno', return_value=False):
        app._on_review_author_links()
    app._clear_form.assert_not_called()
