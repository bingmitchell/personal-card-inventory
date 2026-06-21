#!/usr/bin/env python3
"""
Load cards from data/seed_cards.json into the local SQLite database.
Safe to run multiple times — skips cards that already exist.

Usage:
  python scripts/seed.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from lib.db import (get_connection, init_db, close_connection,
                    check_duplicate_card, insert_card, insert_inventory,
                    insert_transaction, insert_transaction_item)
from lib.validators import validate_card_data, ValidationError


def seed():
    seed_file = ROOT / 'data' / 'seed_cards.json'
    if not seed_file.exists():
        print(f"Seed file not found: {seed_file}")
        sys.exit(1)

    entries = json.loads(seed_file.read_text())
    print(f"Seeding {len(entries)} card(s) from {seed_file.name}...")

    init_db()
    conn = get_connection()
    added = skipped = errors = 0

    for entry in entries:
        card_data = {
            'sport':        entry['sport'],
            'year':         entry['year'],
            'manufacturer': entry['manufacturer'],
            'set_name':     entry['set_name'],
            'card_number':  entry.get('card_number'),
            'player_name':  entry['player_name'],
            'team':         entry.get('team'),
            'insert_name':  entry.get('insert_name'),
            'parallel_name': entry.get('parallel_name'),
            'is_auto':      entry.get('is_auto', False),
            'is_relic':     entry.get('is_relic', False),
            'is_patch':     entry.get('is_patch', False),
            'is_rookie':    entry.get('is_rookie', False),
            'is_numbered':  bool(entry.get('print_run')),
            'print_run':    entry.get('print_run'),
            'notes':        entry.get('card_notes'),
        }

        try:
            card_data = validate_card_data(card_data)
        except ValidationError as e:
            print(f"  SKIP  {entry.get('player_name')} — validation: {e}")
            errors += 1
            continue

        is_dup, _ = check_duplicate_card(conn, card_data)
        if is_dup:
            print(f"  SKIP  {card_data['player_name']} {card_data['year']} {card_data['set_name']} (already exists)")
            skipped += 1
            continue

        try:
            item_price    = entry.get('item_price')
            tax_paid      = entry.get('tax_paid')
            shipping_paid = entry.get('shipping_paid')
            if any(v is not None for v in [item_price, tax_paid, shipping_paid]):
                cost_basis = round((item_price or 0) + (tax_paid or 0) + (shipping_paid or 0), 2)
            else:
                cost_basis = entry.get('cost_basis')

            card_id = insert_card(conn, card_data, is_test=False)
            inventory_id = insert_inventory(
                conn, card_id,
                cost_basis=cost_basis,
                item_price=item_price,
                tax_paid=tax_paid,
                shipping_paid=shipping_paid,
                comp_low=entry.get('comp_low'),
                comp_avg=entry.get('comp_avg'),
                comp_high=entry.get('comp_high'),
                acquisition_date=entry.get('acquisition_date'),
            )

            acq_type = (entry.get('acquisition_type') or '').upper()
            if acq_type in ('PURCHASE', 'TRADE'):
                txn_id = insert_transaction(
                    conn,
                    transaction_type=acq_type,
                    transaction_date=entry.get('acquisition_date'),
                    total_price=cost_basis,
                )
                insert_transaction_item(conn, txn_id, inventory_id, 'acquired', cost_basis)

            conn.commit()
            label = f"{card_data['player_name']} {card_data['year']} {card_data['set_name']}"
            if card_data.get('insert_name'):
                label += f" ({card_data['insert_name']})"
            print(f"  ADDED {label}")
            added += 1

        except Exception as e:
            conn.rollback()
            print(f"  ERROR {entry.get('player_name')} — {e}")
            errors += 1

    close_connection(conn)
    print(f"\nDone. Added: {added}  Skipped: {skipped}  Errors: {errors}")


if __name__ == '__main__':
    seed()
