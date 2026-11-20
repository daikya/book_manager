"""追加コピーと既存候補の相違を全項目表示し、採用する値を選ぶ。"""
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from book_manager.gui.dialog_window_state import restore_dialog_window
from book_manager.services.book_text_parser import FIELDS


class BookTextMergeDialog:
    def __init__(self, parent, *, conflicts, state_store=None):
        self.result = None
        self.window = tk.Toplevel(parent)
        self.window.title('追加分と現在の候補の相違')
        self.window.transient(parent)
        self.window.geometry('900x600')
        self.window.minsize(640, 420)
        outer = ttk.Frame(self.window, padding=10)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='チェックした項目だけ追加分へ置き換えます。初期状態は現在の候補を保持します。\n内容紹介は結合せず、どちらか一方を採用します。取消では追加全体を取り込みません。',
                  wraplength=600).pack(anchor='w', pady=6)
        container = ttk.Frame(outer)
        container.pack(fill='both', expand=True)
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        body = ttk.Frame(canvas)
        item = canvas.create_window((0, 0), window=body, anchor='nw')
        body.bind('<Configure>', lambda event:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event:canvas.itemconfigure(item, width=event.width))
        body.columnconfigure(1, weight=1);body.columnconfigure(2, weight=1)
        self._selected = {}
        for column, text in enumerate(('追加分を採用', '現在の候補', '追加分の候補')):
            ttk.Label(body, text=text).grid(row=0, column=column, sticky='w', padx=4)
        for row, (key, (old, new)) in enumerate(conflicts.items(), 1):
            var = tk.BooleanVar(master=self.window, value=False)
            self._selected[key] = var
            ttk.Checkbutton(body, text=FIELDS[key], variable=var).grid(row=row, column=0, sticky='nw', padx=4, pady=6)
            for column, value in ((1, old), (2, new)):
                text = ScrolledText(body, height=7 if key == 'description' else 3, width=24, wrap='word')
                text.insert('1.0', value);text.configure(state='disabled')
                text.grid(row=row, column=column, sticky='nsew', padx=4, pady=6)
        buttons = ttk.Frame(outer)
        buttons.pack(fill='x', pady=(8, 0))
        ttk.Button(buttons, text='この選択で追加分を取り込む', command=self._confirm).pack(side='left')
        ttk.Button(buttons, text='キャンセル', command=self.window.destroy).pack(side='right')
        self.window.bind('<Escape>', lambda event:self.window.destroy())
        restore_dialog_window(self.window, parent, state_store, default_size=(900, 600))

    def _confirm(self):
        self.result = frozenset(k for k, var in self._selected.items() if var.get())
        self.window.destroy()

    def show(self):
        self.window.grab_set();self.window.wait_window()
        return self.result
