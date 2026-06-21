#!/usr/bin/env python3
"""
Card inventory CLI tool.
Supports interactive card entry and bulk CSV imports.

Usage:
  python import.py add-card                    # Interactive single card entry
  python import.py csv --file cards.csv       # Bulk CSV import
"""

import sys
import csv
import argparse
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from lib.db import get_connection, check_duplicate_card, insert_card, log_import, close_connection
from lib.validators import validate_card_data, validate_csv_row, ValidationError, VALID_SPORTS

def prompt_card_entry():
    """
    Interactive prompt for single card entry.
    Returns: card_data dict
    """
    print("\n" + "="*60)
    print("ADD NEW CARD - Interactive Entry")
    print("="*60)
    
    card_data = {}
    
    # Sport
    print(f"\nAvailable sports: {', '.join(sorted(VALID_SPORTS))}")
    while True:
        sport = input("Sport [required]: ").strip()
        if sport.lower() in VALID_SPORTS:
            card_data['sport'] = sport.lower()
            break
        print(f"  ❌ Invalid sport. Must be one of: {', '.join(sorted(VALID_SPORTS))}")
    
    # Year
    while True:
        try:
            year = int(input("Year [required]: ").strip())
            if 1900 <= year <= 2100:
                card_data['year'] = year
                break
            print("  ❌ Year must be between 1900 and 2100")
        except ValueError:
            print("  ❌ Year must be a number")
    
    # Manufacturer
    card_data['manufacturer'] = input("Manufacturer [required, e.g. 'Topps']: ").strip()
    if not card_data['manufacturer']:
        print("  ⚠️  Using placeholder 'Unknown'")
        card_data['manufacturer'] = 'Unknown'
    
    # Set name
    card_data['set_name'] = input("Set name [required, e.g. 'Chrome Rookie']: ").strip()
    if not card_data['set_name']:
        print("  ⚠️  Using placeholder 'Unknown'")
        card_data['set_name'] = 'Unknown'
    
    # Player name
    card_data['player_name'] = input("Player name [required]: ").strip()
    if not card_data['player_name']:
        print("  ❌ Player name is required")
        return prompt_card_entry()
    
    # Card number (optional)
    card_data['card_number'] = input("Card number [optional]: ").strip() or None
    
    # Team (optional)
    card_data['team'] = input("Team [optional]: ").strip() or None
    
    # Parallel name (optional)
    card_data['parallel_name'] = input("Parallel name [optional, e.g. 'Gold Refractor']: ").strip() or None
    
    # Flags
    card_data['is_auto'] = input("Autograph? (y/n) [default: n]: ").strip().lower() in {'y', 'yes', '1'}
    card_data['is_relic'] = input("Relic/Memorabilia? (y/n) [default: n]: ").strip().lower() in {'y', 'yes', '1'}
    card_data['is_patch'] = input("Patch relic? (y/n) [default: n]: ").strip().lower() in {'y', 'yes', '1'}
    card_data['is_rookie'] = input("Rookie card? (y/n) [default: n]: ").strip().lower() in {'y', 'yes', '1'}
    
    # Print run
    print_run_str = input("Print run [optional, e.g. '25' for /25]: ").strip()
    if print_run_str:
        try:
            card_data['print_run'] = int(print_run_str)
        except ValueError:
            print("  ⚠️  Invalid print run, skipping")
    
    # Notes
    card_data['notes'] = input("Notes [optional]: ").strip() or None
    
    return card_data

def add_card_interactive():
    """Interactive single card addition."""
    conn = None
    try:
        card_data = prompt_card_entry()
        
        # Validate
        try:
            card_data = validate_card_data(card_data)
        except ValidationError as e:
            print(f"\n❌ Validation error:\n{e}")
            return False
        
        # Connect to database
        conn = get_connection()
        
        # Check for duplicate
        print("\n🔍 Checking for duplicates...")
        is_duplicate, existing_card_id = check_duplicate_card(conn, card_data)
        if is_duplicate:
            print(f"⚠️  Card already exists (ID: {existing_card_id})")
            print(f"   Sport: {card_data['sport']}, Year: {card_data['year']}")
            print(f"   Set: {card_data['set_name']}, Card #: {card_data.get('card_number')}")
            print(f"   Player: {card_data['player_name']}")
            
            response = input("\nAdd anyway? (y/n): ").strip().lower()
            if response not in {'y', 'yes'}:
                print("❌ Cancelled.")
                return False
        
        # Insert
        print("\n💾 Inserting card...")
        card_id = insert_card(conn, card_data, is_test=False)
        
        # Log import
        log_import(conn, 'CLI', record_count=1, success_count=1, error_count=0, status='SUCCESS')
        
        print(f"\n✅ Card added successfully! (ID: {card_id})")
        print(f"   {card_data['sport'].title()} | {card_data['year']} {card_data['manufacturer']} {card_data['set_name']}")
        print(f"   {card_data['player_name']}")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    finally:
        close_connection(conn)

