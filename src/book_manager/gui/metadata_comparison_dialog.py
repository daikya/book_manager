"""取得書誌情報と現在値を比較し、反映する項目を選ぶ。"""

from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk

from book_manager.models.fetched_book_data import FetchedBookData


FIELD_LABELS = {
    "title": "書籍名",
    "author": "著者",
    "publisher": "出版社",
    "publication_format": "出版形態",
    "description": "内容紹介",
    "cover_image_url": "書影URL",
}
REFERENCE_FIELDS = frozenset({"description", "cover_image_url"})


@dataclass(frozen=True, slots=True)
class ComparisonField:
    key: str
    label: str
    current: str
    fetched: str | None
    selectable: bool
    selected: bool


def build_comparison_fields(
    current: dict[str, str],
    fetched: FetchedBookData,
    *,
    use_reference_isbn: bool,
) -> tuple[ComparisonField, ...]:
    """未取得・同値・参照ISBNの対象外は選択不可。既存値は初期保持。"""
    rows = []
    for key, label in FIELD_LABELS.items():
        old = current.get(key, "")
        value = getattr(fetched, key, None)
        available = isinstance(value, str) and bool(value.strip())
        allowed = not use_reference_isbn or key in REFERENCE_FIELDS
        selectable = available and allowed and old != value
        rows.append(ComparisonField(
            key=key, label=label, current=old,
            fetched=value if available else None,
            selectable=selectable,
            selected=selectable and not old.strip(),
        ))
    return tuple(rows)


class MetadataComparisonDialog:
    """選択された項目名だけを返す。DBや編集欄を変更しない。"""

    def __init__(self, parent, *, current, fetched, use_reference_isbn):
        self.result = None
        self.window = tk.Toplevel(parent)
        self.window.title("書誌情報の比較・反映項目の選択")
        self.window.geometry("1000x680")
        self.window.minsize(720, 480)
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)
        self._variables = {}
        self._rows = build_comparison_fields(
            current, fetched, use_reference_isbn=use_reference_isbn,
        )
        outer = ttk.Frame(self.window, padding=12)
        outer.pack(fill="both", expand=True)
        purpose = "参照ISBN（別媒体・別版からの補完）" if use_reference_isbn else "通常ISBN"
        sources = "、".join(getattr(fetched, "sources", ())) or "不明"
        identifier = fetched.isbn or "ISBNなし（選択したGoogle IDから取得）"
        ttk.Label(
            outer, text=f"取得に使用した{purpose}: {identifier}\n取得元: {sources}",
            wraplength=940,
        ).pack(anchor="w")
        if use_reference_isbn:
            source_book = " / ".join(
                value for value in (fetched.title, fetched.author, fetched.publisher)
                if isinstance(value, str) and value.strip()
            )
            ttk.Label(
                outer, text=f"参照先の書籍: {source_book or '情報なし'}\n"
                "参照ISBNでは内容紹介と書影のみ反映できます。書影は参照版の画像です。",
                wraplength=940,
            ).pack(anchor="w", pady=(4, 0))
        ttk.Label(
            outer,
            text="反映する項目をチェックしてください。既存値のある項目は初期状態で保持します。",
            wraplength=940,
        ).pack(anchor="w", pady=8)
        container = ttk.Frame(outer)
        container.pack(fill="both", expand=True)
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        body = ttk.Frame(canvas)
        item = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(item, width=event.width))
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, weight=1)
        for column, text in enumerate(("反映", "現在の値", "取得した値")):
            ttk.Label(body, text=text).grid(row=0, column=column, sticky="w", padx=6, pady=4)
        for index, row in enumerate(self._rows, start=1):
            variable = tk.BooleanVar(self.window, row.selected)
            self._variables[row.key] = variable
            option = ttk.Frame(body)
            option.grid(row=index, column=0, sticky="nw", padx=6, pady=6)
            ttk.Checkbutton(
                option, text=row.label, variable=variable,
                state="normal" if row.selectable else "disabled",
            ).pack(anchor="w")
            if not row.selectable:
                if use_reference_isbn and row.key not in REFERENCE_FIELDS:
                    reason = "元の値を保持"
                elif row.fetched is None:
                    reason = "未取得"
                else:
                    reason = "変更なし"
                ttk.Label(option, text=reason).pack(anchor="w")
            height = 6 if row.key == "description" else 3
            for column, value in ((1, row.current), (2, row.fetched)):
                cell = ttk.Frame(body)
                cell.grid(row=index, column=column, sticky="nsew", padx=6, pady=6)
                text = tk.Text(cell, width=28, height=height, wrap="word")
                ys = ttk.Scrollbar(cell, orient="vertical", command=text.yview)
                text.configure(yscrollcommand=ys.set)
                text.pack(side="left", fill="both", expand=True)
                ys.pack(side="right", fill="y")
                text.insert("1.0", value if value else "（なし）")
                text.configure(state="disabled")
        ttk.Label(
            outer, text="編集欄への反映のみです。DBへ保存するにはメイン画面の「更新」を押してください。",
            wraplength=940,
        ).pack(anchor="w", pady=8)
        buttons = ttk.Frame(outer)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="選択した項目を反映", command=self._confirm).pack(side="left")
        ttk.Button(buttons, text="キャンセル", command=self.window.destroy).pack(side="right")
        self.window.grab_set()

    def _confirm(self):
        self.result = frozenset(
            row.key for row in self._rows
            if row.selectable and self._variables[row.key].get()
        )
        self.window.destroy()

    def show(self):
        self.window.wait_window()
        return self.result
