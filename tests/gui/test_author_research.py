"""著者情報の検索・コピー・メモ追記を外部通信なしで検証する。"""
from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock, patch
import tkinter as tk
import pytest

from book_manager.gui.author_dialogs import AuthorEditDialog
from book_manager.services.author_research import (
    amazon_author_search_url, research_author_name, validate_author_source_url,
    append_author_note, append_author_source, author_source_from_note,
)

MODULE = 'book_manager.gui.author_dialogs'
URL = 'https://www.amazon.co.jp/stores/author/B003UWWLW0/about'


@pytest.mark.parametrize('name', ['百田尚樹', ' 石黒 成治 ', 'A & B/#? + 日本語'])
def test_search_encodes_only_author_name(name):
    parts = urlsplit(amazon_author_search_url(name))
    assert parts.scheme == 'https' and parts.hostname == 'www.amazon.co.jp'
    assert parts.fragment == ''
    assert parse_qs(parts.query) == {'i': ['stripbooks'], 'k': [name.strip()]}
    assert research_author_name(name) == name.strip()


@pytest.mark.parametrize('name', ['', '   ', 'A\nB', 'x'*201])
def test_invalid_name_rejected(name):
    with pytest.raises(ValueError):amazon_author_search_url(name)


@pytest.mark.parametrize('url', ['', 'javascript:alert(1)', 'file:///tmp/test', 'https://', 'https://user:pass@example.com/', 'https://example.com/\ntext', 'https://example.com:bad/', 'https://exa mple.com/'])
def test_invalid_source_urls_rejected(url):
    with pytest.raises(ValueError):validate_author_source_url(url)


def test_note_append_preserves_current_and_limits_size():
    assert append_author_note('既存メモ\n', '新規\r\n本文') == '既存メモ\n新規\n本文'
    assert append_author_note('既存', ' ') == '既存'
    assert len(append_author_note('a'*1998, 'b')) == 2000
    with pytest.raises(ValueError):append_author_note('a'*1999, 'b')
    with pytest.raises(ValueError):append_author_note('既存', 'bad\x00text')


def test_source_url_is_preserved_without_duplicate_and_reloaded():
    note = append_author_source('作家', URL)
    assert note == '作家\n情報元URL: ' + URL
    assert append_author_source(note, URL) == note
    second = append_author_source(note, 'https://example.com/author')
    assert author_source_from_note(second) == 'https://example.com/author'
    assert author_source_from_note(note + '\n情報元URL: javascript:test') == URL
    assert author_source_from_note('一般のメモのみ') == ''


def editor():
    d = AuthorEditDialog.__new__(AuthorEditDialog)
    d.window = Mock()
    d._service = Mock()
    d._author = None
    d.result = None
    d._name = Mock();d._name.get.return_value = ' 百田尚樹 '
    d._aliases = Mock();d._aliases.get.return_value = ''
    d._source_url = Mock();d._source_url.get.return_value = URL
    d._note = Mock();d._note.get.return_value = '既存メモ'
    d._research_status = Mock()
    return d


def test_copy_uses_edited_name_without_saving():
    d = editor();d._copy_name()
    d.window.clipboard_clear.assert_called_once()
    d.window.clipboard_append.assert_called_once_with('百田尚樹')
    d._service.create.assert_not_called();d._service.update.assert_not_called()


@pytest.mark.parametrize('method', ['_search_amazon', '_open_source'])
def test_browser_is_opened_only_on_explicit_action(method):
    d = editor()
    with patch(f'{MODULE}.webbrowser.open', return_value=True) as browser:
        getattr(d, method)()
        browser.assert_called_once()
        assert browser.call_args.kwargs == {'new': 2}
    d._service.create.assert_not_called();d._service.update.assert_not_called()


def test_browser_failure_keeps_dialog_and_note():
    d = editor()
    with patch(f'{MODULE}.webbrowser.open', return_value=False), patch(f'{MODULE}.messagebox.showerror') as error:
        d._open_source();error.assert_called_once()
    d.window.destroy.assert_not_called();d._note.delete.assert_not_called()


def test_clipboard_paste_appends_without_saving():
    d = editor();d.window.clipboard_get.return_value = '追記'
    d._paste_note()
    d._note.insert.assert_called_once_with('1.0', '既存メモ\n追記')
    d._service.create.assert_not_called();assert d.result is None


@pytest.mark.parametrize('failure', ['oversize', 'empty_clipboard'])
def test_failed_paste_preserves_note(failure):
    d = editor()
    if failure == 'oversize':d.window.clipboard_get.return_value = 'a'*2001
    else:d.window.clipboard_get.side_effect = tk.TclError('clipboard empty')
    with patch(f'{MODULE}.messagebox.showerror') as error:
        d._paste_note();error.assert_called_once()
    d._note.delete.assert_not_called();d.window.destroy.assert_not_called()


def test_source_is_added_to_note_on_save():
    d = editor();d._service.search.return_value = []
    d._save()
    assert d._service.create.call_args.kwargs['disambiguation_note'] == '既存メモ\n情報元URL: ' + URL
    d.window.destroy.assert_called_once()


def test_invalid_source_prevents_save_and_keeps_input():
    d = editor();d._source_url.get.return_value = 'file:///tmp/a'
    with patch(f'{MODULE}.messagebox.showerror') as error:
        d._save();error.assert_called_once()
    d._service.create.assert_not_called();d.window.destroy.assert_not_called()


def test_appending_url_only_changes_pending_note():
    d = editor();d._append_source()
    d._note.insert.assert_called_once_with('1.0', '既存メモ\n情報元URL: ' + URL)
    assert d.result is None
    d._service.create.assert_not_called();d._service.update.assert_not_called()
