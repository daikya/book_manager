"""書籍候補の検索とISBNの明示的な選択。"""

from __future__ import annotations

from queue import Empty, Queue
from threading import Thread
import tkinter as tk
from tkinter import messagebox, ttk

from book_manager.metadata.exceptions import (
    BookMetadataConnectionError,
    BookMetadataRateLimitError,
    BookMetadataResponseError,
)
from book_manager.models.book_search_candidate import BookSearchCandidate


class CandidateSearchTask:
    """ワーカーはTkへ触れず、同時に1要求だけを実行する。"""

    def __init__(self):
        self._thread = None
        self._results = Queue()

    @property
    def busy(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, search, *, title, author):
        if self.busy:
            return False
        while True:
            try:
                self._results.get_nowait()
            except Empty:
                break

        def run():
            try:
                value = search(title=title, author=author, max_results=20)
                self._results.put((value, None))
            except Exception as error:
                self._results.put((None, error))

        self._thread = Thread(target=run, daemon=True)
        self._thread.start()
        return True

    def poll(self):
        try:
            return self._results.get_nowait()
        except Empty:
            return None


class BookCandidateSearchDialog:
    """選択結果だけを返し、書籍情報の保存や補完は行わない。"""

    def __init__(self, parent, *, search, task, title, author):
        self.result = None
        self._search = search
        self._task = task
        self._candidates = []
        self._pending = False
        self._closed = False
        self._after_id = None
        self.window = tk.Toplevel(parent)
        self.window.title("書籍名・著者名からISBN候補を検索")
        self.window.geometry("980x620")
        self.window.minsize(700, 480)
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.bind("<Destroy>", self._on_destroy, add="+")
        frame = ttk.Frame(self.window, padding=12)
        frame.pack(fill="both", expand=True)
        self._title = tk.StringVar(self.window, title)
        self._author = tk.StringVar(self.window, author)
        self._isbn = tk.StringVar(self.window)
        self._destination = tk.StringVar(self.window, "reference")
        self._status = tk.StringVar(self.window, "条件を確認して検索してください。")
        for label, variable in (("書籍名", self._title), ("著者名", self._author)):
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, width=10).pack(side="left")
            ttk.Entry(row, textvariable=variable).pack(side="left", fill="x", expand=True)
        self._search_button = ttk.Button(frame, text="検索", command=self._start)
        self._search_button.pack(anchor="w", pady=6)
        ttk.Label(frame, textvariable=self._status, wraplength=900).pack(anchor="w")
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill="both", expand=True, pady=8)
        columns = ("title", "author", "publisher", "date", "isbn")
        self._tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse"
        )
        for key, label, width in zip(
            columns, ("書籍名・副題", "著者", "出版社", "出版日", "ISBN"),
            (310, 160, 130, 90, 170), strict=True,
        ):
            self._tree.heading(key, text=label)
            self._tree.column(key, width=width)
        ys = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        xs = ttk.Scrollbar(table_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self._tree.bind("<<TreeviewSelect>>", self._select)
        self._details = tk.StringVar(self.window)
        ttk.Label(frame, textvariable=self._details, wraplength=900).pack(anchor="w")
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=8)
        ttk.Label(row, text="使用するISBN").pack(side="left")
        self._isbn_box = ttk.Combobox(row, textvariable=self._isbn, state="readonly", width=20)
        self._isbn_box.pack(side="left", padx=8)
        ttk.Radiobutton(row, text="参照ISBN", variable=self._destination,
                        value="reference").pack(side="left")
        ttk.Radiobutton(row, text="通常ISBN", variable=self._destination,
                        value="normal").pack(side="left")
        ttk.Label(frame, text="巻・版・媒体を確認してください。別媒体・別版の情報を参照する場合は参照ISBNを選びます。",
                  wraplength=900).pack(anchor="w")
        ttk.Label(frame, text="選択したISBNを編集欄へ反映します。保存にはメイン画面の「更新」が必要です。",
                  wraplength=900).pack(anchor="w")
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=8)
        self._apply_button = ttk.Button(buttons, text="ISBNを編集欄へ反映",
                                       command=self._apply, state="disabled")
        self._apply_button.pack(side="left")
        ttk.Button(buttons, text="閉じる", command=self.close).pack(side="right")
        self.window.grab_set()

    def show(self):
        self.window.wait_window()
        return self.result

    def _start(self):
        if self._pending:
            return
        title, author = self._title.get().strip(), self._author.get().strip()
        if not title and not author:
            messagebox.showwarning("検索条件", "書籍名または著者名を入力してください。",
                                   parent=self.window)
            return
        if not self._task.start(self._search, title=title, author=author):
            self._status.set("前の検索が終了するまでお待ちください。")
            return
        self._pending = True
        self._candidates = []
        self._tree.delete(*self._tree.get_children())
        self._isbn.set("")
        self._isbn_box.configure(values=())
        self._details.set("")
        self._apply_button.configure(state="disabled")
        self._search_button.configure(state="disabled")
        self._status.set("検索中です。閉じると結果を破棄します。")
        self._after_id = self.window.after(100, self._poll)

    def _poll(self):
        self._after_id = None
        if self._closed:
            return
        result = self._task.poll()
        if result is None:
            self._after_id = self.window.after(100, self._poll)
            return
        self._pending = False
        self._search_button.configure(state="normal")
        candidates, error = result
        if error is not None:
            if isinstance(error, BookMetadataRateLimitError):
                text = "Google Booksの利用制限に達しました。時間をおいて再検索してください。"
            elif isinstance(error, BookMetadataConnectionError):
                text = "通信に失敗しました。接続を確認して再検索してください。"
            elif isinstance(error, BookMetadataResponseError):
                text = "Google Booksの応答を取得・解析できませんでした。"
            elif isinstance(error, (ValueError, TypeError)):
                text = "検索条件を確認してください。"
            else:
                text = "候補検索に失敗しました。設定を確認してください。"
            self._status.set(text)
            return
        self._candidates = candidates
        for index, candidate in enumerate(candidates):
            title = candidate.title
            if candidate.subtitle:
                title += " / " + candidate.subtitle
            self._tree.insert("", "end", iid=str(index), values=(
                title, candidate.author or "", candidate.publisher or "",
                candidate.publication_date or "",
                " / ".join(candidate.isbn_candidates) or "ISBNなし",
            ))
        self._status.set(f"{len(candidates)}件の候補。自動選択しません。"
                         if candidates else "該当する候補がありません。条件を修正して再検索できます。")

    def _select(self, _event=None):
        selection = self._tree.selection()
        if not selection:
            return
        candidate = self._candidates[int(selection[0])]
        self._isbn_box.configure(values=candidate.isbn_candidates)
        # 複数ISBNは明示的に選ぶ。1個の場合も候補選択後だけ設定する。
        self._isbn.set(candidate.isbn_candidates[0]
                       if len(candidate.isbn_candidates) == 1 else "")
        self._apply_button.configure(
            state="normal" if candidate.isbn_candidates else "disabled"
        )
        ebook = "電子書籍" if candidate.is_ebook is True else "媒体・版は要確認"
        self._details.set(
            f"取得元: {candidate.source} / {ebook}\n"
            f"書影URL: {candidate.cover_image_url or 'なし'}"
        )

    def _apply(self):
        selection = self._tree.selection()
        if self._pending or not selection:
            return
        candidate = self._candidates[int(selection[0])]
        isbn = self._isbn.get()
        if isbn not in candidate.isbn_candidates:
            messagebox.showwarning("ISBN選択", "使用するISBNを選んでください。",
                                   parent=self.window)
            return
        self.result = (isbn, self._destination.get())
        self.close()

    def _on_destroy(self, event):
        if event.widget is self.window:
            self._closed = True
            if self._after_id is not None:
                try:
                    self.window.after_cancel(self._after_id)
                except tk.TclError:
                    pass
                self._after_id = None

    def close(self):
        self._closed = True
        if self._after_id is not None:
            self.window.after_cancel(self._after_id)
            self._after_id = None
        self.window.destroy()
