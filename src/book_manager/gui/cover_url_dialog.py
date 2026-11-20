"""ISBNに依存しない書影URLの取得・プレビュー。Tk操作はメインスレッドだけで行う。"""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from io import BytesIO
from urllib.parse import urlsplit
from PIL import Image, ImageTk

from book_manager.gui.book_candidate_search_dialog import CandidateSearchTask
from book_manager.gui.dialog_window_state import restore_dialog_window


class CoverUrlDialog:
    def __init__(self, parent, *, url, fetch, state_store=None, prepare_file=None):
        self.result = None
        self._fetch = fetch
        self._prepare_file = prepare_file
        self._task = CandidateSearchTask()
        self._loaded = None
        self._photo = None
        self._after_id = None
        self._closed = False
        self.window = tk.Toplevel(parent)
        self.window.transient(parent)
        self.window.title('書影の編集（URL・画像ファイル）')
        self.window.geometry('720x600')
        self.window.minsize(500, 420)
        body = ttk.Frame(self.window, padding=12)
        body.pack(fill='both', expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(4, weight=1)
        ttk.Label(body, text='ISBNがなくても書影を指定できます。画像のHTTP/HTTPS URLを入力するか、画像ファイルを選択してください。', wraplength=670).grid(row=0, column=0, sticky='w')
        self._url = tk.StringVar(self.window, url or '')
        self._entry = ttk.Entry(body, textvariable=self._url)
        self._entry.grid(row=1, column=0, sticky='ew', pady=8)
        self._entry.bind('<Return>', lambda event:self._start())
        source_buttons = ttk.Frame(body)
        source_buttons.grid(row=2, column=0, sticky='w')
        self._download = ttk.Button(source_buttons, text='URLを取得してプレビュー', command=self._start)
        self._download.pack(side='left')
        self._file_button = ttk.Button(source_buttons, text='画像ファイルを選択', command=self._choose_file,
                                       state='normal' if prepare_file is not None else 'disabled')
        self._file_button.pack(side='left', padx=8)
        self._status = tk.StringVar(self.window, 'URLを取得して画像を確認してください。')
        ttk.Label(body, textvariable=self._status, wraplength=670).grid(row=3, column=0, sticky='w', pady=6)
        self._preview = ttk.Label(body, text='プレビュー', anchor='center')
        self._preview.grid(row=4, column=0, sticky='nsew')
        ttk.Label(body, text='確認後にフォームへ反映し、書籍の「登録」「更新」で保存します。GIF等は先頭フレームを使用します。\n画像本体は完全データZIP・DBバックアップに含まれません。PC移行時は利用者データフォルダーもコピーしてください。', wraplength=670).grid(row=5, column=0, sticky='w', pady=8)
        buttons = ttk.Frame(body)
        buttons.grid(row=6, column=0, sticky='ew')
        self._remove = ttk.Button(buttons, text='書影を解除', command=self._clear)
        self._remove.pack(side='left')
        ttk.Button(buttons, text='キャンセル', command=self.close).pack(side='right')
        self._apply_button = ttk.Button(buttons, text='フォームへ反映', command=self._apply, state='disabled')
        self._apply_button.pack(side='right', padx=8)
        self._url.trace_add('write', self._invalidate)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.bind('<Escape>', lambda event:self.close())
        self.window.bind('<Destroy>', self._destroyed, add='+')
        restore_dialog_window(self.window, parent, state_store, default_size=(720, 600))

    def _invalidate(self, *_args):
        self._loaded = None
        self._photo = None
        self._preview.configure(image='', text='取得後に画像を表示します')
        self._apply_button.configure(state='disabled')

    def _start(self):
        if self._task.busy:
            return
        url = self._url.get().strip()
        try:
            parsed = urlsplit(url)
            if parsed.scheme not in ('http', 'https') or not parsed.hostname:
                raise ValueError('画像のHTTP/HTTPS URLを入力してください。')
        except ValueError as error:
            messagebox.showerror('書影URL', str(error), parent=self.window)
            return
        self._invalidate()
        self._entry.configure(state='disabled')
        self._download.configure(state='disabled')
        self._remove.configure(state='disabled')
        file_button = getattr(self, '_file_button', None)
        if file_button is not None:file_button.configure(state='disabled')
        self._status.set('画像を取得しています…')
        self._task.start_operation(lambda:(url, Path(self._fetch(url))))
        self._after_id = self.window.after(80, self._poll)

    def _choose_file(self):
        if self._task.busy or self._prepare_file is None:
            return
        filename = filedialog.askopenfilename(parent=self.window, title='書影にする画像を選択',
            filetypes=[('画像ファイル', '*.jpg *.jpeg *.png *.webp *.gif *.bmp'), ('すべてのファイル', '*.*')])
        if not filename:
            return
        self._invalidate()
        self._entry.configure(state='disabled')
        self._download.configure(state='disabled')
        self._remove.configure(state='disabled')
        self._file_button.configure(state='disabled')
        self._status.set('画像ファイルを読み込んでいます…')
        path = Path(filename)
        self._task.start_operation(lambda:(None, self._prepare_file(path)))
        self._after_id = self.window.after(80, self._poll)

    def _poll(self):
        self._after_id = None
        if self._closed:
            return
        outcome = self._task.poll()
        if outcome is None:
            self._after_id = self.window.after(80, self._poll)
            return
        self._entry.configure(state='normal')
        self._download.configure(state='normal')
        self._remove.configure(state='normal')
        file_button = getattr(self, '_file_button', None)
        if file_button is not None:
            file_button.configure(state='normal' if self._prepare_file is not None else 'disabled')
        value, error = outcome
        try:
            if error is not None:
                raise error
            url, path = value
            local_file = url is None
            source = BytesIO(path.png_data) if local_file else path
            with Image.open(source) as image:
                preview = image.copy()
            preview.thumbnail((400, 320), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(preview)
            if local_file:
                self._url.set('')
            self._preview.configure(image=photo, text='')
            self._photo = photo
            self._loaded = (url, path)
            self._apply_button.configure(state='normal')
            self._status.set('画像ファイルのプレビューです。反映するとアプリ内へ保存します。' if local_file else '画像を確認し、「フォームへ反映」を押してください。')
        except Exception as error:
            self._loaded = None
            self._status.set('取得・表示に失敗しました。現在の書影は変更していません。')
            messagebox.showerror('書影URL', str(error), parent=self.window)

    def _apply(self):
        if self._loaded is not None:
            self.result = self._loaded
            self.close()

    def _clear(self):
        if messagebox.askyesno('書影の解除', 'フォームの書影を解除しますか？\n書籍への保存は「登録」「更新」で確定します。', parent=self.window):
            self.result = ('', None)
            self.close()

    def _destroyed(self, event):
        if event.widget is self.window:
            self._closed = True
            if self._after_id is not None:
                try:self.window.after_cancel(self._after_id)
                except tk.TclError:pass
                self._after_id = None

    def close(self):
        self._closed = True
        self.window.destroy()

    def show(self):
        self.window.grab_set()
        self.window.wait_window()
        return self.result
