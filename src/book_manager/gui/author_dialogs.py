"""管理著者の選択・管理・編集。書籍との関連は親画面の保存時に確定する。"""
import logging
import tkinter as tk
from tkinter import ttk, messagebox

from book_manager.config.window_state_store import WindowStateStore
from book_manager.gui.dialog_window_state import restore_dialog_window
from book_manager.services.author_matching import find_author_candidates

logger = logging.getLogger(__name__)
MATCH_LABELS = {'exact': '表記一致', 'normalized': '空白・全半角等', 'partial': '部分一致', 'note': '識別メモ'}


def state_store(base, name):
    return None if base is None else WindowStateStore(base.path.with_name(f'{name}_window_state.json'))


def make_table(parent, columns, *, height=12):
    frame = ttk.Frame(parent)
    frame.pack(fill='both', expand=True)
    frame.rowconfigure(0, weight=1);frame.columnconfigure(0, weight=1)
    tree = ttk.Treeview(frame, columns=tuple(key for key, _, _ in columns), show='headings',
                        selectmode='browse', height=height)
    for key, label, width in columns:
        tree.heading(key, text=label);tree.column(key, width=width, minwidth=45)
    scroll = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    horizontal = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
    tree.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
    tree.grid(row=0, column=0, sticky='nsew');scroll.grid(row=0, column=1, sticky='ns')
    horizontal.grid(row=1, column=0, sticky='ew')
    return tree


def show_error(window, error):
    logger.error('著者操作に失敗しました。', exc_info=True)
    messagebox.showerror('著者管理', str(error), parent=window)


class AuthorEditDialog:
    def __init__(self, parent, service, *, author=None, window_state_store=None, initial_name=""):
        self._service = service;self._author = author;self.result = None
        self.window = tk.Toplevel(parent);self.window.transient(parent)
        self.window.title('著者の編集' if author else '著者の新規登録')
        self.window.geometry('660x540');self.window.minsize(520, 440)
        body = ttk.Frame(self.window, padding=12);body.pack(fill='both', expand=True)
        ttk.Label(body, text='同姓同名でも別の著者として登録できます。識別メモには分野・所属・生年などを記入できます。', wraplength=610).pack(anchor='w')
        ttk.Label(body, text='表示名（必須・200文字以内）').pack(anchor='w', pady=(10, 0))
        self._name = tk.StringVar(self.window, author.name if author else initial_name)
        entry = ttk.Entry(body, textvariable=self._name);entry.pack(fill='x')
        ttk.Label(body, text='別名（1行に1つ。カンマでは分割しません）').pack(anchor='w', pady=(10, 0))
        self._aliases = tk.Text(body, height=5, wrap='word');self._aliases.pack(fill='both', expand=True)
        if author:self._aliases.insert('1.0', '\n'.join(author.aliases))
        ttk.Label(body, text='識別メモ（任意・2000文字以内）').pack(anchor='w', pady=(10, 0))
        self._note = tk.Text(body, height=5, wrap='word');self._note.pack(fill='both', expand=True)
        if author:self._note.insert('1.0', author.disambiguation_note or '')
        ttk.Label(body, text='保存すると著者情報が確定します。既存書籍の著者名欄は書き換えません。', wraplength=610).pack(anchor='w', pady=8)
        buttons = ttk.Frame(body);buttons.pack(fill='x')
        ttk.Button(buttons, text='キャンセル', command=self.window.destroy).pack(side='right')
        ttk.Button(buttons, text='保存', command=self._save).pack(side='right', padx=8)
        self.window.bind('<Escape>', lambda e:self.window.destroy())
        restore_dialog_window(self.window, parent, state_store(window_state_store, 'author_edit'), default_size=(660, 540))
        entry.focus_set()

    def _save(self):
        try:
            name = self._name.get()
            aliases = tuple(line for line in self._aliases.get('1.0', 'end-1c').splitlines() if line.strip())
            note = self._note.get('1.0', 'end-1c') or None
            if self._author is None:
                candidates = [c for c in self._service.search(name) if c.match_kind != 'note']
                if candidates and not messagebox.askyesno('同名・類似する著者の確認',
                        f'既存の候補が{len(candidates)}件あります。\n同姓同名の別人など、新しい著者として登録しますか？', parent=self.window):
                    return
                self.result = self._service.create(name=name, aliases=aliases, disambiguation_note=note)
            else:
                self.result = self._service.update(author_id=self._author.id, name=name, aliases=aliases, disambiguation_note=note)
            self.window.destroy()
        except Exception as error:show_error(self.window, error)

    def show(self):
        self.window.grab_set();self.window.wait_window();return self.result


