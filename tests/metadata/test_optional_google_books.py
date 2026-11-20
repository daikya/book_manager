"""キーなしではGoogleへ通信せずopenBDだけでISBN情報を取得する。"""
from unittest.mock import Mock
import pytest
from book_manager.metadata.google_books_client import GoogleBooksClient
from book_manager.metadata.book_metadata_service import BookMetadataService
from book_manager.metadata.exceptions import BookMetadataConfigurationError
from book_manager.models.fetched_book_data import FetchedBookData

ISBN = '9784087754537'


@pytest.mark.parametrize('key', [None, '', '   '])
def test_no_key_skips_google_and_keeps_openbd(key):
    session = Mock();google = GoogleBooksClient(session, api_key=key)
    openbd = Mock();openbd.fetch_by_isbn.return_value = FetchedBookData(isbn=ISBN, title='openBDの書籍')
    service = BookMetadataService([google, openbd], search_client=google)
    assert service.fetch_by_isbn(ISBN).title == 'openBDの書籍'
    openbd.fetch_by_isbn.assert_called_once_with(ISBN)
    with pytest.raises(BookMetadataConfigurationError):service.search_candidates(title='題名')
    session.get.assert_not_called()


def test_key_changes_take_effect_without_recreating_service():
    session = Mock();google = GoogleBooksClient(session)
    openbd = Mock();openbd.fetch_by_isbn.return_value = None
    service = BookMetadataService([google, openbd], search_client=google)
    with pytest.raises(BookMetadataConfigurationError):service.search_candidates(title='題名')
    google.set_api_key('key')
    with pytest.MonkeyPatch.context() as m:
        search = Mock(return_value=[]);m.setattr(google, 'search_candidates', search)
        assert service.search_candidates(title='題名') == [];search.assert_called_once()
    google.set_api_key(None)
    with pytest.raises(BookMetadataConfigurationError):service.search_candidates(title='題名')
    session.get.assert_not_called()
