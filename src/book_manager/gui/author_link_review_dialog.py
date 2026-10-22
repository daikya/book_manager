"""未関連書籍を1冊ずつ確認して管理著者へ関連付ける。"""
import tkinter as tk
from tkinter import ttk, messagebox

from book_manager.gui.author_dialogs import (
    AuthorSelectionDialog, make_table, show_error, state_store,
)
from book_manager.gui.dialog_window_state import restore_dialog_window


class AuthorLinkReviewDialog:
    def __init__(self, parent, service, *, get_book, window_state_store=None):
        self._service = service
        self._get_book = get_book
        self._base_store = window_state_store
        self.window = tk.Toplevel(parent)
        self.window.transient(parent)
        self.window.title('未関連書籍の著者整理')
        self.window.geometry('900x600')
        self.window.minsize(680, 420)
        body = ttk.Frame(self.window, padding=12)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='管理著者が未設定の書籍です。1冊ずつ候補を選び、確認して保存します。\n著者名の原表記は変更しません。名前の自動分割・自動確定は行いません。', wraplength=850).pack(anchor='w')
        self._count = tk.StringVar(self.window)
        ttk.Label(body, textvariable=self._count).pack(anchor='w', pady=6)
        self._tree = make_table(body, (('id', '書籍ID', 70), ('title', '書籍名', 400), ('author', '著者名（原表記）', 280)))
        self._tree.bind('<Double-1>', lambda event: self._choose())
        buttons = ttk.Frame(body)
        buttons.pack(fill='x', pady=8)
        ttk.Button(buttons, text='候補を選んで関連付け', command=self._choose).pack(side='left')
        ttk.Button(buttons, text='一覧を更新', command=self._refresh).pack(side='left', padx=8)
        ttk.Button(buttons, text='閉じる', command=self.window.destroy).pack(side='right')
        ttk.Label(body, text='保存を確認した関連付けは、この画面を閉じても保持されます。', wraplength=850).pack(anchor='w')
        self.window.bind('<Escape>', lambda event: self.window.destroy())
        self._refresh()
        restore_dialog_window(self.window, parent, state_store(window_state_store, 'author_link_review'), default_size=(900, 600))

    def _refresh(self):
        try:
            rows = self._service.unlinked_books()
            self._books = {row['id']: row for row in rows}
            self._tree.delete(*self._tree.get_children())
            for row in rows:
                self._tree.insert('', 'end', iid=str(row['id']), values=(row['id'], row['title'], row['author'] or ''))
            self._count.set(f'未関連：{len(rows)}冊')
        except Exception as error:
            show_error(self.window, error)

    def _choose(self):
        selection = self._tree.selection()
        if not selection:
            messagebox.showinfo('著者整理', '書籍を選択してください。', parent=self.window)
            return
        book = self._books[int(selection[0])]
        try:
            ids = AuthorSelectionDialog(self.window, self._service,
                query=book['author'] or '', get_book=self._get_book,
                window_state_store=self._base_store,
                apply_help="選択を反映すると保存確認へ進みます。まだ関連付けは保存されません。\n著者管理で保存した著者情報は、キャンセルしても保持されます。").show()
            self.window.grab_set()
            if not ids:
                return
            authors = [self._service.get(ident) for ident in ids]
            if any(author is None for author in authors):
                raise ValueError('著者が削除されました。選び直してください。')
            names = '\n'.join(f'{a.name} [ID:{a.id}] {a.disambiguation_note or ""}' for a in authors)
            if not messagebox.askyesno('関連付けの保存',
                f'書籍ID {book["id"]}：{book["title"]}\n原著者名：{book["author"] or "（空欄）"}\n\n管理著者（表示順）：\n{names}\n\nこの関連付けを保存しますか？', parent=self.window):
                return
            self._service.link_unassigned_book(book['id'], ids,
                expected_title=book['title'], expected_author=book['author'])
            self._refresh()
        except Exception as error:
            show_error(self.window, error)

    def show(self):
        self.window.grab_set()
        self.window.wait_window()
