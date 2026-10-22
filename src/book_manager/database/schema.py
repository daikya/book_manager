"""SQLite schema definitions."""

SCHEMA_VERSION = 9


CREATE_BOOK_ITEMS_TABLE = """
CREATE TABLE IF NOT EXISTS book_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn TEXT,
    reference_isbn TEXT,
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


CREATE_READING_HISTORIES_TABLE = """
CREATE TABLE IF NOT EXISTS reading_histories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_item_id INTEGER NOT NULL,
    started_on TEXT,
    completed_on TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (book_item_id)
        REFERENCES book_items (id)
        ON DELETE CASCADE,
    CHECK (
        started_on IS NOT NULL
        OR completed_on IS NOT NULL
        OR notes IS NOT NULL
    ),
    CHECK (
        started_on IS NULL
        OR completed_on IS NULL
        OR (
            CASE WHEN length(started_on) = 7
                THEN started_on || '-01' ELSE started_on END
            <=
            CASE WHEN length(completed_on) = 7
                THEN completed_on || '-31' ELSE completed_on END
        )
    )
)
"""


CREATE_READING_HISTORIES_BOOK_ITEM_ID_INDEX = """
CREATE INDEX IF NOT EXISTS idx_reading_histories_book_item_id
ON reading_histories (book_item_id)
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

CREATE_READING_HISTORIES_TABLE_VERSION_7 = '\nCREATE TABLE IF NOT EXISTS reading_histories (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    book_item_id INTEGER NOT NULL,\n    started_on TEXT,\n    completed_on TEXT,\n    notes TEXT,\n    created_at TEXT NOT NULL,\n    updated_at TEXT NOT NULL,\n    FOREIGN KEY (book_item_id)\n        REFERENCES book_items (id)\n        ON DELETE CASCADE,\n    CHECK (\n        started_on IS NOT NULL\n        OR completed_on IS NOT NULL\n        OR notes IS NOT NULL\n    ),\n    CHECK (\n        started_on IS NULL\n        OR completed_on IS NULL\n        OR started_on <= completed_on\n    )\n)\n'

MIGRATE_VERSION_6_TO_7 = (
    CREATE_READING_HISTORIES_TABLE_VERSION_7,
    CREATE_READING_HISTORIES_BOOK_ITEM_ID_INDEX,
)


CREATE_AUTHORS_TABLE = """
CREATE TABLE IF NOT EXISTS authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 200),
    name_key TEXT NOT NULL CHECK (length(name_key) > 0),
    disambiguation_note TEXT CHECK (length(disambiguation_note) <= 2000),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""
CREATE_AUTHORS_NAME_KEY_INDEX = "CREATE INDEX IF NOT EXISTS idx_authors_name_key ON authors(name_key)"
CREATE_AUTHOR_ALIASES_TABLE = """
CREATE TABLE IF NOT EXISTS author_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 200),
    name_key TEXT NOT NULL CHECK (length(name_key) > 0),
    UNIQUE (author_id, name)
)
"""
CREATE_AUTHOR_ALIASES_NAME_KEY_INDEX = "CREATE INDEX IF NOT EXISTS idx_author_aliases_name_key ON author_aliases(name_key)"
CREATE_BOOK_ITEM_AUTHORS_TABLE = """
CREATE TABLE IF NOT EXISTS book_item_authors (
    book_item_id INTEGER NOT NULL REFERENCES book_items(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES authors(id) ON DELETE RESTRICT,
    position INTEGER NOT NULL CHECK (typeof(position) = 'integer' AND position >= 0),
    PRIMARY KEY (book_item_id, author_id),
    UNIQUE (book_item_id, position)
)
"""
CREATE_BOOK_ITEM_AUTHORS_AUTHOR_INDEX = "CREATE INDEX IF NOT EXISTS idx_book_item_authors_author_id ON book_item_authors(author_id)"
AUTHOR_SCHEMA_STATEMENTS = (
    CREATE_AUTHORS_TABLE, CREATE_AUTHORS_NAME_KEY_INDEX,
    CREATE_AUTHOR_ALIASES_TABLE, CREATE_AUTHOR_ALIASES_NAME_KEY_INDEX,
    CREATE_BOOK_ITEM_AUTHORS_TABLE, CREATE_BOOK_ITEM_AUTHORS_AUTHOR_INDEX,
)

SCHEMA_STATEMENTS = (
    CREATE_BOOK_ITEMS_TABLE,
    CREATE_BOOK_ITEMS_TITLE_INDEX,
    CREATE_BOOK_ITEMS_ISBN_INDEX,
    CREATE_BOOK_ITEMS_MAGAZINE_CODE_INDEX,
    CREATE_TAGS_TABLE,
    CREATE_BOOK_ITEM_TAGS_TABLE,
    CREATE_BOOK_ITEM_TAGS_TAG_ID_INDEX,
    CREATE_READING_HISTORIES_TABLE,
    CREATE_READING_HISTORIES_BOOK_ITEM_ID_INDEX,
)

SCHEMA_STATEMENTS += AUTHOR_SCHEMA_STATEMENTS
