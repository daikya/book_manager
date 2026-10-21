"""Excel取込の登録予定と検査結果を確認する画面。"""
from book_manager.config.window_state_store import WindowStateStore
from book_manager.gui.dialog_window_state import restore_dialog_window

import tkinter as tk
from tkinter import messagebox, ttk

from book_manager.gui.excel_column_mapping_dialog import FIELD_LABELS
from book_manager.models.excel_import import ExcelImportPreview, ExcelImportRecord

STATE_LABELS = {None: "未設定", "unread": "未読", "reading": "読書中", "completed": "読了"}


def record_details(record: ExcelImportRecord) -> str:
    """各行の登録内容を省略せず表示する。"""
    labels = dict(FIELD_LABELS)
    lines = [f"Excel行番号：{record.row_number}"]
    for field, _label in FIELD_LABELS:
        if field in ("started_on", "completed_on", "history_notes"):
            value = getattr(record, field)
        else:
            value = getattr(record.book, field)
        if field == "reading_status":
            value = STATE_LABELS.get(value, value)
            if record.reading_status_suggested:
                value = f"{value}（日付からの提案）"
        elif field == "is_favorite":
            value = "はい" if value else "いいえ"
        elif field == "tags":
            value = " | ".join(value)
        if value is None or value == "":
            value = "（空欄）"
        lines.append(f"{labels[field]}：{value}")
    lines.append(f"読書履歴の追加：{'あり' if record.has_history else 'なし'}")
    return "\n".join(lines)


def preview_summary(preview: ExcelImportPreview) -> str:
    histories = sum(record.has_history for record in preview.records)
    return (f"登録予定：書籍 {len(preview.records)} 件／読書履歴 {histories} 件\n"
            f"エラー {len(preview.errors)} 件／注意事項 {len(preview.warnings)} 件／"
            f"除外・空行 {len(preview.skipped)} 件")


class ExcelImportPreviewDialog:
    """利用者の承認だけを返す。登録処理は呼び出し元が実行する。"""

    def __init__(self, parent: tk.Misc, preview: ExcelImportPreview,
                 *, state_store: WindowStateStore | None = None):
        self._preview = preview
        self.result = False
        self._window = tk.Toplevel(parent)
        self._window.title("Excel取込の事前検査")
        self._window.transient(parent)
        self._window.geometry("900x720")
        self._window.minsize(680, 500)
        self._window.protocol("WM_DELETE_WINDOW", self._cancel)
        body = ttk.Frame(self._window, padding=12)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=f"ファイル：{preview.source_path.name}　シート：{preview.sheet_name}",
                  wraplength=850).pack(anchor="w")
        ttk.Label(body, text=preview_summary(preview)).pack(anchor="w", pady=8)
        if preview.errors:
            status = "エラーがあります。登録は行えません。Excelまたは列割り当てを修正してください。"
        elif not preview.records:
            status = "登録するデータがありません。列割り当てや除外行を確認してください。"
        else:
            status = "登録予定と注意事項を確認してください。同じISBN・書籍名の行も別の書籍として追加します。"
        ttk.Label(body, text=status, wraplength=850).pack(anchor="w", pady=(0, 8))

        notebook = ttk.Notebook(body)
        notebook.pack(fill="both", expand=True)
        planned = ttk.Frame(notebook, padding=6)
        notebook.add(planned, text=f"登録予定 ({len(preview.records)})")
        planned.rowconfigure(0, weight=1)
        planned.rowconfigure(1, weight=1)
        planned.columnconfigure(0, weight=1)
        table_frame = ttk.Frame(planned)
        table_frame.grid(row=0, column=0, sticky="nsew")
        self._records_table = self._table(table_frame,
            (("row", "Excel行", 65), ("title", "書籍名", 230), ("author", "著者名", 150),
             ("state", "読書状態", 100), ("date", "読了日・年月", 115)))
        for index, record in enumerate(preview.records):
            state = STATE_LABELS.get(record.book.reading_status, record.book.reading_status)
            if record.reading_status_suggested:
                state = f"{state}（提案）"
            self._records_table.insert("", "end", iid=str(index), values=(
                record.row_number, record.book.title, record.book.author or "",
                state, record.completed_on or ""))
        detail_frame = ttk.Frame(planned)
        detail_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self._details = tk.Text(detail_frame, height=10, wrap="word", state="disabled")
        detail_scroll = ttk.Scrollbar(detail_frame, orient="vertical", command=self._details.yview)
        self._details.configure(yscrollcommand=detail_scroll.set)
        detail_scroll.pack(side="right", fill="y")
        self._details.pack(fill="both", expand=True)
        self._records_table.bind("<<TreeviewSelect>>", self._show_details)
        if preview.records:
            self._records_table.selection_set("0")
            self._show_details()

        for label, issues in (("エラー", preview.errors), ("注意事項", preview.warnings),
                              ("除外・空行", preview.skipped)):
            page = ttk.Frame(notebook, padding=6)
            notebook.add(page, text=f"{label} ({len(issues)})")
            table = self._table(page, (("row", "Excel行", 65), ("cell", "セル", 75),
                                       ("message", "内容", 680)))
            for issue in issues:
                table.insert("", "end", values=(issue.row_number, issue.coordinate or "", issue.message))

        ttk.Label(body, text="取込前にバックアップを作成します。書籍情報のAPI検索は、取り込み後に個別に行います。",
                  wraplength=850).pack(anchor="w", pady=(10, 4))
        self._accepted = tk.BooleanVar(master=self._window, value=False)
        ttk.Checkbutton(body, text="登録予定と注意事項を確認しました", variable=self._accepted,
                        command=self._update_button).pack(anchor="w")
        buttons = ttk.Frame(body)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="戻る／キャンセル", command=self._cancel).pack(side="right")
        self._import_button = ttk.Button(buttons, text="取り込む", command=self._confirm, state="disabled")
        self._import_button.pack(side="right", padx=8)
        self._window.bind("<Escape>", lambda _event: self._cancel())
        restore_dialog_window(self._window, parent, state_store,
                              default_size=(900, 720))

    @staticmethod
    def _table(parent: tk.Misc, columns: tuple) -> ttk.Treeview:
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        table = ttk.Treeview(parent, columns=tuple(item[0] for item in columns),
                             show="headings", selectmode="browse", height=8)
        for key, label, width in columns:
            table.heading(key, text=label)
            table.column(key, width=width, minwidth=50)
        vertical = ttk.Scrollbar(parent, orient="vertical", command=table.yview)
        horizontal = ttk.Scrollbar(parent, orient="horizontal", command=table.xview)
        table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        table.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        return table

    def _show_details(self, _event=None) -> None:
        selection = self._records_table.selection()
        if not selection:
            return
        record = self._preview.records[int(selection[0])]
        self._details.configure(state="normal")
        self._details.delete("1.0", "end")
        self._details.insert("1.0", record_details(record))
        self._details.configure(state="disabled")

    def _update_button(self) -> None:
        enabled = self._preview.can_import and self._accepted.get()
        self._import_button.configure(state="normal" if enabled else "disabled")

    def _confirm(self) -> None:
        if not self._preview.can_import or not self._accepted.get():
            messagebox.showwarning("取込の確認", "登録可能なデータと確認チェックが必要です。", parent=self._window)
            return
        self.result = True
        self._window.destroy()

    def _cancel(self) -> None:
        self.result = False
        self._window.destroy()

    def show(self) -> bool:
        self._window.grab_set()
        self._window.wait_window()
        return self.result
