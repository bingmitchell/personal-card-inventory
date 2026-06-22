// Database layer for iOS — replaces the Flask API (scripts/lib/db.py + forms.py).
// Uses @capacitor-community/sqlite directly instead of fetch('/api/...').

import { CapacitorSQLite, SQLiteConnection } from '@capacitor-community/sqlite';
import { TABLES, VIEW_SQL } from './schema.js';

const sqlite = new SQLiteConnection(CapacitorSQLite);
let _db = null;

// ── Init ───────────────────────────────────────────────────────────────────

export async function initDB() {
  _db = await sqlite.createConnection('card_inventory', false, 'no-encryption', 1, false);
  await _db.open();

  for (const ddl of TABLES) {
    await _db.execute(ddl);
  }

  // Recreate view (DROP + CREATE so it always reflects current schema)
  await _db.execute('DROP VIEW IF EXISTS v_inventory_detail');
  await _db.execute(VIEW_SQL);
}

function db() {
  if (!_db) throw new Error('DB not initialised — call initDB() first');
  return _db;
}

// ── Inventory ──────────────────────────────────────────────────────────────

export async function getInventory(statusFilter = null) {
  let sql = `
    SELECT inventory_id, status, acquisition_date, card_id, sport, year,
           manufacturer, set_name, insert_name, card_number, player_name, team,
           parallel_name, is_auto, is_relic, is_patch, is_rookie,
           is_numbered, print_run, is_graded, grading_company, grade,
           grade_qualifier, grading_cost, break_id,
           cost_basis, item_price, tax_paid, shipping_paid,
           comp_low, comp_avg, comp_high, unrealized_gain_avg,
           front_image, back_image, inventory_notes
    FROM v_inventory_detail WHERE 1=1
  `;
  const params = [];
  if (statusFilter) {
    sql += ' AND status = ?';
    params.push(statusFilter);
  }
  sql += ' ORDER BY player_name, year DESC';
  const res = await db().query(sql, params);
  return res.values ?? [];
}

export async function getInventoryById(inventoryId) {
  const res = await db().query(`
    SELECT i.inventory_id, i.status, i.acquisition_date, i.location,
           i.is_graded, i.grading_company, i.grade, i.grade_qualifier, i.cert_number,
           i.grading_cost, i.cost_basis, i.item_price, i.tax_paid, i.shipping_paid,
           i.comp_low, i.comp_avg, i.comp_high,
           i.front_image, i.back_image, i.break_id,
           i.notes AS inventory_notes,
           c.card_id, c.sport, c.year, c.manufacturer, c.set_name, c.insert_name,
           c.card_number, c.player_name, c.team, c.parallel_name,
           c.is_base, c.is_auto, c.is_relic, c.is_patch, c.is_rookie,
           c.is_numbered, c.print_run, c.notes AS card_notes
    FROM inventory i JOIN cards c ON c.card_id = i.card_id
    WHERE i.inventory_id = ?
  `, [inventoryId]);
  return res.values?.[0] ?? null;
}

export async function searchOwnedInventory(query) {
  const pattern = `%${query}%`;
  const res = await db().query(`
    SELECT i.inventory_id, c.card_id, c.player_name, c.year, c.manufacturer,
           c.set_name, c.card_number, c.parallel_name, c.is_auto, c.is_relic,
           c.is_rookie, c.print_run, i.is_graded, i.grading_company, i.grade
    FROM inventory i JOIN cards c ON c.card_id = i.card_id
    WHERE i.status = 'OWNED' AND i.deleted_at IS NULL AND c.deleted_at IS NULL
      AND c.is_test = 0
      AND (c.player_name LIKE ? OR c.set_name LIKE ? OR c.manufacturer LIKE ? OR CAST(c.year AS TEXT) LIKE ?)
    ORDER BY c.player_name, c.year DESC LIMIT 25
  `, [pattern, pattern, pattern, pattern]);
  return res.values ?? [];
}

// ── Add Card ───────────────────────────────────────────────────────────────

export async function checkDuplicateCard(cardData) {
  const res = await db().query(`
    SELECT card_id FROM cards
    WHERE year = ? AND manufacturer = ? AND set_name = ?
      AND COALESCE(card_number, '') = ? AND COALESCE(parallel_name, '') = ?
      AND is_auto = ? AND is_relic = ? AND deleted_at IS NULL
    LIMIT 1
  `, [
    cardData.year, cardData.manufacturer, cardData.set_name,
    cardData.card_number ?? '', cardData.parallel_name ?? '',
    cardData.is_auto ? 1 : 0, cardData.is_relic ? 1 : 0,
  ]);
  const row = res.values?.[0];
  return row ? { isDuplicate: true, cardId: row.card_id } : { isDuplicate: false, cardId: null };
}

export async function insertCard(cardData) {
  const res = await db().run(`
    INSERT INTO cards (sport, year, manufacturer, set_name, card_number, player_name,
      team, is_base, insert_name, parallel_name, is_auto, is_relic, is_patch,
      is_rookie, is_numbered, print_run, notes)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
  `, [
    cardData.sport, cardData.year, cardData.manufacturer, cardData.set_name,
    cardData.card_number ?? null, cardData.player_name, cardData.team ?? null,
    cardData.is_base ? 1 : 1,
    cardData.insert_name ?? null, cardData.parallel_name ?? null,
    cardData.is_auto ? 1 : 0, cardData.is_relic ? 1 : 0,
    cardData.is_patch ? 1 : 0, cardData.is_rookie ? 1 : 0,
    cardData.print_run ? 1 : 0, cardData.print_run ?? null,
    cardData.notes ?? null,
  ]);
  return res.changes?.lastId;
}

