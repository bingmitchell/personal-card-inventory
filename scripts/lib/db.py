"""
Database utilities for card inventory system (SQLite).
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime

from .schema import TABLES, VIEWS


def _db_path() -> Path:
    env = os.getenv('CARD_DB_PATH')
    if env:
        return Path(env)
    data_dir = Path.home() / '.card_inventory'
    data_dir.mkdir(exist_ok=True)
    return data_dir / 'card_inventory.db'


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables and views if they don't exist."""
    conn = get_connection()
    try:
        for ddl in TABLES + VIEWS:
            conn.execute(ddl)
        conn.commit()
    finally:
        conn.close()


def close_connection(conn):
    try:
        if conn:
            conn.close()
    except Exception as e:
        print(f"Warning: Failed to close connection: {e}")


def check_duplicate_card(conn, card_data):
    """Returns (exists: bool, card_id: int | None)."""
    query = """
    SELECT card_id FROM cards
    WHERE year = ?
      AND manufacturer = ?
      AND set_name = ?
      AND COALESCE(card_number, '') = ?
      AND COALESCE(parallel_name, '') = ?
      AND is_auto = ?
      AND is_relic = ?
      AND deleted_at IS NULL
    LIMIT 1
    """
    cur = conn.cursor()
    cur.execute(query, (
        card_data['year'],
        card_data['manufacturer'],
        card_data['set_name'],
        card_data.get('card_number') or '',
        card_data.get('parallel_name') or '',
        1 if card_data.get('is_auto') else 0,
        1 if card_data.get('is_relic') else 0,
    ))
    row = cur.fetchone()
    return (True, row[0]) if row else (False, None)


def insert_card(conn, card_data, is_test=False):
    """Insert card into catalog. Commits immediately. Returns card_id."""
    query = """
    INSERT INTO cards (
        sport, year, manufacturer, set_name, card_number, player_name, team,
        is_base, insert_name, parallel_name, is_auto, is_relic, is_patch,
        is_rookie, is_numbered, print_run, notes, is_test
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """
    try:
        cur = conn.cursor()
        cur.execute(query, (
            card_data['sport'],
            card_data['year'],
            card_data['manufacturer'],
            card_data['set_name'],
            card_data.get('card_number'),
            card_data['player_name'],
            card_data.get('team'),
            1 if card_data.get('is_base', True) else 0,
            card_data.get('insert_name'),
            card_data.get('parallel_name'),
            1 if card_data.get('is_auto') else 0,
            1 if card_data.get('is_relic') else 0,
            1 if card_data.get('is_patch') else 0,
            1 if card_data.get('is_rookie') else 0,
            1 if card_data.get('is_numbered') else 0,
            card_data.get('print_run'),
            card_data.get('notes'),
            1 if is_test else 0,
        ))
        card_id = cur.lastrowid
        conn.commit()
        return card_id
    except Exception as e:
        conn.rollback()
        raise Exception(f"Card insert failed: {e}")


def insert_inventory(conn, card_id, cost_basis=None, item_price=None, tax_paid=None,
                     shipping_paid=None, comp_low=None, comp_avg=None,
                     comp_high=None, acquisition_date=None):
    """Insert inventory record. Does NOT commit — caller must commit."""
    comp_updated_at = (
        datetime.now().isoformat()
        if any(v is not None for v in [comp_low, comp_avg, comp_high])
        else None
    )
    query = """
    INSERT INTO inventory (card_id, cost_basis, item_price, tax_paid, shipping_paid,
                           comp_low, comp_avg, comp_high, acquisition_date, comp_updated_at)
    VALUES (?,?,?,?,?,?,?,?,?,?)
    """
    cur = conn.cursor()
    cur.execute(query, (card_id, cost_basis, item_price, tax_paid, shipping_paid,
                        comp_low, comp_avg, comp_high, acquisition_date, comp_updated_at))
    return cur.lastrowid


def insert_transaction(conn, transaction_type, transaction_date, counterparty=None,
                       venue=None, cash_component=0, total_price=None, notes=None):
    """Insert transaction header. Does NOT commit — caller must commit."""
    query = """
    INSERT INTO transactions (transaction_type, transaction_date, counterparty, venue,
                              cash_component, total_price, notes)
    VALUES (?,?,?,?,?,?,?)
    """
    cur = conn.cursor()
    cur.execute(query, (transaction_type, transaction_date, counterparty, venue,
                        cash_component or 0, total_price, notes))
    return cur.lastrowid


def insert_transaction_item(conn, transaction_id, inventory_id, direction, item_price=None):
    """Insert transaction line item. Does NOT commit — caller must commit."""
    query = """
    INSERT INTO transaction_items (transaction_id, inventory_id, direction, item_price)
    VALUES (?,?,?,?)
    """
    cur = conn.cursor()
    cur.execute(query, (transaction_id, inventory_id, direction, item_price))
    return cur.lastrowid


def log_import(conn, import_method, file_name=None, record_count=0,
               success_count=0, error_count=0, status='SUCCESS',
               error_message=None, execution_time=None):
    """Log an import operation. Commits immediately."""
    query = """
    INSERT INTO import_logs (import_method, file_name, record_count, success_count,
                             error_count, status, error_message, execution_time_seconds)
    VALUES (?,?,?,?,?,?,?,?)
    """
    try:
        cur = conn.cursor()
        cur.execute(query, (import_method, file_name, record_count, success_count,
                            error_count, status, error_message, execution_time))
        import_id = cur.lastrowid
        conn.commit()
        return import_id
    except Exception as e:
        conn.rollback()
        raise Exception(f"Import logging failed: {e}")


