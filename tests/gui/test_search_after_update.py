"""更新後の再検索を実SQLite・BookServiceとGUIハンドラーで検証する。"""
from dataclasses import replace
from unittest.mock import Mock, patch

import pytest

from book_manager.database.initializer import initialize_database
from book_manager.repositories.book_repository import BookRepository
from book_manager.services.book_service import BookService
from book_manager.gui.book_manager_application import BookManagerApplication


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def application(tmp_path):
    database = tmp_path / 'books.db'
    initialize_database(database)
    app = BookManagerApplication.__new__(BookManagerApplication)
    app._service = BookService(BookRepository(database))
    app._root = Mock()
    for field in ('title', 'author', 'publisher', 'isbn', 'magazine_code'):
        setattr(app, '_search_' + field + '_var', Value(''))
    for field in ('reading_status', 'favorite', 'rating', 'tag'):
        setattr(app, '_search_' + field + '_var', Value('すべて'))
    app._get_sort_settings = Mock(return_value=('title', False))
    app._display_books = Mock()
    app._clear_form = Mock()
    app._title_entry = Mock()
    app._refresh_tag_options = Mock()
    app._confirm_duplicate_candidates = Mock(return_value=True)
    app._get_form_values = Mock(return_value={'title': '対象'})
    return app


@pytest.mark.parametrize('field,query,initial,change', [
    ('reading_status', '読書中', {'reading_status': 'reading'}, {'reading_status': 'completed'}),
    ('title', '対象', {}, {'title': '別の本'}),
    ('author', '著者A', {'author': '著者A'}, {'author': '著者B'}),
    ('publisher', '出版社A', {'publisher': '出版社A'}, {'publisher': '出版社B'}),
    ('isbn', '9784101010014', {'isbn': '9784101010014'}, {'isbn': None}),
    ('magazine_code', '17651-07', {'magazine_code': '17651-07'}, {'magazine_code': '17651-08'}),
    ('favorite', 'お気に入りのみ', {'is_favorite': True}, {'is_favorite': False}),
    ('rating', '★3以上', {'rating': 5}, {'rating': 1}),
    ('tag', '小説', {'tags': ('小説',)}, {'tags': ()}),
])
def test_update_removes_book_that_no_longer_matches(tmp_path, field, query, initial, change):
    app = application(tmp_path)
    book = app._service.add_book(title='対象', **initial)
    # 別の本が全件一覧へ紛れ込まないことも確認する。
    app._service.add_book(title='無関係')
    getattr(app, '_search_' + field + '_var').set(query)
    assert [b.id for b in app._get_filtered_books()] == [book.id]
    app._selected_book_id = book.id
    app._create_book_item_from_form = Mock(return_value=replace(book, **change))
    with patch('book_manager.gui.book_manager_application.messagebox') as messages:
        messages.askyesno.return_value = True
        app._on_update()
        messages.showerror.assert_not_called()
        messages.showinfo.assert_called_once()
    assert getattr(app, '_search_' + field + '_var').get() == query
    app._display_books.assert_called_once_with([], status_prefix='検索結果')
    app._clear_form.assert_called_once()
    field_name, expected = next(iter(change.items()))
    if field_name == 'magazine_code':
        expected = expected.replace('-', '')
    assert getattr(app._service.get_book(book.id), field_name) == expected


def test_update_retains_other_matching_books_and_sort_order(tmp_path):
    app = application(tmp_path)
    first = app._service.add_book(title='B', publisher='同じ出版社', reading_status='reading')
    second = app._service.add_book(title='A', publisher='同じ出版社', reading_status='reading')
    app._service.add_book(title='他社', publisher='別の出版社', reading_status='reading')
    app._search_publisher_var.set('同じ出版社')
    app._search_reading_status_var.set('読書中')
    app._selected_book_id = first.id
    app._create_book_item_from_form = Mock(return_value=replace(first, notes='更新'))
    with patch('book_manager.gui.book_manager_application.messagebox') as messages:
        messages.askyesno.return_value = True
        app._on_update()
        messages.showerror.assert_not_called()
    displayed = app._display_books.call_args.args[0]
    assert [b.id for b in displayed] == [second.id, first.id]
    assert displayed[1].notes == '更新'
    assert app._search_publisher_var.get() == '同じ出版社'
    assert app._search_reading_status_var.get() == '読書中'


def test_unfiltered_refresh_still_displays_all_books(tmp_path):
    app = application(tmp_path)
    book = app._service.add_book(title='対象')
    app._load_all_books()
    assert [b.id for b in app._display_books.call_args.args[0]] == [book.id]
    assert app._display_books.call_args.kwargs == {'status_prefix': '全'}
