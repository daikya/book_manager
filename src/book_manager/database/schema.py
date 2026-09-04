"""SQLite schema definitions."""

SCHEMA_VERSION = 6


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
    reading_status TEXT,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    rating INTEGER,
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


CREATE_TAGS_TABLE = """
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (length(name) BETWEEN 1 AND 30),
    CHECK (instr(name, '|') = 0),
    CHECK (instr(name, char(10)) = 0),
    CHECK (instr(name, char(13)) = 0)
)
"""


CREATE_BOOK_ITEM_TAGS_TABLE = """
CREATE TABLE IF NOT EXISTS book_item_tags (
    book_item_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (book_item_id, tag_id),
    FOREIGN KEY (book_item_id)
        REFERENCES book_items (id)
        ON DELETE CASCADE,
    FOREIGN KEY (tag_id)
        REFERENCES tags (id)
        ON DELETE CASCADE
)
"""


CREATE_BOOK_ITEM_TAGS_TAG_ID_INDEX = """
CREATE INDEX IF NOT EXISTS idx_book_item_tags_tag_id
ON book_item_tags (tag_id)
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

MIGRATE_VERSION_2_TO_3 = (
    """
    ALTER TABLE book_items
    ADD COLUMN reading_status TEXT
    """,
)

MIGRATE_VERSION_3_TO_4 = (
    """
    ALTER TABLE book_items
    ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0
    """,
)

MIGRATE_VERSION_4_TO_5 = (
    """
    ALTER TABLE book_items
    ADD COLUMN rating INTEGER
    """,
)

MIGRATE_VERSION_5_TO_6 = (
    CREATE_TAGS_TABLE,
    CREATE_BOOK_ITEM_TAGS_TABLE,
    CREATE_BOOK_ITEM_TAGS_TAG_ID_INDEX,
)

SCHEMA_STATEMENTS = (
    CREATE_BOOK_ITEMS_TABLE,
    CREATE_BOOK_ITEMS_TITLE_INDEX,
    CREATE_BOOK_ITEMS_ISBN_INDEX,
    CREATE_BOOK_ITEMS_MAGAZINE_CODE_INDEX,
    CREATE_TAGS_TABLE,
    CREATE_BOOK_ITEM_TAGS_TABLE,
    CREATE_BOOK_ITEM_TAGS_TAG_ID_INDEX,
)
