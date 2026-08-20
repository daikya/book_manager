"""book_manager の正式エントリーポイント。"""

from __future__ import annotations

import os
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import messagebox
import requests

from book_manager.database.initializer import (
    initialize_database,
)
from book_manager.gui.book_manager_application import (
    BookManagerApplication,
)
from book_manager.metadata.book_metadata_service import (
    BookMetadataService,
)
from book_manager.metadata.google_books_client import (
    GoogleBooksClient,
)
from book_manager.metadata.openbd_client import (
    OpenBdClient,
)
from book_manager.repositories.book_repository import (
    BookRepository,
)
from book_manager.services.book_service import (
    BookService,
)
from book_manager.services.cover_image_service import (
    CoverImageService,
)
from book_manager.services.backup_service import (
    BackupService,
)
from book_manager.startup import try_create_backup
from book_manager.services.csv_export_service import (
    CsvExportService,
)

def main() -> None:
    """book_manager を起動する。"""
    database_path = Path(
        "data/books.db",
    )

    initialize_database(
        database_path,
    )

    backup_error: Exception | None = None

    backup_service = BackupService(
        database_path=database_path,
        backup_directory=Path(
            "backups",
        ),
    )

    backup_error = try_create_backup(
        backup_service,
    )

    repository = BookRepository(
        database_path,
    )

    session = requests.Session()

    google_books_client = GoogleBooksClient(
        session=session,
        api_key=os.getenv(
            "GOOGLE_BOOKS_API_KEY"
        ),
    )

    openbd_client = OpenBdClient(
        session=session,
    )

    metadata_service = BookMetadataService(
        clients=[
            google_books_client,
            openbd_client,
        ],
    )

    cover_image_service = CoverImageService(
        session=session,
        cache_directory=Path(
            "cache/covers",
        ),
    )

    service = BookService(
        repository,
        metadata_service=metadata_service,
        cover_image_service=cover_image_service,
    )

    root = tk.Tk()

    if backup_error is not None:
        messagebox.showwarning(
            "自動バックアップエラー",
            (
                "データベースの自動バックアップに"
                "失敗しました。\n\n"
                "アプリケーションは引き続き利用できます。"
            ),
            parent=root,
        )

    csv_export_service = CsvExportService()

    BookManagerApplication(
        root,
        service,
        csv_export_service,
    )

    try:
        root.mainloop()
    finally:
        session.close()


if __name__ == "__main__":
    main()