def add_cards_from_csv(csv_file):
    """Bulk import from CSV file."""
    conn = None
    try:
        csv_path = Path(csv_file)
        if not csv_path.exists():
            print(f"❌ File not found: {csv_file}")
            return False
        
        conn = get_connection()
        
        print(f"\n📁 Reading {csv_file}...")
        inserted = 0
        skipped = 0
        duplicates = 0
        errors = 0
        error_rows = []
        
        start_time = time.time()
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            
            if not reader.fieldnames:
                print("❌ CSV file is empty")
                return False
            
            total_rows = sum(1 for _ in open(csv_path)) - 1  # -1 for header
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (1=header)
                # Validate row
                is_valid, card_data, error_msg = validate_csv_row(row)
                
                if not is_valid:
                    errors += 1
                    error_rows.append((row_num, error_msg))
                    print(f"  Row {row_num}: ⚠️  {error_msg}")
                    continue
                
                # Check for duplicate
                is_duplicate, existing_id = check_duplicate_card(conn, card_data)
                if is_duplicate:
                    duplicates += 1
                    skipped += 1
                    print(f"  Row {row_num}: 🔄 Duplicate (ID: {existing_id}), skipping")
                    continue
                
                # Insert
                try:
                    card_id = insert_card(conn, card_data, is_test=False)
                    inserted += 1
                    print(f"  Row {row_num}: ✅ Inserted (ID: {card_id}) - {card_data['player_name']}")
                except Exception as e:
                    errors += 1
                    error_rows.append((row_num, str(e)))
                    print(f"  Row {row_num}: ❌ {e}")
        
        elapsed = time.time() - start_time
        
        # Determine status
        status = 'SUCCESS' if errors == 0 else ('PARTIAL' if inserted > 0 else 'FAILED')
        
        # Log import
        log_import(
            conn, 
            'CSV', 
            file_name=csv_path.name, 
            record_count=total_rows,
            success_count=inserted,
            error_count=errors + duplicates,
            status=status,
            error_message=f"{errors} errors, {duplicates} duplicates" if errors or duplicates else None,
            execution_time=int(elapsed)
        )
        
        # Summary
        print("\n" + "="*60)
        print("CSV IMPORT SUMMARY")
        print("="*60)
        print(f"Total rows:     {total_rows}")
        print(f"Inserted:       {inserted} ✅")
        print(f"Duplicates:     {duplicates} 🔄")
        print(f"Errors:         {errors} ❌")
        print(f"Time:           {elapsed:.2f}s")
        print(f"Status:         {status}")
        
        if error_rows:
            print(f"\nError details (first 5):")
            for row_num, error_msg in error_rows[:5]:
                print(f"  Row {row_num}: {error_msg}")
        
        return errors == 0
        
    except Exception as e:
        print(f"❌ CSV import failed: {e}")
        return False
    finally:
        close_connection(conn)

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Card inventory import tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  python import.py add-card              # Interactive single card entry
  python import.py csv --file cards.csv  # Bulk CSV import from file
  
CSV format (header required):
  sport,year,manufacturer,set_name,card_number,player_name,team,parallel_name,is_auto,is_relic,is_patch,is_rookie,print_run,notes
  basketball,2003,Topps,Rookie,221,LeBron James,Cleveland Cavaliers,Gold Refractor,true,false,false,true,,None
'''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # add-card subcommand
    subparsers.add_parser('add-card', help='Add card interactively')
    
    # csv subcommand
    csv_parser = subparsers.add_parser('csv', help='Import cards from CSV file')
    csv_parser.add_argument('--file', required=True, help='Path to CSV file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'add-card':
        success = add_card_interactive()
        sys.exit(0 if success else 1)
    elif args.command == 'csv':
        success = add_cards_from_csv(args.file)
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
