"""ファイル選択・非同期プレビューと明示反映時だけの保存を検証する。"""
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from PIL import Image
from book_manager.gui.cover_url_dialog import CoverUrlDialog
from book_manager.gui.book_manager_application import BookManagerApplication
from book_manager.services.local_cover_image import PreparedCoverImage
from test_cover_url_dialog import dialog

MODULE = 'book_manager.gui.cover_url_dialog'


def prepared():
    stream = BytesIO();Image.new('RGB',(900,1200),'blue').save(stream, format='PNG')
    return PreparedCoverImage(stream.getvalue(),900,1200)


def file_dialog():
    d = dialog();d._prepare_file = Mock(return_value=prepared());d._file_button = Mock()
    return d


def test_file_picker_cancel_keeps_loaded_preview():
    d = file_dialog();d._loaded = ('old',Path('old.png'))
    with patch(f'{MODULE}.filedialog.askopenfilename', return_value=''):
        d._choose_file()
    assert d._loaded == ('old',Path('old.png'));d._task.start_operation.assert_not_called()


def test_file_read_is_sent_to_worker_without_saving():
    d = file_dialog()
    with patch(f'{MODULE}.filedialog.askopenfilename', return_value='selected.png'):
        d._choose_file()
    d._prepare_file.assert_not_called()
    result = d._task.start_operation.call_args.args[0]()
    assert result == (None,d._prepare_file.return_value)
    d._prepare_file.assert_called_once_with(Path('selected.png'))
    assert d.result is None


def test_busy_worker_cannot_start_another_file_selection():
    d = file_dialog();d._task.busy = True
    with patch(f'{MODULE}.filedialog.askopenfilename') as picker:
        d._choose_file();picker.assert_not_called()


def test_local_preview_clears_old_url_and_fits_preview_area():
    d = file_dialog();image = prepared();d._task.poll.return_value = ((None,image),None)
    with patch(f'{MODULE}.ImageTk.PhotoImage') as photo:d._poll()
    preview = photo.call_args.args[0]
    assert preview.width <= 400 and preview.height <= 320
    d._url.set.assert_called_once_with('')
    assert d._loaded == (None,image)
    d._apply();assert d.result == (None,image)


def test_failed_file_read_does_not_allow_apply():
    d = file_dialog();d._task.poll.return_value = (None,ValueError('bad file'))
    with patch(f'{MODULE}.messagebox.showerror') as error:
        d._poll();error.assert_called_once()
    assert d._loaded is None and d.result is None


def test_closed_dialog_ignores_late_prepared_image():
    d = file_dialog();d._closed = True;d._poll();d._task.poll.assert_not_called()


def app():
    a = BookManagerApplication.__new__(BookManagerApplication)
    a._root = Mock();a._service = Mock();a._metadata_form_snapshot = Mock(return_value=('same',))
    a._current_cover_image_url = 'https://example.com/old.jpg';a._current_cover_image_path = 'cache/old.jpg'
    a._display_cover_image = Mock();a._clear_cover_state = Mock()
    a._service.store_local_cover_image.return_value = Path('/test/cache/covers/local/hash.png')
    a._service.create_stored_cover_image_path.return_value = 'cache/covers/local/hash.png'
    return a


def test_parent_explicit_local_apply_stores_and_replaces_old_url_without_db_save():
    a = app();image = prepared()
    with patch('book_manager.gui.book_manager_application.CoverUrlDialog') as child:
        child.return_value.show.return_value = (None,image);a._on_edit_cover_url()
        assert child.call_args.kwargs['prepare_file'] == a._service.prepare_local_cover_image
    a._service.store_local_cover_image.assert_called_once_with(image)
    assert a._current_cover_image_url is None and a._current_cover_image_path == 'cache/covers/local/hash.png'
    a._clear_cover_state.assert_not_called();a._service.update_book.assert_not_called();a._service.add_book.assert_not_called()


@pytest.mark.parametrize('failure', ['cancel','changed','save','display'])
def test_cancel_changed_target_and_failures_keep_previous_cover(failure):
    a = app();image = prepared()
    if failure == 'changed':a._metadata_form_snapshot.side_effect = [('before',),('changed',)]
    if failure == 'save':a._service.store_local_cover_image.side_effect = OSError('disk')
    if failure == 'display':a._display_cover_image.side_effect = OSError('display')
    with patch('book_manager.gui.book_manager_application.CoverUrlDialog') as child, patch('book_manager.gui.book_manager_application.messagebox'):
        child.return_value.show.return_value = None if failure == 'cancel' else (None,image)
        a._on_edit_cover_url()
    assert a._current_cover_image_url == 'https://example.com/old.jpg' and a._current_cover_image_path == 'cache/old.jpg'
    if failure in ('cancel','changed'):a._service.store_local_cover_image.assert_not_called()
