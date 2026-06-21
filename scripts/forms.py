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

from lib.db import get_connection, check_duplicate_card, insert_card, log_import, close_connection
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
        
        # Prepare card data
        card_data = {
            'sport': data.get('sport', '').strip(),
            'year': data.get('year', '').strip(),
            'manufacturer': data.get('manufacturer', '').strip(),
            'set_name': data.get('set_name', '').strip(),
            'player_name': data.get('player_name', '').strip(),
            'card_number': data.get('card_number', '').strip() or None,
            'team': data.get('team', '').strip() or None,
            'parallel_name': data.get('parallel_name', '').strip() or None,
            'insert_name': data.get('insert_name', '').strip() or None,
            'is_auto': data.get('is_auto', False),
            'is_relic': data.get('is_relic', False),
            'is_patch': data.get('is_patch', False),
            'is_rookie': data.get('is_rookie', False),
            'is_numbered': data.get('is_numbered', False),
            'print_run': data.get('print_run', '').strip() or None,
            'notes': data.get('notes', '').strip() or None,
        }
        
        # Validate
        try:
            card_data = validate_card_data(card_data)
        except ValidationError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        # Connect to database
        conn = get_connection()
        
        # Check for duplicate
        is_duplicate, existing_id = check_duplicate_card(conn, card_data)
        if is_duplicate:
            return jsonify({
                'success': False,
                'error': 'Card already exists in inventory',
                'existing_card_id': existing_id,
                'duplicate': True
            }), 409  # Conflict
        
        # Insert
        start_time = time.time()
        card_id = insert_card(conn, card_data, is_test=False)
        elapsed = time.time() - start_time
        
        # Log import
        log_import(
            conn, 
            'WEB_FORM', 
            record_count=1, 
            success_count=1, 
            error_count=0, 
            status='SUCCESS',
            execution_time=int(elapsed)
        )
        
        return jsonify({
            'success': True,
            'message': 'Card added successfully',
            'card_id': card_id,
            'card_data': {
                'player_name': card_data['player_name'],
                'sport': card_data['sport'],
                'year': card_data['year'],
                'set_name': card_data['set_name']
            }
        }), 201
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return jsonify({'success': False, 'error': str(e)}), 500
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
