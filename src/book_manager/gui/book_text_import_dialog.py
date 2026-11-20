"""貼り付けた1冊分を編集・比較し、選択項目だけを親フォームへ返す。"""
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from book_manager.gui.dialog_window_state import restore_dialog_window
from book_manager.gui.long_text_dialog import text_dialog_store
from book_manager.gui.book_text_merge_dialog import BookTextMergeDialog
from book_manager.services.book_text_merge import (
    check_book_text_identity, extend_book_text_identity, plan_book_text_merge,
)
from book_manager.services.book_text_parser import FIELDS, parse_book_text, select_book_text_fields


class BookTextImportDialog:
    def __init__(self, parent, *, current, state_store=None):
        self.result = None
        self._current = dict(current)
        self._parsed_source = None
        self._identity = None
        self._merge_store = text_dialog_store(state_store, 'book_paste_merge')
        self.window = tk.Toplevel(parent)
        self.window.title('書誌情報の貼り付け・確認')
        self.window.transient(parent)
        self.window.geometry('940x680')
        self.window.minsize(660, 480)
        outer = ttk.Frame(self.window, padding=10)
        outer.pack(fill='both', expand=True)
        scroll = ttk.Frame(outer)
        scroll.pack(fill='both', expand=True)
        canvas = tk.Canvas(scroll, highlightthickness=0)
        bar = ttk.Scrollbar(scroll, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side='left', fill='both', expand=True)
        bar.pack(side='right', fill='y')
        body = ttk.Frame(canvas)
        item = canvas.create_window((0, 0), window=body, anchor='nw')
        body.bind('<Configure>', lambda event:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event:canvas.itemconfigure(item, width=event.width))
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, weight=1)
        ttk.Label(body, text='1冊・1版ずつ読み取ります。同じ版の続きは、原文欄を次のコピーで置き換えて「追加分として読み取る」を押してください。',
                  wraplength=600).grid(row=0, column=0, columnspan=3, sticky='w', pady=4)
        self._source = ScrolledText(body, height=8, width=50, wrap='word', undo=True)
        self._source.grid(row=1, column=0, columnspan=3, sticky='ew')
        actions = ttk.Frame(body)
        actions.grid(row=2, column=0, columnspan=3, sticky='w', pady=6)
        ttk.Button(actions, text='クリップボードから貼り付け', command=self._paste_clipboard).pack(side='left')
        ttk.Button(actions, text='新しく読み取る', command=self._parse).pack(side='left', padx=8)
        self._additional_button = ttk.Button(actions, text='追加分として読み取る', command=self._merge, state='disabled')
        self._additional_button.pack(side='left')
        self._warnings = tk.StringVar(master=self.window, value='読み取れない項目は空欄になります。Amazonへの通信は行いません。')
        ttk.Label(body, textvariable=self._warnings, wraplength=600).grid(
            row=3, column=0, columnspan=3, sticky='w', pady=6)
        for column, label in enumerate(('反映する項目', '現在のフォーム', '読み取り候補（修正できます）')):
            ttk.Label(body, text=label).grid(row=4, column=column, sticky='w', padx=4)
        self._variables = {}
        self._selected = {}
        for row, (key, label) in enumerate(FIELDS.items(), 5):
            selected = tk.BooleanVar(master=self.window, value=False)
            self._selected[key] = selected
            ttk.Checkbutton(body, text=label, variable=selected).grid(row=row, column=0, sticky='nw', pady=5)
            if key == 'description':
                old = ScrolledText(body, height=7, width=24, wrap='word')
                old.insert('1.0', current.get(key, ''))
                old.configure(state='disabled')
                candidate = ScrolledText(body, height=7, width=24, wrap='word', undo=True)
            else:
                old = ttk.Entry(body)
                old.insert(0, current.get(key, ''))
                old.configure(state='readonly')
                variable = tk.StringVar(master=self.window)
                self._variables[key] = variable
                candidate = ttk.Entry(body, textvariable=variable)
            old.grid(row=row, column=1, sticky='nsew', padx=4, pady=5)
            candidate.grid(row=row, column=2, sticky='nsew', padx=4, pady=5)
            if key == 'description':self._description = candidate
        ttk.Label(outer, text='反映はフォームまでです。保存はメイン画面の「新規登録」「更新」で行います。\n書影・参照ISBN・管理著者の関連付け・読書記録は変更しません。',
                  wraplength=620).pack(anchor='w', pady=6)
        footer = ttk.Frame(outer)
        footer.pack(fill='x')
        self._apply_button = ttk.Button(footer, text='選択した項目をフォームへ反映', command=self._apply, state='disabled')
        self._apply_button.pack(side='left')
        ttk.Button(footer, text='キャンセル', command=self.window.destroy).pack(side='right')
        self.window.bind('<Escape>', lambda event:self.window.destroy())
        restore_dialog_window(self.window, parent, state_store, default_size=(940, 680))
        self._source.focus_set()

    def _paste_clipboard(self):
        try:
            value = self.window.clipboard_get()
        except tk.TclError:
            messagebox.showerror('貼り付け', 'クリップボードにテキストがありません。', parent=self.window)
            return
        self._source.delete('1.0', 'end')
        self._source.insert('1.0', value)
        self._apply_button.configure(state='disabled')
        self._warnings.set('貼り付けました。初回は「新しく読み取る」、同じ版の続きは「追加分として読み取る」を押してください。')

    def _parse(self):
        self._identity = None
        self._additional_button.configure(state='disabled')
        self._parsed_source = None
        self._apply_button.configure(state='disabled')
        for var in self._variables.values():var.set('')
        self._description.delete('1.0', 'end')
        for var in self._selected.values():var.set(False)
        source = self._source.get('1.0', 'end-1c')
        try:
            candidate = parse_book_text(source)
        except ValueError as error:
            self._warnings.set(str(error))
            messagebox.showerror('書誌情報の読み取り', str(error), parent=self.window)
            return
        for key, value in candidate.values.items():
            if key == 'description':self._description.insert('1.0', value)
            else:self._variables[key].set(value)
            self._selected[key].set(bool(value.strip()) and not self._current.get(key, '').strip())
        self._warnings.set('\n'.join(candidate.warnings))
        self._identity = candidate
        self._parsed_source = source
        self._additional_button.configure(state='normal')
        self._apply_button.configure(state='normal')

    def _candidate_values(self):
        values = {key:var.get() for key, var in self._variables.items()}
        values['description'] = self._description.get('1.0', 'end-1c')
        return values

    def _merge(self):
        if self._identity is None:
            messagebox.showinfo('追加読み取り', '最初のコピーを「新しく読み取る」で読み取ってください。', parent=self.window)
            return
        self._apply_button.configure(state='disabled')
        source = self._source.get('1.0', 'end-1c')
        try:
            candidate = parse_book_text(source)
            identified = check_book_text_identity(self._identity, candidate)
        except ValueError as error:
            self._warnings.set(str(error))
            messagebox.showerror('追加読み取り', str(error), parent=self.window)
            return
        if not identified:
            old = self._identity.values
            new = candidate.values
            if not messagebox.askyesno('同じ版か確認',
                    '同じ版を識別する情報が不足しています。\n'
                    f'現在: {old.get("title") or "書籍名なし"} / {old.get("publication_format") or "出版形態なし"}\n'
                    f'追加: {new.get("title") or "書籍名なし"} / {new.get("publication_format") or "出版形態なし"}\n'
                    '同じ書籍・同じ版の情報として追加しますか？', parent=self.window):
                self._warnings.set('追加を取り消しました。前回の原文・候補へ戻しました。')
                self._restore_apply_availability()
                return
        before = self._candidate_values()
        merged, conflicts = plan_book_text_merge(before, candidate.values)
        if conflicts:
            adopted = BookTextMergeDialog(self.window, conflicts=conflicts, state_store=self._merge_store).show()
            self.window.grab_set()
            if adopted is None:
                self._warnings.set('追加を取り消しました。候補とチェックは保持しています。')
                self._restore_apply_availability()
                return
            for key in adopted:
                merged[key] = conflicts[key][1]
        # 追加が確定するまでは、候補・チェック・照合用情報を変更しない。
        for key, value in merged.items():
            if key == 'description':
                self._description.delete('1.0', 'end')
                self._description.insert('1.0', value)
            else:
                self._variables[key].set(value)
            if value.strip() and not before.get(key, '').strip():
                self._selected[key].set(not self._current.get(key, '').strip())
        self._identity = extend_book_text_identity(self._identity, candidate)
        self._parsed_source = source
        missing = {label + 'を読み取れませんでした。' for key, label in FIELDS.items() if merged.get(key, '').strip()}
        warnings = [w for w in candidate.warnings if not any(w.startswith(prefix) for prefix in missing)
                    and not (merged.get('isbn', '').strip() and w.startswith('ISBNは未取得'))]
        self._warnings.set('追加分を取り込みました。既存の候補とチェックを保持し、不足項目を補いました。\n' + '\n'.join(warnings))
        self._apply_button.configure(state='normal')

    def _restore_apply_availability(self):
        # 追加の取消では、直前に確定した原文と候補へ戻す。
        if self._parsed_source is not None:
            self._source.delete('1.0', 'end')
            self._source.insert('1.0', self._parsed_source)
        self._apply_button.configure(state='normal' if self._parsed_source is not None else 'disabled')

    def _apply(self):
        if self._parsed_source is None or self._source.get('1.0', 'end-1c') != self._parsed_source:
            messagebox.showwarning('再読み取り', '貼り付け内容を変更した場合は、「新しく読み取る」または「追加分として読み取る」を押してください。', parent=self.window)
            return
        values = self._candidate_values()
        try:
            result = select_book_text_fields(values, {key for key, var in self._selected.items() if var.get()})
        except ValueError as error:
            messagebox.showerror('反映内容の確認', str(error), parent=self.window)
            return
        self.result = result
        self.window.destroy()

    def show(self):
        self.window.grab_set()
        self.window.wait_window()
        return self.result
