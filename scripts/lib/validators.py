"""
Input validation for card data.
Enforces database constraints and enum values.
"""

class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass

VALID_SPORTS = {'baseball', 'basketball', 'football', 'hockey', 'soccer', 'tennis', 'golf', 'other'}

def validate_card_data(card_data):
    """
    Validate card data before insertion.
    Raises ValidationError if validation fails.
    Returns: validated card_data dict (cleaned)
    """
    errors = []
    
    # Required fields
    if not card_data.get('sport'):
        errors.append("sport is required")
    elif card_data['sport'].lower() not in VALID_SPORTS:
        errors.append(f"sport must be one of: {', '.join(sorted(VALID_SPORTS))}")
    else:
        card_data['sport'] = card_data['sport'].lower()
    
    if not card_data.get('year'):
        errors.append("year is required")
    else:
        try:
            year = int(card_data['year'])
            if year < 1900 or year > 2100:
                errors.append("year must be between 1900 and 2100")
            card_data['year'] = year
        except ValueError:
            errors.append("year must be a number")
    
    if not card_data.get('manufacturer'):
        errors.append("manufacturer is required")
    
    if not card_data.get('set_name'):
        errors.append("set_name is required")
    
    if not card_data.get('player_name'):
        errors.append("player_name is required")
    
    # Optional fields with validation
    if card_data.get('print_run'):
        try:
            print_run = int(card_data['print_run'])
            if print_run <= 0:
                errors.append("print_run must be greater than 0")
            card_data['print_run'] = print_run
        except ValueError:
            errors.append("print_run must be a number")
    
    # Boolean fields
    for field in ['is_auto', 'is_relic', 'is_patch', 'is_rookie', 'is_numbered', 'is_base']:
        if field in card_data:
            if isinstance(card_data[field], bool):
                continue
            if isinstance(card_data[field], str):
                card_data[field] = card_data[field].lower() in {'true', '1', 'yes', 'on'}
    
    if errors:
        raise ValidationError("\n".join(errors))
    
    return card_data

def validate_csv_row(row):
    """
    Validate a single CSV row.
    Returns: (is_valid: bool, card_data: dict or None, error_message: str or None)
    """
    try:
        # Expected CSV columns (required)
        required_cols = {'sport', 'year', 'manufacturer', 'set_name', 'player_name'}
        missing = required_cols - set(row.keys())
        if missing:
            return False, None, f"Missing required columns: {', '.join(missing)}"
        
        # Build card data from row
        card_data = {
            'sport': row['sport'].strip(),
            'year': row['year'].strip(),
            'manufacturer': row['manufacturer'].strip(),
            'set_name': row['set_name'].strip(),
            'player_name': row['player_name'].strip(),
            'card_number': row.get('card_number', '').strip() or None,
            'team': row.get('team', '').strip() or None,
            'parallel_name': row.get('parallel_name', '').strip() or None,
            'insert_name': row.get('insert_name', '').strip() or None,
            'is_auto': row.get('is_auto', 'false').strip().lower() in {'true', '1', 'yes'},
            'is_relic': row.get('is_relic', 'false').strip().lower() in {'true', '1', 'yes'},
            'is_patch': row.get('is_patch', 'false').strip().lower() in {'true', '1', 'yes'},
            'is_rookie': row.get('is_rookie', 'false').strip().lower() in {'true', '1', 'yes'},
            'is_numbered': row.get('is_numbered', 'false').strip().lower() in {'true', '1', 'yes'},
            'print_run': row.get('print_run', '').strip() or None,
            'notes': row.get('notes', '').strip() or None,
        }
        
        # Validate
        validate_card_data(card_data)
        return True, card_data, None
    except ValidationError as e:
        return False, None, str(e)
    except Exception as e:
        return False, None, f"CSV parsing error: {e}"
