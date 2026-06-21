#!/usr/bin/env python3
"""
Flask web form for adding cards to inventory.
Serves at http://localhost:8000/form

Usage:
  python forms.py
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import sys
import os
import threading
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent))

from lib.db import (get_connection, init_db, check_duplicate_card, insert_card, log_import,
                    insert_inventory, insert_transaction, insert_transaction_item,
                    mark_inventory_disposed, search_owned_inventory,
                    get_inventory_by_id, update_card, update_inventory,
                    update_inventory_photos, _photos_dir, close_connection)
from lib.validators import validate_card_data, ValidationError, VALID_SPORTS

# When frozen by PyInstaller, templates live inside sys._MEIPASS
_BASE_DIR = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent

app = Flask(__name__, template_folder=str(_BASE_DIR / 'templates'))
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
        item_price    = _parse_decimal(data.get('item_price'))
        tax_paid      = _parse_decimal(data.get('tax_paid'))
        shipping_paid = _parse_decimal(data.get('shipping_paid'))
        # cost_basis = sum of breakdown if provided, else fall back to a direct total field
        if any(v is not None for v in [item_price, tax_paid, shipping_paid]):
            cost_basis = (item_price or 0) + (tax_paid or 0) + (shipping_paid or 0)
        else:
            cost_basis = _parse_decimal(data.get('cost_basis'))
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
                item_price=item_price,
                tax_paid=tax_paid,
                shipping_paid=shipping_paid,
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

@app.route('/edit/<int:inventory_id>', methods=['GET'])
def edit_page(inventory_id):
    return render_template('edit.html', inventory_id=inventory_id)


@app.route('/api/inventory/<int:inventory_id>', methods=['GET'])
def get_inventory_detail(inventory_id):
    conn = None
    try:
        conn = get_connection()
        row = get_inventory_by_id(conn, inventory_id)
        if not row:
            return jsonify({'error': 'Not found'}), 404
        for k, v in row.items():
            if hasattr(v, 'isoformat'):
                row[k] = v.isoformat()
        return jsonify(row)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        close_connection(conn)


@app.route('/api/inventory/<int:inventory_id>', methods=['PUT'])
def update_inventory_entry(inventory_id):
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        def _s(val):
            return str(val).strip() if val is not None else ''

        def _dec(val):
            try:
                return float(val) if val not in (None, '', 'null') else None
            except (TypeError, ValueError):
                return None

        card_data = {
            'sport':        _s(data.get('sport')),
            'year':         _s(data.get('year')),
            'manufacturer': _s(data.get('manufacturer')),
            'set_name':     _s(data.get('set_name')),
            'player_name':  _s(data.get('player_name')),
            'card_number':  _s(data.get('card_number')) or None,
            'team':         _s(data.get('team')) or None,
            'insert_name':  _s(data.get('insert_name')) or None,
            'parallel_name': _s(data.get('parallel_name')) or None,
            'is_auto':      bool(data.get('is_auto', False)),
            'is_relic':     bool(data.get('is_relic', False)),
            'is_patch':     bool(data.get('is_patch', False)),
            'is_rookie':    bool(data.get('is_rookie', False)),
            'is_numbered':  bool(data.get('print_run')),
            'print_run':    data.get('print_run') or None,
            'card_notes':   _s(data.get('card_notes')) or None,
        }

        item_price    = _dec(data.get('item_price'))
        tax_paid      = _dec(data.get('tax_paid'))
        shipping_paid = _dec(data.get('shipping_paid'))
        if any(v is not None for v in [item_price, tax_paid, shipping_paid]):
            cost_basis = (item_price or 0) + (tax_paid or 0) + (shipping_paid or 0)
        else:
            cost_basis = _dec(data.get('cost_basis'))

        inv_data = {
            'status':          (_s(data.get('status')) or 'OWNED').upper(),
            'acquisition_date': data.get('acquisition_date') or None,
            'item_price':      item_price,
            'tax_paid':        tax_paid,
            'shipping_paid':   shipping_paid,
            'cost_basis':      cost_basis,
            'comp_low':        _dec(data.get('comp_low')),
            'comp_avg':        _dec(data.get('comp_avg')),
            'comp_high':       _dec(data.get('comp_high')),
            'inventory_notes': _s(data.get('inventory_notes')) or None,
        }

        conn = get_connection()
        row = get_inventory_by_id(conn, inventory_id)
        if not row:
            return jsonify({'success': False, 'error': 'Not found'}), 404

        update_card(conn, row['card_id'], card_data)
        update_inventory(conn, inventory_id, inv_data)
        conn.commit()

        return jsonify({'success': True, 'message': 'Entry updated'})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        close_connection(conn)


@app.route('/inventory', methods=['GET'])
def inventory_page():
    """Render the inventory view page."""
    return render_template('inventory.html')


@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    """Return all inventory rows from v_inventory_detail as JSON."""
    status_filter = request.args.get('status', '').upper() or None
    conn = None
    try:
        conn = get_connection()
        query = """
            SELECT inventory_id, status, acquisition_date, card_id, sport, year,
                   manufacturer, set_name, insert_name, card_number, player_name, team,
                   parallel_name, is_auto, is_relic, is_patch, is_rookie,
                   is_numbered, print_run, is_graded, grading_company, grade,
                   grade_qualifier, cost_basis, item_price, tax_paid, shipping_paid,
                   comp_low, comp_avg, comp_high, unrealized_gain_avg, inventory_notes
            FROM v_inventory_detail
            WHERE 1=1
        """
        params = []
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        query += " ORDER BY player_name, year DESC"

        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()

        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
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


_ALLOWED_IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'webp', 'gif', 'heic', 'heif'}

@app.route('/api/inventory/<int:inventory_id>/photos', methods=['POST'])
def upload_photos(inventory_id):
    conn = None
    try:
        conn = get_connection()
        if not get_inventory_by_id(conn, inventory_id):
            return jsonify({'error': 'Not found'}), 404

        photos = _photos_dir()
        updated = {}

        for side in ('front', 'back'):
            f = request.files.get(side)
            if not f or not f.filename:
                continue
            ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
            if ext not in _ALLOWED_IMAGE_EXTS:
                return jsonify({'error': f'Unsupported file type: .{ext}'}), 400
            filename = f'{inventory_id}_{side}.{ext}'
            f.save(str(photos / filename))
            updated[f'{side}_image'] = filename

        if updated:
            update_inventory_photos(conn,
                                    inventory_id,
                                    front_image=updated.get('front_image'),
                                    back_image=updated.get('back_image'))
            conn.commit()

        return jsonify({'success': True, **updated})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        close_connection(conn)


@app.route('/photos/<path:filename>')
def serve_photo(filename):
    safe = os.path.basename(filename)
    return send_from_directory(str(_photos_dir()), safe)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    conn = None
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
    finally:
        close_connection(conn)

@app.route('/api/quit', methods=['POST'])
def quit_app():
    """Shut down the server cleanly from the browser."""
    def _stop():
        time.sleep(0.5)
        os._exit(0)
    threading.Thread(target=_stop, daemon=True).start()
    return jsonify({'status': 'shutting down'})


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found', 'path': request.path}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    init_db()

    print("\n" + "="*60)
    print("Card Inventory")
    print("="*60)
    print("Open:   http://localhost:8000/form")
    print("Health: http://localhost:8000/api/health")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=8000, debug=False)
