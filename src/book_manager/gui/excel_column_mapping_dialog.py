"""Excelの列と書籍・読書履歴の項目を対応付ける画面。"""
from book_manager.config.window_state_store import WindowStateStore
from book_manager.gui.dialog_window_state import restore_dialog_window

import tkinter as tk
from tkinter import messagebox, ttk

from book_manager.models.excel_import import ExcelImportOptions
from book_manager.models.excel_workbook import ExcelSheetData

FIELD_LABELS = (
    ("title", "書籍名（必須）"), ("author", "著者名"),
    ("isbn", "ISBN"), ("reference_isbn", "参照ISBN"),
    ("magazine_code", "雑誌コード"), ("publisher", "出版社"),
    ("publication_format", "出版形態"), ("description", "内容紹介"),
    ("completion_month", "読了年月"), ("reading_status", "読書状態"),
    ("is_favorite", "お気に入り"), ("rating", "評価"),
    ("tags", "タグ（複数は | 区切り）"), ("notes", "書籍の備考"),
    ("started_on", "読書開始日・年月"), ("completed_on", "読了日・年月"),
    ("history_notes", "読書履歴の備考"),
)


def column_name(number: int) -> str:
    """1始まりの列番号をA、B、…、AAの表示に変換する。"""
    if type(number) is not int or number < 1:
        raise ValueError("列番号は1以上の整数で指定してください。")
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def parse_excluded_rows(text: str) -> tuple[int, ...]:
    """実際のExcel行番号をカンマ区切りまたは範囲で指定する。"""
    text = text.strip()
    if not text:
        return ()
    rows = set()
    for part in text.replace("、", ",").replace("，", ",").split(","):
        part = part.strip()
        pieces = part.split("-")
        if not all(piece.isascii() and piece.isdigit() for piece in pieces) or len(pieces) > 2:
            raise ValueError("除外行は「2,5,8-10」のように指定してください。")
        start = int(pieces[0])
        end = int(pieces[-1])
        if start < 1 or end < start or end > 100000:
            raise ValueError("除外行の範囲が不正です。")
        rows.update(range(start, end + 1))
    return tuple(sorted(rows))


class ExcelColumnMappingDialog:
    """割り当て結果を返す。DB登録やAPI検索は行わない。"""

    def __init__(self, parent: tk.Misc, sheet: ExcelSheetData,
                 *, state_store: WindowStateStore | None = None):
        self._sheet = sheet
        self.result: ExcelImportOptions | None = None
        self._window = tk.Toplevel(parent)
        self._window.title("Excelの列割り当て")
        self._window.transient(parent)
        self._window.geometry("760x700")
        self._window.minsize(620, 480)
        self._window.protocol("WM_DELETE_WINDOW", self._cancel)

        body = ttk.Frame(self._window, padding=12)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=f"シート：{sheet.sheet_name}　見出し行：{sheet.header.row_number}").pack(anchor="w")
        ttk.Label(body, text="取り込む項目に対応するExcelの列を選んでください。不要な項目は「取り込まない」のままにします。",
                  wraplength=700).pack(anchor="w", pady=(4, 10))

        scroll_frame = ttk.Frame(body)
        scroll_frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(scroll_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        fields = ttk.Frame(canvas)
        item = canvas.create_window((0, 0), window=fields, anchor="nw")
        fields.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(item, width=event.width))
        fields.columnconfigure(1, weight=1)
        fields.columnconfigure(2, weight=1)

        self._choices = ["取り込まない"] + [
            f"{column_name(index)}列：{self._display(cell.value)}"
            for index, cell in enumerate(sheet.header.cells, 1)
        ]
        self._variables = {}
        for row, (field, label) in enumerate(FIELD_LABELS):
            ttk.Label(fields, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=5)
            variable = tk.StringVar(master=self._window, value=self._choices[0])
            self._variables[field] = variable
            combo = ttk.Combobox(fields, textvariable=variable, values=self._choices,
                                 state="readonly", width=26)
            combo.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=5)
            sample = ttk.Label(fields, text="", wraplength=220)
            sample.grid(row=row, column=2, sticky="w", pady=5)
            combo.bind("<<ComboboxSelected>>", lambda _event, var=variable, widget=sample:
                       widget.configure(text=self._sample(var.get())))

        extra = ttk.Frame(body)
        extra.pack(fill="x", pady=(12, 6))
        ttk.Label(extra, text="除外するExcel行番号（例：2,5,8-10）").grid(row=0, column=0, sticky="w")
        self._excluded = tk.StringVar(master=self._window)
        ttk.Entry(extra, textvariable=self._excluded, width=28).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Label(extra, text="出版形態の列を指定しない場合の既定値").grid(row=1, column=0, sticky="w", pady=6)
        self._default_format = tk.StringVar(master=self._window)
        ttk.Entry(extra, textvariable=self._default_format, width=28).grid(row=1, column=1, sticky="ew", padx=8)
        extra.columnconfigure(1, weight=1)
        buttons = ttk.Frame(body)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="キャンセル", command=self._cancel).pack(side="right")
        ttk.Button(buttons, text="事前検査へ", command=self._confirm).pack(side="right", padx=8)
        self._window.bind("<Escape>", lambda _event: self._cancel())
        restore_dialog_window(self._window, parent, state_store,
                              default_size=(760, 700))

    @staticmethod
    def _display(value: object) -> str:
        if value is None:
            return "（空欄）"
        text = str(value).replace("\n", " ").replace("\r", " ")
        return text if len(text) <= 45 else text[:45] + "…"

    def _sample(self, choice: str) -> str:
        column = self._choices.index(choice)
        if column == 0:
            return ""
        for row in self._sheet.rows:
            cell = row.cells[column - 1]
            if cell.issue:
                return f"{cell.coordinate}：{cell.issue}"
            if cell.value is not None and str(cell.value).strip():
                return f"例：{self._display(cell.value)}"
        return "例：（空欄）"

    def _confirm(self) -> None:
        try:
            options = ExcelImportOptions(
                column_mapping=tuple((field, self._choices.index(variable.get()))
                    for field, variable in self._variables.items()
                    if variable.get() != self._choices[0]),
                excluded_rows=parse_excluded_rows(self._excluded.get()),
                default_publication_format=self._default_format.get().strip() or None,
            )
            actual_rows = {row.row_number for row in self._sheet.rows}
            if any(row not in actual_rows for row in options.excluded_rows):
                raise ValueError("除外行には、見出し行を除く実際のデータ行番号を指定してください。")
        except ValueError as error:
            messagebox.showwarning("列割り当ての確認", str(error), parent=self._window)
            return
        self.result = options
        self._window.destroy()

    def _cancel(self) -> None:
        self.result = None
        self._window.destroy()

    def show(self) -> ExcelImportOptions | None:
        self._window.grab_set()
        self._window.wait_window()
        return self.result
