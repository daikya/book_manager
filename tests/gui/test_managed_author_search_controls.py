"""管理著者の複数選択を検索条件として保持する。"""
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
from book_manager.gui.book_manager_application import BookManagerApplication


def application():
    app = BookManagerApplication.__new__(BookManagerApplication)
    app._root = Mock()
    app._search_managed_author_ids_value = (2,)
    app._search_managed_author_var = Mock()
    app._search_managed_author_mode_var = Mock()
    app._search_managed_author_mode_var.get.return_value = 'いずれか（OR）'
    app._author_service = Mock()
    app._author_service.list_authors.return_value = [
        SimpleNamespace(id=1, name='山田太郎', disambiguation_note='経済学'),
        SimpleNamespace(id=2, name='山田太郎', disambiguation_note='小説家'),
    ]
    app._service = Mock()
    return app


def test_refresh_keeps_identity_and_displays_multiple_ids():
    app = application()
    app._search_managed_author_ids_value = (1, 2)
    app._refresh_search_managed_authors()
    caption = app._search_managed_author_var.set.call_args.args[0]
    assert '2人' in caption and 'ID:1' in caption and 'ID:2' in caption
    assert app._search_managed_author_ids() == (1, 2)


def test_deleted_author_does_not_silently_remove_filter():
    app = application()
    app._author_service.list_authors.return_value = []
    app._refresh_search_managed_authors()
    assert app._search_managed_author_ids() == (2,)
    assert '削除された著者 [ID:2]' in app._search_managed_author_var.set.call_args.args[0]


def test_old_form_without_filter_is_compatible():
    app = BookManagerApplication.__new__(BookManagerApplication)
    assert app._search_managed_author_ids() == ()
    assert app._search_managed_author_mode() == 'any'


def set_empty_filters(app):
    for name in ('title', 'author', 'publisher', 'isbn', 'magazine_code'):
        variable = Mock()
        variable.get.return_value = ''
        setattr(app, '_search_' + name + '_var', variable)
    for name in ('reading_status', 'favorite', 'rating', 'tag'):
        variable = Mock()
        variable.get.return_value = 'すべて'
        setattr(app, '_search_' + name + '_var', variable)


@pytest.mark.parametrize('label,mode', [('いずれか（OR）', 'any'), ('全員（AND）', 'all')])
def test_selected_ids_passed_with_other_conditions(label, mode):
    app = application()
    set_empty_filters(app)
    app._search_managed_author_ids_value = (1, 2)
    app._search_managed_author_mode_var.get.return_value = label
    app._get_filtered_books()
    assert app._service.search_books.call_args.kwargs['managed_author_ids'] == (1, 2)
    assert app._service.search_books.call_args.kwargs['managed_author_mode'] == mode
    assert app._has_search_conditions()
    app._load_all_books = Mock()
    app._search_title_entry = Mock()
    app._on_clear_search()
    assert app._search_managed_author_ids() == ()
    app._search_managed_author_mode_var.set.assert_called_once_with('いずれか（OR）')
    app._load_all_books.assert_called_once_with()


def test_reload_after_edit_preserves_author_filter():
    app = application()
    set_empty_filters(app)
    app._get_sort_settings = Mock(return_value=('title', False))
    app._get_filtered_books = Mock(return_value=['filtered'])
    app._service.sort_books.return_value = ['sorted']
    app._display_books = Mock()
    app._load_all_books()
    app._display_books.assert_called_once_with(['sorted'], status_prefix='検索結果')
    app._service.get_sorted_books.assert_not_called()


@pytest.mark.parametrize('result', [None, (), (1, 2)])
def test_dialog_cancel_apply_and_empty_selection(result):
    app = application()
    app._on_search = Mock()
    with patch('book_manager.gui.book_manager_application.AuthorSelectionDialog') as dialog:
        dialog.return_value.show.return_value = result
        app._on_select_search_authors()
        assert dialog.call_args.kwargs['selected_ids'] == (2,)
        assert dialog.call_args.kwargs['search_mode'] is True
    assert app._search_managed_author_ids() == ((2,) if result is None else result)
    assert app._on_search.call_count == (0 if result is None else 1)
    app._service.update_book.assert_not_called()
    app._author_service.set_book_authors.assert_not_called()


def test_author_only_clear_retains_other_conditions_and_mode():
    app = application()
    set_empty_filters(app)
    app._search_title_var.get.return_value = '保持する書名'
    app._on_search = Mock()
    app._on_clear_search_authors()
    assert app._search_managed_author_ids() == ()
    app._search_title_var.set.assert_not_called()
    app._search_managed_author_mode_var.set.assert_not_called()
    app._on_search.assert_called_once_with()


def test_failed_dialog_keeps_selection():
    app = application()
    app._on_search = Mock()
    with patch('book_manager.gui.book_manager_application.AuthorSelectionDialog', side_effect=RuntimeError('failed')), patch('book_manager.gui.book_manager_application.messagebox') as messages:
        app._on_select_search_authors()
        messages.showerror.assert_called_once()
    assert app._search_managed_author_ids() == (2,)
    app._on_search.assert_not_called()
