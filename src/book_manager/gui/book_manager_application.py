"""書籍管理アプリケーションのメインGUI。"""

from __future__ import annotations

import tkinter as tk
import traceback
import logging
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import TYPE_CHECKING
from PIL import Image, ImageTk
from pathlib import Path
from datetime import datetime
import ctypes
import sys

from book_manager.gui.metadata_comparison_dialog import MetadataComparisonDialog
from book_manager.gui.book_candidate_search_dialog import (
    BookCandidateSearchDialog, CandidateSearchTask,
)
from book_manager.gui.author_link_review_dialog import AuthorLinkReviewDialog
from book_manager.gui.author_dialogs import AuthorSelectionDialog
from book_manager.services.author_service import AuthorService
from book_manager.gui.excel_column_mapping_dialog import ExcelColumnMappingDialog
from book_manager.gui.excel_import_preview_dialog import ExcelImportPreviewDialog
from book_manager.models.book_item import BookItem
from book_manager.models.application_settings import BackupSettingsSnapshot
from book_manager.models.reading_history import ReadingHistory
from book_manager.models.reading_statistics import (
    MonthlyReadingCount,
    ReadingStatisticsSummary,
)
from book_manager.models.fetched_book_data import (
    FetchedBookData,
)
from book_manager.gui.window_positioning import (
    ScreenWorkArea,
    WindowRectangle,
    calculate_safe_window_rectangle,
    center_window_on_parent,
    get_screen_work_areas,
    select_work_area,
)
from book_manager.config.window_state_store import (
    WindowStateStore,
    WindowStateStoreError,
)
from book_manager.config.list_view_state_store import (
    ListViewStateStore,
    ListViewStateStoreError,
)
from book_manager.models.list_view_state import ListViewState
from book_manager.models.window_state import WindowState
from book_manager.services.application_settings_service import (
    ApplicationSettingsError,
    CoverCacheSettingsError,
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
    from book_manager.services.excel_workbook_reader_service import ExcelWorkbookReaderService
    from book_manager.services.excel_import_preflight_service import ExcelImportPreflightService
    from book_manager.services.excel_import_service import ExcelImportService
    from book_manager.services.backup_service import BackupService
    from book_manager.services.application_settings_service import (
        ApplicationSettingsService,
    )
    from book_manager.services.book_service import BookService
    from book_manager.services.cover_image_service import (
        CoverCacheStatus,
    )
    from book_manager.services.csv_export_service import (
        CsvExportService,
    )
    from book_manager.services.csv_import_service import (
        CsvImportService,
    )
    from book_manager.services.csv_data_package_export_service import (
        CsvDataPackageExportService,
    )
    from book_manager.services.csv_data_package_import_service import (
        CsvDataPackageImportService,
    )
    from book_manager.services.csv_data_package_preflight_service import (
        CsvDataPackagePreflightService,
    )
    from book_manager.services.reading_history_service import (
        ReadingHistoryService,
    )
    from collections.abc import Callable


logger = logging.getLogger(__name__)


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

    SORT_KEY_TYPE_MAP = {
        "registered": "登録順",
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
        window_state_store: WindowStateStore | None = None,
        list_view_state_store: ListViewStateStore | None = None,
        csv_data_package_export_service: (
            CsvDataPackageExportService | None
        ) = None,
        csv_data_package_preflight_service: (
            CsvDataPackagePreflightService | None
        ) = None,
        csv_data_package_import_service: (
            CsvDataPackageImportService | None
        ) = None,
        excel_workbook_reader_service: ExcelWorkbookReaderService | None = None,
        excel_import_preflight_service: ExcelImportPreflightService | None = None,
        excel_import_service: ExcelImportService | None = None,
        author_service: AuthorService | None = None,
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
            window_state_store:
                メインウィンドウ状態の保存処理。未指定時は従来の
                中央配置を使用し、状態を保存しない。
            list_view_state_store:
                一覧表示状態の保存処理。未指定時は既定の列幅と
                並び順を使用する。
        """
        self._root = root
        self._service = service
        self._csv_export_service = csv_export_service
        self._csv_import_service = csv_import_service
        self._csv_data_package_export_service = (
            csv_data_package_export_service
        )
        self._csv_data_package_preflight_service = (
            csv_data_package_preflight_service
        )
        self._csv_data_package_import_service = (
            csv_data_package_import_service
        )
        self._excel_workbook_reader_service = excel_workbook_reader_service
        self._excel_import_preflight_service = excel_import_preflight_service
        self._excel_import_service = excel_import_service
        self._backup_service = backup_service
        self._reading_history_service = reading_history_service
        self._application_settings_service = (
            application_settings_service
        )
        self._on_google_books_api_key_changed = (
            on_google_books_api_key_changed
        )
        self._window_state_store = window_state_store
        self._list_view_state_store = list_view_state_store
        self._list_view_state_save_suppressed = False
        self._last_normal_rectangle: WindowRectangle | None = None
        self._window_state_save_suppressed = False
        self._author_service = author_service
        self._managed_author_ids: tuple[int, ...] | None = ()
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
        self._reference_isbn_var = tk.StringVar(
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
        self._restore_list_view_state()
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

        if getattr(self, "_window_state_store", None) is None:
            self._configure_root_without_saved_state()
        else:
            self._configure_root_with_saved_state()

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

    def _configure_root_without_saved_state(self) -> None:
        """互換性のため従来どおり主画面中央へ配置する。"""

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

    def _configure_root_with_saved_state(self) -> None:
        """保存状態を現在のモニター構成へ安全に復元する。"""
        work_areas = get_screen_work_areas(self._root)
        saved_state = self._window_state_store.load()
        primary_area = self._get_primary_work_area(work_areas)

        if saved_state is None:
            width = min(1350, primary_area.width)
            height = min(800, primary_area.height)
            candidate = WindowRectangle(
                x=primary_area.right + 1,
                y=primary_area.bottom + 1,
                width=width,
                height=height,
            )
        else:
            candidate = WindowRectangle(
                x=saved_state.x,
                y=saved_state.y,
                width=saved_state.width,
                height=saved_state.height,
            )

        rectangle = calculate_safe_window_rectangle(
            candidate,
            work_areas,
            default_width=1350,
            default_height=800,
            minimum_width=self.MINIMUM_WIDTH,
            minimum_height=self.MINIMUM_HEIGHT,
        )
        selected_area = select_work_area(candidate, work_areas)
        self._last_normal_rectangle = rectangle
        self._root.geometry(self._format_geometry(rectangle))
        self._root.minsize(
            min(self.MINIMUM_WIDTH, selected_area.width),
            min(self.MINIMUM_HEIGHT, selected_area.height),
        )
        self._root.update_idletasks()

        if saved_state is not None and saved_state.maximized:
            self._root.state("zoomed")

        self._root.bind(
            "<Configure>",
            self._on_root_configure,
            add="+",
        )

    @staticmethod
    def _get_primary_work_area(
        work_areas: tuple[ScreenWorkArea, ...],
    ) -> ScreenWorkArea:
        """主モニター、または取得結果の先頭を返す。"""
        return next(
            (area for area in work_areas if area.primary),
            work_areas[0],
        )

    @staticmethod
    def _format_geometry(rectangle: WindowRectangle) -> str:
        """負の座標を含めてTkinter用geometry文字列を返す。"""
        return (
            f"{rectangle.width}x{rectangle.height}"
            f"{rectangle.x:+d}{rectangle.y:+d}"
        )

    def _on_root_configure(self, event: tk.Event[tk.Misc]) -> None:
        """通常表示時の最新矩形をメモリ上だけに保持する。"""
        if event.widget is not self._root:
            return
        self._capture_normal_rectangle()

    def _capture_normal_rectangle(self) -> None:
        """通常表示中なら現在の矩形をメモリへ反映する。"""
        try:
            if self._root.state() != "normal":
                return
            width = self._root.winfo_width()
            height = self._root.winfo_height()
            if width <= 1 or height <= 1:
                return
            self._last_normal_rectangle = WindowRectangle(
                x=self._root.winfo_x(),
                y=self._root.winfo_y(),
                width=width,
                height=height,
            )
        except tk.TclError:
            return

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

        self._search_managed_author_var = tk.StringVar(search_frame, "すべて")
        self._search_managed_author_options = {}
        ttk.Label(search_frame, text="管理著者").grid(
            row=2, column=4, sticky="w", pady=(8, 0), padx=(0, 6),
        )
        author_filter_frame = ttk.Frame(search_frame)
        author_filter_frame.grid(row=2, column=5, columnspan=5, sticky="ew", pady=(8, 0))
        self._search_managed_author_combobox = ttk.Combobox(
            author_filter_frame, textvariable=self._search_managed_author_var,
            state="readonly" if self._author_service is not None else "disabled",
            width=28, postcommand=self._refresh_search_managed_authors,
        )
        self._search_managed_author_combobox.pack(side="left", fill="x", expand=True)
        ttk.Button(author_filter_frame, text="未関連書籍の整理",
            command=self._on_review_author_links,
            state="normal" if self._author_service is not None else "disabled",
        ).pack(side="left", padx=(6, 0))
        self._search_managed_author_combobox.bind("<<ComboboxSelected>>", self._on_search)
        self._refresh_search_managed_authors()

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

    def _restore_list_view_state(self) -> None:
        """保存された列幅と並び順を一覧へ反映する。"""
        store = getattr(
            self,
            "_list_view_state_store",
            None,
        )
        if store is None:
            return

        state = store.load()
        if state is None:
            return

        for column_id in ("#0", *self.TREE_COLUMNS):
            saved_width = state.column_widths.get(
                column_id,
            )
            if saved_width is None:
                continue

            minimum_width = int(
                self._book_tree.column(
                    column_id,
                    "minwidth",
                )
            )
            restored_width = max(
                minimum_width,
                min(
                    saved_width,
                    ListViewState.MAXIMUM_COLUMN_WIDTH,
                ),
            )
            self._book_tree.column(
                column_id,
                width=restored_width,
            )

        self._sort_type_var.set(
            self.SORT_KEY_TYPE_MAP[state.sort_by]
        )
        self._sort_direction_var.set(
            "descending"
            if state.descending
            else "ascending"
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

        author_frame = ttk.Frame(form_frame)
        author_frame.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=4)
        author_frame.columnconfigure(0, weight=1)
        self._author_entry = ttk.Entry(author_frame, textvariable=self._author_var, width=15)
        self._author_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._managed_author_button = ttk.Button(author_frame, text="著者選択(0)",
            command=self._on_select_authors, state="normal" if self._author_service is not None else "disabled")
        self._managed_author_button.grid(row=0, column=1)

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
        ttk.Label(form_frame, text="ISBN").grid(
            row=3, column=0, sticky="w", padx=(0, 6), pady=4,
        )
        identifier_frame = ttk.Frame(form_frame)
        identifier_frame.grid(
            row=3, column=1, columnspan=3, sticky="ew", pady=4,
        )
        self._isbn_entry = ttk.Entry(
            identifier_frame, textvariable=self._isbn_var, width=15,
        )
        self._isbn_entry.grid(row=0, column=0, padx=(0, 12))
        ttk.Label(identifier_frame, text="参照ISBN").grid(
            row=0, column=1, sticky="w", padx=(0, 6),
        )
        self._reference_isbn_entry = ttk.Entry(
            identifier_frame, textvariable=self._reference_isbn_var, width=15,
        )
        self._reference_isbn_entry.grid(row=0, column=2, padx=(0, 12))
        ttk.Label(identifier_frame, text="雑誌コード").grid(
            row=0, column=3, sticky="w", padx=(0, 6),
        )
        self._magazine_code_entry = ttk.Entry(
            identifier_frame, textvariable=self._magazine_code_var, width=8,
        )
        self._magazine_code_entry.grid(row=0, column=4, padx=(0, 12))
        self._candidate_search_button = ttk.Button(
            identifier_frame, text="書籍候補を検索",
            command=self._on_search_book_candidates,
        )
        self._candidate_search_button.grid(row=0, column=5, sticky="w")

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

        # 画像の要求サイズで表示枠が広がらないよう、独立した領域を設ける。
        self._cover_viewport = ttk.Frame(cover_frame, width=170, height=240)
        self._cover_viewport.grid(row=0, column=0, sticky="nsew")
        self._cover_viewport.grid_propagate(False)
        self._cover_image_label = ttk.Label(
            self._cover_viewport, text="画像なし", anchor="center",
        )
        self._cover_image_label.place(x=0, y=0, relwidth=1, relheight=1)
        self._cover_viewport.bind("<Configure>", self._on_cover_viewport_resize)

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

        self._data_io_button = ttk.Button(
            button_frame,
            text="データ入出力 ▼",
            command=self._show_data_io_menu,
        )
        self._data_io_button.grid(
            row=0,
            column=6,
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

            if self._search_managed_author_id() is not None:
                books = self._service.sort_books(
                    self._get_filtered_books(), sort_by=sort_by,
                    descending=descending,
                )
                prefix = "検索結果"
            else:
                books = self._service.get_sorted_books(
                    sort_by=sort_by, descending=descending,
                )
                prefix = "全"
            self._display_books(books, status_prefix=prefix)

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
        self._reference_isbn_var.set(book_item.reference_isbn or "")
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
        self._load_managed_authors(book_item.id)
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

        self._display_selected_cover_image()

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

    def _metadata_form_snapshot(self) -> tuple:
        """比較対象と入力値・書影状態を保存し、反映直前に再確認する。"""
        return (
            self._selected_book_id,
            self._isbn_var.get(), self._reference_isbn_var.get(),
            self._title_var.get(), self._author_var.get(),
            self._publisher_var.get(), self._publication_format_var.get(),
            self._description_text.get("1.0", "end-1c"),
            self._current_cover_image_url, self._current_cover_image_path,
        )

    def _choose_metadata_fields(
        self, fetched_data: FetchedBookData, *, use_reference_isbn: bool,
    ) -> frozenset[str] | None:
        """比較画面を中央へ表示して反映項目を選ぶ。"""
        current = {
            "title": self._title_var.get(),
            "author": self._author_var.get(),
            "publisher": self._publisher_var.get(),
            "publication_format": self._publication_format_var.get(),
            "description": self._description_text.get("1.0", "end-1c"),
            "cover_image_url": self._current_cover_image_url or "",
        }
        dialog = MetadataComparisonDialog(
            self._root, current=current, fetched=fetched_data,
            use_reference_isbn=use_reference_isbn,
        )
        center_window_on_parent(dialog.window, self._root)
        return dialog.show()

    def _apply_fetched_book_data(
        self,
        fetched_data: FetchedBookData,
        *,
        use_reference_isbn: bool = False,
        selected_fields: frozenset[str] | None = None,
    ) -> None:
        """選択した書誌情報だけを入力フォームへ反映する。"""
        isbn_variable = (
            self._reference_isbn_var if use_reference_isbn else self._isbn_var
        )
        if fetched_data.isbn:
            isbn_variable.set(fetched_data.isbn)

        def has_text(value):
            return isinstance(value, str) and bool(value.strip())

        if not use_reference_isbn:
            for key, value, variable in (
                ("title", fetched_data.title, self._title_var),
                ("author", fetched_data.author, self._author_var),
                ("publisher", fetched_data.publisher, self._publisher_var),
                ("publication_format", fetched_data.publication_format, self._publication_format_var),
            ):
                if has_text(value) and (selected_fields is None or key in selected_fields):
                    variable.set(value)

        if has_text(fetched_data.description):
            current_description = self._description_text.get("1.0", "end-1c")
            should_apply = (
                "description" in selected_fields
                if selected_fields is not None
                else not use_reference_isbn or not current_description.strip()
            )
            if should_apply:
                self._replace_text(
                    self._description_text, fetched_data.description,
                )

    def _apply_fetched_cover(self, cover_url: str | None) -> None:
        """取得失敗・URL欠落時は既存書影を保持する。"""
        if not isinstance(cover_url, str) or not cover_url.strip():
            return
        try:
            cover_path = self._service.fetch_cover_image(cover_url)
            stored_path = self._service.create_stored_cover_image_path(cover_path)
            self._display_cover_image(str(cover_path))
        except Exception:
            traceback.print_exc()
            messagebox.showwarning(
                "表紙画像を表示できません",
                "新しい表紙画像を表示できなかったため、既存の表紙情報を保持しました。",
                parent=self._root,
            )
            return
        self._current_cover_image_url = cover_url
        self._current_cover_image_path = stored_path

    def _display_cover_image(
        self,
        image_path: str,
    ) -> None:
        """元画像を保持し、表示領域に収まる画像を作成する。"""
        with Image.open(image_path) as image:
            source = image.copy()
        self._render_cover_image(source)

    def _render_cover_image(self, source=None) -> None:
        if source is None:
            source = getattr(self, "_cover_source_image", None)
        if source is None:
            return
        viewport = getattr(self, "_cover_viewport", None)
        width, height = (170, 240) if viewport is None else (
            viewport.winfo_width(), viewport.winfo_height(),
        )
        # 初回レイアウト前は仮サイズで描画し、Configureで実寸へ合わせる。
        if width <= 1 or height <= 1:
            width, height = 170, 240
        display_image = source.copy()
        display_image.thumbnail(
            (max(1, width - 4), max(1, height - 4)),
            Image.Resampling.LANCZOS,
        )
        photo = ImageTk.PhotoImage(display_image)
        self._cover_image_label.configure(image=photo, text="")
        self._cover_photo = photo
        self._cover_source_image = source

    def _on_cover_viewport_resize(self, _event=None) -> None:
        try:
            self._render_cover_image()
        except Exception:
            logger.exception("表紙画像の表示サイズを更新できませんでした。")

    def _clear_cover_image(self) -> None:
        """表紙画像表示を初期状態へ戻す。"""
        self._cover_photo = None
        self._cover_source_image = None

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
    ) -> bool:
        """保存済みの表紙画像を表示する。"""
        if cover_image_path is None:
            self._clear_cover_image()
            return False

        image_path = self._service.resolve_cover_image_path(
            cover_image_path,
        )

        if image_path is None or not image_path.is_file():
            self._clear_cover_image()
            return False

        try:
            self._display_cover_image(
                str(image_path),
            )
            return True
        except Exception:
            traceback.print_exc()
            self._clear_cover_image()
            return False

    def _display_selected_cover_image(self) -> None:
        """選択中の書籍に必要な表紙画像だけを取得して表示する。"""
        if self._display_saved_cover_image(
            self._current_cover_image_path,
        ):
            return

        if not self._current_cover_image_url:
            return

        try:
            image_path = self._service.fetch_cover_image(
                self._current_cover_image_url,
            )
            self._current_cover_image_path = (
                self._service.create_stored_cover_image_path(
                    image_path,
                )
            )
            self._display_cover_image(str(image_path))
        except Exception:
            logger.warning(
                "選択された書籍の表紙画像を再取得できませんでした。",
                exc_info=True,
            )
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
        self._reference_isbn_var.set("")
        self._magazine_code_var.set("")
        self._author_var.set("")
        self._managed_author_ids = ()
        self._refresh_managed_author_caption()
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
            "reference_isbn": self._reference_isbn_var.get(),
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
            reference_isbn=values["reference_isbn"],
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
            **({"managed_author_id": self._search_managed_author_id()}
               if self._search_managed_author_id() is not None else {}),
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
            or self._search_managed_author_id() is not None
        )

    def _on_review_author_links(self) -> None:
        if self._author_service is None:
            return
        has_input = any(
            getattr(self, name).get().strip()
            for name in ("_title_var", "_author_var", "_publisher_var", "_isbn_var",
                         "_reference_isbn_var", "_magazine_code_var", "_tags_var",
                         "_publication_format_var", "_completion_month_var")
        )
        has_input = has_input or any(
            widget.get("1.0", "end-1c").strip()
            for widget in (self._description_text, self._notes_text)
        ) or bool(self._managed_author_ids) or self._is_favorite_var.get() or (
            self._reading_status_var.get() != "未設定"
            or self._rating_var.get() != "未評価"
        )
        if self._selected_book_id is not None or has_input:
            if not messagebox.askyesno("著者整理", "入力フォームをクリアして著者整理を開きます。未保存の入力は失われます。続けますか？", parent=self._root):
                return
        self._clear_form()
        try:
            AuthorLinkReviewDialog(self._root, self._author_service,
                get_book=self._service.get_book,
                window_state_store=getattr(self, "_window_state_store", None)).show()
            self._refresh_search_managed_authors()
            self._load_all_books()
        except Exception as error:
            messagebox.showerror("著者整理エラー", str(error), parent=self._root)

    def _search_managed_author_id(self) -> int | None:
        variable = getattr(self, "_search_managed_author_var", None)
        if variable is None:
            return None
        return self._search_managed_author_options.get(variable.get())

    def _refresh_search_managed_authors(self) -> None:
        """表示名を更新しても選択中の人物IDを維持する。"""
        selected_id = self._search_managed_author_id()
        options = {}
        try:
            service = getattr(self, "_author_service", None)
            for author in service.list_authors() if service is not None else ():
                note = " ".join((author.disambiguation_note or "").split())
                label = f"{author.name} [ID:{author.id}]" + (f" — {note}" if note else "")
                options[label] = author.id
            selected = next((label for label, ident in options.items()
                             if ident == selected_id), "すべて")
            if selected_id is not None and selected == "すべて":
                selected = f"削除された著者 [ID:{selected_id}]"
                options[selected] = selected_id
            self._search_managed_author_options = options
            self._search_managed_author_combobox.configure(values=("すべて", *options))
            self._search_managed_author_var.set(selected)
        except Exception as error:
            messagebox.showerror("管理著者の読込エラー", str(error), parent=self._root)

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

    def _refresh_managed_author_caption(self) -> None:
        button = getattr(self, "_managed_author_button", None)
        if button is not None:
            ids = getattr(self, "_managed_author_ids", None)
            button.configure(text="著者選択(読込失敗)" if ids is None else f"著者選択({len(ids)})")

    def _load_managed_authors(self, book_id: int) -> None:
        service = getattr(self, "_author_service", None)
        if service is None:
            return
        try:
            self._managed_author_ids = tuple(author.id for author in service.get_book_authors(book_id))
        except Exception as error:
            self._managed_author_ids = None
            logger.exception("管理著者を読み込めませんでした。")
            messagebox.showerror("著者読込エラー", f"管理著者を読み込めませんでした。関連は変更せず保持します。\n{error}", parent=self._root)
        self._refresh_managed_author_caption()

    def _managed_author_save_arguments(self) -> dict:
        if getattr(self, "_author_service", None) is None:
            return {}
        ids = getattr(self, "_managed_author_ids", None)
        return {} if ids is None else {"author_ids": tuple(ids)}

    def _on_select_authors(self) -> None:
        service = getattr(self, "_author_service", None)
        if service is None:
            return
        book_id = self._selected_book_id
        try:
            result = AuthorSelectionDialog(self._root, service,
                selected_ids=getattr(self, "_managed_author_ids", ()) or (),
                query=self._author_var.get(), get_book=self._service.get_book,
                window_state_store=getattr(self, "_window_state_store", None)).show()
            if result is None:
                return
            if book_id != self._selected_book_id:
                messagebox.showwarning("著者選択", "編集中の書籍が変わったため、再度選択してください。", parent=self._root)
                return
            self._managed_author_ids = tuple(result)
            self._refresh_managed_author_caption()
        except Exception as error:
            logger.exception("著者選択に失敗しました。")
            messagebox.showerror("著者選択エラー", str(error), parent=self._root)

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

        ttk.Label(input_frame, text="開始日・年月").grid(
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
        ttk.Label(input_frame, text="YYYY-MM または YYYY-MM-DD").grid(
            row=0,
            column=2,
            sticky="w",
            padx=(8, 0),
            pady=(0, 6),
        )

        ttk.Label(input_frame, text="読了日・年月").grid(
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
        ttk.Label(input_frame, text="YYYY-MM または YYYY-MM-DD").grid(
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
            text="開始日・年月",
        )
        self._reading_history_tree.heading(
            "completed_on",
            text="読了日・年月",
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
        *,
        vertical_offset: int = 0,
    ) -> None:
        """親画面中央から指定量だけ上下へ移動して待機する。"""
        center_window_on_parent(
            dialog,
            self._root,
            vertical_offset=vertical_offset,
        )
        dialog.wait_window()

    def _on_open_settings(self) -> None:
        """アプリケーション設定画面を表示する。"""
        try:
            snapshot = (
                self._application_settings_service.get_snapshot()
            )
            backup_snapshot = (
                self._application_settings_service
                .get_backup_settings_snapshot()
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
        dialog.geometry("900x800")
        dialog.transient(self._root)
        dialog.grab_set()
        dialog.resizable(True, False)
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

        content_canvas = tk.Canvas(
            dialog,
            highlightthickness=0,
            borderwidth=0,
        )
        content_canvas.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        content_scrollbar = ttk.Scrollbar(
            dialog,
            orient="vertical",
            command=content_canvas.yview,
        )
        content_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )
        content_canvas.configure(
            yscrollcommand=content_scrollbar.set,
        )
        content_frame = ttk.Frame(content_canvas)
        content_frame.columnconfigure(0, weight=1)
        content_window = content_canvas.create_window(
            (0, 0),
            window=content_frame,
            anchor="nw",
        )
        content_frame.bind(
            "<Configure>",
            lambda _event: content_canvas.configure(
                scrollregion=content_canvas.bbox("all"),
            ),
        )
        content_canvas.bind(
            "<Configure>",
            lambda event: content_canvas.itemconfigure(
                content_window,
                width=event.width,
            ),
        )

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
            content_frame,
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
            content_frame,
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

        self._create_cover_cache_frame(
            content_frame,
            dialog,
            snapshot.cover_cache_directory,
        )
        self._create_backup_settings_frame(
            content_frame,
            dialog,
            backup_snapshot,
        )

        information_frame = ttk.LabelFrame(
            content_frame,
            text="アプリケーション情報",
            padding=10,
        )
        information_frame.grid(
            row=4,
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

        ttk.Label(
            information_frame,
            text="ウィンドウ配置",
        ).grid(
            row=len(information_rows),
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=3,
        )
        ttk.Button(
            information_frame,
            text="初期状態に戻す",
            command=lambda: self._reset_window_state(dialog),
        ).grid(
            row=len(information_rows),
            column=1,
            sticky="w",
            pady=3,
        )

        ttk.Label(
            information_frame,
            text="一覧表示",
        ).grid(
            row=len(information_rows) + 1,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=3,
        )
        ttk.Button(
            information_frame,
            text="初期状態に戻す",
            command=lambda: self._reset_list_view_state(dialog),
        ).grid(
            row=len(information_rows) + 1,
            column=1,
            sticky="w",
            pady=3,
        )

        button_frame = ttk.Frame(dialog)
        button_frame.grid(
            row=1,
            column=0,
            columnspan=2,
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
        self._wait_for_dialog(
            dialog,
            vertical_offset=-40,
        )

    def _create_cover_cache_frame(
        self,
        parent: ttk.Frame,
        dialog: tk.Toplevel,
        cache_directory: Path,
    ) -> None:
        """表紙画像キャッシュの状態と操作ボタンを表示する。"""
        frame = ttk.LabelFrame(
            parent,
            text="表紙画像キャッシュ",
            padding=10,
        )
        frame.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=12,
            pady=6,
        )
        frame.columnconfigure(1, weight=1)

        status_variable = tk.StringVar(
            master=dialog,
            value="確認中...",
        )
        ttk.Label(frame, text="現在の状態").grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=3,
        )
        ttk.Label(
            frame,
            textvariable=status_variable,
        ).grid(
            row=0,
            column=1,
            sticky="w",
            pady=3,
        )

        buttons = ttk.Frame(frame)
        buttons.grid(
            row=0,
            column=2,
            sticky="e",
        )
        ttk.Button(
            buttons,
            text="フォルダーを開く",
            command=lambda: self._open_settings_directory(
                cache_directory,
                dialog,
            ),
        ).grid(row=0, column=0, padx=(0, 6))
        clear_button = ttk.Button(
            buttons,
            text="キャッシュを削除",
        )
        clear_button.configure(
            command=lambda: self._clear_cover_cache(
                clear_button,
                status_variable,
                dialog,
            ),
        )
        clear_button.grid(row=0, column=1)

        ttk.Label(
            frame,
            text=(
                "削除しても書籍情報は残ります。必要な表紙画像は、"
                "書籍を選択したときに再取得されます。"
            ),
            wraplength=650,
        ).grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(8, 0),
        )
        self._refresh_cover_cache_status(
            status_variable,
            dialog,
            show_error=False,
        )

    @staticmethod
    def _format_file_size(size_bytes: int) -> str:
        """バイト数を読みやすい二進接頭辞表記へ変換する。"""
        if size_bytes < 0:
            raise ValueError("ファイルサイズは0以上である必要があります。")

        value = float(size_bytes)
        units = ("B", "KiB", "MiB", "GiB")
        for unit in units[:-1]:
            if value < 1024:
                if unit == "B":
                    return f"{int(value)} {unit}"
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} {units[-1]}"

    @classmethod
    def _format_cover_cache_status(
        cls,
        status: CoverCacheStatus,
    ) -> str:
        """キャッシュ状態を設定画面用の文字列へ変換する。"""
        return (
            f"{status.file_count}件・"
            f"{cls._format_file_size(status.total_size_bytes)}"
        )

    def _refresh_cover_cache_status(
        self,
        status_variable: tk.StringVar,
        dialog: tk.Toplevel,
        *,
        show_error: bool = True,
    ) -> CoverCacheStatus | None:
        """最新のキャッシュ状態を取得して画面へ反映する。"""
        try:
            status = (
                self._application_settings_service
                .get_cover_cache_status()
            )
        except CoverCacheSettingsError as error:
            status_variable.set("取得できません")
            if show_error:
                messagebox.showerror(
                    "表紙画像キャッシュエラー",
                    str(error),
                    parent=dialog,
                )
            return None

        status_variable.set(
            self._format_cover_cache_status(status),
        )
        return status

    def _clear_cover_cache(
        self,
        button: ttk.Button,
        status_variable: tk.StringVar,
        dialog: tk.Toplevel,
    ) -> None:
        """確認後に表紙画像キャッシュを削除する。"""
        status = self._refresh_cover_cache_status(
            status_variable,
            dialog,
        )
        if status is None:
            return
        if status.file_count == 0:
            messagebox.showinfo(
                "表紙画像キャッシュ",
                "削除する表紙画像キャッシュはありません。",
                parent=dialog,
            )
            return

        confirmed = messagebox.askyesno(
            "表紙画像キャッシュの削除",
            (
                f"{status.file_count}件・"
                f"{self._format_file_size(status.total_size_bytes)}の"
                "表紙画像キャッシュを削除します。\n\n"
                "DBに保存された書籍情報は削除しません。"
                "必要な表紙画像は書籍を選択したときに再取得されます。\n\n"
                "この操作は取り消せません。続行しますか？"
            ),
            parent=dialog,
        )
        if not confirmed:
            return

        button.configure(state="disabled")
        try:
            result = (
                self._application_settings_service
                .clear_cover_cache()
            )
        except CoverCacheSettingsError as error:
            messagebox.showerror(
                "表紙画像キャッシュエラー",
                str(error),
                parent=dialog,
            )
            return
        finally:
            button.configure(state="normal")

        status_variable.set(
            self._format_cover_cache_status(
                result.remaining_status,
            ),
        )
        self._clear_form()
        self._on_sort_changed()

        if result.failed_count:
            messagebox.showwarning(
                "表紙画像キャッシュ",
                (
                    f"{result.deleted_count}件を削除しました。\n"
                    f"削除できなかったファイル：{result.failed_count}件\n"
                    "残っているキャッシュ："
                    f"{result.remaining_status.file_count}件"
                ),
                parent=dialog,
            )
            return

        messagebox.showinfo(
            "表紙画像キャッシュ",
            (
                f"{result.deleted_count}件・"
                f"{self._format_file_size(result.deleted_size_bytes)}を"
                "削除しました。"
            ),
            parent=dialog,
        )

    def _create_backup_settings_frame(
        self,
        parent: ttk.Frame,
        dialog: tk.Toplevel,
        snapshot: BackupSettingsSnapshot,
    ) -> None:
        """バックアップ状態、設定と手動作成ボタンを表示する。"""
        frame = ttk.LabelFrame(parent, text="バックアップ", padding=10)
        frame.grid(row=3, column=0, sticky="ew", padx=12, pady=6)
        frame.columnconfigure(1, weight=1)

        interval = tk.StringVar(
            master=dialog,
            value=str(snapshot.saved_settings.backup_interval_hours),
        )
        generations = tk.StringVar(
            master=dialog,
            value=str(snapshot.saved_settings.max_backups),
        )
        last_backup = tk.StringVar(master=dialog)
        count = tk.StringVar(master=dialog)
        active = tk.StringVar(master=dialog)
        self._set_backup_settings_view(snapshot, last_backup, count, active)

        ttk.Label(frame, text="最後のバックアップ").grid(
            row=0, column=0, sticky="w", pady=3,
        )
        ttk.Label(frame, textvariable=last_backup).grid(
            row=0, column=1, sticky="w", pady=3,
        )
        ttk.Label(frame, text="バックアップ件数").grid(
            row=1, column=0, sticky="w", pady=3,
        )
        ttk.Label(frame, textvariable=count).grid(
            row=1, column=1, sticky="w", pady=3,
        )
        ttk.Label(frame, text="現在有効な設定").grid(
            row=2, column=0, sticky="w", pady=3,
        )
        ttk.Label(frame, textvariable=active).grid(
            row=2, column=1, sticky="w", pady=3,
        )
        ttk.Label(frame, text="自動バックアップ間隔（時間）").grid(
            row=3, column=0, sticky="w", pady=3,
        )
        ttk.Entry(frame, textvariable=interval, width=8).grid(
            row=3, column=1, sticky="w", pady=3,
        )
        ttk.Label(frame, text="保持世代数（件）").grid(
            row=4, column=0, sticky="w", pady=3,
        )
        ttk.Entry(frame, textvariable=generations, width=8).grid(
            row=4, column=1, sticky="w", pady=3,
        )
        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, columnspan=2, sticky="e", pady=6)
        ttk.Button(
            buttons,
            text="設定を保存",
            command=lambda: self._save_backup_settings(
                interval, generations, last_backup, count, active, dialog,
            ),
        ).grid(row=0, column=0, padx=(0, 6))
        backup_button = ttk.Button(buttons, text="今すぐバックアップ")
        backup_button.configure(
            command=lambda: self._create_backup_from_settings(
                backup_button, last_backup, count, active, dialog,
            ),
        )
        backup_button.grid(row=0, column=1)
        ttk.Label(
            frame,
            text=(
                "保存した設定は次回起動から適用されます。"
                "自動バックアップは起動時に判定します。"
                "表示はファイルの存在を示し、復元可能性の保証ではありません。"
            ),
            wraplength=650,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(2, 0))

    @staticmethod
    def _set_backup_settings_view(
        snapshot: BackupSettingsSnapshot,
        last_backup: tk.StringVar,
        count: tk.StringVar,
        active: tk.StringVar,
    ) -> None:
        """取得済み状態を画面へ反映する。"""
        if snapshot.latest_backup_datetime is None:
            last_backup.set("バックアップなし")
        else:
            timestamp = snapshot.latest_backup_datetime.strftime(
                "%Y/%m/%d %H:%M:%S"
            )
            last_backup.set(f"{timestamp}  {snapshot.latest_backup_path}")
        count.set(f"{snapshot.backup_count}件")
        settings = snapshot.active_settings
        suffix = "（変更は次回起動時に反映）" if snapshot.changes_pending_restart else ""
        active.set(
            f"{settings.backup_interval_hours}時間・"
            f"{settings.max_backups}件{suffix}"
        )

    def _refresh_backup_settings_view(
        self,
        last_backup: tk.StringVar,
        count: tk.StringVar,
        active: tk.StringVar,
        dialog: tk.Toplevel,
    ) -> bool:
        try:
            snapshot = (
                self._application_settings_service
                .get_backup_settings_snapshot()
            )
        except ApplicationSettingsError as error:
            messagebox.showerror("バックアップエラー", str(error), parent=dialog)
            return False
        self._set_backup_settings_view(snapshot, last_backup, count, active)
        return True

    def _save_backup_settings(
        self,
        interval: tk.StringVar,
        generations: tk.StringVar,
        last_backup: tk.StringVar,
        count: tk.StringVar,
        active: tk.StringVar,
        dialog: tk.Toplevel,
    ) -> None:
        try:
            self._application_settings_service.save_backup_settings(
                interval.get(), generations.get(),
            )
        except ApplicationSettingsError as error:
            messagebox.showerror("設定エラー", str(error), parent=dialog)
            return
        if self._refresh_backup_settings_view(
            last_backup, count, active, dialog,
        ):
            messagebox.showinfo(
                "設定", "バックアップ設定を保存しました。次回起動から適用します。",
                parent=dialog,
            )

    def _create_backup_from_settings(
        self,
        button: ttk.Button,
        last_backup: tk.StringVar,
        count: tk.StringVar,
        active: tk.StringVar,
        dialog: tk.Toplevel,
    ) -> None:
        """二重クリックを防ぎながら手動バックアップを実行する。"""
        button.configure(state="disabled")
        try:
            result = self._application_settings_service.create_backup_now()
        except ApplicationSettingsError as error:
            messagebox.showerror("バックアップエラー", str(error), parent=dialog)
            return
        finally:
            button.configure(state="normal")
        if result is None:
            messagebox.showwarning(
                "バックアップ", "バックアップ元のデータベースがありません。",
                parent=dialog,
            )
            return
        self._refresh_backup_settings_view(last_backup, count, active, dialog)
        messagebox.showinfo(
            "バックアップ", f"バックアップを作成しました。\n{result}",
            parent=dialog,
        )

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

    def _reset_window_state(self, dialog: tk.Toplevel) -> None:
        """保存済み配置を削除し、このセッションの終了保存を抑止する。"""
        confirmed = messagebox.askyesno(
            "ウィンドウ配置の初期化",
            (
                "保存されているメインウィンドウの位置とサイズを"
                "初期状態に戻します。\n\n"
                "変更は次回起動時から適用されます。続行しますか？"
            ),
            parent=dialog,
        )
        if not confirmed:
            return

        store = getattr(self, "_window_state_store", None)
        if store is None:
            messagebox.showerror(
                "ウィンドウ配置の初期化エラー",
                "ウィンドウ配置の保存処理を利用できません。",
                parent=dialog,
            )
            return

        try:
            store.delete()
        except WindowStateStoreError:
            logger.warning(
                "ウィンドウ状態を削除できませんでした。",
                exc_info=True,
            )
            messagebox.showerror(
                "ウィンドウ配置の初期化エラー",
                "保存されているウィンドウ配置を削除できませんでした。",
                parent=dialog,
            )
            return

        self._window_state_save_suppressed = True
        messagebox.showinfo(
            "ウィンドウ配置の初期化",
            (
                "ウィンドウ配置を初期状態へ戻しました。\n\n"
                "次回起動時から適用されます。"
            ),
            parent=dialog,
        )

    def _reset_list_view_state(self, dialog: tk.Toplevel) -> None:
        """保存済み一覧状態を削除し、終了時の再保存を抑止する。"""
        confirmed = messagebox.askyesno(
            "一覧表示の初期化",
            (
                "保存されている一覧の列幅と並び順を"
                "初期状態に戻します。\n\n"
                "変更は次回起動時から適用されます。続行しますか？"
            ),
            parent=dialog,
        )
        if not confirmed:
            return

        store = getattr(
            self,
            "_list_view_state_store",
            None,
        )
        if store is None:
            messagebox.showerror(
                "一覧表示の初期化エラー",
                "一覧表示状態の保存処理を利用できません。",
                parent=dialog,
            )
            return

        try:
            store.delete()
        except ListViewStateStoreError:
            logger.warning(
                "一覧表示状態を削除できませんでした。",
                exc_info=True,
            )
            messagebox.showerror(
                "一覧表示の初期化エラー",
                "保存されている一覧表示状態を削除できませんでした。",
                parent=dialog,
            )
            return

        self._list_view_state_save_suppressed = True
        messagebox.showinfo(
            "一覧表示の初期化",
            (
                "一覧表示を初期状態へ戻しました。\n\n"
                "次回起動時から適用されます。"
            ),
            parent=dialog,
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

        variable = getattr(self, "_search_managed_author_var", None)
        if variable is not None:
            variable.set("すべて")

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
                reference_isbn=values["reference_isbn"],
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
                **self._managed_author_save_arguments(),
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
                **self._managed_author_save_arguments(),
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
            preview = self._csv_import_service.preview_file(Path(input_filename))
            lines = [
                f"登録予定: {preview.importable_count}件",
                f"スキップ: {preview.skipped_count}件",
                f"エラー: {preview.error_count}件",
            ]
            for label, issues in (("スキップ", preview.skipped), ("エラー", preview.errors)):
                if issues:
                    lines.extend(["", f"【{label}】"])
                    lines.extend(
                        f"{issue.row_number}行目: {issue.message}" for issue in issues[:20]
                    )
                    if len(issues) > 20:
                        lines.append(f"ほか{len(issues) - 20}件")
            if preview.importable_count == 0:
                messagebox.showinfo("CSV事前検査", "\n".join(lines), parent=self._root)
                return
            lines.extend([
                "", "スキップ行とエラー行は登録しません。",
                "取込前にバックアップを作成します。登録予定行を取り込みますか？",
            ])
            if not messagebox.askyesno(
                "CSVインポート確認", "\n".join(lines), parent=self._root,
            ):
                return
            result = self._csv_import_service.execute_preview(
                preview, backup_service=self._backup_service,
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

            if result.backup_path is not None:
                message_lines.extend(["", f"取込前バックアップ: {result.backup_path}"])

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

    def _show_data_io_menu(self) -> None:
        """書籍一覧CSVと完全データZIPの操作メニューを表示する。"""
        menu = tk.Menu(
            self._root,
            tearoff=False,
        )
        menu.add_command(
            label="書籍一覧をCSVへエクスポート",
            command=self._on_export_csv,
        )
        menu.add_command(
            label="書籍一覧CSVをインポート",
            command=self._on_import_csv,
        )
        if self._has_excel_import_services():
            menu.add_command(label="Excelから書籍と読書履歴をインポート", command=self._on_import_excel)
        if self._has_csv_data_package_services():
            menu.add_separator()
            menu.add_command(
                label="完全データをZIPへエクスポート",
                command=self._on_export_csv_data_package,
            )
            menu.add_command(
                label="完全データZIPをインポート",
                command=self._on_import_csv_data_package,
            )

        try:
            menu.tk_popup(
                self._data_io_button.winfo_rootx(),
                (
                    self._data_io_button.winfo_rooty()
                    + self._data_io_button.winfo_height()
                ),
            )
        finally:
            menu.grab_release()

    def _has_excel_import_services(self) -> bool:
        """Excel取込に必要なServiceが揃っているか返す。"""
        return all(getattr(self, name, None) is not None for name in (
            "_excel_workbook_reader_service", "_excel_import_preflight_service", "_excel_import_service",
        ))

    def _excel_dialog_state_store(self, name: str) -> WindowStateStore | None:
        """Excel子画面ごとの配置を、利用者設定と同じ保存先で管理する。"""
        store = getattr(self, "_window_state_store", None)
        if store is None:
            return None
        return WindowStateStore(store.path.with_name(f"{name}_window_state.json"))

    def _on_import_excel(self) -> None:
        """Excel選択、列割り当て、全行検査、承認、登録を順に行う。"""
        if not self._has_excel_import_services():
            messagebox.showwarning("Excel取込", "Excel取込の準備ができていません。", parent=self._root)
            return
        filename = filedialog.askopenfilename(
            title="1シートのExcelファイルを選択", filetypes=[("Excelファイル", "*.xlsx")],
            parent=self._root,
        )
        if not filename:
            return
        try:
            sheet = self._excel_workbook_reader_service.read_sheet(Path(filename))
            while True:
                options = ExcelColumnMappingDialog(
                    self._root, sheet,
                    state_store=self._excel_dialog_state_store("excel_column_mapping"),
                ).show()
                if options is None:
                    return
                preview = self._excel_import_preflight_service.preview_sheet(sheet, options=options)
                if ExcelImportPreviewDialog(
                    self._root, preview,
                    state_store=self._excel_dialog_state_store("excel_import_preview"),
                ).show():
                    result = self._excel_import_service.import_preview(preview)
                    break
                # 確認画面から戻った場合は、列割り当てから再確認する。
        except Exception as error:
            logger.exception("Excelインポートに失敗しました。")
            messagebox.showerror("Excelインポートエラー", str(error), parent=self._root)
            return
        self._refresh_tag_options()
        self._load_all_books()
        messagebox.showinfo(
            "Excelインポート完了",
            f"書籍：{result.counts.books}件\n"
            f"新規タグ：{result.counts.tags}件\n"
            f"読書履歴：{result.counts.reading_histories}件\n\n"
            f"取込前バックアップ：{result.backup_path}",
            parent=self._root,
        )

    def _has_csv_data_package_services(self) -> bool:
        """完全データ入出力に必要なServiceが揃っているか返す。"""
        return all(
            service is not None
            for service in (
                getattr(
                    self,
                    "_csv_data_package_export_service",
                    None,
                ),
                getattr(
                    self,
                    "_csv_data_package_preflight_service",
                    None,
                ),
                getattr(
                    self,
                    "_csv_data_package_import_service",
                    None,
                ),
            )
        )

    def _on_export_csv_data_package(self) -> None:
        """書籍・タグ・関連・読書履歴をZIPへ出力する。"""
        service = self._csv_data_package_export_service
        if service is None:
            return

        output_filename = filedialog.asksaveasfilename(
            parent=self._root,
            title="完全データZIPを保存",
            defaultextension=".zip",
            initialfile=service.create_default_file_name(),
            filetypes=[
                ("ZIPファイル", "*.zip"),
                ("すべてのファイル", "*.*"),
            ],
        )
        if not output_filename:
            return

        try:
            result = service.export(Path(output_filename))
            messagebox.showinfo(
                "完全データ出力完了",
                (
                    "完全データの出力が完了しました。\n\n"
                    f"保存先: {result.output_path}\n"
                    f"書籍: {result.book_item_count}件\n"
                    f"タグ: {result.tag_count}件\n"
                    "書籍タグ関連: "
                    f"{result.book_item_tag_count}件\n"
                    "読書履歴: "
                    f"{result.reading_history_count}件\n"
                    f"管理著者: {result.author_count}件／別名: {result.author_alias_count}件\n"
                    f"書籍著者関連: {result.book_item_author_count}件"
                ),
                parent=self._root,
            )
        except Exception as error:
            logger.exception("完全データの出力に失敗しました。")
            messagebox.showerror(
                "完全データ出力エラー",
                (
                    "完全データZIPを保存できませんでした。\n\n"
                    "出力先には未完成のZIPを残していません。\n"
                    f"詳細: {error}"
                ),
                parent=self._root,
            )

    def _on_import_csv_data_package(self) -> None:
        """完全データZIPを検査し、確認後に空DBへ復元する。"""
        preflight_service = self._csv_data_package_preflight_service
        import_service = self._csv_data_package_import_service
        if preflight_service is None or import_service is None:
            return

        input_filename = filedialog.askopenfilename(
            parent=self._root,
            title="完全データZIPを選択",
            filetypes=[
                ("ZIPファイル", "*.zip"),
                ("すべてのファイル", "*.*"),
            ],
        )
        if not input_filename:
            return

        try:
            preview = preflight_service.preview(Path(input_filename))
        except Exception as error:
            logger.exception("完全データの事前検査に失敗しました。")
            messagebox.showerror(
                "完全データ事前検査エラー",
                (
                    "完全データZIPを検査できませんでした。\n\n"
                    f"詳細: {error}"
                ),
                parent=self._root,
            )
            return

        preview_message = self._format_csv_data_package_preview(
            preview
        )
        if not preview.can_import:
            messagebox.showerror(
                "完全データ事前検査エラー",
                preview_message,
                parent=self._root,
            )
            return

        confirmed = messagebox.askyesno(
            "完全データ取込の確認",
            (
                f"{preview_message}\n\n"
                "完全データは空のデータベースだけに"
                "取り込めます。\n"
                "実行直前にデータベースをバックアップします。\n\n"
                "取り込みを実行しますか？"
            ),
            parent=self._root,
        )
        if not confirmed:
            return

        try:
            result = import_service.import_preview(preview)
            self._refresh_tag_options()
            self._load_all_books()
            messagebox.showinfo(
                "完全データ取込完了",
                (
                    "完全データの取り込みが完了しました。\n\n"
                    f"書籍: {result.book_item_count}件\n"
                    f"タグ: {result.tag_count}件\n"
                    "書籍タグ関連: "
                    f"{result.book_item_tag_count}件\n"
                    "読書履歴: "
                    f"{result.reading_history_count}件\n"
                    f"管理著者: {result.author_count}件／別名: {result.author_alias_count}件\n"
                    f"書籍著者関連: {result.book_item_author_count}件\n\n"
                    f"実行前バックアップ: {result.backup_path}"
                ),
                parent=self._root,
            )
        except Exception as error:
            logger.exception("完全データの取り込みに失敗しました。")
            messagebox.showerror(
                "完全データ取込エラー",
                (
                    "完全データを取り込めませんでした。\n\n"
                    "データベースへの変更は保存されていません。\n"
                    "バックアップ作成後の失敗では、作成済みの"
                    "バックアップも保持されます。\n"
                    f"詳細: {error}"
                ),
                parent=self._root,
            )

    @classmethod
    def _format_csv_data_package_preview(cls, preview: object) -> str:
        """完全データの件数と検査Issueを確認用文面に整形する。"""
        manifest = preview.manifest
        if manifest is None:
            message_lines = [
                "パッケージ情報を読み取れませんでした。",
            ]
        else:
            message_lines = [
                "【完全データの内容】",
                f"生成元Version: {manifest.application_version}",
                f"出力日時: {manifest.exported_at}",
                f"書籍: {manifest.book_item_count}件",
                f"タグ: {manifest.tag_count}件",
                "書籍タグ関連: "
                f"{manifest.book_item_tag_count}件",
                "読書履歴: "
                f"{manifest.reading_history_count}件",
                f"管理著者: {manifest.author_count}件／別名: {manifest.author_alias_count}件",
                f"書籍著者関連: {manifest.book_item_author_count}件",
            ]

        cls._append_csv_data_package_issues(
            message_lines,
            "警告",
            preview.warnings,
        )
        cls._append_csv_data_package_issues(
            message_lines,
            "エラー",
            preview.errors,
        )
        if not preview.issues:
            message_lines.extend(["", "検査結果: 問題ありません。"])
        return "\n".join(message_lines)

    @staticmethod
    def _append_csv_data_package_issues(
        message_lines: list[str],
        heading: str,
        issues: tuple[object, ...],
    ) -> None:
        """検査Issueを最大20件まで確認用文面へ追加する。"""
        if not issues:
            return

        message_lines.extend(["", f"【{heading}】"])
        for issue in issues[:20]:
            location = issue.file_name
            if issue.row_number is not None:
                location += f" {issue.row_number}行目"
            if issue.column_name is not None:
                location += f" {issue.column_name}"
            message_lines.append(f"{location}: {issue.message}")

        remaining_count = len(issues) - 20
        if remaining_count > 0:
            message_lines.append(f"ほか{remaining_count}件")

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
        self._save_list_view_state_on_exit()
        self._save_window_state_on_exit()
        self._root.destroy()

    def _save_list_view_state_on_exit(self) -> None:
        """現在の列幅と並び順を終了時に一度だけ保存する。"""
        store = getattr(
            self,
            "_list_view_state_store",
            None,
        )
        if (
            store is None
            or getattr(
                self,
                "_list_view_state_save_suppressed",
                False,
            )
        ):
            return

        try:
            column_widths = {
                column_id: int(
                    self._book_tree.column(
                        column_id,
                        "width",
                    )
                )
                for column_id in (
                    "#0",
                    *self.TREE_COLUMNS,
                )
            }
            sort_by, descending = (
                self._get_sort_settings()
            )
            store.save(
                ListViewState(
                    column_widths=column_widths,
                    sort_by=sort_by,
                    descending=descending,
                )
            )
        except (
            ListViewStateStoreError,
            tk.TclError,
            TypeError,
            ValueError,
        ):
            logger.warning(
                "一覧表示状態を保存できませんでした。",
                exc_info=True,
            )

    def _save_window_state_on_exit(self) -> None:
        """通常矩形と最大化状態を終了時に一度だけ保存する。"""
        if (
            getattr(self, "_window_state_store", None) is None
            or getattr(self, "_window_state_save_suppressed", False)
            or getattr(self, "_last_normal_rectangle", None) is None
        ):
            return

        try:
            root_state = self._root.state()
            if root_state == "normal":
                self._capture_normal_rectangle()
            rectangle = self._last_normal_rectangle
            if rectangle is None:
                return
            self._window_state_store.save(
                WindowState(
                    x=rectangle.x,
                    y=rectangle.y,
                    width=rectangle.width,
                    height=rectangle.height,
                    maximized=(root_state == "zoomed"),
                )
            )
        except (WindowStateStoreError, tk.TclError, ValueError, TypeError):
            logger.warning(
                "ウィンドウ状態を保存できませんでした。",
                exc_info=True,
            )

    def _on_search_book_candidates(self) -> None:
        """登録前・登録済みフォームから候補を検索し、比較後に反映する。"""
        task = getattr(self, "_candidate_search_task", None)
        if task is None:
            task = CandidateSearchTask()
            self._candidate_search_task = task
        if task.busy:
            messagebox.showinfo(
                "ISBN候補検索", "前の検索が終了するまでお待ちください。",
                parent=self._root,
            )
            return
        form_snapshot = self._metadata_form_snapshot()
        snapshot = (
            self._selected_book_id, self._title_var.get(), self._author_var.get(),
            self._isbn_var.get(), self._reference_isbn_var.get(), self._publisher_var.get(),
        )
        self._candidate_search_button.configure(state="disabled")
        try:
            dialog = BookCandidateSearchDialog(
                self._root, search=self._service.search_book_candidates,
                task=task, title=snapshot[1], author=snapshot[2], publisher=snapshot[5],
                fetch=self._service.fetch_book_candidate,
            )
            center_window_on_parent(dialog.window, self._root)
            result = dialog.show()
            if result is None or not self._root.winfo_exists():
                return
            current = (
                self._selected_book_id, self._title_var.get(), self._author_var.get(),
                self._isbn_var.get(), self._reference_isbn_var.get(), self._publisher_var.get(),
            )
            if snapshot != current:
                messagebox.showwarning(
                    "ISBN候補検索", "対象または入力内容が変わりました。再検索してください。",
                    parent=self._root,
                )
                return
            fetched, destination = result
            use_reference = destination == "reference"
            selected = self._choose_metadata_fields(fetched, use_reference_isbn=use_reference)
            if selected is None:
                self._edit_status_var.set("書誌情報の反映をキャンセルしました。")
                return
            if self._metadata_form_snapshot() != form_snapshot:
                messagebox.showwarning("書誌情報の比較", "入力内容が変わったため反映しません。再検索してください。", parent=self._root)
                return
            if not selected:
                self._edit_status_var.set("反映する項目が選択されていません。")
                return
            variable = self._reference_isbn_var if use_reference else self._isbn_var
            if fetched.isbn and variable.get().strip() and variable.get().strip() != fetched.isbn:
                if not messagebox.askyesno("ISBN変更", "入力済みのISBNを選択候補のISBNへ変更しますか。", parent=self._root):
                    return
            self._apply_fetched_book_data(fetched, use_reference_isbn=use_reference, selected_fields=selected)
            if "cover_image_url" in selected:
                self._apply_fetched_cover(fetched.cover_image_url)
            self._edit_status_var.set("候補の書誌情報を反映しました。保存するには登録または更新してください。")
        finally:
            try:
                if self._root.winfo_exists():
                    self._candidate_search_button.configure(state="normal")
            except tk.TclError:
                pass  # 親ウィンドウも終了済み。

    def _on_fetch_book_metadata(self) -> None:
        """ISBNを優先し、空欄の場合は参照ISBNから書誌情報を取得する。"""
        isbn = self._isbn_var.get().strip()
        use_reference_isbn = not isbn
        if use_reference_isbn:
            isbn = self._reference_isbn_var.get().strip()

        if isbn == "":
            messagebox.showwarning(
                "入力内容の確認",
                "ISBNまたは参照ISBNを入力してください。",
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

            snapshot = self._metadata_form_snapshot()
            result = self._service.fetch_book_metadata(
                isbn,
            )

            selected_fields = self._choose_metadata_fields(
                result, use_reference_isbn=use_reference_isbn,
            )
            if selected_fields is None:
                self._edit_status_var.set(
                    "書誌情報の反映をキャンセルしました。",
                )
                return

            if self._metadata_form_snapshot() != snapshot:
                messagebox.showwarning(
                    "書誌情報の比較",
                    "対象または入力内容が変わったため反映しません。もう一度取得・比較してください。",
                    parent=self._root,
                )
                self._edit_status_var.set("入力変更を検出したため反映を中止しました。")
                return
            if not selected_fields:
                self._edit_status_var.set("反映する項目が選択されていません。")
                return
            self._apply_fetched_book_data(
                result, use_reference_isbn=use_reference_isbn,
                selected_fields=selected_fields,
            )
            if "cover_image_url" in selected_fields:
                self._apply_fetched_cover(result.cover_image_url)

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
