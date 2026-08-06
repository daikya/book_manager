"""書籍管理アプリケーションのメインGUI。"""

from __future__ import annotations

import tkinter as tk
import traceback
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING
from PIL import Image, ImageTk

from book_manager.models.book_item import BookItem
from book_manager.models.fetched_book_data import (
    FetchedBookData,
)

from book_manager.metadata.exceptions import (
    BookMetadataConfigurationError,
    BookMetadataConnectionError,
    BookMetadataNotFoundError,
    BookMetadataRateLimitError,
    BookMetadataResponseError,
)

if TYPE_CHECKING:
    from book_manager.services.book_service import BookService

class BookManagerApplication:
    """書籍管理アプリケーションのメインウィンドウを管理する。"""

    WINDOW_TITLE = "書籍管理"
    WINDOW_SIZE = "1350x760"
    MINIMUM_WIDTH = 1150
    MINIMUM_HEIGHT = 650

    SEARCH_TYPES = (
        "書籍名",
        "ISBN",
        "雑誌コード",
    )

    PUBLICATION_FORMATS = (
        "",
        "文庫",
        "単行本",
        "新書",
        "雑誌",
        "電子書籍",
        "その他",
    )

    TREE_COLUMNS = (
        "id",
        "title",
        "author",
        "publisher",
        "publication_format",
        "isbn",
        "magazine_code",
        "completion_month",
    )

    def __init__(
        self,
        root: tk.Tk,
        service: BookService,
    ) -> None:
        """GUIを初期化する。

        Args:
            root: Tkinterのルートウィンドウ。
            service: 書籍管理処理を提供するBookService。
        """
        self._root = root
        self._service = service

        self._selected_book_id: int | None = None
        self._cover_photo: tk.PhotoImage | None = None
        self._search_type_var = tk.StringVar(
            master=self._root,
            value=self.SEARCH_TYPES[0],
        )
        self._search_keyword_var = tk.StringVar(
            master=self._root,
        )

        self._title_var = tk.StringVar(
            master=self._root,
        )
        self._isbn_var = tk.StringVar(
            master=self._root,
        )
        self._magazine_code_var = tk.StringVar(
            master=self._root,
        )
        self._author_var = tk.StringVar(
            master=self._root,
        )
        self._publisher_var = tk.StringVar(
            master=self._root,
        )
        self._publication_format_var = tk.StringVar(
            master=self._root,
        )
        self._completion_month_var = tk.StringVar(
            master=self._root,
        )

        self._count_status_var = tk.StringVar(
            master=self._root,
            value="全 0件",
        )
        self._edit_status_var = tk.StringVar(
            master=self._root,
            value="新規登録",
        )

        self._configure_root()
        self._create_widgets()
        self._load_all_books()

        self._title_entry.focus_set()

    def _configure_root(self) -> None:
        """メインウィンドウを設定する。"""
        self._root.title(self.WINDOW_TITLE)
        self._root.geometry(self.WINDOW_SIZE)
        self._root.minsize(
            self.MINIMUM_WIDTH,
            self.MINIMUM_HEIGHT,
        )

        self._root.rowconfigure(
            0,
            weight=1,
        )
        self._root.columnconfigure(
            0,
            weight=1,
        )

        self._root.protocol(
            "WM_DELETE_WINDOW",
            self._on_exit,
        )

    def _create_widgets(self) -> None:
        """メインウィンドウ内のウィジェットを作成する。"""
        main_frame = ttk.Frame(
            self._root,
            padding=10,
        )
        main_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        main_frame.columnconfigure(
            0,
            weight=1,
        )
        main_frame.rowconfigure(
            1,
            weight=3,
        )
        main_frame.rowconfigure(
            2,
            weight=2,
        )

        self._create_search_frame(
            main_frame,
        )
        self._create_list_frame(
            main_frame,
        )
        self._create_form_frame(
            main_frame,
        )
        self._create_button_frame(
            main_frame,
        )
        self._set_edit_buttons_enabled(
            False,
        )
        self._create_status_frame(
            main_frame,
        )

    def _set_edit_buttons_enabled(
        self,
        enabled: bool,
    ) -> None:
        """更新・削除ボタンの有効状態を設定する。"""
        state = "normal" if enabled else "disabled"

        self._update_button.configure(
            state=state,
        )
        self._delete_button.configure(
            state=state,
        )

    def _create_search_frame(
        self,
        parent: ttk.Frame,
    ) -> None:
        """検索領域を作成する。"""
        search_frame = ttk.LabelFrame(
            parent,
            text="検索",
            padding=8,
        )
        search_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        search_frame.columnconfigure(
            2,
            weight=1,
        )

        ttk.Label(
            search_frame,
            text="検索種類",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 6),
        )

        self._search_type_combobox = ttk.Combobox(
            search_frame,
            textvariable=self._search_type_var,
            values=self.SEARCH_TYPES,
            state="readonly",
            width=12,
        )
        self._search_type_combobox.grid(
            row=0,
            column=1,
            sticky="w",
            padx=(0, 10),
        )

        self._search_entry = ttk.Entry(
            search_frame,
            textvariable=self._search_keyword_var,
        )
        self._search_entry.grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(0, 8),
        )
        self._search_entry.bind(
            "<Return>",
            self._on_search,
        )

        self._search_button = ttk.Button(
            search_frame,
            text="検索",
            command=self._on_search,
        )
        self._search_button.grid(
            row=0,
            column=3,
            padx=(0, 6),
        )

        self._show_all_button = ttk.Button(
            search_frame,
            text="全件表示",
            command=self._on_show_all,
        )
        self._show_all_button.grid(
            row=0,
            column=4,
            padx=(0, 6),
        )

        self._clear_search_button = ttk.Button(
            search_frame,
            text="検索条件クリア",
            command=self._on_clear_search,
        )
        self._clear_search_button.grid(
            row=0,
            column=5,
        )

    def _create_list_frame(
        self,
        parent: ttk.Frame,
    ) -> None:
        """書籍一覧領域を作成する。"""
        list_frame = ttk.LabelFrame(
            parent,
            text="書籍一覧",
            padding=8,
        )
        list_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
            pady=(0, 8),
        )

        list_frame.rowconfigure(
            0,
            weight=1,
        )
        list_frame.columnconfigure(
            0,
            weight=1,
        )

        self._book_tree = ttk.Treeview(
            list_frame,
            columns=self.TREE_COLUMNS,
            show="headings",
            selectmode="browse",
        )

        self._configure_tree_columns()

        vertical_scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self._book_tree.yview,
        )
        horizontal_scrollbar = ttk.Scrollbar(
            list_frame,
            orient="horizontal",
            command=self._book_tree.xview,
        )

        self._book_tree.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )

        self._book_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        vertical_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )
        horizontal_scrollbar.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        self._book_tree.bind(
            "<<TreeviewSelect>>",
            self._on_tree_select,
        )

    def _configure_tree_columns(self) -> None:
        """書籍一覧の列を設定する。"""
        column_definitions = {
            "id": {
                "heading": "ID",
                "width": 60,
                "minwidth": 50,
                "anchor": "center",
                "stretch": False,
            },
            "title": {
                "heading": "書籍名",
                "width": 250,
                "minwidth": 160,
                "anchor": "w",
                "stretch": True,
            },
            "author": {
                "heading": "著者名",
                "width": 160,
                "minwidth": 100,
                "anchor": "w",
                "stretch": True,
            },
            "publisher": {
                "heading": "出版社",
                "width": 140,
                "minwidth": 100,
                "anchor": "w",
                "stretch": True,
            },
            "publication_format": {
                "heading": "出版形態",
                "width": 90,
                "minwidth": 80,
                "anchor": "center",
                "stretch": False,
            },
            "isbn": {
                "heading": "ISBN",
                "width": 130,
                "minwidth": 110,
                "anchor": "w",
                "stretch": False,
            },
            "magazine_code": {
                "heading": "雑誌コード",
                "width": 100,
                "minwidth": 90,
                "anchor": "center",
                "stretch": False,
            },
            "completion_month": {
                "heading": "読了年月",
                "width": 90,
                "minwidth": 80,
                "anchor": "center",
                "stretch": False,
            },
        }

        for column_name, definition in column_definitions.items():
            self._book_tree.heading(
                column_name,
                text=definition["heading"],
            )
            self._book_tree.column(
                column_name,
                width=definition["width"],
                minwidth=definition["minwidth"],
                anchor=definition["anchor"],
                stretch=definition["stretch"],
            )

    def _create_form_frame(
        self,
        parent: ttk.Frame,
    ) -> None:
        """書籍情報入力領域を作成する。"""
        form_frame = ttk.LabelFrame(
            parent,
            text="書籍情報",
            padding=8,
        )
        form_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            pady=(0, 8),
        )

        form_frame.columnconfigure(
            1,
            weight=1,
        )
        form_frame.columnconfigure(
            3,
            weight=1,
        )
        form_frame.columnconfigure(
            4,
            weight=0,
            minsize=190,
        )
        form_frame.rowconfigure(
            4,
            weight=1,
        )
        form_frame.rowconfigure(
            5,
            weight=1,
        )

        ttk.Label(
            form_frame,
            text="書籍名 *",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 6),
            pady=4,
        )

        self._title_entry = ttk.Entry(
            form_frame,
            textvariable=self._title_var,
        )
        self._title_entry.grid(
            row=0,
            column=1,
            columnspan=3,
            sticky="ew",
            pady=4,
        )

        ttk.Label(
            form_frame,
            text="著者名",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 6),
            pady=4,
        )

        self._author_entry = ttk.Entry(
            form_frame,
            textvariable=self._author_var,
        )
        self._author_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=4,
        )

        ttk.Label(
            form_frame,
            text="出版社",
        ).grid(
            row=1,
            column=2,
            sticky="w",
            padx=(0, 6),
            pady=4,
        )

        self._publisher_entry = ttk.Entry(
            form_frame,
            textvariable=self._publisher_var,
        )
        self._publisher_entry.grid(
            row=1,
            column=3,
            sticky="ew",
            pady=4,
        )

        ttk.Label(
            form_frame,
            text="出版形態",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=(0, 6),
            pady=4,
        )

        self._publication_format_combobox = ttk.Combobox(
            form_frame,
            textvariable=self._publication_format_var,
            values=self.PUBLICATION_FORMATS,
        )
        self._publication_format_combobox.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=4,
        )

        ttk.Label(
            form_frame,
            text="読了年月",
        ).grid(
            row=2,
            column=2,
            sticky="w",
            padx=(0, 6),
            pady=4,
        )

        completion_month_frame = ttk.Frame(
            form_frame,
        )
        completion_month_frame.grid(
            row=2,
            column=3,
            sticky="ew",
            pady=4,
        )
        completion_month_frame.columnconfigure(
            0,
            weight=1,
        )

        self._completion_month_entry = ttk.Entry(
            completion_month_frame,
            textvariable=self._completion_month_var,
        )
        self._completion_month_entry.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        ttk.Label(
            completion_month_frame,
            text="例：2026-07",
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(6, 0),
        )

        ttk.Label(
            form_frame,
            text="ISBN",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=(0, 6),
            pady=4,
        )

        self._isbn_entry = ttk.Entry(
            form_frame,
            textvariable=self._isbn_var,
        )
        self._isbn_entry.grid(
            row=3,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=4,
        )

        ttk.Label(
            form_frame,
            text="雑誌コード",
        ).grid(
            row=3,
            column=2,
            sticky="w",
            padx=(0, 6),
            pady=4,
        )

        self._magazine_code_entry = ttk.Entry(
            form_frame,
            textvariable=self._magazine_code_var,
        )
        self._magazine_code_entry.grid(
            row=3,
            column=3,
            sticky="ew",
            pady=4,
        )

        ttk.Label(
            form_frame,
            text="内容紹介",
        ).grid(
            row=4,
            column=0,
            sticky="nw",
            padx=(0, 6),
            pady=4,
        )

        description_frame = ttk.Frame(
            form_frame,
        )
        description_frame.grid(
            row=4,
            column=1,
            columnspan=3,
            sticky="nsew",
            pady=4,
        )
        description_frame.rowconfigure(
            0,
            weight=1,
        )
        description_frame.columnconfigure(
            0,
            weight=1,
        )

        self._description_text = tk.Text(
            description_frame,
            height=4,
            wrap="word",
        )
        description_scrollbar = ttk.Scrollbar(
            description_frame,
            orient="vertical",
            command=self._description_text.yview,
        )
        self._description_text.configure(
            yscrollcommand=description_scrollbar.set,
        )

        self._description_text.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        description_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        ttk.Label(
            form_frame,
            text="備考",
        ).grid(
            row=5,
            column=0,
            sticky="nw",
            padx=(0, 6),
            pady=4,
        )

        notes_frame = ttk.Frame(
            form_frame,
        )
        notes_frame.grid(
            row=5,
            column=1,
            columnspan=3,
            sticky="nsew",
            pady=4,
        )
        notes_frame.rowconfigure(
            0,
            weight=1,
        )
        notes_frame.columnconfigure(
            0,
            weight=1,
        )

        self._notes_text = tk.Text(
            notes_frame,
            height=4,
            wrap="word",
        )
        notes_scrollbar = ttk.Scrollbar(
            notes_frame,
            orient="vertical",
            command=self._notes_text.yview,
        )
        self._notes_text.configure(
            yscrollcommand=notes_scrollbar.set,
        )

        self._notes_text.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        notes_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )
        cover_frame = ttk.LabelFrame(
            form_frame,
            text="表紙画像",
            padding=8,
        )
        cover_frame.grid(
            row=0,
            column=4,
            rowspan=6,
            sticky="ns",
            padx=(12, 0),
            pady=4,
        )

        self._cover_image_label = ttk.Label(
            cover_frame,
            text="画像なし",
            anchor="center",
            width=22,
        )
        self._cover_image_label.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        cover_frame.rowconfigure(
            0,
            weight=1,
        )
        cover_frame.columnconfigure(
            0,
            weight=1,
        )

    def _create_button_frame(
        self,
        parent: ttk.Frame,
    ) -> None:
        """操作ボタン領域を作成する。"""
        button_frame = ttk.Frame(
            parent,
        )
        button_frame.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

        button_frame.columnconfigure(
            7,
            weight=1,
        )

        self._add_button = ttk.Button(
            button_frame,
            text="新規登録",
            command=self._on_add,
        )
        self._add_button.grid(
            row=0,
            column=0,
            padx=(0, 6),
        )

        self._update_button = ttk.Button(
            button_frame,
            text="更新",
            command=self._on_update,
        )
        self._update_button.grid(
            row=0,
            column=1,
            padx=(0, 6),
        )

        self._delete_button = ttk.Button(
            button_frame,
            text="削除",
            command=self._on_delete,
        )
        self._delete_button.grid(
            row=0,
            column=2,
            padx=(0, 6),
        )

        self._fetch_metadata_button = ttk.Button(
            button_frame,
            text="書誌情報取得",
            command=self._on_fetch_book_metadata,
        )
        self._fetch_metadata_button.grid(
            row=0,
            column=3,
            padx=(0, 6),
        )

        self._clear_button = ttk.Button(
            button_frame,
            text="入力クリア",
            command=self._on_clear,
        )
        self._clear_button.grid(
            row=0,
            column=4,
            padx=(0, 6),
        )

        self._reload_button = ttk.Button(
            button_frame,
            text="再読み込み",
            command=self._on_reload,
        )
        self._reload_button.grid(
            row=0,
            column=5,
            padx=(0, 6),
        )

        self._exit_button = ttk.Button(
            button_frame,
            text="終了",
            command=self._on_exit,
        )
        self._exit_button.grid(
            row=0,
            column=8,
            sticky="e",
        )

    def _create_status_frame(
        self,
        parent: ttk.Frame,
    ) -> None:
        """状態表示領域を作成する。"""
        status_frame = ttk.Frame(
            parent,
            relief="sunken",
            padding=(6, 3),
        )
        status_frame.grid(
            row=4,
            column=0,
            sticky="ew",
        )

        status_frame.columnconfigure(
            0,
            weight=1,
        )

        ttk.Label(
            status_frame,
            textvariable=self._count_status_var,
            anchor="w",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        ttk.Label(
            status_frame,
            textvariable=self._edit_status_var,
            anchor="e",
        ).grid(
            row=0,
            column=1,
            sticky="e",
        )

    def _load_all_books(self) -> None:
        """全書籍を取得して一覧へ表示する。"""
        try:
            books = self._service.get_all_books()
            self._display_books(
                books,
                status_prefix="全",
            )
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "読み込みエラー",
                "書籍情報を読み込めませんでした。",
                parent=self._root,
            )

    def _display_books(
        self,
        books: list[BookItem],
        *,
        status_prefix: str,
    ) -> None:
        """書籍一覧をTreeViewへ表示する。

        Args:
            books: 表示する書籍一覧。
            status_prefix: 件数表示の先頭文字列。
        """
        for item_id in self._book_tree.get_children():
            self._book_tree.delete(
                item_id,
            )

        displayed_count = 0

        for book in books:
            if book.id is None:
                continue

            self._book_tree.insert(
                "",
                "end",
                iid=str(book.id),
                values=(
                    book.id,
                    book.title,
                    book.author or "",
                    book.publisher or "",
                    book.publication_format or "",
                    book.isbn or "",
                    book.magazine_code or "",
                    book.completion_month or "",
                ),
            )
            displayed_count += 1

        self._count_status_var.set(
            f"{status_prefix} {displayed_count}件",
        )

    def _display_book_in_form(
        self,
        book_item: BookItem,
    ) -> None:
        """BookItemの内容を入力フォームへ表示する。

        Args:
            book_item: 表示する書籍。
        """
        if book_item.id is None:
            raise ValueError(
                "表示対象のBookItemにはidが必要です。",
            )

        self._title_var.set(
            book_item.title,
        )
        self._isbn_var.set(
            book_item.isbn or "",
        )
        self._magazine_code_var.set(
            book_item.magazine_code or "",
        )
        self._author_var.set(
            book_item.author or "",
        )
        self._publisher_var.set(
            book_item.publisher or "",
        )
        self._publication_format_var.set(
            book_item.publication_format or "",
        )
        self._completion_month_var.set(
            book_item.completion_month or "",
        )

        self._replace_text(
            self._description_text,
            book_item.description,
        )
        self._replace_text(
            self._notes_text,
            book_item.notes,
        )

        self._selected_book_id = book_item.id
        self._edit_status_var.set(
            f"編集中：ID {book_item.id}",
        )
        self._set_edit_buttons_enabled(
            True,
        )
        self._clear_cover_image()

    @staticmethod
    def _replace_text(
        text_widget: tk.Text,
        value: str | None,
    ) -> None:
        """Textウィジェットの内容を置き換える。"""
        text_widget.delete(
            "1.0",
            tk.END,
        )
        text_widget.insert(
            "1.0",
            value or "",
        )

    def _has_metadata_input_values(self) -> bool:
        """外部書誌情報の反映対象欄に入力があるか確認する。"""
        values = (
            self._title_var.get(),
            self._author_var.get(),
            self._publisher_var.get(),
            self._publication_format_var.get(),
            self._description_text.get(
                "1.0",
                tk.END,
            ),
        )

        return any(
            value.strip()
            for value in values
        )

    def _confirm_metadata_overwrite(self) -> bool:
        """入力済み書誌情報を上書きするか確認する。"""
        if not self._has_metadata_input_values():
            return True

        return messagebox.askyesno(
            "書誌情報の上書き確認",
            (
                "すでに入力されている書誌情報があります。\n"
                "取得した書誌情報で上書きしますか？"
            ),
            parent=self._root,
        )

    def _apply_fetched_book_data(
        self,
        fetched_data: FetchedBookData,
    ) -> None:
        """取得した書誌情報を入力フォームへ反映する。"""
        self._isbn_var.set(
            fetched_data.isbn,
        )

        if fetched_data.title is not None:
            self._title_var.set(
                fetched_data.title,
            )

        if fetched_data.author is not None:
            self._author_var.set(
                fetched_data.author,
            )

        if fetched_data.publisher is not None:
            self._publisher_var.set(
                fetched_data.publisher,
            )

        if fetched_data.publication_format is not None:
            self._publication_format_var.set(
                fetched_data.publication_format,
            )

        if fetched_data.description is not None:
            self._replace_text(
                self._description_text,
                fetched_data.description,
            )

    def _display_cover_image(
        self,
        image_path: str,
    ) -> None:
        """表紙画像ファイルを読み込んでGUIへ表示する。"""
        with Image.open(image_path) as image:
            display_image = image.copy()

        display_image.thumbnail(
            (170, 240),
            Image.Resampling.LANCZOS,
        )

        self._cover_photo = ImageTk.PhotoImage(
            display_image,
        )

        self._cover_image_label.configure(
            image=self._cover_photo,
            text="",
        )

    def _clear_cover_image(self) -> None:
        """表紙画像表示を初期状態へ戻す。"""
        self._cover_photo = None

        self._cover_image_label.configure(
            image="",
            text="画像なし",
        )

    def _select_book_in_tree(
        self,
        book_id: int,
    ) -> None:
        """指定された書籍をTreeView上で選択する。

        Args:
            book_id: 選択する書籍ID。
        """
        iid = str(book_id)

        if not self._book_tree.exists(iid):
            return

        self._book_tree.selection_set(
            iid,
        )
        self._book_tree.focus(
            iid,
        )
        self._book_tree.see(
            iid,
        )

    def _clear_selected_book(self) -> None:
        """一覧選択と編集対象IDを解除する。"""
        selected_items = self._book_tree.selection()

        if selected_items:
            self._book_tree.selection_remove(
                *selected_items,
            )

        self._selected_book_id = None
        self._edit_status_var.set(
            "新規登録",
        )

    def _clear_form(self) -> None:
        """入力フォームと選択状態を初期化する。"""
        self._title_var.set("")
        self._isbn_var.set("")
        self._magazine_code_var.set("")
        self._author_var.set("")
        self._publisher_var.set("")
        self._publication_format_var.set("")
        self._completion_month_var.set("")

        self._description_text.delete(
            "1.0",
            tk.END,
        )
        self._notes_text.delete(
            "1.0",
            tk.END,
        )

        selected_items = self._book_tree.selection()

        if selected_items:
            self._book_tree.selection_remove(
                *selected_items,
            )

        self._selected_book_id = None
        self._edit_status_var.set(
            "新規登録",
        )
        self._set_edit_buttons_enabled(
            False,
        )
        self._clear_cover_image()

    def _get_form_values(self) -> dict[str, str | None]:
        """入力フォームの値を取得する。"""
        return {
            "title": self._title_var.get(),
            "isbn": self._isbn_var.get(),
            "magazine_code": self._magazine_code_var.get(),
            "author": self._author_var.get(),
            "publisher": self._publisher_var.get(),
            "publication_format": (
                self._publication_format_var.get()
            ),
            "description": self._description_text.get(
                "1.0",
                tk.END,
            ).rstrip("\n"),
            "completion_month": (
                self._completion_month_var.get()
            ),
            "notes": self._notes_text.get(
                "1.0",
                tk.END,
            ).rstrip("\n"),
        }

    def _create_book_item_from_form(
        self,
        *,
        book_id: int | None = None,
    ) -> BookItem:
        """入力フォームの値からBookItemを作成する。"""
        values = self._get_form_values()

        return BookItem(
            id=book_id,
            title=str(values["title"] or ""),
            isbn=values["isbn"],
            magazine_code=values["magazine_code"],
            author=values["author"],
            publisher=values["publisher"],
            publication_format=values["publication_format"],
            description=values["description"],
            completion_month=values["completion_month"],
            notes=values["notes"],
        )

    def _confirm_duplicate_candidates(
        self,
        *,
        values: dict[str, str | None],
        exclude_book_id: int | None = None,
    ) -> bool:
        """重複候補を確認し、処理を続行するか判定する。"""
        candidates = self._service.find_duplicate_candidates(
            title=values["title"],
            isbn=values["isbn"],
            magazine_code=values["magazine_code"],
        )

        if exclude_book_id is not None:
            candidates = [
                candidate
                for candidate in candidates
                if candidate.id != exclude_book_id
            ]

        if not candidates:
            return True

        candidate_lines: list[str] = []

        for candidate in candidates[:10]:
            candidate_id = (
                str(candidate.id)
                if candidate.id is not None
                else "-"
            )
            title = candidate.title or "書籍名なし"
            isbn = candidate.isbn or "-"
            magazine_code = candidate.magazine_code or "-"

            candidate_lines.append(
                (
                    f"ID: {candidate_id}\n"
                    f"書籍名: {title}\n"
                    f"ISBN: {isbn}\n"
                    f"雑誌コード: {magazine_code}"
                )
            )

        candidate_text = "\n\n".join(
            candidate_lines,
        )

        if len(candidates) > 10:
            candidate_text += (
                f"\n\nほか {len(candidates) - 10}件"
            )

        return messagebox.askyesno(
            "重複候補の確認",
            (
                "同じ書籍の可能性があるデータが"
                "見つかりました。\n\n"
                f"{candidate_text}\n\n"
                "このまま処理を続けますか？"
            ),
            parent=self._root,
        )

    def _reload_and_select_book(
        self,
        book_id: int,
    ) -> None:
        """一覧を再読み込みして指定書籍を選択する。"""
        self._load_all_books()

        if not self._book_tree.exists(
            str(book_id),
        ):
            self._clear_form()
            return

        self._select_book_in_tree(
            book_id,
        )

        book_item = self._service.get_book(
            book_id,
        )

        if book_item is not None:
            self._display_book_in_form(
                book_item,
            )





