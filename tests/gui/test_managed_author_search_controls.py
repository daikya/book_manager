"""管理著者の検索選択をIDで保持する。"""
from types import SimpleNamespace
from unittest.mock import Mock
from book_manager.gui.book_manager_application import BookManagerApplication


def application():
    app = BookManagerApplication.__new__(BookManagerApplication)
    app._search_managed_author_var = Mock()
    app._search_managed_author_var.get.return_value = '旧表示'
    app._search_managed_author_options = {'旧表示': 2}
    app._search_managed_author_combobox = Mock()
    app._author_service = Mock()
    app._author_service.list_authors.return_value = [
        SimpleNamespace(id=1, name='山田太郎', disambiguation_note='経済学'),
        SimpleNamespace(id=2, name='山田太郎', disambiguation_note='小説家'),
    ]
    return app


def test_refresh_keeps_identity_and_distinguishes_homonyms():
    app = application()
    app._refresh_search_managed_authors()
    values = app._search_managed_author_combobox.configure.call_args.kwargs['values']
    assert len(values) == 3
    assert 'ID:1' in values[1] and '経済学' in values[1]
    assert 'ID:2' in values[2] and '小説家' in values[2]
    app._search_managed_author_var.set.assert_called_once_with(values[2])


def test_deleted_author_does_not_silently_remove_filter():
    app = application()
    app._author_service.list_authors.return_value = []
    app._refresh_search_managed_authors()
    assert app._search_managed_author_options == {'削除された著者 [ID:2]': 2}


def test_old_form_without_filter_is_compatible():
    app = BookManagerApplication.__new__(BookManagerApplication)
    assert app._search_managed_author_id() is None


def test_selected_id_is_passed_with_other_conditions():
    app = application()
    for name in ('title', 'author', 'publisher', 'isbn', 'magazine_code'):
        variable = Mock()
        variable.get.return_value = ''
        setattr(app, '_search_' + name + '_var', variable)
    for name in ('reading_status', 'favorite', 'rating', 'tag'):
        variable = Mock()
        variable.get.return_value = 'すべて'
        setattr(app, '_search_' + name + '_var', variable)
    app._service = Mock()
    app._get_filtered_books()
    assert app._service.search_books.call_args.kwargs['managed_author_id'] == 2
    assert app._has_search_conditions()
    app._load_all_books = Mock()
    app._search_title_entry = Mock()
    app._on_clear_search()
    app._search_managed_author_var.set.assert_called_once_with('すべて')
    app._load_all_books.assert_called_once_with()


def test_reload_after_edit_preserves_author_filter():
    app = application()
    app._get_sort_settings = Mock(return_value=('title', False))
    app._get_filtered_books = Mock(return_value=['filtered'])
    app._service = Mock()
    app._service.sort_books.return_value = ['sorted']
    app._display_books = Mock()
    app._load_all_books()
    app._get_filtered_books.assert_called_once_with()
    app._display_books.assert_called_once_with(['sorted'], status_prefix='検索結果')
    app._service.get_sorted_books.assert_not_called()
