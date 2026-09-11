"""書籍管理アプリケーションのメインGUI。"""

from __future__ import annotations

import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import TYPE_CHECKING
from PIL import Image, ImageTk
from pathlib import Path
from datetime import datetime
import ctypes
import sys

from book_manager.models.book_item import BookItem
from book_manager.models.reading_history import ReadingHistory
from book_manager.models.reading_statistics import (
    MonthlyReadingCount,
    ReadingStatisticsSummary,
)
from book_manager.models.fetched_book_data import (
    FetchedBookData,
)
from book_manager.gui.window_positioning import (
    center_window_on_parent,
)
from book_manager.services.application_settings_service import (
    ApplicationSettingsError,
    DirectoryOpenError,
)

from book_manager.metadata.exceptions import (
    BookMetadataConfigurationError,
    BookMetadataConnectionError,
    BookMetadataNotFoundError,
    BookMetadataRateLimitError,
    BookMetadataResponseError,
)

if TYPE_CHECKING:
    from book_manager.services.backup_service import BackupService
    from book_manager.services.application_settings_service import (
        ApplicationSettingsService,
    )
    from book_manager.services.book_service import BookService
    from book_manager.services.csv_export_service import (
        CsvExportService,
    )
    from book_manager.services.csv_import_service import (
        CsvImportService,
    )
    from book_manager.services.reading_history_service import (
        ReadingHistoryService,
    )
    from collections.abc import Callable