class AuthorManagementDialog:
    def __init__(self, parent, service, *, get_book, window_state_store=None, initial_name=""):
        self._service = service;self._get_book = get_book;self._base_store = window_state_store
        self._initial_name = initial_name
        self.window = tk.Toplevel(parent);self.window.transient(parent);self.window.title('著者管理')
        self.window.geometry('960x620');self.window.minsize(740, 460)
        body = ttk.Frame(self.window, padding=12);body.pack(fill='both', expand=True)
        top = ttk.Frame(body);top.pack(fill='x', pady=(0, 8))
        self._query = tk.StringVar(self.window)
        entry = ttk.Entry(top, textvariable=self._query);entry.pack(side='left', fill='x', expand=True)
        entry.bind('<Return>', lambda e:self._refresh())
        ttk.Button(top, text='検索', command=self._refresh).pack(side='left', padx=6)
        ttk.Button(top, text='全件表示', command=self._all).pack(side='left')
        self._tree = make_table(body, (('id', 'ID', 55), ('name', '表示名', 150), ('aliases', '別名', 190),
                                      ('note', '識別メモ', 260), ('count', '書籍数', 65)))
        self._tree.bind('<Double-1>', lambda e:self._edit())
        buttons = ttk.Frame(body);buttons.pack(fill='x', pady=10)
        for label, command in [('新規登録', self._new), ('編集', self._edit), ('削除', self._delete), ('関連書籍を表示', self._show_books), ('重複著者を統合', self._merge)]:
            ttk.Button(buttons, text=label, command=command).pack(side='left', padx=(0, 6))
        ttk.Button(buttons, text='閉じる', command=self.window.destroy).pack(side='right')
        ttk.Label(body, text='著者の登録・編集は保存すると確定します。同じ名前の別人はID・識別メモで区別してください。', wraplength=880).pack(anchor='w')
        self.window.bind('<Escape>', lambda e:self.window.destroy())
        self._refresh()
        restore_dialog_window(self.window, parent, state_store(window_state_store, 'author_management'), default_size=(960, 620))

    def _all(self):self._query.set('');self._refresh()

    def _refresh(self):
        try:
            authors = self._service.list_authors()
            self._authors = {a.id:a for a in authors}
            query = self._query.get()
            if query.strip():authors = [c.author for c in find_author_candidates(authors, query)]
            counts = self._service.usage_counts()
            self._tree.delete(*self._tree.get_children())
            for a in authors:
                self._tree.insert('', 'end', iid=str(a.id), values=(a.id, a.name, '／'.join(a.aliases),
                                  (a.disambiguation_note or '').replace('\n', ' '), counts.get(a.id, 0)))
        except Exception as error:show_error(self.window, error)

    def _selected(self):
        selection = self._tree.selection()
        if not selection:
            messagebox.showinfo('著者管理', '著者を選択してください。', parent=self.window);return None
        return self._authors.get(int(selection[0]))

    def _new(self):self._open_editor(None)

    def _edit(self):
        author = self._selected()
        if author:self._open_editor(author)

    def _open_editor(self, author):
        result = AuthorEditDialog(self.window, self._service, author=author, window_state_store=self._base_store,
            initial_name=getattr(self, "_initial_name", "") if author is None else "").show()
        self.window.grab_set()
        if result:
            self._query.set('');self._refresh();self._tree.selection_set(str(result.id));self._tree.see(str(result.id))

    def _delete(self):
        author = self._selected()
        if not author:return
        try:
            if self._service.linked_book_ids(author.id):
                messagebox.showwarning('削除できません', '書籍に関連付けられた著者は削除できません。先に書籍側で関連を解除してください。', parent=self.window);return
            if messagebox.askyesno('著者削除', f'ID {author.id}：{author.name}\nこの著者と別名を削除しますか？', parent=self.window):
                self._service.delete(author.id);self._refresh()
        except Exception as error:show_error(self.window, error)

    def _merge(self):
        from book_manager.gui.author_merge_dialog import AuthorMergeDialog
        author = self._selected()
        if author is None:
            return
        try:
            result = AuthorMergeDialog(self.window, self._service, source=author,
                window_state_store=self._base_store).show()
            self.window.grab_set()
            if result:
                self._query.set('')
                self._refresh()
                self._tree.selection_set(str(result.id))
                self._tree.see(str(result.id))
        except Exception as error:
            show_error(self.window, error)

    def _show_books(self):
        author = self._selected()
        if not author:return
        try:
            ids = self._service.linked_book_ids(author.id)
            books = [self._get_book(book_id) for book_id in ids]
            window = tk.Toplevel(self.window);window.transient(self.window)
            window.title(f'関連書籍：{author.name}（ID {author.id}）');window.geometry('740x480');window.minsize(500, 320)
            body = ttk.Frame(window, padding=12);body.pack(fill='both', expand=True)
            tree = make_table(body, (('id', '書籍ID', 70), ('title', '書籍名', 440), ('author', '著者名（原表記）', 180)))
            for book in books:
                if book is not None:tree.insert('', 'end', values=(book.id, book.title, book.author or ''))
            ttk.Button(body, text='閉じる', command=window.destroy).pack(anchor='e', pady=8)
            restore_dialog_window(window, self.window, state_store(self._base_store, 'author_books'), default_size=(740, 480))
            window.grab_set();window.wait_window();self.window.grab_set()
        except Exception as error:show_error(self.window, error)

    def show(self):self.window.grab_set();self.window.wait_window()


