"""管理著者選択をフォームに保持し、書籍保存時だけ引き渡す。"""
from unittest.mock import Mock,patch
from types import SimpleNamespace

from book_manager.gui.book_manager_application import BookManagerApplication
from book_manager.models.book_item import BookItem

MODULE='book_manager.gui.book_manager_application'


def app():
    a=BookManagerApplication.__new__(BookManagerApplication)
    a._root=Mock();a._service=Mock();a._author_service=Mock();a._window_state_store=None
    a._selected_book_id=None;a._managed_author_ids=(1,2);a._managed_author_button=Mock()
    a._author_var=Mock();a._author_var.get.return_value='原著者名'
    a._title_entry=Mock();a._refresh_tag_options=Mock();a._load_all_books=Mock();a._clear_form=Mock()
    a._confirm_duplicate_candidates=Mock(return_value=True)
    values={name:None for name in ['isbn','reference_isbn','magazine_code','publisher','publication_format',
        'description','cover_image_url','cover_image_path','completion_month','reading_status','rating','notes']}
    values.update(title='本',author='原著者名',tags=(),is_favorite=False)
    a._get_form_values=Mock(return_value=values)
    return a


def test_selection_cancel_keeps_pending_ids_and_original_text():
    a=app()
    with patch(f'{MODULE}.AuthorSelectionDialog') as dialog:
        dialog.return_value.show.return_value=None;a._on_select_authors()
    assert a._managed_author_ids==(1,2)
    a._author_var.set.assert_not_called();a._service.add_book.assert_not_called();a._service.update_book.assert_not_called()


def test_selection_changes_only_pending_ids_and_caption():
    a=app()
    with patch(f'{MODULE}.AuthorSelectionDialog') as dialog:
        dialog.return_value.show.return_value=(2,1);a._on_select_authors()
    assert a._managed_author_ids==(2,1)
    a._author_var.set.assert_not_called();a._author_service.set_book_authors.assert_not_called()
    a._service.add_book.assert_not_called();a._service.update_book.assert_not_called()


def test_add_passes_author_ids_to_atomic_book_service():
    a=app();a._service.add_book.return_value=BookItem('本',id=10)
    with patch(f'{MODULE}.messagebox.showinfo'):a._on_add()
    assert a._service.add_book.call_args.kwargs['author_ids']==(1,2)
    a._author_service.set_book_authors.assert_not_called()


def test_update_passes_author_ids_to_atomic_book_service():
    a=app();a._selected_book_id=5;a._create_book_item_from_form=Mock(return_value=BookItem('本',id=5))
    a._service.update_book.return_value=True
    with patch(f'{MODULE}.messagebox.askyesno',return_value=True),patch(f'{MODULE}.messagebox.showinfo'):a._on_update()
    assert a._service.update_book.call_args.kwargs['author_ids']==(1,2)
    a._author_service.set_book_authors.assert_not_called()


def test_update_cancel_never_saves_associations():
    a=app();a._selected_book_id=5
    with patch(f'{MODULE}.messagebox.askyesno',return_value=False):a._on_update()
    a._service.update_book.assert_not_called();assert a._managed_author_ids==(1,2)


def test_save_failure_keeps_pending_selection():
    a=app();a._service.add_book.side_effect=ValueError('invalid')
    with patch(f'{MODULE}.messagebox.showerror'):a._on_add()
    a._clear_form.assert_not_called();assert a._managed_author_ids==(1,2)


def test_loading_book_uses_ids_not_author_text():
    a=app();a._author_service.get_book_authors.return_value=[SimpleNamespace(id=20),SimpleNamespace(id=10)]
    a._load_managed_authors(5)
    assert a._managed_author_ids==(20,10)
    a._author_var.set.assert_not_called()


def test_load_failure_omits_author_changes_to_preserve_saved_links():
    a=app();a._author_service.get_book_authors.side_effect=RuntimeError('read failed')
    with patch(f'{MODULE}.messagebox.showerror'),patch(f'{MODULE}.logger'):a._load_managed_authors(5)
    assert a._managed_author_ids is None
    assert a._managed_author_save_arguments()=={}


def test_confirmed_empty_selection_explicitly_clears_links_on_save():
    a=app();a._managed_author_ids=()
    assert a._managed_author_save_arguments()=={'author_ids':()}


def test_feature_absent_preserves_existing_book_service_call_contract():
    a=app();a._author_service=None
    assert a._managed_author_save_arguments()=={}