# ここからイベントハンドラ

    def _on_search(
        self,
        _event: tk.Event[tk.Misc] | None = None,
    ) -> None:
        """指定された条件で書籍を検索する。"""
        search_type = self._search_type_var.get()
        keyword = self._search_keyword_var.get()

        try:
            if search_type == "書籍名":
                books = self._service.search_books_by_title(
                    keyword,
                )
            elif search_type == "ISBN":
                books = self._service.find_books_by_isbn(
                    keyword,
                )
            elif search_type == "雑誌コード":
                books = (
                    self._service.find_books_by_magazine_code(
                        keyword,
                    )
                )
            else:
                messagebox.showerror(
                    "検索エラー",
                    "検索種類が正しくありません。",
                    parent=self._root,
                )
                return

            self._display_books(
                books,
                status_prefix="検索結果",
            )
            self._clear_form()

        except ValueError as error:
            messagebox.showerror(
                "検索エラー",
                str(error),
                parent=self._root,
            )
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "検索エラー",
                "書籍情報を検索できませんでした。",
                parent=self._root,
            )

    def _on_show_all(self) -> None:
        """検索条件を初期化して全書籍を表示する。"""
        self._search_type_var.set(
            self.SEARCH_TYPES[0],
        )
        self._search_keyword_var.set("")

        self._load_all_books()

    def _on_clear_search(self) -> None:
        """検索条件を初期状態へ戻す。"""
        self._search_type_var.set(
            self.SEARCH_TYPES[0],
        )
        self._search_keyword_var.set("")
        self._search_entry.focus_set()

    def _on_tree_select(
        self,
        _event: tk.Event[tk.Misc],
    ) -> None:
        """選択された書籍を入力フォームへ表示する。"""
        selected_items = self._book_tree.selection()

        if not selected_items:
            return

        selected_iid = selected_items[0]

        try:
            book_id = int(selected_iid)
        except ValueError:
            traceback.print_exc()
            messagebox.showerror(
                "選択エラー",
                "選択された書籍を識別できませんでした。",
                parent=self._root,
            )
            return

        try:
            book_item = self._service.get_book(
                book_id,
            )

            if book_item is None:
                messagebox.showwarning(
                    "書籍が見つかりません",
                    (
                        "選択された書籍が見つかりませんでした。\n"
                        "一覧を再読み込みします。"
                    ),
                    parent=self._root,
                )
                self._load_all_books()
                self._clear_form()
                return

            self._display_book_in_form(
                book_item,
            )

        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "読み込みエラー",
                "選択された書籍情報を読み込めませんでした。",
                parent=self._root,
            )

    def _on_add(self) -> None:
        """入力内容を新しい書籍として登録する。"""
        values = self._get_form_values()

        title = str(values["title"] or "").strip()

        if title == "":
            messagebox.showwarning(
                "入力不足",
                "書籍名を入力してください。",
                parent=self._root,
            )
            self._title_entry.focus_set()
            return

        if self._selected_book_id is not None:
            continue_registration = messagebox.askyesno(
                "新規登録の確認",
                (
                    "現在、既存の書籍を編集中です。\n"
                    "入力内容を別の書籍として"
                    "新規登録しますか？"
                ),
                parent=self._root,
            )

            if not continue_registration:
                return
        
        try:
            if not self._confirm_duplicate_candidates(
                values=values,
            ):
                return

            registered_book = self._service.add_book(
                title=values["title"],
                isbn=values["isbn"],
                magazine_code=values["magazine_code"],
                author=values["author"],
                publisher=values["publisher"],
                publication_format=(
                    values["publication_format"]
                ),
                description=values["description"],
                completion_month=(
                    values["completion_month"]
                ),
                notes=values["notes"],
            )

            if registered_book.id is None:
                raise RuntimeError(
                    "登録済み書籍のIDを取得できませんでした。",
                )

            registered_book_id = registered_book.id

            self._reload_and_select_book(
                registered_book_id,
            )

            messagebox.showinfo(
                "登録完了",
                "書籍を登録しました。",
                parent=self._root,
            )

        except ValueError as error:
            messagebox.showerror(
                "入力エラー",
                str(error),
                parent=self._root,
            )
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "登録エラー",
                "書籍を登録できませんでした。",
                parent=self._root,
            )


    def _on_update(self) -> None:
        """選択中の書籍を入力内容で更新する。"""
        if self._selected_book_id is None:
            messagebox.showwarning(
                "更新対象なし",
                (
                    "更新する書籍が選択されていません。\n"
                    "書籍一覧から更新対象を選択してください。"
                ),
                parent=self._root,
            )
            return

        book_id = self._selected_book_id
        values = self._get_form_values()
        title = str(values["title"] or "").strip()

        if title == "":
            messagebox.showwarning(
                "入力不足",
                "書籍名を入力してください。",
                parent=self._root,
            )
            self._title_entry.focus_set()
            return

        try:
            if not self._confirm_duplicate_candidates(
                values=values,
                exclude_book_id=book_id,
            ):
                return

            confirmed = messagebox.askyesno(
                "更新の確認",
                "選択中の書籍情報を更新しますか？",
                parent=self._root,
            )

            if not confirmed:
                return

            book_item = self._create_book_item_from_form(
                book_id=book_id,
            )

            updated = self._service.update_book(
                book_item,
            )

            if not updated:
                messagebox.showwarning(
                    "書籍が見つかりません",
                    (
                        "更新対象の書籍が見つかりませんでした。\n"
                        "一覧を再読み込みします。"
                    ),
                    parent=self._root,
                )
                self._load_all_books()
                self._clear_form()
                return

            self._reload_and_select_book(
                book_id,
            )

            messagebox.showinfo(
                "更新完了",
                "書籍情報を更新しました。",
                parent=self._root,
            )

        except ValueError as error:
            messagebox.showerror(
                "入力エラー",
                str(error),
                parent=self._root,
            )
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "更新エラー",
                "書籍情報を更新できませんでした。",
                parent=self._root,
            )

    def _on_delete(self) -> None:
        """選択中の書籍を削除する。"""
        if self._selected_book_id is None:
            messagebox.showwarning(
                "削除対象なし",
                (
                    "削除する書籍が選択されていません。\n"
                    "書籍一覧から削除対象を選択してください。"
                ),
                parent=self._root,
            )
            return

        book_id = self._selected_book_id
        title = self._title_var.get().strip()

        display_title = title or f"ID {book_id}"

        confirmed = messagebox.askyesno(
            "削除の確認",
            (
                "次の書籍を削除しますか？\n\n"
                f"{display_title}\n\n"
                "この操作は取り消せません。"
            ),
            parent=self._root,
        )

        if not confirmed:
            return

        try:
            deleted = self._service.delete_book(
                book_id,
            )

            if deleted is False:
                messagebox.showwarning(
                    "書籍が見つかりません",
                    (
                        "削除対象の書籍が見つかりませんでした。\n"
                        "一覧を再読み込みします。"
                    ),
                    parent=self._root,
                )
                self._load_all_books()
                self._clear_form()
                return

            self._clear_form()
            self._load_all_books()

            messagebox.showinfo(
                "削除完了",
                "書籍を削除しました。",
                parent=self._root,
            )

        except ValueError as error:
            messagebox.showerror(
                "削除エラー",
                str(error),
                parent=self._root,
            )
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "削除エラー",
                "書籍を削除できませんでした。",
                parent=self._root,
            )

    def _on_clear(self) -> None:
        """入力フォームを初期状態へ戻す。"""
        self._clear_form()
        self._title_entry.focus_set()

    def _on_reload(self) -> None:
        """書籍一覧を最新状態へ更新する。"""
        selected_book_id = self._selected_book_id

        self._load_all_books()

        if selected_book_id is None:
            return

        if self._book_tree.exists(
            str(selected_book_id),
        ):
            self._select_book_in_tree(
                selected_book_id,
            )
        else:
            self._clear_form()

    def _on_exit(self) -> None:
        """アプリケーションを終了する。"""
        self._root.destroy()

    def _on_fetch_book_metadata(self) -> None:
        """ISBNから外部書誌情報を取得してフォームへ反映する。"""
        isbn = self._isbn_var.get().strip()

        if isbn == "":
            messagebox.showwarning(
                "入力不足",
                "ISBNを入力してください。",
                parent=self._root,
            )
            self._isbn_entry.focus_set()
            return

        try:
            self._fetch_metadata_button.configure(
                state="disabled",
            )
            self._edit_status_var.set(
                "書誌情報を取得しています...",
            )
            self._root.update_idletasks()

            result = self._service.fetch_book_metadata(
                isbn,
            )

            if not self._confirm_metadata_overwrite():
                self._edit_status_var.set(
                    "書誌情報の反映をキャンセルしました。",
                )
                return

            self._apply_fetched_book_data(
                result,
            )

            if result.cover_image_url is not None:
                try:
                    cover_path = self._service.fetch_cover_image(
                        result.cover_image_url,
                    )

                    self._display_cover_image(
                        str(cover_path),
                    )

                except Exception:
                    traceback.print_exc()
                    self._clear_cover_image()

                    messagebox.showwarning(
                        "表紙画像取得エラー",
                        (
                            "書誌情報は取得できましたが、"
                            "表紙画像を表示できませんでした。"
                        ),
                        parent=self._root,
                    )
            else:
                self._clear_cover_image()

            self._edit_status_var.set(
                "書誌情報を取得しました。",
            )

            messagebox.showinfo(
                "書誌情報取得完了",
                (
                    "書誌情報を取得して"
                    "入力フォームへ反映しました。"
                ),
                parent=self._root,
            )

        except ValueError as error:
            messagebox.showwarning(
                "ISBN入力エラー",
                str(error),
                parent=self._root,
            )
            self._edit_status_var.set(
                "ISBNの入力内容を確認してください。",
            )

        except BookMetadataNotFoundError:
            messagebox.showwarning(
                "書誌情報なし",
                (
                    "入力されたISBNに対応する"
                    "書誌情報が見つかりませんでした。"
                ),
                parent=self._root,
            )
            self._edit_status_var.set(
                "書誌情報が見つかりませんでした。",
            )

        except BookMetadataConnectionError:
            messagebox.showerror(
                "通信エラー",
                (
                    "外部書誌情報サービスへ"
                    "接続できませんでした。\n"
                    "インターネット接続を確認して、"
                    "もう一度お試しください。"
                ),
                parent=self._root,
            )
            self._edit_status_var.set(
                "外部サービスへ接続できませんでした。",
            )

        except BookMetadataRateLimitError:
            messagebox.showwarning(
                "利用制限",
                (
                    "外部書誌情報サービスの"
                    "利用制限に達しました。\n"
                    "しばらく時間をおいてから"
                    "もう一度お試しください。"
                ),
                parent=self._root,
            )
            self._edit_status_var.set(
                "外部サービスの利用制限に達しました。",
            )

        except BookMetadataResponseError:
            messagebox.showerror(
                "応答エラー",
                (
                    "外部書誌情報サービスから"
                    "正常な応答を取得できませんでした。\n"
                    "しばらく時間をおいてから"
                    "もう一度お試しください。"
                ),
                parent=self._root,
            )
            self._edit_status_var.set(
                "外部サービスの応答を処理できませんでした。",
            )

        except BookMetadataConfigurationError:
            messagebox.showerror(
                "設定エラー",
                (
                    "外部書誌情報取得機能の"
                    "設定が完了していません。"
                ),
                parent=self._root,
            )
            self._edit_status_var.set(
                "書誌情報取得機能の設定エラーです。",
            )

        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "書誌情報取得エラー",
                "予期しないエラーが発生しました。",
                parent=self._root,
            )
            self._edit_status_var.set(
                "書誌情報の取得に失敗しました。",
            )

        finally:
            self._fetch_metadata_button.configure(
                state="normal",
            )