export async function insertInventory(cardId, opts = {}) {
  const compUpdatedAt = (opts.comp_low != null || opts.comp_avg != null || opts.comp_high != null)
    ? new Date().toISOString() : null;
  const res = await db().run(`
    INSERT INTO inventory (card_id, cost_basis, item_price, tax_paid, shipping_paid,
      comp_low, comp_avg, comp_high, acquisition_date, comp_updated_at,
      is_graded, grading_company, grade, grade_qualifier, cert_number, grading_cost, break_id)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
  `, [
    cardId,
    opts.cost_basis ?? null, opts.item_price ?? null,
    opts.tax_paid ?? null, opts.shipping_paid ?? null,
    opts.comp_low ?? null, opts.comp_avg ?? null, opts.comp_high ?? null,
    opts.acquisition_date ?? null, compUpdatedAt,
    opts.is_graded ? 1 : 0,
    opts.grading_company ?? null, opts.grade ?? null,
    opts.grade_qualifier ?? null, opts.cert_number ?? null,
    opts.grading_cost ?? null, opts.break_id ?? null,
  ]);
  return res.changes?.lastId;
}

export async function insertTransaction(opts = {}) {
  const res = await db().run(`
    INSERT INTO transactions (transaction_type, transaction_date, counterparty,
      venue, cash_component, total_price)
    VALUES (?,?,?,?,?,?)
  `, [
    opts.transaction_type, opts.transaction_date ?? null,
    opts.counterparty ?? null, opts.venue ?? null,
    opts.cash_component ?? 0, opts.total_price ?? null,
  ]);
  return res.changes?.lastId;
}

export async function insertTransactionItem(transactionId, inventoryId, direction, itemPrice = null) {
  await db().run(
    'INSERT INTO transaction_items (transaction_id, inventory_id, direction, item_price) VALUES (?,?,?,?)',
    [transactionId, inventoryId, direction, itemPrice],
  );
}

export async function markInventoryDisposed(inventoryIds, transactionId) {
  if (!inventoryIds.length) return;
  const placeholders = inventoryIds.map(() => '?').join(',');
  await db().run(
    `UPDATE inventory SET status = 'TRADED', updated_at = datetime('now') WHERE inventory_id IN (${placeholders})`,
    inventoryIds,
  );
  for (const id of inventoryIds) {
    await db().run(
      "INSERT INTO transaction_items (transaction_id, inventory_id, direction) VALUES (?,?,'disposed')",
      [transactionId, id],
    );
  }
}

// ── Edit Card ──────────────────────────────────────────────────────────────

export async function updateCard(cardId, data) {
  await db().run(`
    UPDATE cards SET sport=?, year=?, manufacturer=?, set_name=?, card_number=?,
      player_name=?, team=?, insert_name=?, parallel_name=?,
      is_auto=?, is_relic=?, is_patch=?, is_rookie=?, is_numbered=?, print_run=?,
      notes=?, updated_at=datetime('now')
    WHERE card_id = ?
  `, [
    data.sport, data.year, data.manufacturer, data.set_name,
    data.card_number ?? null, data.player_name, data.team ?? null,
    data.insert_name ?? null, data.parallel_name ?? null,
    data.is_auto ? 1 : 0, data.is_relic ? 1 : 0,
    data.is_patch ? 1 : 0, data.is_rookie ? 1 : 0,
    data.print_run ? 1 : 0, data.print_run ?? null,
    data.card_notes ?? null, cardId,
  ]);
}

export async function updateInventory(inventoryId, data) {
  const compUpdatedAt = (data.comp_low != null || data.comp_avg != null || data.comp_high != null)
    ? new Date().toISOString() : null;
  await db().run(`
    UPDATE inventory SET
      status=?, acquisition_date=?, item_price=?, tax_paid=?, shipping_paid=?, cost_basis=?,
      is_graded=?, grading_company=?, grade=?, grade_qualifier=?, cert_number=?, grading_cost=?,
      comp_low=?, comp_avg=?, comp_high=?,
      comp_updated_at=COALESCE(?, comp_updated_at),
      notes=?, updated_at=datetime('now')
    WHERE inventory_id = ?
  `, [
    data.status ?? 'OWNED', data.acquisition_date ?? null,
    data.item_price ?? null, data.tax_paid ?? null, data.shipping_paid ?? null,
    data.cost_basis ?? null,
    data.is_graded ? 1 : 0, data.grading_company ?? null,
    data.grade ?? null, data.grade_qualifier ?? null,
    data.cert_number ?? null, data.grading_cost ?? null,
    data.comp_low ?? null, data.comp_avg ?? null, data.comp_high ?? null,
    compUpdatedAt,
    data.inventory_notes ?? null, inventoryId,
  ]);
}

// ── Breaks ─────────────────────────────────────────────────────────────────

export async function getBreaks() {
  const res = await db().query(
    'SELECT break_id, break_name, box_cost, expected_cards FROM breaks ORDER BY break_id DESC'
  );
  return res.values ?? [];
}

export async function getOrCreateBreak(breakName, boxCost = null, expectedCards = null) {
  const existing = await db().query('SELECT break_id FROM breaks WHERE break_name = ? LIMIT 1', [breakName]);
  if (existing.values?.length) {
    const id = existing.values[0].break_id;
    if (boxCost != null || expectedCards != null) {
      await db().run(
        'UPDATE breaks SET box_cost=COALESCE(?,box_cost), expected_cards=COALESCE(?,expected_cards) WHERE break_id=?',
        [boxCost, expectedCards, id],
      );
    }
    return id;
  }
  const res = await db().run(
    'INSERT INTO breaks (break_name, box_cost, expected_cards) VALUES (?,?,?)',
    [breakName, boxCost, expectedCards],
  );
  return res.changes?.lastId;
}
