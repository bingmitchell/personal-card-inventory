// SQLite schema for iOS — mirrors scripts/lib/schema.py exactly.
// Applied at startup via initDB().

export const TABLES = [
  `CREATE TABLE IF NOT EXISTS cards (
    card_id         INTEGER PRIMARY KEY,
    sport           TEXT NOT NULL,
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
    print_run       INTEGER,
    is_test         INTEGER NOT NULL DEFAULT 0,
    notes           TEXT,
    deleted_at      TEXT,
    version         INTEGER DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
  )`,
  `CREATE TABLE IF NOT EXISTS inventory (
    inventory_id    INTEGER PRIMARY KEY,
    card_id         INTEGER NOT NULL REFERENCES cards(card_id),
    status          TEXT NOT NULL DEFAULT 'OWNED',
    acquisition_date TEXT,
    location        TEXT,
    is_graded       INTEGER NOT NULL DEFAULT 0,
    grading_company TEXT,
    grade           TEXT,
    grade_qualifier TEXT,
    cert_number     TEXT,
    grading_cost    REAL,
    cost_basis      REAL,
    item_price      REAL,
    tax_paid        REAL,
    shipping_paid   REAL,
    comp_low        REAL,
    comp_avg        REAL,
    comp_high       REAL,
    comp_updated_at TEXT,
    front_image     TEXT,
    back_image      TEXT,
    break_id        INTEGER REFERENCES breaks(break_id),
    notes           TEXT,
    deleted_at      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
  )`,
  `CREATE TABLE IF NOT EXISTS breaks (
    break_id        INTEGER PRIMARY KEY,
    break_name      TEXT NOT NULL,
    box_cost        REAL,
    expected_cards  INTEGER,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
  )`,
  `CREATE TABLE IF NOT EXISTS transactions (
    transaction_id  INTEGER PRIMARY KEY,
    transaction_type TEXT NOT NULL,
    transaction_date TEXT,
    counterparty    TEXT,
    venue           TEXT,
    cash_component  REAL DEFAULT 0,
    total_price     REAL,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
  )`,
  `CREATE TABLE IF NOT EXISTS transaction_items (
    item_id         INTEGER PRIMARY KEY,
    transaction_id  INTEGER NOT NULL REFERENCES transactions(transaction_id),
    inventory_id    INTEGER NOT NULL REFERENCES inventory(inventory_id),
    direction       TEXT NOT NULL,
    item_price      REAL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
  )`,
];

export const VIEW_SQL = `
  CREATE VIEW IF NOT EXISTS v_inventory_detail AS
  SELECT
    i.inventory_id, i.card_id, i.status, i.acquisition_date,
    i.location, i.is_graded, i.grading_company, i.grade,
    i.grade_qualifier, i.cert_number, i.grading_cost,
    i.cost_basis, i.item_price, i.tax_paid, i.shipping_paid,
    i.comp_low, i.comp_avg, i.comp_high, i.comp_updated_at,
    i.front_image, i.back_image,
    i.break_id,
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
`;
