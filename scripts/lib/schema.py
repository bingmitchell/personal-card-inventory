"""
SQLite schema. Applied at startup via init_db().
TABLES  — CREATE TABLE IF NOT EXISTS (idempotent)
MIGRATIONS — ALTER TABLE additions for existing databases
VIEWS   — always dropped and recreated so they stay current
"""

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS cards (
        card_id         INTEGER PRIMARY KEY,
        sport           TEXT NOT NULL CHECK(sport IN ('baseball','basketball','football','hockey','soccer','tennis','golf','other')),
        year            INTEGER NOT NULL,
        manufacturer    TEXT NOT NULL,
        set_name        TEXT NOT NULL,
        card_number     TEXT,
        player_name     TEXT NOT NULL,
        team            TEXT,
        is_base         INTEGER NOT NULL DEFAULT 1,
        insert_name     TEXT,
        parallel_name   TEXT,
        is_auto         INTEGER NOT NULL DEFAULT 0,
        is_relic        INTEGER NOT NULL DEFAULT 0,
        is_patch        INTEGER NOT NULL DEFAULT 0,
        is_rookie       INTEGER NOT NULL DEFAULT 0,
        is_numbered     INTEGER NOT NULL DEFAULT 0,
        print_run       INTEGER CHECK(print_run > 0),
        is_test         INTEGER NOT NULL DEFAULT 0,
        notes           TEXT,
        deleted_at      TEXT,
        version         INTEGER DEFAULT 1,
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS inventory (
        inventory_id    INTEGER PRIMARY KEY,
        card_id         INTEGER NOT NULL REFERENCES cards(card_id),
        status          TEXT NOT NULL DEFAULT 'OWNED'
                            CHECK(status IN ('OWNED','SOLD','TRADED','LOST')),
        acquisition_date TEXT,
        location        TEXT,
        is_graded       INTEGER NOT NULL DEFAULT 0,
        grading_company TEXT,
        grade           TEXT,
        grade_qualifier TEXT,
        cert_number     TEXT,
        cost_basis      REAL CHECK(cost_basis >= 0),
        item_price      REAL CHECK(item_price >= 0),
        tax_paid        REAL CHECK(tax_paid >= 0),
        shipping_paid   REAL CHECK(shipping_paid >= 0),
        comp_low        REAL CHECK(comp_low >= 0),
        comp_avg        REAL CHECK(comp_avg >= 0),
        comp_high       REAL CHECK(comp_high >= 0),
        comp_updated_at TEXT,
        front_image     TEXT,
        back_image      TEXT,
        notes           TEXT,
        deleted_at      TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id  INTEGER PRIMARY KEY,
        transaction_type TEXT NOT NULL
                            CHECK(transaction_type IN ('PURCHASE','SALE','TRADE','DONATION')),
        transaction_date TEXT,
        counterparty    TEXT,
        venue           TEXT,
        cash_component  REAL DEFAULT 0,
        total_price     REAL,
        notes           TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transaction_items (
        item_id         INTEGER PRIMARY KEY,
        transaction_id  INTEGER NOT NULL REFERENCES transactions(transaction_id),
        inventory_id    INTEGER NOT NULL REFERENCES inventory(inventory_id),
        direction       TEXT NOT NULL CHECK(direction IN ('acquired','disposed')),
        item_price      REAL,
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS import_logs (
        import_id               INTEGER PRIMARY KEY,
        import_method           TEXT,
        file_name               TEXT,
        record_count            INTEGER DEFAULT 0,
        success_count           INTEGER DEFAULT 0,
        error_count             INTEGER DEFAULT 0,
        status                  TEXT,
        error_message           TEXT,
        execution_time_seconds  INTEGER,
        created_at              TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
]

# Column additions for existing databases that predate a schema change.
# Each tuple: (table, column_name, column_definition)
MIGRATIONS = [
    ("inventory", "item_price",    "REAL CHECK(item_price >= 0)"),
    ("inventory", "tax_paid",      "REAL CHECK(tax_paid >= 0)"),
    ("inventory", "shipping_paid", "REAL CHECK(shipping_paid >= 0)"),
    ("inventory", "front_image",   "TEXT"),
    ("inventory", "back_image",    "TEXT"),
]

VIEW_NAMES = ["v_inventory_detail"]

VIEWS = [
    """
    CREATE VIEW v_inventory_detail AS
    SELECT
        i.inventory_id, i.card_id, i.status, i.acquisition_date,
        i.location, i.is_graded, i.grading_company, i.grade,
        i.grade_qualifier, i.cert_number,
        i.cost_basis, i.item_price, i.tax_paid, i.shipping_paid,
        i.comp_low, i.comp_avg, i.comp_high, i.comp_updated_at,
        i.front_image, i.back_image,
        i.notes AS inventory_notes,
        c.sport, c.year, c.manufacturer, c.set_name, c.card_number,
        c.player_name, c.team, c.is_base, c.insert_name, c.parallel_name,
        c.is_auto, c.is_relic, c.is_patch, c.is_rookie, c.is_numbered, c.print_run,
        CASE
            WHEN i.comp_avg IS NOT NULL AND i.cost_basis IS NOT NULL
                THEN i.comp_avg - i.cost_basis
            WHEN i.comp_low IS NOT NULL AND i.cost_basis IS NOT NULL
                THEN i.comp_low - i.cost_basis
            ELSE NULL
        END AS unrealized_gain_avg
    FROM inventory i
    JOIN cards c ON c.card_id = i.card_id
    WHERE i.deleted_at IS NULL AND c.deleted_at IS NULL
    """,
]