class BookManagerApplication:
    """書籍管理アプリケーションのメインウィンドウを管理する。"""

    WINDOW_TITLE = "書籍管理"
    WINDOW_SIZE = "1350x800"
    MINIMUM_WIDTH = 1150
    MINIMUM_HEIGHT = 650

    SORT_TYPES = (
        "登録順",
        "書籍名",
        "著者名",
        "出版社",
        "読了年月",
        "読書状態",
        "お気に入り",
        "評価",
    )

    TREE_SORT_TYPE_MAP = {
        "id": "登録順",
        "title": "書籍名",
        "author": "著者名",
        "publisher": "出版社",
        "completion_month": "読了年月",
        "reading_status": "読書状態",
        "is_favorite": "お気に入り",
        "rating": "評価",
    }

    PUBLICATION_FORMATS = (
        "",
        "文庫",
        "単行本",
        "新書",
        "雑誌",
        "電子書籍",
        "その他",
    )

    READING_STATUS_LABELS = {
        None: "未設定",
        "unread": "未読",
        "reading": "読書中",
        "completed": "読了",
    }

    READING_STATUS_VALUES = {
        "未設定": None,
        "未読": "unread",
        "読書中": "reading",
        "読了": "completed",
    }

    READING_STATUS_OPTIONS = (
        "未設定",
        "未読",
        "読書中",
        "読了",
    )

    RATING_LABELS = {
        None: "未評価",
        1: "★",
        2: "★★",
        3: "★★★",
        4: "★★★★",
        5: "★★★★★",
    }

    RATING_VALUES = {
        "未評価": None,
        "★": 1,
        "★★": 2,
        "★★★": 3,
        "★★★★": 4,
        "★★★★★": 5,
    }

    RATING_OPTIONS = (
        "未評価",
        "★",
        "★★",
        "★★★",
        "★★★★",
        "★★★★★",
    )

    SEARCH_READING_STATUS_VALUES = {
        "すべて": None,
        "未設定": "unset",
        "未読": "unread",
        "読書中": "reading",
        "読了": "completed",
    }

    SEARCH_READING_STATUS_OPTIONS = (
        "すべて",
        "未設定",
        "未読",
        "読書中",
        "読了",
    )

    SEARCH_FAVORITE_VALUES = {
        "すべて": None,
        "お気に入りのみ": "favorite",
        "お気に入り以外": "not_favorite",
    }

    SEARCH_FAVORITE_OPTIONS = (
        "すべて",
        "お気に入りのみ",
        "お気に入り以外",
    )

    SEARCH_RATING_VALUES = {
        "すべて": None,
        "未評価": "unrated",
        "★1以上": 1,
        "★2以上": 2,
        "★3以上": 3,
        "★4以上": 4,
        "★5": 5,
    }

    SEARCH_RATING_OPTIONS = (
        "すべて",
        "未評価",
        "★1以上",
        "★2以上",
        "★3以上",
        "★4以上",
        "★5",
    )

    SEARCH_TAG_ALL = "すべて"
    SEARCH_TAG_UNTAGGED = "タグ未設定"
    TAG_SEPARATOR = "|"

    TREE_COLUMNS = (
        "id",
        "title",
        "author",
        "publisher",
        "publication_format",
        "isbn",
        "magazine_code",
        "completion_month",
        "reading_status",
        "is_favorite",
        "rating",
        "tags",
    )

    def __init__(
        self,
        root: tk.Tk,
        service: BookService,
        csv_export_service: CsvExportService,
        csv_import_service: CsvImportService,
        backup_service: BackupService,
        reading_history_service: ReadingHistoryService,
        application_settings_service: ApplicationSettingsService,
        on_google_books_api_key_changed: Callable[
            [str | None],
            None,
        ],
    ) -> None:
        """GUIを初期化する。

        Args:
            root: Tkinterのルートウィンドウ。
            service: 書籍管理処理を提供するBookService。
            backup_service:
                データベースのバックアップ・復元処理を提供する
                BackupService。
            reading_history_service:
                ReadingHistoryService。
            application_settings_service:
                アプリケーション設定の参照・更新処理。
            on_google_books_api_key_changed:
                Google Books APIキー変更時に呼び出す処理。
        """
        self._root = root
        self._service = service
        self._csv_export_service = csv_export_service
        self._csv_import_service = csv_import_service
        self._backup_service = backup_service
        self._reading_history_service = reading_history_service
        self._application_settings_service = (
            application_settings_service
        )
        self._on_google_books_api_key_changed = (
            on_google_books_api_key_changed
        )
        self._selected_book_id: int | None = None
        self._cover_photo: tk.PhotoImage | None = None
        self._current_cover_image_url: str | None = None
        self._current_cover_image_path: str | None = None
        self._thumbnail_photos: dict[
            int,
            ImageTk.PhotoImage,
        ] = {}
        self._search_title_var = tk.StringVar(
            master=self._root,
        )
        self._search_author_var = tk.StringVar(
            master=self._root,
        )
        self._search_publisher_var = tk.StringVar(
            master=self._root,
        )
        self._search_isbn_var = tk.StringVar(
            master=self._root,
        )
        self._search_magazine_code_var = tk.StringVar(
            master=self._root,
        )
        self._search_reading_status_var = tk.StringVar(
            master=self._root,
            value="すべて",
        )
        self._search_favorite_var = tk.StringVar(
            master=self._root,
            value="すべて",
        )
        self._search_rating_var = tk.StringVar(
            master=self._root,
            value="すべて",
        )
        self._search_tag_var = tk.StringVar(
            master=self._root,
            value=self.SEARCH_TAG_ALL,
        )

        self._sort_type_var = tk.StringVar(
            master=self._root,
            value=self.SORT_TYPES[0],
        )
        self._sort_direction_var = tk.StringVar(
            master=self._root,
            value="descending",
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
        self._reading_status_var = tk.StringVar(
            master=self._root,
            value="未設定",
        )
        self._is_favorite_var = tk.BooleanVar(
            master=self._root,
            value=False,
        )
        self._rating_var = tk.StringVar(
            master=self._root,
            value="未評価",
        )
        self._tags_var = tk.StringVar(
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
        self._refresh_tag_options()
        self._load_all_books()

        self._title_entry.focus_set()

    def _get_available_screen_size(
        self,
    ) -> tuple[int, int]:
        """利用可能な画面領域のサイズを取得する。"""
        if sys.platform != "win32":
            return (
                self._root.winfo_screenwidth(),
                self._root.winfo_screenheight(),
            )

        class Rect(ctypes.Structure):
            """Windowsの矩形情報を表す。"""

            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        work_area = Rect()

        success = ctypes.windll.user32.SystemParametersInfoW(
            0x0030,
            0,
            ctypes.byref(work_area),
            0,
        )

        if not success:
            return (
                self._root.winfo_screenwidth(),
                self._root.winfo_screenheight(),
            )

        return (
            work_area.right - work_area.left,
            work_area.bottom - work_area.top,
        )

    def _configure_root(self) -> None:
        """メインウィンドウを設定する。"""
        self._root.title(self.WINDOW_TITLE)

        window_width = 1350
        window_height = 800

        screen_width, screen_height = (
            self._get_available_screen_size()
        )

        position_x = max(
            0,
            (screen_width - window_width) // 2,
        )
        position_y = max(
            0,
            (screen_height - window_height) // 2,
        )

        self._root.geometry(
            f"{window_width}x{window_height}"
            f"+{position_x}+{position_y}"
        )

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
            minsize=330,
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

        for column in (
            1,
            3,
            5,
            7,
            9,
        ):
            search_frame.columnconfigure(
                column,
                weight=1,
            )

        ttk.Label(
            search_frame,
            text="書籍名",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 6),
        )

        self._search_title_entry = ttk.Entry(
            search_frame,
            textvariable=self._search_title_var,
            width=18,
        )
        self._search_title_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 10),
        )
        self._search_title_entry.bind(
            "<Return>",
            self._on_search,
        )

        ttk.Label(
            search_frame,
            text="著者名",
        ).grid(
            row=0,
            column=2,
            sticky="w",
            padx=(0, 6),
        )

        self._search_author_entry = ttk.Entry(
            search_frame,
            textvariable=self._search_author_var,
            width=16,
        )
        self._search_author_entry.grid(
            row=0,
            column=3,
            sticky="ew",
            padx=(0, 10),
        )
        self._search_author_entry.bind(
            "<Return>",
            self._on_search,
        )

        ttk.Label(
            search_frame,
            text="出版社",
        ).grid(
            row=0,
            column=4,
            sticky="w",
            padx=(0, 6),
        )

        self._search_publisher_entry = ttk.Entry(
            search_frame,
            textvariable=self._search_publisher_var,
            width=14,
        )
        self._search_publisher_entry.grid(
            row=0,
            column=5,
            sticky="ew",
            padx=(0, 10),
        )
        self._search_publisher_entry.bind(
            "<Return>",
            self._on_search,
        )

        ttk.Label(
            search_frame,
            text="ISBN",
        ).grid(
            row=0,
            column=6,
            sticky="w",
            padx=(0, 6),
        )

        self._search_isbn_entry = ttk.Entry(
            search_frame,
            textvariable=self._search_isbn_var,
            width=14,
        )
        self._search_isbn_entry.grid(
            row=0,
            column=7,
            sticky="ew",
            padx=(0, 10),
        )
        self._search_isbn_entry.bind(
            "<Return>",
            self._on_search,
        )

        ttk.Label(
            search_frame,
            text="雑誌コード",
        ).grid(
            row=0,
            column=8,
            sticky="w",
            padx=(0, 6),
        )

        self._search_magazine_code_entry = ttk.Entry(
            search_frame,
            textvariable=self._search_magazine_code_var,
            width=10,
        )
        self._search_magazine_code_entry.grid(
            row=0,
            column=9,
            sticky="ew",
        )
        self._search_magazine_code_entry.bind(
            "<Return>",
            self._on_search,
        )

        ttk.Label(
            search_frame,
            text="読書状態",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 6),
            pady=(8, 0),
        )

        self._search_reading_status_combobox = ttk.Combobox(
            search_frame,
            textvariable=self._search_reading_status_var,
            values=self.SEARCH_READING_STATUS_OPTIONS,
            state="readonly",
            width=10,
        )
        self._search_reading_status_combobox.grid(
            row=1,
            column=1,
            sticky="w",
            padx=(0, 10),
            pady=(8, 0),
        )

        ttk.Label(
            search_frame,
            text="お気に入り",
        ).grid(
            row=1,
            column=2,
            sticky="w",
            padx=(0, 6),
            pady=(8, 0),
        )

        self._search_favorite_combobox = ttk.Combobox(
            search_frame,
            textvariable=self._search_favorite_var,
            values=self.SEARCH_FAVORITE_OPTIONS,
            state="readonly",
            width=14,
        )
        self._search_favorite_combobox.grid(
            row=1,
            column=3,
            sticky="w",
            padx=(0, 10),
            pady=(8, 0),
        )

        ttk.Label(
            search_frame,
            text="評価",
        ).grid(
            row=1,
            column=4,
            sticky="w",
            padx=(0, 6),
            pady=(8, 0),
        )

        self._search_rating_combobox = ttk.Combobox(
            search_frame,
            textvariable=self._search_rating_var,
            values=self.SEARCH_RATING_OPTIONS,
            state="readonly",
            width=10,
        )
        self._search_rating_combobox.grid(
            row=1,
            column=5,
            sticky="w",
            padx=(0, 10),
            pady=(8, 0),
        )

        ttk.Label(
            search_frame,
            text="タグ",
        ).grid(
            row=1,
            column=6,
            sticky="w",
            padx=(0, 6),
            pady=(8, 0),
        )

        self._search_tag_combobox = ttk.Combobox(
            search_frame,
            textvariable=self._search_tag_var,
            values=(
                self.SEARCH_TAG_ALL,
                self.SEARCH_TAG_UNTAGGED,
            ),
            state="readonly",
            width=14,
        )
        self._search_tag_combobox.grid(
            row=1,
            column=7,
            sticky="w",
            padx=(0, 10),
            pady=(8, 0),
        )

        self._search_button = ttk.Button(
            search_frame,
            text="検索",
            command=self._on_search,
        )
        self._search_button.grid(
            row=1,
            column=8,
            padx=(0, 6),
            pady=(8, 0),
        )

        self._clear_search_button = ttk.Button(
            search_frame,
            text="検索条件クリア",
            command=self._on_clear_search,
        )
        self._clear_search_button.grid(
            row=1,
            column=9,
            sticky="w",
            pady=(8, 0),
        )

        sort_frame = ttk.Frame(
            search_frame,
        )
        sort_frame.grid(
            row=2,
            column=0,
            columnspan=4,
            sticky="w",
            pady=(8, 0),
        )

        ttk.Label(
            sort_frame,
            text="並べ替え",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 6),
        )

        self._sort_type_combobox = ttk.Combobox(
            sort_frame,
            textvariable=self._sort_type_var,
            values=self.SORT_TYPES,
            state="readonly",
            width=12,
        )
        self._sort_type_combobox.grid(
            row=0,
            column=1,
            sticky="w",
            padx=(0, 10),
        )

        self._sort_type_combobox.bind(
            "<<ComboboxSelected>>",
            self._on_sort_changed,
        )

        self._sort_descending_radio = ttk.Radiobutton(
            sort_frame,
            text="降順",
            variable=self._sort_direction_var,
            value="descending",
            command=self._on_sort_changed,
        )
        self._sort_descending_radio.grid(
            row=0,
            column=2,
            padx=(0, 10),
        )

        self._sort_ascending_radio = ttk.Radiobutton(
            sort_frame,
            text="昇順",
            variable=self._sort_direction_var,
            value="ascending",
            command=self._on_sort_changed,
        )
        self._sort_ascending_radio.grid(
            row=0,
            column=3,
        )

    def _on_tree_heading_click(
        self,
        column_name: str,
    ) -> None:
        """書籍一覧のヘッダークリックで並べ替える。"""
        sort_type = self.TREE_SORT_TYPE_MAP.get(
            column_name,
        )

        if sort_type is None:
            return

        current_sort_type = self._sort_type_var.get()

        if current_sort_type == sort_type:
            current_direction = (
                self._sort_direction_var.get()
            )

            new_direction = (
                "ascending"
                if current_direction == "descending"
                else "descending"
            )
        else:
            new_direction = "ascending"

        self._sort_type_var.set(
            sort_type,
        )
        self._sort_direction_var.set(
            new_direction,
        )

        self._on_sort_changed()

    def _get_sort_settings(
        self,
    ) -> tuple[str, bool]:
        """GUIの並べ替え指定をService用の値へ変換する。"""
        sort_type_map = {
            "登録順": "registered",
            "書籍名": "title",
            "著者名": "author",
            "出版社": "publisher",
            "読了年月": "completion_month",
            "読書状態": "reading_status",
            "お気に入り": "is_favorite",
            "評価": "rating",
        }

        selected_sort_type = self._sort_type_var.get()

        sort_by = sort_type_map.get(
            selected_sort_type,
        )

        if sort_by is None:
            raise ValueError(
                "並べ替え項目が正しくありません。"
            )

        descending = (
            self._sort_direction_var.get()
            == "descending"
        )

        return (
            sort_by,
            descending,
        )

    def _create_list_frame(
        self,
        parent: ttk.Frame,
    ) -> None:
        """書籍一覧領域を作成する。"""
        list_frame = ttk.LabelFrame(
            parent,
            text="書籍一覧",
            padding=(8, 4),
        )
        list_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
            pady=(0, 4),
        )

        list_frame.rowconfigure(
            0,
            weight=1,
        )
        list_frame.columnconfigure(
            0,
            weight=1,
        )

        style = ttk.Style(
            self._root,
        )

        style.configure(
            "Book.Treeview",
            rowheight=56,
        )

        self._book_tree = ttk.Treeview(
            list_frame,
            columns=self.TREE_COLUMNS,
            show="tree headings",
            selectmode="browse",
            style="Book.Treeview",
            height=4,
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

        self._book_tree.heading(
            "#0",
            text="表紙",
        )

        self._book_tree.column(
            "#0",
            width=60,
            minwidth=60,
            anchor="center",
            stretch=False,
        )

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
            "reading_status": {
                "heading": "読書状態",
                "width": 80,
                "minwidth": 70,
                "anchor": "center",
                "stretch": False,
            },
            "is_favorite": {
                "heading": "お気に入り",
                "width": 60,
                "minwidth": 50,
                "anchor": "center",
                "stretch": False,
            },
            "rating": {
                "heading": "評価",
                "width": 100,
                "minwidth": 90,
                "anchor": "center",
                "stretch": False,
            },
            "tags": {
                "heading": "タグ",
                "width": 180,
                "minwidth": 120,
                "anchor": "w",
                "stretch": True,
            },
        }

        for column_name, definition in column_definitions.items():

            heading_options: dict[str, object] = {
                "text": definition["heading"],
            }

            if column_name in self.TREE_SORT_TYPE_MAP:
                heading_options["command"] = (
                    lambda column_name=column_name:
                    self._on_tree_heading_click(
                        column_name,
                    )
                )

            self._book_tree.heading(
                column_name,
                **heading_options,
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
            5,
            weight=1,
        )
        form_frame.rowconfigure(
            6,
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
            text="読書状態",
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(12, 6),
        )

        self._reading_status_combobox = ttk.Combobox(
            completion_month_frame,
            textvariable=self._reading_status_var,
            values=self.READING_STATUS_OPTIONS,
            state="readonly",
            width=8,
        )
        self._reading_status_combobox.grid(
            row=0,
            column=2,
            sticky="w",
        )
        ttk.Label(
            completion_month_frame,
            text="評価",
        ).grid(
            row=0,
            column=3,
            sticky="w",
            padx=(12, 6),
        )
        self._rating_combobox = ttk.Combobox(
            completion_month_frame,
            textvariable=self._rating_var,
            values=self.RATING_OPTIONS,
            state="readonly",
            width=7,
        )
        self._rating_combobox.grid(
            row=0,
            column=4,
            sticky="w",
        )
        self._is_favorite_checkbutton = ttk.Checkbutton(
            completion_month_frame,
            text="お気に入り",
            variable=self._is_favorite_var,
        )
        self._is_favorite_checkbutton.grid(
            row=0,
            column=5,
            sticky="w",
            padx=(12, 0),
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
            text="タグ",
        ).grid(
            row=4,
            column=0,
            sticky="w",
            padx=(0, 6),
            pady=4,
        )

        tag_frame = ttk.Frame(form_frame)
        tag_frame.grid(
            row=4,
            column=1,
            columnspan=3,
            sticky="ew",
            pady=4,
        )
        tag_frame.columnconfigure(0, weight=1)
        self._tags_entry = ttk.Entry(
            tag_frame,
            textvariable=self._tags_var,
        )
        self._tags_entry.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 6),
        )
        self._select_tags_button = ttk.Button(
            tag_frame,
            text="タグ選択",
            command=self._on_select_tags,
        )
        self._select_tags_button.grid(
            row=0,
            column=1,
        )

        ttk.Label(
            form_frame,
            text="内容紹介",
        ).grid(
            row=5,
            column=0,
            sticky="nw",
            padx=(0, 6),
            pady=4,
        )

        description_frame = ttk.Frame(
            form_frame,
        )
        description_frame.grid(
            row=5,
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
            row=6,
            column=0,
            sticky="nw",
            padx=(0, 6),
            pady=4,
        )

        notes_frame = ttk.Frame(
            form_frame,
        )
        notes_frame.grid(
            row=6,
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
            rowspan=7,
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
            13,
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

        self._csv_export_button = ttk.Button(
            button_frame,
            text="CSVエクスポート",
            command=self._on_export_csv,
        )
        self._csv_export_button.grid(
            row=0,
            column=6,
            padx=(0, 6),
        )

        self._csv_import_button = ttk.Button(
            button_frame,
            text="CSVインポート",
            command=self._on_import_csv,
        )

        self._csv_import_button.grid(
            row=0,
            column=7,
            padx=(0, 6),
        )

        self._backup_restore_button = ttk.Button(
            button_frame,
            text="バックアップ復元",
            command=self._on_restore_backup,
        )
        self._backup_restore_button.grid(
            row=0,
            column=8,
            padx=(0, 6),
        )

        self._tag_management_button = ttk.Button(
            button_frame,
            text="タグ管理",
            command=self._on_manage_tags,
        )
        self._tag_management_button.grid(
            row=0,
            column=9,
            padx=(0, 6),
        )

        self._reading_history_button = ttk.Button(
            button_frame,
            text="読書履歴",
            command=self._on_manage_reading_histories,
        )
        self._reading_history_button.grid(
            row=0,
            column=10,
            padx=(0, 6),
        )

        self._reading_statistics_button = ttk.Button(
            button_frame,
            text="読書集計",
            command=self._on_show_reading_statistics,
        )
        self._reading_statistics_button.grid(
            row=0,
            column=11,
            padx=(0, 6),
        )

        self._settings_button = ttk.Button(
            button_frame,
            text="設定",
            command=self._on_open_settings,
        )
        self._settings_button.grid(
            row=0,
            column=12,
            padx=(0, 6),
        )

        self._exit_button = ttk.Button(
            button_frame,
            text="終了",
            command=self._on_exit,
        )
        self._exit_button.grid(
            row=0,
            column=13,
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
            sort_by, descending = (
                self._get_sort_settings()
            )

            books = self._service.get_sorted_books(
                sort_by=sort_by,
                descending=descending,
            )

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

    def _create_thumbnail_photo(
        self,
        cover_image_path: str | None,
    ) -> ImageTk.PhotoImage | None:
        """一覧表示用の表紙サムネイルを生成する。"""
        if not cover_image_path:
            return None

        image_path = self._service.resolve_cover_image_path(
            cover_image_path,
        )

        if image_path is None or not image_path.is_file():
            return None

        try:
            with Image.open(image_path) as image:
                thumbnail_image = image.copy()

            thumbnail_image.thumbnail(
                (40, 52),
                Image.Resampling.LANCZOS,
            )

            return ImageTk.PhotoImage(
                thumbnail_image,
            )

        except Exception:
            traceback.print_exc()
            return None

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

        self._thumbnail_photos.clear()

        displayed_count = 0

        for book in books:
            if book.id is None:
                continue

            thumbnail_photo = self._create_thumbnail_photo(
                book.cover_image_path,
            )

            if thumbnail_photo is not None:
                self._thumbnail_photos[book.id] = (
                    thumbnail_photo
                )

            self._book_tree.insert(
                "",
                "end",
                iid=str(book.id),
                image=thumbnail_photo or "",
                values=(
                    book.id,
                    book.title,
                    book.author or "",
                    book.publisher or "",
                    book.publication_format or "",
                    book.isbn or "",
                    book.magazine_code or "",
                    book.completion_month or "",
                    self.READING_STATUS_LABELS.get(
                        book.reading_status,
                        "未設定",
                    ),
                    "★" if book.is_favorite else "",
                    (
                        ""
                        if book.rating is None
                        else self.RATING_LABELS.get(
                            book.rating,
                            "",
                        )
                    ),
                    self.TAG_SEPARATOR.join(book.tags),
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
        self._reading_status_var.set(
            self.READING_STATUS_LABELS.get(
                book_item.reading_status,
                "未設定",
            )
        )
        self._is_favorite_var.set(
            book_item.is_favorite,
        )
        self._rating_var.set(
            self.RATING_LABELS.get(
                book_item.rating,
                "未評価",
            )
        )
        self._tags_var.set(
            self.TAG_SEPARATOR.join(book_item.tags),
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
        self._current_cover_image_url = (
            book_item.cover_image_url
        )
        self._current_cover_image_path = (
            book_item.cover_image_path
        )

        self._display_saved_cover_image(
            self._current_cover_image_path,
        )

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

    def _clear_cover_state(self) -> None:
        """表紙画像の表示と内部状態を初期化する。"""
        self._current_cover_image_url = None
        self._current_cover_image_path = None
        self._clear_cover_image()

    def _display_saved_cover_image(
        self,
        cover_image_path: str | None,
    ) -> None:
        """保存済みの表紙画像を表示する。"""
        if cover_image_path is None:
            self._clear_cover_image()
            return

        image_path = self._service.resolve_cover_image_path(
            cover_image_path,
        )

        if image_path is None or not image_path.is_file():
            self._clear_cover_image()
            return

        try:
            self._display_cover_image(
                str(image_path),
            )
        except Exception:
            traceback.print_exc()
            self._clear_cover_image()

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
        self._reading_status_var.set(
            "未設定",
        )
        self._is_favorite_var.set(False)
        self._rating_var.set("未評価")
        self._tags_var.set("")
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
        self._clear_cover_state()
    def _get_form_values(
        self,
    ) -> dict[
        str,
        str | int | bool | tuple[str, ...] | None,
    ]:
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
            "cover_image_url": (
                self._current_cover_image_url
            ),
            "cover_image_path": (
                self._current_cover_image_path
            ),
            "completion_month": (
                self._completion_month_var.get()
            ),
            "reading_status": (
                self.READING_STATUS_VALUES.get(
                    self._reading_status_var.get()
                )
            ),
            "is_favorite": self._is_favorite_var.get(),
            "rating": self.RATING_VALUES.get(
                self._rating_var.get()
            ),
            "tags": tuple(
                tag_name.strip()
                for tag_name in self._tags_var.get().split(
                    self.TAG_SEPARATOR
                )
                if tag_name.strip()
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
            cover_image_url=values["cover_image_url"],
            cover_image_path=values["cover_image_path"],
            completion_month=values["completion_month"],
            reading_status=values["reading_status"],
            is_favorite=values["is_favorite"],
            rating=values["rating"],
            tags=values["tags"],
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

    def _get_filtered_books(
        self,
    ) -> list[BookItem]:
        """現在の検索条件に一致する書籍一覧を取得する。"""
        reading_status_filter = (
            self.SEARCH_READING_STATUS_VALUES[
                self._search_reading_status_var.get()
            ]
        )
        favorite_filter = (
            self.SEARCH_FAVORITE_VALUES[
                self._search_favorite_var.get()
            ]
        )
        rating_filter = (
            self.SEARCH_RATING_VALUES[
                self._search_rating_var.get()
            ]
        )
        selected_tag = self._search_tag_var.get()
        tag_name = (
            selected_tag
            if selected_tag
            not in {
                self.SEARCH_TAG_ALL,
                self.SEARCH_TAG_UNTAGGED,
            }
            else None
        )
        untagged_only = (
            selected_tag == self.SEARCH_TAG_UNTAGGED
        )

        return self._service.search_books(
            title=self._search_title_var.get(),
            author=self._search_author_var.get(),
            publisher=self._search_publisher_var.get(),
            isbn=self._search_isbn_var.get(),
            magazine_code=self._search_magazine_code_var.get(),
            reading_status_filter=reading_status_filter,
            favorite_filter=favorite_filter,
            rating_filter=rating_filter,
            tag_name=tag_name,
            untagged_only=untagged_only,
        )

    def _has_search_conditions(
        self,
    ) -> bool:
        """検索条件が1つ以上入力されているか判定する。"""
        has_text_condition = any(
            value.strip()
            for value in (
                self._search_title_var.get(),
                self._search_author_var.get(),
                self._search_publisher_var.get(),
                self._search_isbn_var.get(),
                self._search_magazine_code_var.get(),
            )
        )

        has_filter_condition = any(
            value != "すべて"
            for value in (
                self._search_reading_status_var.get(),
                self._search_favorite_var.get(),
                self._search_rating_var.get(),
                self._search_tag_var.get(),
            )
        )

        return (
            has_text_condition
            or has_filter_condition
        )

    def _refresh_tag_options(self) -> None:
        """検索用タグ選択肢を最新状態へ更新する。"""
        current_value = self._search_tag_var.get()
        tag_names = tuple(
            tag.name
            for tag in self._service.get_all_tags()
        )
        options = (
            self.SEARCH_TAG_ALL,
            self.SEARCH_TAG_UNTAGGED,
            *tag_names,
        )
        self._search_tag_combobox.configure(values=options)

        if current_value not in options:
            self._search_tag_var.set(self.SEARCH_TAG_ALL)

    def _on_select_tags(self) -> None:
        """登録済みタグからフォームへ設定するタグを選択する。"""
        tags = self._service.get_all_tags()

        if not tags:
            messagebox.showinfo(
                "タグ選択",
                "登録済みのタグはありません。",
                parent=self._root,
            )
            return

        dialog = tk.Toplevel(self._root)
        dialog.title("タグ選択")
        dialog.transient(self._root)
        dialog.grab_set()

        listbox = tk.Listbox(
            dialog,
            selectmode=tk.MULTIPLE,
            exportselection=False,
            height=min(12, len(tags)),
            width=36,
        )
        listbox.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="nsew",
            padx=10,
            pady=10,
        )

        selected_names = {
            name.strip()
            for name in self._tags_var.get().split(
                self.TAG_SEPARATOR
            )
            if name.strip()
        }

        for index, tag in enumerate(tags):
            listbox.insert(tk.END, tag.name)
            if tag.name in selected_names:
                listbox.selection_set(index)

        def apply_selection() -> None:
            names = sorted(
                listbox.get(index)
                for index in listbox.curselection()
            )
            self._tags_var.set(
                self.TAG_SEPARATOR.join(names)
            )
            dialog.destroy()

        ttk.Button(
            dialog,
            text="設定",
            command=apply_selection,
        ).grid(row=1, column=0, padx=10, pady=(0, 10))
        ttk.Button(
            dialog,
            text="キャンセル",
            command=dialog.destroy,
        ).grid(row=1, column=1, padx=10, pady=(0, 10))
        self._wait_for_dialog(dialog)

    def _on_manage_tags(self) -> None:
        """タグの名称変更と削除を行うダイアログを表示する。"""
        dialog = tk.Toplevel(self._root)
        dialog.title("タグ管理")
        dialog.transient(self._root)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)

        tag_tree = ttk.Treeview(
            dialog,
            columns=("name", "book_count"),
            show="headings",
            selectmode="browse",
            height=12,
        )
        tag_tree.heading("name", text="タグ名")
        tag_tree.heading("book_count", text="使用冊数")
        tag_tree.column(
            "name",
            width=260,
            minwidth=160,
            anchor="w",
        )
        tag_tree.column(
            "book_count",
            width=90,
            minwidth=80,
            anchor="center",
            stretch=False,
        )
        tag_tree.grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="nsew",
            padx=10,
            pady=10,
        )

        ttk.Button(
            dialog,
            text="タグ名変更",
            command=lambda: self._rename_selected_tag(
                tag_tree,
            ),
        ).grid(row=1, column=0, padx=10, pady=(0, 10))
        ttk.Button(
            dialog,
            text="タグ削除",
            command=lambda: self._delete_selected_tag(
                tag_tree,
            ),
        ).grid(row=1, column=1, padx=10, pady=(0, 10))
        ttk.Button(
            dialog,
            text="閉じる",
            command=dialog.destroy,
        ).grid(row=1, column=2, padx=10, pady=(0, 10))

        self._populate_tag_management_tree(tag_tree)
        self._wait_for_dialog(dialog)

    def _populate_tag_management_tree(
        self,
        tag_tree: ttk.Treeview,
    ) -> None:
        """タグ管理一覧へタグ名と使用冊数を表示する。"""
        for item_id in tag_tree.get_children():
            tag_tree.delete(item_id)

        for tag in self._service.get_all_tags():
            if tag.id is None:
                continue

            tag_tree.insert(
                "",
                "end",
                iid=str(tag.id),
                values=(
                    tag.name,
                    self._service.count_books_by_tag(tag.id),
                ),
            )

    def _get_selected_tag(
        self,
        tag_tree: ttk.Treeview,
    ) -> tuple[int, str] | None:
        """タグ管理一覧で選択中のタグIDと名称を返す。"""
        selection = tag_tree.selection()

        if not selection:
            messagebox.showwarning(
                "タグ未選択",
                "操作するタグを選択してください。",
                parent=tag_tree.winfo_toplevel(),
            )
            return None

        item_id = selection[0]
        values = tag_tree.item(item_id, "values")

        return int(item_id), str(values[0])

    def _rename_selected_tag(
        self,
        tag_tree: ttk.Treeview,
    ) -> None:
        """タグ管理一覧で選択中のタグ名を変更する。"""
        selected_tag = self._get_selected_tag(tag_tree)

        if selected_tag is None:
            return

        tag_id, current_name = selected_tag
        new_name = simpledialog.askstring(
            "タグ名変更",
            "新しいタグ名を入力してください。",
            initialvalue=current_name,
            parent=tag_tree.winfo_toplevel(),
        )

        if new_name is None:
            return

        try:
            renamed = self._service.rename_tag(
                tag_id=tag_id,
                name=new_name,
            )

            if not renamed:
                messagebox.showwarning(
                    "タグが見つかりません",
                    "変更対象のタグが見つかりませんでした。",
                    parent=tag_tree.winfo_toplevel(),
                )
                self._refresh_after_tag_change(tag_tree)
                return

            self._refresh_after_tag_change(tag_tree)
            messagebox.showinfo(
                "タグ名変更完了",
                "タグ名を変更しました。",
                parent=tag_tree.winfo_toplevel(),
            )
        except ValueError as error:
            messagebox.showerror(
                "タグ名の確認",
                str(error),
                parent=tag_tree.winfo_toplevel(),
            )
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "タグ名変更エラー",
                "タグ名を変更できませんでした。",
                parent=tag_tree.winfo_toplevel(),
            )

    def _delete_selected_tag(
        self,
        tag_tree: ttk.Treeview,
    ) -> None:
        """タグ管理一覧で選択中のタグを削除する。"""
        selected_tag = self._get_selected_tag(tag_tree)

        if selected_tag is None:
            return

        tag_id, tag_name = selected_tag
        book_count = self._service.count_books_by_tag(tag_id)
        confirmed = messagebox.askyesno(
            "タグ削除の確認",
            (
                f"タグ「{tag_name}」は{book_count}件の書籍で"
                "使用されています。\n"
                "このタグを削除すると、すべての書籍から"
                "解除されます。\n"
                "削除しますか？"
            ),
            parent=tag_tree.winfo_toplevel(),
        )

        if not confirmed:
            return

        try:
            deleted = self._service.delete_tag(tag_id)

            if not deleted:
                messagebox.showwarning(
                    "タグが見つかりません",
                    "削除対象のタグが見つかりませんでした。",
                    parent=tag_tree.winfo_toplevel(),
                )
                self._refresh_after_tag_change(tag_tree)
                return

            self._refresh_after_tag_change(tag_tree)
            messagebox.showinfo(
                "タグ削除完了",
                "タグを削除しました。",
                parent=tag_tree.winfo_toplevel(),
            )
        except ValueError as error:
            messagebox.showerror(
                "タグ削除エラー",
                str(error),
                parent=tag_tree.winfo_toplevel(),
            )
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "タグ削除エラー",
                "タグを削除できませんでした。",
                parent=tag_tree.winfo_toplevel(),
            )

    def _refresh_after_tag_change(
        self,
        tag_tree: ttk.Treeview,
    ) -> None:
        """タグ変更後にタグと書籍の表示を最新状態へ更新する。"""
        selected_book_id = self._selected_book_id
        self._populate_tag_management_tree(tag_tree)
        self._refresh_tag_options()
        self._on_reload()

        if selected_book_id is None:
            return

        book_item = self._service.get_book(selected_book_id)

        if book_item is not None:
            self._display_book_in_form(book_item)

    def _on_manage_reading_histories(self) -> None:
        """選択中の書籍の読書履歴ダイアログを表示する。"""
        if self._selected_book_id is None:
            messagebox.showwarning(
                "書籍未選択",
                "読書履歴を表示する書籍を選択してください。",
                parent=self._root,
            )
            return

        book_item = self._service.get_book(
            self._selected_book_id
        )

        if book_item is None:
            messagebox.showwarning(
                "書籍が見つかりません",
                "対象の書籍が見つかりませんでした。",
                parent=self._root,
            )
            return

        self._open_reading_history_dialog(book_item)

    def _open_reading_history_dialog(
        self,
        book_item: BookItem,
    ) -> None:
        """指定された書籍の読書履歴ダイアログを構築する。"""
        if book_item.id is None:
            return

        dialog = tk.Toplevel(self._root)
        dialog.title("読書履歴")
        dialog.geometry("800x600")
        dialog.minsize(680, 520)
        dialog.transient(self._root)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(2, weight=1)

        self._reading_history_book_id = book_item.id
        self._selected_reading_history_id: int | None = None
        self._reading_history_started_on_var = tk.StringVar(
            master=dialog,
        )
        self._reading_history_completed_on_var = tk.StringVar(
            master=dialog,
        )

        ttk.Label(
            dialog,
            text=f"対象書籍：{book_item.title}",
            wraplength=750,
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=12,
            pady=(12, 6),
        )

        input_frame = ttk.LabelFrame(
            dialog,
            text="履歴内容",
            padding=10,
        )
        input_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=12,
            pady=(0, 8),
        )
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="読書開始日").grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 6),
        )
        ttk.Entry(
            input_frame,
            textvariable=self._reading_history_started_on_var,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            pady=(0, 6),
        )
        ttk.Label(input_frame, text="YYYY-MM-DD").grid(
            row=0,
            column=2,
            sticky="w",
            padx=(8, 0),
            pady=(0, 6),
        )

        ttk.Label(input_frame, text="読了日").grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 6),
        )
        ttk.Entry(
            input_frame,
            textvariable=self._reading_history_completed_on_var,
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            pady=(0, 6),
        )
        ttk.Label(input_frame, text="YYYY-MM-DD").grid(
            row=1,
            column=2,
            sticky="w",
            padx=(8, 0),
            pady=(0, 6),
        )

        ttk.Label(input_frame, text="読書メモ").grid(
            row=2,
            column=0,
            sticky="nw",
            padx=(0, 8),
        )
        self._reading_history_notes_text = tk.Text(
            input_frame,
            height=5,
            wrap="word",
        )
        self._reading_history_notes_text.grid(
            row=2,
            column=1,
            columnspan=2,
            sticky="ew",
        )

        history_frame = ttk.Frame(dialog)
        history_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=12,
            pady=(0, 8),
        )
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)

        self._reading_history_tree = ttk.Treeview(
            history_frame,
            columns=("started_on", "completed_on", "notes"),
            show="headings",
            selectmode="browse",
        )
        self._reading_history_tree.heading(
            "started_on",
            text="開始日",
        )
        self._reading_history_tree.heading(
            "completed_on",
            text="読了日",
        )
        self._reading_history_tree.heading(
            "notes",
            text="読書メモ",
        )
        self._reading_history_tree.column(
            "started_on",
            width=110,
            stretch=False,
        )
        self._reading_history_tree.column(
            "completed_on",
            width=110,
            stretch=False,
        )
        self._reading_history_tree.column(
            "notes",
            width=480,
        )
        self._reading_history_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        scrollbar = ttk.Scrollbar(
            history_frame,
            orient="vertical",
            command=self._reading_history_tree.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._reading_history_tree.configure(
            yscrollcommand=scrollbar.set,
        )
        self._reading_history_tree.bind(
            "<<TreeviewSelect>>",
            self._on_reading_history_select,
        )

        button_frame = ttk.Frame(dialog)
        button_frame.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=12,
            pady=(0, 12),
        )
        button_frame.columnconfigure(4, weight=1)

        ttk.Button(
            button_frame,
            text="新規登録",
            command=self._add_reading_history,
        ).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(
            button_frame,
            text="更新",
            command=self._update_reading_history,
        ).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(
            button_frame,
            text="削除",
            command=self._delete_reading_history,
        ).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(
            button_frame,
            text="入力クリア",
            command=self._clear_reading_history_form,
        ).grid(row=0, column=3, padx=(0, 6))
        ttk.Button(
            button_frame,
            text="閉じる",
            command=dialog.destroy,
        ).grid(row=0, column=5)

        try:
            self._populate_reading_history_tree(
                book_item.id,
                self._reading_history_tree,
            )
        except ValueError as error:
            messagebox.showerror(
                "読書履歴エラー",
                str(error),
                parent=dialog,
            )
            dialog.destroy()
            return
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "読書履歴エラー",
                "読書履歴を処理できませんでした。",
                parent=dialog,
            )
            dialog.destroy()
            return

        self._wait_for_dialog(dialog)

    def _populate_reading_history_tree(
        self,
        book_item_id: int,
        history_tree: ttk.Treeview,
    ) -> None:
        """指定書籍の読書履歴を一覧へ表示する。"""
        for item_id in history_tree.get_children():
            history_tree.delete(item_id)

        histories = (
            self._reading_history_service.get_histories_for_book(
                book_item_id
            )
        )

        for history in histories:
            if history.id is None:
                continue

            history_tree.insert(
                "",
                "end",
                iid=str(history.id),
                values=(
                    history.started_on or "",
                    history.completed_on or "",
                    self._reading_history_notes_summary(
                        history.notes
                    ),
                ),
            )

    @staticmethod
    def _reading_history_notes_summary(
        notes: str | None,
    ) -> str:
        """一覧表示用に読書メモを一行へ要約する。"""
        if notes is None:
            return ""

        single_line = " ".join(notes.splitlines())
        maximum_length = 50

        if len(single_line) <= maximum_length:
            return single_line

        return f"{single_line[:maximum_length]}…"

    def _on_reading_history_select(
        self,
        _event: tk.Event[tk.Misc] | None = None,
    ) -> None:
        """選択した読書履歴を入力欄へ表示する。"""
        selection = self._reading_history_tree.selection()

        if not selection:
            return

        reading_history_id = int(selection[0])

        try:
            history = self._reading_history_service.get_history(
                reading_history_id
            )

            if history is None:
                messagebox.showwarning(
                    "読書履歴が見つかりません",
                    "選択した読書履歴が見つかりませんでした。",
                    parent=self._reading_history_tree.winfo_toplevel(),
                )
                self._populate_reading_history_tree(
                    self._reading_history_book_id,
                    self._reading_history_tree,
                )
                self._clear_reading_history_form()
                return

            self._selected_reading_history_id = history.id
            self._reading_history_started_on_var.set(
                history.started_on or ""
            )
            self._reading_history_completed_on_var.set(
                history.completed_on or ""
            )
            self._reading_history_notes_text.delete("1.0", tk.END)
            self._reading_history_notes_text.insert(
                "1.0",
                history.notes or "",
            )
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "読書履歴エラー",
                "読書履歴を処理できませんでした。",
                parent=self._reading_history_tree.winfo_toplevel(),
            )

    def _get_reading_history_form_values(
        self,
    ) -> tuple[str, str, str]:
        """読書履歴入力欄の値を取得する。"""
        return (
            self._reading_history_started_on_var.get(),
            self._reading_history_completed_on_var.get(),
            self._reading_history_notes_text.get("1.0", "end-1c"),
        )

    def _add_reading_history(self) -> None:
        """入力内容を新しい読書履歴として登録する。"""
        started_on, completed_on, notes = (
            self._get_reading_history_form_values()
        )
        parent = self._reading_history_tree.winfo_toplevel()

        try:
            self._reading_history_service.add_history(
                book_item_id=self._reading_history_book_id,
                started_on=started_on,
                completed_on=completed_on,
                notes=notes,
            )
            self._populate_reading_history_tree(
                self._reading_history_book_id,
                self._reading_history_tree,
            )
            self._clear_reading_history_form()
            messagebox.showinfo(
                "読書履歴登録完了",
                "読書履歴を登録しました。",
                parent=parent,
            )
        except ValueError as error:
            messagebox.showerror(
                "読書履歴の確認",
                str(error),
                parent=parent,
            )
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "読書履歴エラー",
                "読書履歴を処理できませんでした。",
                parent=parent,
            )

    def _update_reading_history(self) -> None:
        """選択中の読書履歴を入力内容で更新する。"""
        parent = self._reading_history_tree.winfo_toplevel()

        if self._selected_reading_history_id is None:
            messagebox.showwarning(
                "読書履歴未選択",
                "更新する読書履歴を選択してください。",
                parent=parent,
            )
            return

        started_on, completed_on, notes = (
            self._get_reading_history_form_values()
        )
        history = ReadingHistory(
            id=self._selected_reading_history_id,
            book_item_id=self._reading_history_book_id,
            started_on=started_on,
            completed_on=completed_on,
            notes=notes,
        )

        try:
            updated = self._reading_history_service.update_history(
                history
            )

            if not updated:
                messagebox.showwarning(
                    "読書履歴が見つかりません",
                    "更新する読書履歴が見つかりませんでした。",
                    parent=parent,
                )
                self._populate_reading_history_tree(
                    self._reading_history_book_id,
                    self._reading_history_tree,
                )
                self._clear_reading_history_form()
                return

            self._populate_reading_history_tree(
                self._reading_history_book_id,
                self._reading_history_tree,
            )
            self._clear_reading_history_form()
            messagebox.showinfo(
                "読書履歴更新完了",
                "読書履歴を更新しました。",
                parent=parent,
            )
        except ValueError as error:
            messagebox.showerror(
                "読書履歴の確認",
                str(error),
                parent=parent,
            )
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "読書履歴エラー",
                "読書履歴を処理できませんでした。",
                parent=parent,
            )

    def _delete_reading_history(self) -> None:
        """選択中の読書履歴を確認後に削除する。"""
        parent = self._reading_history_tree.winfo_toplevel()

        if self._selected_reading_history_id is None:
            messagebox.showwarning(
                "読書履歴未選択",
                "削除する読書履歴を選択してください。",
                parent=parent,
            )
            return

        confirmed = messagebox.askyesno(
            "読書履歴削除の確認",
            "選択した読書履歴を削除しますか？",
            parent=parent,
        )

        if not confirmed:
            return

        try:
            deleted = self._reading_history_service.delete_history(
                self._selected_reading_history_id
            )

            if not deleted:
                messagebox.showwarning(
                    "読書履歴が見つかりません",
                    "削除する読書履歴が見つかりませんでした。",
                    parent=parent,
                )
            else:
                messagebox.showinfo(
                    "読書履歴削除完了",
                    "読書履歴を削除しました。",
                    parent=parent,
                )

            self._populate_reading_history_tree(
                self._reading_history_book_id,
                self._reading_history_tree,
            )
            self._clear_reading_history_form()
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "読書履歴エラー",
                "読書履歴を処理できませんでした。",
                parent=parent,
            )

    def _clear_reading_history_form(self) -> None:
        """読書履歴の入力欄と選択状態をクリアする。"""
        self._selected_reading_history_id = None
        self._reading_history_started_on_var.set("")
        self._reading_history_completed_on_var.set("")
        self._reading_history_notes_text.delete("1.0", tk.END)

        selections = self._reading_history_tree.selection()

        if selections:
            self._reading_history_tree.selection_remove(*selections)

    def _on_show_reading_statistics(self) -> None:
        """読書集計ダイアログを表示する。"""
        self._open_reading_statistics_dialog()

    def _open_reading_statistics_dialog(self) -> None:
        """読書集計ダイアログを構築する。"""
        dialog = tk.Toplevel(self._root)
        dialog.title("読書集計")
        dialog.geometry("900x650")
        dialog.minsize(760, 540)
        dialog.transient(self._root)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(2, weight=1)

        self._reading_statistics_dialog = dialog
        self._reading_statistics_year_var = tk.StringVar(
            master=dialog,
        )
        self._reading_statistics_summary_vars = {
            "total_history_count": tk.StringVar(master=dialog),
            "books_with_history_count": tk.StringVar(master=dialog),
            "completed_history_count": tk.StringVar(master=dialog),
            "reread_book_count": tk.StringVar(master=dialog),
        }
        self._reading_statistics_month_vars = [
            tk.StringVar(master=dialog)
            for _ in range(12)
        ]
        self._monthly_reading_counts: list[
            MonthlyReadingCount
        ] = []

        ttk.Label(
            dialog,
            text="読書集計",
            font=("TkDefaultFont", 14, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=12,
            pady=(12, 8),
        )

        summary_frame = ttk.LabelFrame(
            dialog,
            text="全体集計",
            padding=10,
        )
        summary_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=12,
            pady=(0, 8),
        )

        summary_items = (
            ("履歴総数", "total_history_count"),
            ("履歴のある書籍", "books_with_history_count"),
            ("読了記録", "completed_history_count"),
            ("再読書籍", "reread_book_count"),
        )

        for column, (label_text, key) in enumerate(summary_items):
            summary_frame.columnconfigure(column, weight=1)
            item_frame = ttk.Frame(summary_frame, padding=6)
            item_frame.grid(row=0, column=column, sticky="ew")
            ttk.Label(
                item_frame,
                text=label_text,
                anchor="center",
            ).grid(row=0, column=0, sticky="ew")
            ttk.Label(
                item_frame,
                textvariable=(
                    self._reading_statistics_summary_vars[key]
                ),
                anchor="center",
                font=("TkDefaultFont", 13, "bold"),
            ).grid(row=1, column=0, sticky="ew", pady=(4, 0))
            item_frame.columnconfigure(0, weight=1)

        chart_frame = ttk.LabelFrame(
            dialog,
            text="月別読了数",
            padding=10,
        )
        chart_frame.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=12,
            pady=(0, 8),
        )
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(1, weight=1)

        year_frame = ttk.Frame(chart_frame)
        year_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )
        ttk.Label(year_frame, text="対象年").grid(
            row=0,
            column=0,
            padx=(0, 8),
        )
        self._reading_statistics_year_combobox = ttk.Combobox(
            year_frame,
            textvariable=self._reading_statistics_year_var,
            width=10,
            state="readonly",
        )
        self._reading_statistics_year_combobox.grid(
            row=0,
            column=1,
            sticky="w",
        )
        self._reading_statistics_year_combobox.bind(
            "<<ComboboxSelected>>",
            self._on_reading_statistics_year_changed,
        )

        self._reading_statistics_canvas = tk.Canvas(
            chart_frame,
            background="white",
            highlightthickness=1,
            highlightbackground="#b0b0b0",
        )
        self._reading_statistics_canvas.grid(
            row=1,
            column=0,
            sticky="nsew",
        )
        self._reading_statistics_canvas.bind(
            "<Configure>",
            self._on_reading_statistics_canvas_configure,
        )

        month_frame = ttk.Frame(chart_frame)
        month_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(8, 0),
        )

        for index, month_var in enumerate(
            self._reading_statistics_month_vars
        ):
            column = index % 6
            row = index // 6
            month_frame.columnconfigure(column, weight=1)
            ttk.Label(
                month_frame,
                textvariable=month_var,
                anchor="center",
            ).grid(
                row=row,
                column=column,
                sticky="ew",
                pady=2,
            )

        button_frame = ttk.Frame(dialog)
        button_frame.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=12,
            pady=(0, 12),
        )
        button_frame.columnconfigure(0, weight=1)
        ttk.Button(
            button_frame,
            text="閉じる",
            command=dialog.destroy,
        ).grid(row=0, column=1)

        try:
            self._load_reading_statistics()
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "読書集計エラー",
                "読書集計を表示できませんでした。",
                parent=dialog,
            )
            dialog.destroy()
            return

        self._wait_for_dialog(dialog)

    def _wait_for_dialog(
        self,
        dialog: tk.Toplevel,
    ) -> None:
        """親画面中央へ表示して待機する。"""
        center_window_on_parent(
            dialog,
            self._root,
        )
        dialog.wait_window()

    def _on_open_settings(self) -> None:
        """アプリケーション設定画面を表示する。"""
        try:
            snapshot = (
                self._application_settings_service.get_snapshot()
            )
        except ApplicationSettingsError as error:
            messagebox.showerror(
                "設定エラー",
                str(error),
                parent=self._root,
            )
            return

        dialog = tk.Toplevel(self._root)
        dialog.title("設定")
        dialog.transient(self._root)
        dialog.grab_set()
        dialog.resizable(True, False)
        dialog.columnconfigure(0, weight=1)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

        api_key_variable = tk.StringVar(master=dialog)
        api_key_status_variable = tk.StringVar(
            master=dialog,
            value=(
                "設定済み"
                if snapshot.google_books_api_key_is_configured
                else "未設定"
            ),
        )

        external_service_frame = ttk.LabelFrame(
            dialog,
            text="外部サービス",
            padding=10,
        )
        external_service_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=12,
            pady=(12, 6),
        )
        external_service_frame.columnconfigure(1, weight=1)

        ttk.Label(
            external_service_frame,
            text="Google Books APIキー",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
        )
        api_key_entry = ttk.Entry(
            external_service_frame,
            textvariable=api_key_variable,
            show="*",
            width=56,
        )
        api_key_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 8),
        )
        ttk.Label(
            external_service_frame,
            textvariable=api_key_status_variable,
            width=8,
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )

        api_key_button_frame = ttk.Frame(
            external_service_frame,
        )
        api_key_button_frame.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="e",
            pady=(8, 0),
        )
        ttk.Button(
            api_key_button_frame,
            text="保存",
            command=lambda: self._save_google_books_api_key(
                api_key_variable,
                api_key_status_variable,
                dialog,
            ),
        ).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(
            api_key_button_frame,
            text="削除",
            command=lambda: self._delete_google_books_api_key(
                api_key_variable,
                api_key_status_variable,
                dialog,
            ),
        ).grid(row=0, column=1)

        ttk.Label(
            external_service_frame,
            text=(
                "APIキーは現在のWindows利用者の環境変数へ"
                "保存されます。保存済みの値は画面へ"
                "表示しません。"
            ),
            wraplength=650,
        ).grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(8, 0),
        )

        data_frame = ttk.LabelFrame(
            dialog,
            text="利用者データ",
            padding=10,
        )
        data_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=12,
            pady=6,
        )
        data_frame.columnconfigure(1, weight=1)

        path_rows = (
            (
                "データベース",
                snapshot.database_path,
                snapshot.database_path.parent,
            ),
            (
                "バックアップ",
                snapshot.backup_directory,
                snapshot.backup_directory,
            ),
            (
                "表紙画像",
                snapshot.cover_cache_directory,
                snapshot.cover_cache_directory,
            ),
            (
                "ログ",
                snapshot.log_path,
                snapshot.log_path.parent,
            ),
        )

        for row, (label, path, directory) in enumerate(path_rows):
            self._create_settings_path_row(
                data_frame,
                row=row,
                label=label,
                path=path,
                directory=directory,
                dialog=dialog,
            )

        information_frame = ttk.LabelFrame(
            dialog,
            text="アプリケーション情報",
            padding=10,
        )
        information_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=12,
            pady=6,
        )
        information_frame.columnconfigure(1, weight=1)

        information_rows = (
            ("アプリケーション名", snapshot.application_name),
            ("Version", snapshot.application_version),
            ("利用者データ", str(snapshot.root_directory)),
        )

        for row, (label, value) in enumerate(information_rows):
            ttk.Label(
                information_frame,
                text=label,
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 8),
                pady=3,
            )
            ttk.Label(
                information_frame,
                text=value,
            ).grid(
                row=row,
                column=1,
                sticky="w",
                pady=3,
            )

        button_frame = ttk.Frame(dialog)
        button_frame.grid(
            row=3,
            column=0,
            sticky="e",
            padx=12,
            pady=(6, 12),
        )
        ttk.Button(
            button_frame,
            text="閉じる",
            command=dialog.destroy,
        ).grid(row=0, column=0)

        api_key_entry.focus_set()
        self._wait_for_dialog(dialog)

    def _create_settings_path_row(
        self,
        parent: ttk.LabelFrame,
        *,
        row: int,
        label: str,
        path: Path,
        directory: Path,
        dialog: tk.Toplevel,
    ) -> None:
        """設定画面へ利用者データのパス行を追加する。"""
        ttk.Label(
            parent,
            text=label,
        ).grid(
            row=row,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=3,
        )
        path_entry = ttk.Entry(parent, width=72)
        path_entry.insert(0, str(path))
        path_entry.configure(state="readonly")
        path_entry.grid(
            row=row,
            column=1,
            sticky="ew",
            padx=(0, 8),
            pady=3,
        )
        ttk.Button(
            parent,
            text="フォルダーを開く",
            command=lambda: self._open_settings_directory(
                directory,
                dialog,
            ),
        ).grid(
            row=row,
            column=2,
            pady=3,
        )

    def _save_google_books_api_key(
        self,
        api_key_variable: tk.StringVar,
        status_variable: tk.StringVar,
        dialog: tk.Toplevel,
    ) -> None:
        """入力されたGoogle Books APIキーを保存する。"""
        try:
            api_key = (
                self._application_settings_service
                .save_google_books_api_key(
                    api_key_variable.get()
                )
            )
        except ApplicationSettingsError as error:
            messagebox.showerror(
                "設定エラー",
                str(error),
                parent=dialog,
            )
            return

        api_key_variable.set("")
        status_variable.set("設定済み")

        try:
            self._on_google_books_api_key_changed(api_key)
        except Exception:
            traceback.print_exc()
            messagebox.showwarning(
                "設定反映の確認",
                (
                    "APIキーは保存されましたが、現在の画面へ"
                    "反映できませんでした。アプリケーションを"
                    "再起動してください。"
                ),
                parent=dialog,
            )
            return

        messagebox.showinfo(
            "設定",
            "Google Books APIキーを保存しました。",
            parent=dialog,
        )

    def _delete_google_books_api_key(
        self,
        api_key_variable: tk.StringVar,
        status_variable: tk.StringVar,
        dialog: tk.Toplevel,
    ) -> None:
        """Google Books APIキーを確認後に削除する。"""
        try:
            snapshot = (
                self._application_settings_service.get_snapshot()
            )
        except ApplicationSettingsError as error:
            messagebox.showerror(
                "設定エラー",
                str(error),
                parent=dialog,
            )
            return

        if not snapshot.google_books_api_key_is_configured:
            messagebox.showinfo(
                "設定",
                "Google Books APIキーは設定されていません。",
                parent=dialog,
            )
            return

        should_delete = messagebox.askyesno(
            "APIキー削除",
            "Google Books APIキーを削除しますか？",
            parent=dialog,
        )

        if not should_delete:
            return

        try:
            (
                self._application_settings_service
                .delete_google_books_api_key()
            )
        except ApplicationSettingsError as error:
            messagebox.showerror(
                "設定エラー",
                str(error),
                parent=dialog,
            )
            return

        api_key_variable.set("")
        status_variable.set("未設定")

        try:
            self._on_google_books_api_key_changed(None)
        except Exception:
            traceback.print_exc()
            messagebox.showwarning(
                "設定反映の確認",
                (
                    "APIキーは削除されましたが、現在の画面へ"
                    "反映できませんでした。アプリケーションを"
                    "再起動してください。"
                ),
                parent=dialog,
            )
            return

        messagebox.showinfo(
            "設定",
            "Google Books APIキーを削除しました。",
            parent=dialog,
        )

    def _open_settings_directory(
        self,
        directory: Path,
        dialog: tk.Toplevel,
    ) -> None:
        """設定画面で選択したフォルダーを開く。"""
        try:
            self._application_settings_service.open_directory(
                directory
            )
        except DirectoryOpenError as error:
            messagebox.showerror(
                "フォルダーエラー",
                str(error),
                parent=dialog,
            )

    def _load_reading_statistics(self) -> None:
        """全体集計と対象年一覧を読み込む。"""
        summary = (
            self._reading_history_service.get_statistics_summary()
        )
        self._set_reading_statistics_summary(summary)
        years = self._reading_history_service.get_completed_years()
        year_values = tuple(str(year) for year in years)
        self._reading_statistics_year_combobox.configure(
            values=year_values,
        )

        if not years:
            self._reading_statistics_year_var.set("")
            self._reading_statistics_year_combobox.configure(
                state="disabled",
            )
            self._set_monthly_reading_counts([])
            return

        self._reading_statistics_year_combobox.configure(
            state="readonly",
        )
        self._reading_statistics_year_var.set(str(years[0]))
        self._refresh_monthly_reading_statistics(years[0])

    def _set_reading_statistics_summary(
        self,
        summary: ReadingStatisticsSummary,
    ) -> None:
        """全体集計値を画面表示へ反映する。"""
        values = {
            "total_history_count": (
                f"{summary.total_history_count}回"
            ),
            "books_with_history_count": (
                f"{summary.books_with_history_count}冊"
            ),
            "completed_history_count": (
                f"{summary.completed_history_count}回"
            ),
            "reread_book_count": f"{summary.reread_book_count}冊",
        }

        for key, value in values.items():
            self._reading_statistics_summary_vars[key].set(value)

    def _on_reading_statistics_year_changed(
        self,
        _event: tk.Event[tk.Misc] | None = None,
    ) -> None:
        """選択年に応じて月別読了数を更新する。"""
        year_text = self._reading_statistics_year_var.get()

        if year_text == "":
            self._set_monthly_reading_counts([])
            return

        try:
            self._refresh_monthly_reading_statistics(int(year_text))
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "読書集計エラー",
                "読書集計を表示できませんでした。",
                parent=self._reading_statistics_dialog,
            )

    def _refresh_monthly_reading_statistics(
        self,
        year: int,
    ) -> None:
        """指定年の月別集計を取得して表示する。"""
        monthly_counts = (
            self._reading_history_service.get_monthly_reading_counts(
                year
            )
        )
        self._set_monthly_reading_counts(monthly_counts)

    def _set_monthly_reading_counts(
        self,
        monthly_counts: list[MonthlyReadingCount],
    ) -> None:
        """月別数値と棒グラフへ集計結果を反映する。"""
        count_by_month = {
            item.month: item.completed_count
            for item in monthly_counts
        }

        for month, month_var in enumerate(
            self._reading_statistics_month_vars,
            start=1,
        ):
            month_var.set(
                f"{month}月 {count_by_month.get(month, 0)}件"
            )

        self._monthly_reading_counts = list(monthly_counts)
        self._draw_monthly_reading_chart(
            self._reading_statistics_canvas,
            self._monthly_reading_counts,
        )

    def _on_reading_statistics_canvas_configure(
        self,
        _event: tk.Event[tk.Misc] | None = None,
    ) -> None:
        """Canvasの現在サイズに合わせてグラフを再描画する。"""
        self._draw_monthly_reading_chart(
            self._reading_statistics_canvas,
            self._monthly_reading_counts,
        )

    @staticmethod
    def _draw_monthly_reading_chart(
        canvas: tk.Canvas,
        monthly_counts: list[MonthlyReadingCount],
    ) -> None:
        """月別読了数をCanvasへ棒グラフとして描画する。"""
        canvas.delete("all")
        canvas.update_idletasks()
        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 1)
        counts = {
            item.month: item.completed_count
            for item in monthly_counts
        }
        maximum_count = max(counts.values(), default=0)

        if maximum_count == 0:
            canvas.create_text(
                width / 2,
                height / 2,
                text="読了記録がありません。",
                fill="#555555",
            )
            return

        left_margin = 40
        right_margin = 20
        top_margin = 30
        bottom_margin = 40
        drawable_width = max(
            width - left_margin - right_margin,
            1,
        )
        drawable_height = max(
            height - top_margin - bottom_margin,
            1,
        )
        slot_width = drawable_width / 12
        bar_width = max(slot_width * 0.62, 1)
        baseline = top_margin + drawable_height

        canvas.create_line(
            left_margin,
            top_margin,
            left_margin,
            baseline,
            fill="#777777",
        )
        canvas.create_line(
            left_margin,
            baseline,
            width - right_margin,
            baseline,
            fill="#777777",
        )

        for month in range(1, 13):
            count = counts.get(month, 0)
            center_x = (
                left_margin
                + slot_width * (month - 1)
                + slot_width / 2
            )
            bar_height = (
                drawable_height * count / maximum_count
            )
            top_y = baseline - bar_height

            if count > 0:
                canvas.create_rectangle(
                    center_x - bar_width / 2,
                    top_y,
                    center_x + bar_width / 2,
                    baseline,
                    fill="#4f81bd",
                    outline="#3a6491",
                )

            count_y = max(top_y - 10, 10)
            canvas.create_text(
                center_x,
                count_y,
                text=str(count),
                fill="#333333",
            )
            canvas.create_text(
                center_x,
                baseline + 18,
                text=f"{month}月",
                fill="#333333",
            )

