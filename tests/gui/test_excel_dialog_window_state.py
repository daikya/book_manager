"""Excel子画面の独立した配置保存・復元をGUIなしで検証する。"""
from types import SimpleNamespace
from unittest.mock import Mock, patch

from book_manager.config.window_state_store import WindowStateStore
from book_manager.gui.dialog_window_state import restore_dialog_window
from book_manager.gui.window_positioning import ScreenWorkArea
from book_manager.models.window_state import WindowState

MODULE = 'book_manager.gui.dialog_window_state'


def make_window():
    window = Mock()
    window.state.return_value = 'normal'
    window.winfo_x.return_value = 230
    window.winfo_y.return_value = 140
    window.winfo_width.return_value = 760
    window.winfo_height.return_value = 700
    window.minsize.return_value = (620, 480)
    return window


def callbacks(window):
    return {call.args[0]: call.args[1] for call in window.bind.call_args_list}


def test_first_open_center_then_move_and_reopen(tmp_path):
    store = WindowStateStore(tmp_path / 'mapping.json')
    window, parent = make_window(), Mock()
    with patch(f'{MODULE}.center_window_on_parent') as center:
        restore_dialog_window(window, parent, store, default_size=(760, 700))
    center.assert_called_once_with(window, parent)
    events = callbacks(window)
    window.winfo_x.return_value = 400
    events['<Configure>'](SimpleNamespace(widget=window))
    events['<Destroy>'](SimpleNamespace(widget=Mock()))
    assert store.load() is None
    events['<Destroy>'](SimpleNamespace(widget=window))
    assert store.load().x == 400
    other = make_window()
    with patch(f'{MODULE}.get_screen_work_areas', return_value=(ScreenWorkArea(0, 0, 1920, 1080),)), patch(f'{MODULE}.center_window_on_parent') as center:
        restore_dialog_window(other, parent, store, default_size=(760, 700))
    center.assert_not_called()
    other.geometry.assert_called_once_with('760x700+400+140')


def test_off_screen_saved_position_is_recovered(tmp_path):
    store = WindowStateStore(tmp_path / 'preview.json')
    store.save(WindowState(9000, 9000, 900, 720, False))
    window = make_window()
    with patch(f'{MODULE}.get_screen_work_areas', return_value=(ScreenWorkArea(0, 0, 1280, 800),)):
        restore_dialog_window(window, Mock(), store, default_size=(900, 720))
    window.geometry.assert_called_once_with('900x720+190+40')


def test_corrupt_state_and_failed_save_do_not_block_dialog(tmp_path):
    store = WindowStateStore(tmp_path / 'mapping.json')
    store.path.write_text('{broken')
    window = make_window()
    with patch(f'{MODULE}.center_window_on_parent') as center:
        restore_dialog_window(window, Mock(), store, default_size=(760, 700))
    center.assert_called_once()
    with patch.object(store, 'save', side_effect=OSError('read only')):
        callbacks(window)['<Destroy>'](SimpleNamespace(widget=window))
