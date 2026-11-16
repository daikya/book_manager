"""内容紹介・備考の編集。反映はフォームまで、DB保存は親の登録・更新で行う。"""
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from book_manager.config.window_state_store import WindowStateStore
from book_manager.gui.dialog_window_state import restore_dialog_window


class FormTextValue:
    """既存フォームのText操作を保ち、画面外のTkウィジェットを不要にする。"""
    def __init__(self, value=''):
        self.value = value

    def get(self, start='1.0', end='end-1c'):
        return self.value + ('\n' if end == 'end' else '')

    def delete(self, start='1.0', end='end'):
        self.value = ''

    def insert(self, index, value):
        self.value = str(value) + self.value


def text_dialog_store(base, name):
    return None if base is None else WindowStateStore(
        base.path.with_name(f'{name}_window_state.json'))


class LongTextDialog:
    def __init__(self, parent, *, title, value, state_store=None):
        self.result = None
        self.window = tk.Toplevel(parent)
        self.window.transient(parent)
        self.window.title(title)
        self.window.geometry('820x600')
        self.window.minsize(480, 320)
        body = ttk.Frame(self.window, padding=12)
        body.pack(fill='both', expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        ttk.Label(body, text='反映後、メイン画面の「登録」「更新」で書籍へ保存します。').grid(
            row=0, column=0, sticky='w', pady=(0, 8))
        self._text = ScrolledText(body, wrap='word', undo=True)
        self._text.grid(row=1, column=0, sticky='nsew')
        self._text.insert('1.0', value)
        buttons = ttk.Frame(body)
        buttons.grid(row=2, column=0, sticky='ew', pady=(8, 0))
        ttk.Button(buttons, text='キャンセル', command=self.window.destroy).pack(side='right')
        ttk.Button(buttons, text='フォームへ反映', command=self._apply).pack(side='right', padx=8)
        self.window.bind('<Escape>', lambda event:self.window.destroy())
        restore_dialog_window(self.window, parent, state_store, default_size=(820, 600))
        self._text.focus_set()

    def _apply(self):
        self.result = self._text.get('1.0', 'end-1c')
        self.window.destroy()

    def show(self):
        self.window.grab_set()
        self.window.wait_window()
        return self.result
