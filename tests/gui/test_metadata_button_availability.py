"""設定変更後と候補検索終了後にキーの有無を反映する。"""
from unittest.mock import Mock, patch
import pytest
from book_manager.gui.book_manager_application import BookManagerApplication
from book_manager.services.application_settings_service import ApplicationSettingsError


def app():
    a = BookManagerApplication.__new__(BookManagerApplication)
    a._root = Mock();a._application_settings_service = Mock()
    a._candidate_search_button = Mock();a._fetch_metadata_button = Mock()
    a._google_books_hint = Mock();a._on_google_books_api_key_changed = Mock()
    return a


@pytest.mark.parametrize('configured,busy,state', [(False, False, 'disabled'), (True, False, 'normal'), (True, True, 'normal'), (False, True, 'disabled')])
def test_availability_and_openbd_button(configured, busy, state):
    a = app();a._candidate_search_task = Mock(busy=busy)
    a._application_settings_service.get_google_books_api_key.return_value = "key" if configured else None
    a._refresh_google_books_availability()
    a._candidate_search_button.configure.assert_called_with(state=state)
    a._on_google_books_api_key_changed.assert_called_once_with('key' if configured else None)
    a._fetch_metadata_button.configure.assert_not_called()
    assert bool(a._google_books_hint.configure.call_args.kwargs['text']) is not configured


def test_settings_read_failure_disables_candidates():
    a = app();a._application_settings_service.get_google_books_api_key.side_effect = ApplicationSettingsError('read')
    a._refresh_google_books_availability()
    a._candidate_search_button.configure.assert_called_with(state='disabled')


def test_unconfigured_action_cannot_open_candidate_dialog():
    a = app();a._google_books_configured = False
    with patch('book_manager.gui.book_manager_application.BookCandidateSearchDialog') as dialog, patch('book_manager.gui.book_manager_application.messagebox.showinfo'):
        a._on_search_book_candidates();dialog.assert_not_called()


def test_save_and_delete_update_button_immediately():
    a = app();a._application_settings_service.save_google_books_api_key.return_value = 'key'
    key = Mock();status = Mock();dialog = Mock()
    with patch('book_manager.gui.book_manager_application.messagebox') as msg:
        a._save_google_books_api_key(key, status, dialog)
        a._candidate_search_button.configure.assert_called_with(state='normal')
        a._on_google_books_api_key_changed.assert_called_with('key')
        a._application_settings_service.get_snapshot.return_value.google_books_api_key_is_configured = True
        msg.askyesno.return_value = True
        a._delete_google_books_api_key(key, status, dialog)
        a._candidate_search_button.configure.assert_called_with(state='disabled')
        a._on_google_books_api_key_changed.assert_called_with(None)
        a._fetch_metadata_button.configure.assert_not_called()