class AuthorSelectionDialog:
    def __init__(self, parent, service, *, selected_ids=(), query='', get_book, window_state_store=None, apply_help=None):
        self._service = service;self._get_book = get_book;self._base_store = window_state_store
        self._initial_name = query
        self._selected_ids = list(selected_ids);self.result = None
        self.window = tk.Toplevel(parent);self.window.transient(parent);self.window.title('管理著者の選択')
        self.window.geometry('1000x650');self.window.minsize(780, 480)
        body = ttk.Frame(self.window, padding=12);body.pack(fill='both', expand=True)
        ttk.Label(body, text='著者名欄の原表記は保持します。候補のID・識別メモを確認して選択してください。', wraplength=930).pack(anchor='w')
        top = ttk.Frame(body);top.pack(fill='x', pady=8)
        self._query = tk.StringVar(self.window, query)
        entry = ttk.Entry(top, textvariable=self._query);entry.pack(side='left', fill='x', expand=True)
        entry.bind('<Return>', lambda e:self._refresh())
        ttk.Button(top, text='検索', command=self._refresh).pack(side='left', padx=6)
        ttk.Button(top, text='全件表示', command=self._all).pack(side='left')
        ttk.Button(top, text='著者管理', command=self._manage).pack(side='right', padx=6)
        panes = ttk.Panedwindow(body, orient='horizontal');panes.pack(fill='both', expand=True)
        left = ttk.LabelFrame(panes, text='登録済み著者の候補', padding=6)
        right = ttk.LabelFrame(panes, text='この書籍の管理著者（上から表示順）', padding=6)
        panes.add(left, weight=3);panes.add(right, weight=2)
        self._candidates = make_table(left, (('id','ID',55),('name','表示名',140),('note','識別メモ',210),('match','一致の目安',110)))
        ttk.Button(left, text='選択へ追加 →', command=self._add).pack(anchor='e', pady=6)
        self._selected = make_table(right, (('id','ID',55),('name','表示名',130),('note','識別メモ',180)))
        order = ttk.Frame(right);order.pack(fill='x', pady=6)
        for label, command in [('上へ',lambda:self._move(-1)),('下へ',lambda:self._move(1)),('選択から外す',self._remove)]:
            ttk.Button(order, text=label, command=command).pack(side='left', padx=(0, 4))
        self._candidates.bind('<Double-1>', lambda e:self._add())
        ttk.Label(body, text=apply_help or '「選択を反映」は入力フォームへ反映します。関連付けの保存は書籍の「登録」「更新」で確定します。\n著者管理で保存した著者情報は、この画面をキャンセルしても保持されます。', wraplength=930).pack(anchor='w', pady=8)
        buttons = ttk.Frame(body);buttons.pack(fill='x')
        ttk.Button(buttons, text='キャンセル', command=self.window.destroy).pack(side='right')
        ttk.Button(buttons, text='選択を反映', command=self._apply).pack(side='right', padx=8)
        self.window.bind('<Escape>', lambda e:self.window.destroy())
        self._refresh()
        restore_dialog_window(self.window, parent, state_store(window_state_store, 'author_selection'), default_size=(1000, 650))

    def _all(self):self._query.set('');self._refresh()

    def _refresh(self):
        try:
            authors = self._service.list_authors();self._authors = {a.id:a for a in authors}
            query = self._query.get()
            rows = [(c.author, f'{MATCH_LABELS[c.match_kind]}：{c.matched_text}') for c in find_author_candidates(authors, query)] if query.strip() else [(a,'') for a in authors]
            self._candidates.delete(*self._candidates.get_children())
            for author, match in rows:
                self._candidates.insert('', 'end', iid=str(author.id), values=(author.id, author.name,
                                         (author.disambiguation_note or '').replace('\n', ' '), match))
            self._render_selected()
        except Exception as error:show_error(self.window, error)

    def _render_selected(self):
        self._selected.delete(*self._selected.get_children())
        for author_id in self._selected_ids:
            author = self._authors.get(author_id)
            self._selected.insert('', 'end', iid=str(author_id), values=(author_id, author.name if author else '削除された著者',
                                  (author.disambiguation_note or '').replace('\n', ' ') if author else '選択から外してください'))

    def _add(self):
        selection = self._candidates.selection()
        if not selection:return
        author_id = int(selection[0])
        if author_id not in self._selected_ids:self._selected_ids.append(author_id)
        self._render_selected()

    def _remove(self):
        selection = self._selected.selection()
        if selection:self._selected_ids.remove(int(selection[0]));self._render_selected()

    def _move(self, direction):
        selection = self._selected.selection()
        if not selection:return
        author_id = int(selection[0]);index = self._selected_ids.index(author_id);target = index + direction
        if not 0 <= target < len(self._selected_ids):return
        self._selected_ids[index], self._selected_ids[target] = self._selected_ids[target], self._selected_ids[index]
        self._render_selected();self._selected.selection_set(str(author_id))

    def _manage(self):
        AuthorManagementDialog(self.window, self._service, get_book=self._get_book,
            window_state_store=self._base_store, initial_name=self._initial_name).show()
        self.window.grab_set();self._refresh()

    def _apply(self):
        try:
            if any(self._service.get(author_id) is None for author_id in self._selected_ids):
                messagebox.showwarning('著者選択', '削除された著者を選択から外し、選び直してください。', parent=self.window);return
            self.result = tuple(self._selected_ids);self.window.destroy()
        except Exception as error:show_error(self.window, error)

    def show(self):self.window.grab_set();self.window.wait_window();return self.result
