"""書籍候補の検索とISBNの明示的な選択。"""

from __future__ import annotations

from book_manager.metadata.candidate_matching import candidate_match, prepare_search_terms, rank_candidates

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

    def start(self, search, *, title, author, publisher="", start_index=0):
        options = {"start_index": start_index} if start_index else {}
        return self.start_operation(lambda: search(title=title, author=author, publisher=publisher, max_results=20, **options))

    def start_operation(self, operation):
        if self.busy:
            return False
        while True:
            try:
                self._results.get_nowait()
            except Empty:
                break

        def run():
            try:
                value = operation()
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
    """候補の詳細を取得して返す。フォームとDBの更新は親画面で行う。"""

    def __init__(self, parent, *, search, task, title, author, publisher="", fetch=None):
        self.result = None
        self._fetch = fetch
        self._operation = "search"
        self._start_index = 0
        self._all_candidates = []
        self._search = search
        self._task = task
        self._candidates = []
        self._pending = False
        self._closed = False
        self._after_id = None
        self.window = tk.Toplevel(parent)
        self.window.title("書籍名・著者名・出版社からISBN候補を検索")
        self.window.geometry("980x620")
        self.window.minsize(700, 480)
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.bind("<Destroy>", self._on_destroy, add="+")
        frame = ttk.Frame(self.window, padding=12)
        frame.pack(fill="both", expand=True)
        self._title = tk.StringVar(self.window, title)
        self._author = tk.StringVar(self.window, author)
        self._publisher = tk.StringVar(self.window, publisher)
        self._conditions = {}
        self._entries = []
        self._isbn = tk.StringVar(self.window)
        self._destination = tk.StringVar(self.window, "normal")
        self._only_matches = tk.BooleanVar(self.window, False)
        self._status = tk.StringVar(self.window, "条件を確認して検索してください。")
        for label, variable in (("書籍名", self._title), ("著者名", self._author), ("出版社", self._publisher)):
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, width=10).pack(side="left")
            entry = ttk.Entry(row, textvariable=variable)
            entry.pack(side="left", fill="x", expand=True)
            self._entries.append(entry)
        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=6)
        self._search_button = ttk.Button(controls, text="検索", command=self._start)
        self._search_button.pack(side="left")
        self._broaden_button = ttk.Button(controls, text="条件別に追加検索（最大3回）", command=self._broaden)
        self._broaden_button.pack(side="left", padx=6)
        self._next_button = ttk.Button(controls, text="次の20件", command=self._next_page, state="disabled")
        self._next_button.pack(side="left")
        ttk.Checkbutton(controls, text="一致・部分一致のみ表示", variable=self._only_matches,
                        command=self._render).pack(side="left", padx=6)
        ttk.Label(frame, text="取得先: Google Books / 一致の目安は取得済み候補の比較です。", wraplength=900).pack(anchor="w")
        ttk.Label(frame, textvariable=self._status, wraplength=900).pack(anchor="w")
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill="both", expand=True, pady=8)
        columns = ("title", "author", "publisher", "date", "isbn", "match")
        self._tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse", height=5
        )
        for key, label, width in zip(
            columns, ("書籍名・副題", "著者", "出版社", "出版日", "ISBN", "一致の目安"),
            (260, 130, 110, 85, 150, 310), strict=True,
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
        ttk.Label(frame, text="選択候補の書誌情報を比較後に反映します。保存にはメイン画面の「登録」「更新」が必要です。",
                  wraplength=900).pack(anchor="w")
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=8)
        self._apply_button = ttk.Button(buttons, text="書誌情報を取得して比較",
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
        publisher = self._publisher.get().strip()
        try:
            prepare_search_terms(title=title, author=author, publisher=publisher)
        except (ValueError, TypeError) as error:
            messagebox.showwarning("検索条件", str(error), parent=self.window)
            return
        if not self._task.start(self._search, title=title, author=author, publisher=publisher):
            self._status.set("前の検索が終了するまでお待ちください。")
            return
        self._conditions = dict(title=title, author=author, publisher=publisher)
        for entry in self._entries:
            entry.configure(state="disabled")
        self._operation = "search"
        self._start_index = 0
        self._all_candidates = []
        self._next_button.configure(state="disabled")
        self._broaden_button.configure(state="disabled")
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
        for entry in self._entries:
            entry.configure(state="normal")
        self._search_button.configure(state="normal")
        self._broaden_button.configure(state="normal")
        self._next_button.configure(state="normal" if self._conditions and self._start_index < 180 else "disabled")
        candidates, error = result
        if error is not None:
            if self._operation == "page":
                self._start_index = max(0, self._start_index - 20)
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
            self._select()
            return
        if self._operation == "detail":
            self.result = (candidates, self._detail_destination)
            self.close()
            return
        seen = {c.source_id for c in self._all_candidates if c.source_id}
        for candidate in candidates:
            if candidate.source_id and candidate.source_id in seen:
                continue
            self._all_candidates.append(candidate)
            if candidate.source_id:
                seen.add(candidate.source_id)
        self._all_candidates = rank_candidates(self._all_candidates, **self._conditions)
        self._render()
        self._next_button.configure(state="normal" if candidates and self._start_index < 180 else "disabled")

    def _render(self):
        if self._pending:
            return
        self._tree.delete(*self._tree.get_children())
        self._isbn.set("")
        self._isbn_box.configure(values=())
        self._details.set("")
        self._apply_button.configure(state="disabled")
        candidates = self._all_candidates
        if self._only_matches.get():
            count = sum(bool(v.strip()) for v in self._conditions.values())
            candidates = [c for c in candidates if candidate_match(c, **self._conditions)[0][1] == count]
        self._candidates = candidates
        for index, candidate in enumerate(candidates):
            title = candidate.title
            if candidate.subtitle:
                title += " / " + candidate.subtitle
            self._tree.insert("", "end", iid=str(index), values=(
                title, candidate.author or "", candidate.publisher or "",
                candidate.publication_date or "",
                " / ".join(candidate.isbn_candidates) or "ISBNなし",
                candidate_match(candidate, **self._conditions)[1],
            ))
        self._status.set(f"表示{len(candidates)}件 / 取得済み{len(self._all_candidates)}件（一致の目安順）。"
                         if candidates else "候補がありません。空白・記号を変えるか、一部の条件を空欄にして再検索してください。")

    def _additional(self, operation, kind):
        if self._pending or not self._conditions:
            return
        current = dict(title=self._title.get().strip(), author=self._author.get().strip(), publisher=self._publisher.get().strip())
        if current != self._conditions:
            self._status.set("条件が変わりました。まず「検索」を押してください。")
            return
        if not self._task.start_operation(operation):
            return
        self._operation = kind
        self._pending = True
        for entry in self._entries:
            entry.configure(state="disabled")
        for button in (self._search_button, self._broaden_button, self._next_button, self._apply_button):
            button.configure(state="disabled")
        self._status.set("取得中です。閉じると結果を破棄します。")
        self._after_id = self.window.after(100, self._poll)

    def _next_page(self):
        if self._start_index >= 180 or self._pending:
            return
        index = self._start_index + 20
        def search():
            return self._search(**self._conditions, max_results=20, start_index=index)
        self._additional(search, "page")
        if self._pending:
            self._start_index = index

    def _broaden(self):
        if not self._conditions:
            self._start()
            return
        if sum(bool(v) for v in self._conditions.values()) < 2:
            self._status.set("条件別の追加検索には2項目以上を指定してください。")
            return
        conditions = self._conditions.copy()
        def search():
            results = []
            for key, value in conditions.items():
                if value:
                    results.extend(self._search(**{key: value}, max_results=20))
            return results
        self._additional(search, "broaden")

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
            state="normal" if candidate.source_id else "disabled"
        )
        ebook = "電子書籍" if candidate.is_ebook is True else "媒体・版は要確認"
        self._details.set(
            f"取得元: {candidate.source} / {ebook}\n"
            f"{candidate_match(candidate, **self._conditions)[1]}\n"
            f"書影URL: {candidate.cover_image_url or 'なし'}"
        )

    def _apply(self):
        selection = self._tree.selection()
        if self._pending or not selection:
            return
        candidate = self._candidates[int(selection[0])]
        isbn = self._isbn.get()
        if candidate.isbn_candidates and isbn not in candidate.isbn_candidates:
            messagebox.showwarning("ISBN選択", "使用するISBNを選んでください。", parent=self.window)
            return
        if self._fetch is None or not candidate.source_id:
            self._status.set("候補の詳細を取得できません。")
            return
        self._detail_destination = self._destination.get()
        self._additional(lambda: self._fetch(candidate, isbn=isbn), "detail")

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
