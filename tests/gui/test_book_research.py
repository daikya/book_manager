"""書籍入力支援は検索・コピーだけを行い、入力やDBを変更しない。"""
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit
import tkinter as tk
import pytest

from book_manager.services.book_research import (
    amazon_book_search_url, book_search_query, research_isbn,
)
from book_manager.gui.book_research_dialog import BookResearchDialog
from book_manager.gui.book_manager_application import BookManagerApplication

MODULE = 'book_manager.gui.book_research_dialog'
ISBN = '9784087754537'


def test_isbn_takes_priority_over_title_and_author():
    assert book_search_query(isbn='978-4-08-775453-7', title='別の題名', author='別の著者') == ISBN
    assert research_isbn('4-08-775453-7') == '4087754537'


@pytest.mark.parametrize('title,author', [('A&B / #?日本語', '甲 乙'), ('本', '')])
def test_title_author_are_url_encoded(title, author):
    url = urlsplit(amazon_book_search_url(title=title, author=author))
    assert url.scheme == 'https' and url.netloc == 'www.amazon.co.jp'
    assert not url.fragment
    assert parse_qs(url.query) == {'i': ['stripbooks'], 'k': [' '.join(x for x in (title, author) if x)]}


@pytest.mark.parametrize('values', [dict(), dict(isbn='123', title='題名'), dict(isbn='9784087754538'), dict(title='A\nB'), dict(title='本', author='A\x00B')])
def test_bad_input_is_not_silently_used_as_search(values):
    with pytest.raises(ValueError):book_search_query(**values)


def dialog():
    d = BookResearchDialog.__new__(BookResearchDialog)
    d.window = Mock();d._status = Mock()
    d._values = dict(isbn=ISBN, title='題名', author='著者')
    return d


@pytest.mark.parametrize('target,expected', [('isbn', ISBN), ('title', '題名'), ('query', ISBN)])
def test_copy_only_changes_clipboard(target, expected):
    d = dialog();before = d._values.copy();d._copy(target)
    d.window.clipboard_append.assert_called_once_with(expected)
    assert d._values == before


def test_amazon_search_does_not_touch_clipboard_or_form():
    d = dialog();before = d._values.copy()
    with patch(f'{MODULE}.webbrowser.open', return_value=True) as browser:
        d._search();browser.assert_called_once_with(amazon_book_search_url(**before), new=2)
    d.window.clipboard_clear.assert_not_called();assert d._values == before


def test_browser_failure_is_reported():
    d = dialog()
    with patch(f'{MODULE}.webbrowser.open', return_value=False), patch(f'{MODULE}.messagebox.showerror') as error:
        d._search();error.assert_called_once()
    d.window.destroy.assert_not_called()


def test_invalid_isbn_preserves_clipboard():
    d = dialog();d._values['isbn'] = '123'
    with patch(f'{MODULE}.messagebox.showerror') as error:
        d._copy('isbn');error.assert_called_once()
    d.window.clipboard_clear.assert_not_called()


def test_clipboard_error_is_reported():
    d = dialog();d.window.clipboard_clear.side_effect = tk.TclError('clipboard')
    with patch(f'{MODULE}.messagebox.showerror') as error:
        d._copy('title');error.assert_called_once()


def test_dialog_uses_independent_geometry_store():
    with patch(f'{MODULE}.tk'), patch(f'{MODULE}.ttk'), patch(f'{MODULE}.restore_dialog_window') as restore:
        store = Mock();store.path = __import__('pathlib').Path('/tmp/window_state.json');d = BookResearchDialog(Mock(), title='本', state_store=store)
        assert restore.call_args.args[2] is store
        assert restore.call_args.kwargs['default_size'] == (680, 440)


def test_main_passes_edited_form_without_reference_isbn():
    app = BookManagerApplication.__new__(BookManagerApplication);app._root = Mock()
    for name, value in [('isbn', ''), ('reference_isbn', ISBN), ('title', '編集中の題名'), ('author', '編集中の著者')]:
        var = Mock();var.get.return_value = value;setattr(app, f'_{name}_var', var)
    app._metadata_form_snapshot = Mock(return_value=())
    app._publisher_var = Mock();app._publisher_var.get.return_value = ''
    app._publication_format_var = Mock();app._publication_format_var.get.return_value = ''
    app._description_text = Mock();app._description_text.get.return_value = ''
    with patch('book_manager.gui.book_manager_application.BookResearchDialog') as cls:
        cls.return_value.show.return_value = None
        app._on_book_research()
        assert cls.call_args.kwargs['isbn'] == ''
        assert cls.call_args.kwargs['title'] == '編集中の題名'
        assert cls.call_args.kwargs['author'] == '編集中の著者'
    app._reference_isbn_var.get.assert_not_called()
