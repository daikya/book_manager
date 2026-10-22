"""統合元・統合先と関連書籍を確認する。"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

from book_manager.gui.author_dialogs import state_store, show_error, make_table
from book_manager.services.author_matching import find_author_candidates
from book_manager.gui.dialog_window_state import restore_dialog_window


def describe_plan(plan):
    def person(label, author):
        return (f'{label}：{author.name} [ID:{author.id}]\n'
                f'別名：{"／".join(author.aliases) or "（なし）"}\n'
                f'識別メモ：{author.disambiguation_note or "（なし）"}')
    lines = [person('統合元（削除）', plan.source), person('統合先（保持）', plan.target),
             '統合後の別名：' + ('／'.join(plan.aliases) or '（なし）'),
             f'関連書籍：{len(plan.books)}冊（統合先だけに関連する書籍も表示）']
    for book in plan.books:
        lines.append(f'書籍ID:{book.id} {book.title}\n原著者名：{book.original_author or "（空欄）"}\n'
                     f'著者ID順：{book.before_ids} → {book.after_ids}')
    return '\n\n'.join(lines)


class AuthorMergeDialog:
    def __init__(self, parent, service, *, source, window_state_store=None):
        self._service = service
        self._source = source
        self._plan = None
        self.result = None
        self.window = tk.Toplevel(parent)
        self.window.transient(parent)
        self.window.title('管理著者の統合')
        self.window.geometry('900x700')
        self.window.minsize(700, 540)
        body = ttk.Frame(self.window, padding=12)
        body.pack(fill='both', expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(4, weight=1)
        body.rowconfigure(5, weight=1)
        ttk.Label(body, text=f'統合元（削除）：{source.name} [ID:{source.id}]\n同姓同名の別人ではないことを確認してください。元の書籍の著者名は変更しません。', wraplength=850).grid(row=0, column=0, sticky='w')
        top = ttk.Frame(body)
        top.grid(row=1, column=0, sticky='ew', pady=8)
        ttk.Label(top, text='統合先を検索').pack(side='left')
        self._query = tk.StringVar(self.window, source.name)
        entry = ttk.Entry(top, textvariable=self._query)
        entry.pack(side='left', fill='x', expand=True, padx=8)
        entry.bind('<Return>', lambda event:self._refresh_targets())
        ttk.Button(top, text='検索', command=self._refresh_targets).pack(side='left')
        ttk.Button(top, text='全件表示', command=self._all_targets).pack(side='left', padx=6)
        ttk.Button(top, text='内容を再確認', command=self._preview).pack(side='right')
        ttk.Label(body, text='表示名・別名・識別メモで検索します。空白・全半角の違いを考慮します。', wraplength=850).grid(row=2, column=0, sticky='w')
        self._target_count = tk.StringVar(self.window)
        ttk.Label(body, textvariable=self._target_count).grid(row=3, column=0, sticky='w')
        targets_frame = ttk.LabelFrame(body, text='統合先（保持する著者）', padding=4)
        targets_frame.grid(row=4, column=0, sticky='nsew', pady=(4, 8))
        self._target_tree = make_table(targets_frame, (
            ('id', 'ID', 55), ('name', '表示名', 160),
            ('aliases', '別名', 210), ('note', '識別メモ', 340),
        ), height=5)
        self._target_tree.bind('<<TreeviewSelect>>', self._on_target_selected)
        self._details = ScrolledText(body, height=8, wrap='word', state='disabled')
        self._details.grid(row=5, column=0, sticky='nsew')
        ttk.Label(body, text='統合後の識別メモ（編集可・2000文字以内）。検索・全件表示・再確認・選び直しで初期化します。', wraplength=850).grid(row=6, column=0, sticky='w', pady=(8, 4))
        self._note = ScrolledText(body, height=5, wrap='word')
        self._note.grid(row=7, column=0, sticky='ew')
        ttk.Label(body, text='保存すると統合元のIDを削除します。取り消す場合は保存前にキャンセルしてください。', wraplength=850).grid(row=8, column=0, sticky='w', pady=8)
        buttons = ttk.Frame(body)
        buttons.grid(row=9, column=0, sticky='ew')
        ttk.Button(buttons, text='キャンセル', command=self.window.destroy).pack(side='right')
        self._save_button = ttk.Button(buttons, text='確認して統合', command=self._save, state='disabled')
        self._save_button.pack(side='right', padx=8)
        self.window.bind('<Escape>', lambda event:self.window.destroy())
        self._refresh_targets()
        restore_dialog_window(self.window, parent, state_store(window_state_store, 'author_merge'), default_size=(900, 700))

    def _reset_preview(self):
        self._plan = None
        self._save_button.configure(state='disabled')
        self._details.configure(state='normal')
        self._details.delete('1.0', 'end')
        self._details.insert('1.0', '一覧から統合先を選択し、比較内容を確認してください。')
        self._details.configure(state='disabled')
        self._note.delete('1.0', 'end')

    def _all_targets(self):
        self._query.set('')
        self._refresh_targets()

    def _refresh_targets(self):
        # 別の候補へ移った後に以前の計画を保存しない。
        self._reset_preview()
        self._target_tree.delete(*self._target_tree.get_children())
        self._target_count.set('読込中')
        try:
            authors = [a for a in self._service.list_authors() if a.id != self._source.id]
            query = self._query.get()
            rows = [c.author for c in find_author_candidates(authors, query)] if query.strip() else authors
            for author in rows:
                self._target_tree.insert('', 'end', iid=str(author.id), values=(
                    author.id, author.name, '／'.join(author.aliases),
                    ' '.join((author.disambiguation_note or '').split())))
            self._target_count.set(f'候補：{len(rows)}人（統合元は除外）')
        except Exception as error:
            self._target_count.set('読み込めませんでした')
            show_error(self.window, error)

    def _on_target_selected(self, _event=None):
        selected = self._target_tree.selection()
        if selected and self._plan is not None and self._plan.target.id == int(selected[0]):
            return
        self._preview()

    def _preview(self):
        self._reset_preview()
        selected = self._target_tree.selection()
        if not selected:
            return
        target_id = int(selected[0])
        try:
            plan = self._service.preview_merge(self._source.id, target_id)
            self._details.configure(state='normal')
            self._details.delete('1.0', 'end')
            self._details.insert('1.0', describe_plan(plan))
            self._details.configure(state='disabled')
            self._note.delete('1.0', 'end')
            self._note.insert('1.0', plan.suggested_note)
            self._plan = plan
            self._save_button.configure(state='normal')
        except Exception as error:
            show_error(self.window, error)

    def _save(self):
        if self._plan is None:
            return
        plan = self._plan
        note = self._note.get('1.0', 'end-1c')
        if not messagebox.askyesno('著者統合の最終確認',
            f'統合元：{plan.source.name} [ID:{plan.source.id}] を削除し、\n'
            f'統合先：{plan.target.name} [ID:{plan.target.id}] に別名・関連書籍を引き継ぎます。\n'
            f'関連書籍：{len(plan.books)}冊\n\n同じ人物であることを確認しましたか？', parent=self.window):
            return
        try:
            self.result = self._service.merge(plan, disambiguation_note=note)
            self.window.destroy()
        except Exception as error:
            self._plan = None
            self._save_button.configure(state='disabled')
            show_error(self.window, error)

    def show(self):
        self.window.grab_set()
        self.window.wait_window()
        return self.result
