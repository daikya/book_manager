"""book_manager の正式エントリーポイント。"""

from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path

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


def main() -> None:
    """book_manager を起動する。"""
    database_path = Path(
        "data/books.db",
    )

    initialize_database(
        database_path,
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

    BookManagerApplication(
        root,
        service,
    )

    try:
        root.mainloop()
    finally:
        session.close()


if __name__ == "__main__":
    main()