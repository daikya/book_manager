"""編集中の書籍からAmazon検索・コピーを行う。書籍内容は変更しない。"""
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from book_manager.gui.dialog_window_state import restore_dialog_window
from book_manager.gui.long_text_dialog import text_dialog_store
from book_manager.gui.book_text_import_dialog import BookTextImportDialog
from book_manager.services.book_research import (
    amazon_book_search_url, book_search_query, research_book_title, research_isbn,
)


class BookResearchDialog:
    def __init__(self, parent, *, isbn='', title='', author='', state_store=None, current=None):
        self.result = None
        self._values = dict(isbn=isbn, title=title, author=author)
        self._current = dict(current) if current is not None else dict(self._values)
        self._paste_state_store = text_dialog_store(state_store, 'book_paste')
        self.window = tk.Toplevel(parent)
        self.window.title('書籍入力支援')
        self.window.transient(parent)
        self.window.geometry('680x440')
        self.window.minsize(480, 420)
        self._status = tk.StringVar(master=self.window)
        body = ttk.Frame(self.window, padding=12)
        body.pack(fill='both', expand=True)
        body.columnconfigure(1, weight=1)
        for row, (label, value) in enumerate((('ISBN', isbn), ('書籍名', title), ('著者名', author))):
            ttk.Label(body, text=label).grid(row=row, column=0, sticky='w', padx=(0, 8), pady=4)
            entry = ttk.Entry(body)
            entry.insert(0, value)
            entry.configure(state='readonly')
            entry.grid(row=row, column=1, sticky='ew', pady=4)
        ttk.Label(body, text='ISBNを優先し、空欄なら書籍名・著者名で検索します。\n参照ISBNは使いません。商品ページはブラウザーで確認してください。',
                  wraplength=430).grid(row=3, column=0, columnspan=2, sticky='w', pady=8)
        buttons = ttk.Frame(body)
        buttons.grid(row=4, column=0, columnspan=2, sticky='w')
        ttk.Button(buttons, text='Amazonで検索', command=self._search).pack(side='left')
        ttk.Button(buttons, text='検索語をコピー', command=lambda:self._copy('query')).pack(side='left', padx=6)
        copies = ttk.Frame(body)
        copies.grid(row=5, column=0, columnspan=2, sticky='w', pady=6)
        ttk.Button(copies, text='ISBNをコピー', command=lambda:self._copy('isbn'),
                   state='normal' if isbn.strip() else 'disabled').pack(side='left')
        ttk.Button(copies, text='書籍名をコピー', command=lambda:self._copy('title'),
                   state='normal' if title.strip() else 'disabled').pack(side='left', padx=6)
        ttk.Label(body, textvariable=self._status, wraplength=430).grid(
            row=6, column=0, columnspan=2, sticky='w')
        ttk.Button(body, text='書誌情報を貼り付け・確認', command=self._paste_book_text).grid(
            row=7, column=0, columnspan=2, sticky='w', pady=6)
        body.rowconfigure(7, weight=1)
        ttk.Button(body, text='閉じる', command=self.window.destroy).grid(row=8, column=1, sticky='e')
        self.window.bind('<Escape>', lambda event:self.window.destroy())
        restore_dialog_window(self.window, parent, state_store, default_size=(680, 440))

    def _search(self):
        try:
            url = amazon_book_search_url(**self._values)
            if not webbrowser.open(url, new=2):
                raise RuntimeError('ブラウザーを開けませんでした。検索語をコピーして検索してください。')
            self._status.set('Amazonの検索をブラウザーで開きました。')
        except (ValueError, RuntimeError, OSError, webbrowser.Error) as error:
            messagebox.showerror('Amazon検索', str(error), parent=self.window)

    def _copy(self, target):
        try:
            if target == 'isbn':
                text = research_isbn(self._values['isbn'])
            elif target == 'title':
                text = research_book_title(self._values['title'])
            else:
                text = book_search_query(**self._values)
            self.window.clipboard_clear()
            self.window.clipboard_append(text)
            self._status.set('クリップボードへコピーしました。')
        except (ValueError, tk.TclError) as error:
            messagebox.showerror('コピー', str(error), parent=self.window)

    def _paste_book_text(self):
        result = BookTextImportDialog(self.window, current=self._current,
                                     state_store=self._paste_state_store).show()
        if result is not None:
            self.result = result
            self.window.destroy()
        else:
            self.window.grab_set()

    def show(self):
        self.window.grab_set()
        self.window.wait_window()
        return self.result
