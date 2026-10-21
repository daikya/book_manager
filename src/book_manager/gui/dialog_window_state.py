"""子画面を初回は親中央、以降は保存した配置へ表示する。"""
import logging
import tkinter as tk

from book_manager.config.window_state_store import WindowStateStore, WindowStateStoreError
from book_manager.models.window_state import WindowState
from book_manager.gui.window_positioning import (
    WindowRectangle, calculate_safe_window_rectangle,
    center_window_on_parent, get_screen_work_areas,
)

logger = logging.getLogger(__name__)


def restore_dialog_window(window, parent, store: WindowStateStore | None,
                          *, default_size: tuple[int, int]) -> None:
    """子ウィジェットのイベントを除外し、閉じたときだけ配置を保存する。"""
    window.update_idletasks()
    saved = store.load() if store is not None else None
    if saved is None:
        center_window_on_parent(window, parent)
    else:
        minimum_width, minimum_height = window.minsize()
        rectangle = calculate_safe_window_rectangle(
            WindowRectangle(saved.x, saved.y, saved.width, saved.height),
            get_screen_work_areas(parent),
            default_width=default_size[0], default_height=default_size[1],
            minimum_width=minimum_width, minimum_height=minimum_height,
        )
        window.geometry(f"{rectangle.width}x{rectangle.height}"
                        f"{rectangle.x:+d}{rectangle.y:+d}")
    window.update_idletasks()
    last_state = None

    def capture(event=None):
        nonlocal last_state
        if event is not None and event.widget is not window:
            return
        try:
            if window.state() != "normal":
                return
            width, height = window.winfo_width(), window.winfo_height()
            if width <= 1 or height <= 1:
                return
            last_state = WindowState(window.winfo_x(), window.winfo_y(),
                                     width, height, False)
        except (tk.TclError, ValueError):
            return

    def save(event):
        if event.widget is not window or store is None or last_state is None:
            return
        try:
            store.save(last_state)
        except (WindowStateStoreError, OSError):
            logger.warning("Excel子画面の配置を保存できませんでした。", exc_info=True)

    capture()
    window.bind("<Configure>", capture, add="+")
    window.bind("<Destroy>", save, add="+")