def search_owned_inventory(conn, query, limit=25):
    """Search owned inventory by player, set, manufacturer, or year."""
    sql = """
    SELECT i.inventory_id, c.card_id, c.player_name, c.year, c.manufacturer,
           c.set_name, c.card_number, c.parallel_name, c.is_auto, c.is_relic,
           c.is_rookie, c.print_run, i.is_graded, i.grading_company, i.grade
    FROM inventory i
    JOIN cards c ON c.card_id = i.card_id
    WHERE i.status = 'OWNED'
      AND i.deleted_at IS NULL
      AND c.deleted_at IS NULL
      AND c.is_test = 0
      AND (
          c.player_name LIKE ? OR
          c.set_name    LIKE ? OR
          c.manufacturer LIKE ? OR
          CAST(c.year AS TEXT) LIKE ?
      )
    ORDER BY c.player_name, c.year DESC
    LIMIT ?
    """
    pattern = f'%{query}%'
    cur = conn.cursor()
    cur.execute(sql, (pattern, pattern, pattern, pattern, limit))
    return [dict(r) for r in cur.fetchall()]


def get_inventory_by_id(conn, inventory_id):
    """Return a single inventory+card row for pre-filling the edit form."""
    query = """
    SELECT i.inventory_id, i.status, i.acquisition_date, i.location,
           i.is_graded, i.grading_company, i.grade, i.grade_qualifier, i.cert_number,
           i.cost_basis, i.item_price, i.tax_paid, i.shipping_paid,
           i.comp_low, i.comp_avg, i.comp_high, i.notes AS inventory_notes,
           c.card_id, c.sport, c.year, c.manufacturer, c.set_name, c.insert_name,
           c.card_number, c.player_name, c.team, c.parallel_name,
           c.is_base, c.is_auto, c.is_relic, c.is_patch, c.is_rookie,
           c.is_numbered, c.print_run, c.notes AS card_notes
    FROM inventory i
    JOIN cards c ON c.card_id = i.card_id
    WHERE i.inventory_id = ?
    """
    cur = conn.cursor()
    cur.execute(query, (inventory_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def update_card(conn, card_id, data):
    """Update card catalog fields. Does NOT commit — caller must commit."""
    query = """
    UPDATE cards SET
        sport         = ?,
        year          = ?,
        manufacturer  = ?,
        set_name      = ?,
        card_number   = ?,
        player_name   = ?,
        team          = ?,
        insert_name   = ?,
        parallel_name = ?,
        is_auto       = ?,
        is_relic      = ?,
        is_patch      = ?,
        is_rookie     = ?,
        is_numbered   = ?,
        print_run     = ?,
        notes         = ?,
        updated_at    = datetime('now')
    WHERE card_id = ?
    """
    conn.execute(query, (
        data['sport'], data['year'], data['manufacturer'], data['set_name'],
        data.get('card_number'), data['player_name'], data.get('team'),
        data.get('insert_name'), data.get('parallel_name'),
        1 if data.get('is_auto') else 0,
        1 if data.get('is_relic') else 0,
        1 if data.get('is_patch') else 0,
        1 if data.get('is_rookie') else 0,
        1 if data.get('is_numbered') else 0,
        data.get('print_run'),
        data.get('card_notes'),
        card_id,
    ))


def update_inventory(conn, inventory_id, data):
    """Update inventory fields. Does NOT commit — caller must commit."""
    comp_updated_at = (
        datetime.now().isoformat()
        if any(data.get(k) is not None for k in ['comp_low', 'comp_avg', 'comp_high'])
        else None
    )
    query = """
    UPDATE inventory SET
        status           = ?,
        acquisition_date = ?,
        item_price       = ?,
        tax_paid         = ?,
        shipping_paid    = ?,
        cost_basis       = ?,
        comp_low         = ?,
        comp_avg         = ?,
        comp_high        = ?,
        comp_updated_at  = COALESCE(?, comp_updated_at),
        notes            = ?,
        updated_at       = datetime('now')
    WHERE inventory_id = ?
    """
    conn.execute(query, (
        data.get('status', 'OWNED'),
        data.get('acquisition_date'),
        data.get('item_price'), data.get('tax_paid'), data.get('shipping_paid'),
        data.get('cost_basis'),
        data.get('comp_low'), data.get('comp_avg'), data.get('comp_high'),
        comp_updated_at,
        data.get('inventory_notes'),
        inventory_id,
    ))


def mark_inventory_disposed(conn, inventory_ids, transaction_id):
    """Mark cards as TRADED and insert disposed transaction items. Caller must commit."""
    if not inventory_ids:
        return
    placeholders = ','.join('?' * len(inventory_ids))
    conn.execute(
        f"UPDATE inventory SET status = 'TRADED', updated_at = datetime('now') "
        f"WHERE inventory_id IN ({placeholders}) AND status = 'OWNED'",
        inventory_ids,
    )
    conn.executemany(
        "INSERT INTO transaction_items (transaction_id, inventory_id, direction) VALUES (?,?,'disposed')",
        [(transaction_id, iid) for iid in inventory_ids],
    )