# ここからイベントハンドラ

    def _on_search(
        self,
        _event: tk.Event[tk.Misc] | None = None,
    ) -> None:
        """指定された条件で書籍を検索する。"""
        try:
            books = self._get_filtered_books()

            sort_by, descending = (
                self._get_sort_settings()
            )

            books = self._service.sort_books(
                books,
                sort_by=sort_by,
                descending=descending,
            )

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

    def _on_clear_search(self) -> None:
        """検索条件を初期状態へ戻して全件表示する。"""
        self._search_title_var.set("")
        self._search_author_var.set("")
        self._search_publisher_var.set("")
        self._search_isbn_var.set("")
        self._search_magazine_code_var.set("")
        self._search_reading_status_var.set(
            "すべて"
        )
        self._search_favorite_var.set(
            "すべて"
        )
        self._search_rating_var.set(
            "すべて"
        )
        self._search_tag_var.set(
            self.SEARCH_TAG_ALL
        )

        self._load_all_books()

        self._search_title_entry.focus_set()

    def _on_sort_changed(
        self,
        _event: tk.Event[tk.Misc] | None = None,
    ) -> None:
        """現在の検索条件を保ったまま一覧を並べ替える。"""
        selected_book_id = self._selected_book_id

        try:
            books = self._get_filtered_books()

            sort_by, descending = (
                self._get_sort_settings()
            )

            books = self._service.sort_books(
                books,
                sort_by=sort_by,
                descending=descending,
            )

            status_prefix = (
                "検索結果"
                if self._has_search_conditions()
                else "全"
            )

            self._display_books(
                books,
                status_prefix=status_prefix,
            )

            if selected_book_id is None:
                return

            if self._book_tree.exists(
                str(selected_book_id),
            ):
                self._select_book_in_tree(
                    selected_book_id,
                )

        except ValueError as error:
            messagebox.showerror(
                "並べ替えエラー",
                str(error),
                parent=self._root,
            )
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "並べ替えエラー",
                "書籍一覧を並べ替えできませんでした。",
                parent=self._root,
            )

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
                "入力内容の確認",
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
                cover_image_url=values["cover_image_url"],
                cover_image_path=values["cover_image_path"],
                completion_month=(
                    values["completion_month"]
                ),
                reading_status=values["reading_status"],
                is_favorite=values["is_favorite"],
                rating=values["rating"],
                tags=values["tags"],
                notes=values["notes"],
            )

            if registered_book.id is None:
                raise RuntimeError(
                    "登録済み書籍のIDを取得できませんでした。",
                )

            self._refresh_tag_options()
            self._load_all_books()

            messagebox.showinfo(
                "登録完了",
                "書籍を登録しました。",
                parent=self._root,
            )

            self._clear_form()
            self._title_entry.focus_set()

        except ValueError as error:
            messagebox.showerror(
                "入力内容の確認",
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
                "入力内容の確認",
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
                (
                    "次の書籍情報を更新しますか？\n\n"
                    f"{title}"
                ),
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

            self._refresh_tag_options()
            self._load_all_books()

            messagebox.showinfo(
                "更新完了",
                "書籍情報を更新しました。",
                parent=self._root,
            )

            self._clear_form()
            self._title_entry.focus_set()

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
        """現在の検索・ソート条件を維持して一覧を再読み込みする。"""
        selected_book_id = self._selected_book_id

        try:
            books = self._get_filtered_books()

            sort_by, descending = (
                self._get_sort_settings()
            )

            books = self._service.sort_books(
                books,
                sort_by=sort_by,
                descending=descending,
            )

            status_prefix = (
                "検索結果"
                if self._has_search_conditions()
                else "全"
            )

            self._display_books(
                books,
                status_prefix=status_prefix,
            )

            if selected_book_id is None:
                return

            if self._book_tree.exists(
                str(selected_book_id),
            ):
                self._select_book_in_tree(
                    selected_book_id,
                )

        except ValueError as error:
            messagebox.showerror(
                "再読み込みエラー",
                str(error),
                parent=self._root,
            )
        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "再読み込みエラー",
                "書籍情報を再読み込みできませんでした。",
                parent=self._root,
            )

    def _on_export_csv(self) -> None:
        """登録済み書籍をCSVファイルへエクスポートする。"""
        try:
            books = self._service.get_sorted_books(
                sort_by="registered",
                descending=True,
            )

            if not books:
                messagebox.showinfo(
                    "CSVエクスポート",
                    "エクスポートできる書籍がありません。",
                    parent=self._root,
                )
                return

            default_filename = (
                "book_manager_"
                f"{datetime.now():%Y%m%d_%H%M%S}"
                ".csv"
            )

            output_filename = filedialog.asksaveasfilename(
                parent=self._root,
                title="CSVファイルを保存",
                defaultextension=".csv",
                initialfile=default_filename,
                filetypes=[
                    (
                        "CSVファイル",
                        "*.csv",
                    ),
                    (
                        "すべてのファイル",
                        "*.*",
                    ),
                ],
            )

            if not output_filename:
                return
            self._csv_export_service.export(
                books,
                Path(output_filename),
            )

            messagebox.showinfo(
                "CSVエクスポート完了",
                "CSVエクスポートが完了しました。",
                parent=self._root,
            )

        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "CSVエクスポートエラー",
                "CSVファイルを保存できませんでした。",
                parent=self._root,
            )

    def _on_import_csv(self) -> None:
        """CSVファイルから書籍情報をインポートする。"""
        input_filename = filedialog.askopenfilename(
            title="CSVファイルを選択",
            filetypes=[
                (
                    "CSVファイル",
                    "*.csv",
                ),
                (
                    "すべてのファイル",
                    "*.*",
                ),
            ],
            parent=self._root,
        )

        if not input_filename:
            return

        try:
            result = self._csv_import_service.import_file(
                Path(input_filename),
            )

            self._refresh_tag_options()
            self._load_all_books()

            message_lines = [
                "CSVインポートが完了しました。",
                "",
                f"登録: {result.imported_count}件",
                f"スキップ: {result.skipped_count}件",
                f"エラー: {result.error_count}件",
            ]

            if result.skipped:
                message_lines.extend(
                    [
                        "",
                        "【スキップ】",
                    ]
                )
                message_lines.extend(
                    f"{issue.row_number}行目: {issue.message}"
                    for issue in result.skipped
                )

            if result.errors:
                message_lines.extend(
                    [
                        "",
                        "【エラー】",
                    ]
                )
                message_lines.extend(
                    f"{issue.row_number}行目: {issue.message}"
                    for issue in result.errors
                )

            messagebox.showinfo(
                "CSVインポート完了",
                "\n".join(message_lines),
                parent=self._root,
            )

        except Exception:
            traceback.print_exc()
            messagebox.showerror(
                "CSVインポートエラー",
                "CSVファイルをインポートできませんでした。",
                parent=self._root,
            )

    def _on_restore_backup(self) -> None:
        """バックアップからデータベースを復元する。"""
        backup_filename = filedialog.askopenfilename(
            title="復元するバックアップを選択",
            filetypes=[
                (
                    "SQLiteデータベース",
                    "*.db",
                ),
                (
                    "すべてのファイル",
                    "*.*",
                ),
            ],
        )

        if not backup_filename:
            return

        confirmed = messagebox.askyesno(
            "バックアップ復元の確認",
            (
                "バックアップからデータを復元します。\n\n"
                "現在のデータは復元前にバックアップされます。\n"
                "復元すると、現在のデータは選択した"
                "バックアップ時点の状態に置き換わります。\n\n"
                "続行しますか？"
            ),
            parent=self._root,
        )

        if not confirmed:
            return

        try:
            self._backup_service.restore_backup(
                Path(backup_filename),
            )

            self._selected_book_id = None
            self._refresh_tag_options()
            self._load_all_books()

            messagebox.showinfo(
                "バックアップ復元完了",
                "バックアップからデータを復元しました。",
                parent=self._root,
            )

        except Exception:
            traceback.print_exc()

            messagebox.showerror(
                "バックアップ復元エラー",
                "バックアップからデータを復元できませんでした。",
                parent=self._root,
            )

    def _on_exit(self) -> None:
        """アプリケーションを終了する。"""
        self._root.destroy()

    def _on_fetch_book_metadata(self) -> None:
        """ISBNから外部書誌情報を取得してフォームへ反映する。"""
        isbn = self._isbn_var.get().strip()

        if isbn == "":
            messagebox.showwarning(
                "入力内容の確認",
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
                self._current_cover_image_url = (
                    result.cover_image_url
                )

                try:
                    cover_path = self._service.fetch_cover_image(
                        result.cover_image_url,
                    )

                    self._current_cover_image_path = (
                        self._service
                        .create_stored_cover_image_path(
                            cover_path,
                        )
                    )

                    self._display_cover_image(
                        str(cover_path),
                    )

                except Exception:
                    traceback.print_exc()

                    self._current_cover_image_path = None

                    self._clear_cover_image()

                    messagebox.showwarning(
                        "表紙画像を表示できません",
                        (
                            "書誌情報は取得できましたが、"
                            "表紙画像を表示できませんでした。"
                        ),
                        parent=self._root,
                    )
            else:
                self._clear_cover_state()

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
                "ISBN入力内容の確認",
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
