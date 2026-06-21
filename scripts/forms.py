#!/usr/bin/env python3
"""
Flask web form for adding cards to inventory.
Serves at http://localhost:8000/form

Usage:
  python forms.py
"""

from flask import Flask, render_template, request, jsonify
import sys
from pathlib import Path
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from lib.db import (get_connection, check_duplicate_card, insert_card, log_import,
                    insert_inventory, insert_transaction, insert_transaction_item,
                    mark_inventory_disposed, search_owned_inventory,
                    close_connection)
from lib.validators import validate_card_data, ValidationError, VALID_SPORTS

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

@app.route('/', methods=['GET'])
@app.route('/form', methods=['GET'])
def form_page():
    """Serve the card entry form."""
    return render_template('form.html', valid_sports=sorted(VALID_SPORTS))

@app.route('/api/add-card', methods=['POST'])
def api_add_card():
    """
    API endpoint to add a card.
    Accepts JSON POST request with card data.
    """
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        def _parse_decimal(val):
            try:
                return float(val) if val not in (None, '', 'null') else None
            except (TypeError, ValueError):
                return None

        def _s(val):
            """Safely convert any value to a stripped string; returns '' for None."""
            return str(val).strip() if val is not None else ''

        # Card catalog fields
        card_data = {
            'sport': _s(data.get('sport')),
            'year': _s(data.get('year')),
            'manufacturer': _s(data.get('manufacturer')),
            'set_name': _s(data.get('set_name')),
            'player_name': _s(data.get('player_name')),
            'card_number': _s(data.get('card_number')) or None,
            'team': _s(data.get('team')) or None,
            'parallel_name': _s(data.get('parallel_name')) or None,
            'insert_name': _s(data.get('insert_name')) or None,
            'is_auto': data.get('is_auto', False),
            'is_relic': data.get('is_relic', False),
            'is_patch': data.get('is_patch', False),
            'is_rookie': data.get('is_rookie', False),
            'is_numbered': bool(data.get('print_run')),
            'print_run': data.get('print_run') or None,
            'notes': _s(data.get('notes')) or None,
        }

        # Acquisition fields
        acquisition_type    = (data.get('acquisition_type') or '').strip().upper() or None
        acquisition_date    = data.get('acquisition_date') or None
        counterparty        = (data.get('counterparty') or '').strip() or None
        venue               = (data.get('venue') or '').strip() or None
        cost_basis          = _parse_decimal(data.get('cost_basis'))
        cash_component      = _parse_decimal(data.get('cash_component')) or 0
        traded_inventory_ids = [int(x) for x in (data.get('traded_inventory_ids') or []) if x]

        # Comp values
        comp_low  = _parse_decimal(data.get('comp_low'))
        comp_avg  = _parse_decimal(data.get('comp_avg'))
        comp_high = _parse_decimal(data.get('comp_high'))

        # Validate
        try:
            card_data = validate_card_data(card_data)
        except ValidationError as e:
            return jsonify({'success': False, 'error': str(e)}), 400

        # Connect to database
        conn = get_connection()

        # Check for duplicate card in catalog
        is_duplicate, existing_id = check_duplicate_card(conn, card_data)
        if is_duplicate:
            return jsonify({
                'success': False,
                'error': 'Card already exists in catalog',
                'existing_card_id': existing_id,
                'duplicate': True
            }), 409

        start_time = time.time()

        is_test = bool(data.get('is_test', False))

        # 1. Insert card into catalog (auto-commits inside insert_card)
        card_id = insert_card(conn, card_data, is_test=is_test)

        # 2. Insert inventory + transaction atomically
        try:
            inventory_id = insert_inventory(
                conn, card_id,
                cost_basis=cost_basis,
                comp_low=comp_low,
                comp_avg=comp_avg,
                comp_high=comp_high,
                acquisition_date=acquisition_date or None,
            )

            if acquisition_type in ('PURCHASE', 'TRADE'):
                transaction_id = insert_transaction(
                    conn,
                    transaction_type=acquisition_type,
                    transaction_date=acquisition_date or None,
                    counterparty=counterparty,
                    venue=venue,
                    cash_component=cash_component if acquisition_type == 'TRADE' else 0,
                    total_price=cost_basis,
                )
                insert_transaction_item(
                    conn, transaction_id, inventory_id,
                    direction='acquired',
                    item_price=cost_basis,
                )
                if acquisition_type == 'TRADE' and traded_inventory_ids:
                    mark_inventory_disposed(conn, traded_inventory_ids, transaction_id)

            conn.commit()
        except Exception:
            conn.rollback()
            raise

        elapsed = time.time() - start_time

        log_import(conn, 'WEB_FORM', record_count=1, success_count=1,
                   error_count=0, status='SUCCESS', execution_time=int(elapsed))

        return jsonify({
            'success': True,
            'message': 'Card added successfully',
            'card_id': card_id,
            'inventory_id': inventory_id,
            'card_data': {
                'player_name': card_data['player_name'],
                'sport': card_data['sport'],
                'year': card_data['year'],
                'set_name': card_data['set_name'],
            }
        }), 201
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        close_connection(conn)

@app.route('/api/inventory/search', methods=['GET'])
def inventory_search():
    """Search owned inventory cards for the trade card picker."""
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    conn = None
    try:
        conn = get_connection()
        results = search_owned_inventory(conn, q)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        close_connection(conn)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
    finally:
        close_connection(conn)

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found', 'path': request.path}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Card Inventory Form Server")
    print("="*60)
    print("Form:   http://localhost:8000/form")
    print("Health: http://localhost:8000/api/health")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=8000, debug=False)
