"""ISBNなしの手動書影URL・非同期取得・取消・失敗保持。"""
from pathlib import Path
from unittest.mock import Mock,patch
import pytest
from PIL import Image
from book_manager.gui.cover_url_dialog import CoverUrlDialog
from book_manager.gui.book_manager_application import BookManagerApplication


def dialog():
    obj=CoverUrlDialog.__new__(CoverUrlDialog)
    obj.window=Mock();obj._closed=False;obj._task=Mock();obj._task.busy=False
    obj._fetch=Mock();obj._url=Mock();obj._entry=Mock();obj._download=Mock()
    obj._remove=Mock();obj._apply_button=Mock();obj._preview=Mock();obj._status=Mock()
    obj._loaded=None;obj.result=None;obj._after_id=None
    return obj


@pytest.mark.parametrize('url',['','file:///tmp/cover.png','ftp://example.com/a','https:///missing'])
def test_invalid_url_does_not_start_request(url):
    obj=dialog();obj._url.get.return_value=url
    with patch('book_manager.gui.cover_url_dialog.messagebox.showerror'):obj._start()
    obj._task.start_operation.assert_not_called()


def test_successful_preview_can_be_applied(tmp_path):
    obj=dialog();path=tmp_path/'cover.png';Image.new('RGB',(900,1200)).save(path)
    obj._task.poll.return_value=(('https://example.com/a',path),None)
    with patch('book_manager.gui.cover_url_dialog.ImageTk.PhotoImage') as photo:obj._poll()
    assert photo.call_args.args[0].height<=320
    obj._apply()
    assert obj.result==('https://example.com/a',path)


def test_request_failure_does_not_offer_apply():
    obj=dialog();obj._task.poll.return_value=(None,OSError('failed'))
    with patch('book_manager.gui.cover_url_dialog.messagebox.showerror'):obj._poll()
    assert obj._loaded is None and obj.result is None


def test_closed_dialog_ignores_late_download():
    obj=dialog();obj._closed=True;obj._poll()
    obj._task.poll.assert_not_called()


def test_url_change_invalidates_previous_preview():
    obj=dialog();obj._loaded=('old',Path('old'));obj._invalidate()
    assert obj._loaded is None
    obj._apply_button.configure.assert_called_once_with(state='disabled')


@pytest.mark.parametrize('result',[None,('https://example.com/new',Path('new.png')),('',None)])
def test_parent_applies_only_confirmed_form_changes(result):
    app=BookManagerApplication.__new__(BookManagerApplication)
    app._root=Mock();app._service=Mock();app._metadata_form_snapshot=Mock(return_value=('same',))
    app._current_cover_image_url='old';app._current_cover_image_path='old-path'
    app._display_cover_image=Mock();app._clear_cover_state=Mock()
    app._service.create_stored_cover_image_path.return_value='cache/new'
    with patch('book_manager.gui.book_manager_application.CoverUrlDialog') as child:
        child.return_value.show.return_value=result;app._on_edit_cover_url()
    if result is None:
        assert app._current_cover_image_url=='old'
    elif not result[0]:app._clear_cover_state.assert_called_once_with()
    else:
        assert app._current_cover_image_url==result[0]
        assert app._current_cover_image_path=='cache/new'
    app._service.update_book.assert_not_called()


def test_parent_display_failure_keeps_old_url_and_path():
    app=BookManagerApplication.__new__(BookManagerApplication)
    app._root=Mock();app._service=Mock();app._metadata_form_snapshot=Mock(return_value=('same',))
    app._current_cover_image_url='old';app._current_cover_image_path='old-path'
    app._display_cover_image=Mock(side_effect=OSError('bad image'))
    with patch('book_manager.gui.book_manager_application.CoverUrlDialog') as child,patch('book_manager.gui.book_manager_application.messagebox.showerror'):
        child.return_value.show.return_value=('https://example.com/new',Path('bad'));app._on_edit_cover_url()
    assert app._current_cover_image_url=='old' and app._current_cover_image_path=='old-path'
