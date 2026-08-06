"""SQLite schema definitions."""

SCHEMA_VERSION = 2


CREATE_BOOK_ITEMS_TABLE = """
CREATE TABLE IF NOT EXISTS book_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn TEXT,
    magazine_code TEXT,
    title TEXT NOT NULL,
    author TEXT,
    publisher TEXT,
    publication_format TEXT,
    description TEXT,
    cover_image_url TEXT,
    cover_image_path TEXT,
    completion_month TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


CREATE_BOOK_ITEMS_TITLE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_book_items_title
ON book_items (title)
"""


CREATE_BOOK_ITEMS_ISBN_INDEX = """
CREATE INDEX IF NOT EXISTS idx_book_items_isbn
ON book_items (isbn)
"""


CREATE_BOOK_ITEMS_MAGAZINE_CODE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_book_items_magazine_code
ON book_items (magazine_code)
"""


MIGRATE_VERSION_1_TO_2 = (
    """
    ALTER TABLE book_items
    ADD COLUMN cover_image_url TEXT
    """,
    """
    ALTER TABLE book_items
    ADD COLUMN cover_image_path TEXT
    """,
)


SCHEMA_STATEMENTS = (
    CREATE_BOOK_ITEMS_TABLE,
    CREATE_BOOK_ITEMS_TITLE_INDEX,
    CREATE_BOOK_ITEMS_ISBN_INDEX,
    CREATE_BOOK_ITEMS_MAGAZINE_CODE_INDEX,
)