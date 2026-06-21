"""
Database utilities for card inventory system.
Handles connections, deduplication, and import logging.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_connection():
    """Create and return a PostgreSQL database connection."""
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', 5432),
            database=os.getenv('POSTGRES_DB', 'card_inventory'),
            user=os.getenv('POSTGRES_USER', 'carduser'),
            password=os.getenv('POSTGRES_PASSWORD', 'changeme')
        )
        return conn
    except Exception as e:
        raise Exception(f"Database connection failed: {e}")

def check_duplicate_card(conn, card_data):
    """
    Check if a card variant already exists in the database.
    Returns: (exists: bool, card_id: int or None)
    """
    query = """
    SELECT card_id FROM cards
    WHERE year = %s
      AND manufacturer = %s
      AND set_name = %s
      AND COALESCE(card_number, '') = %s
      AND COALESCE(parallel_name, '') = %s
      AND is_auto = %s
      AND is_relic = %s
      AND deleted_at IS NULL
    LIMIT 1
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(query, (
                card_data['year'],
                card_data['manufacturer'],
                card_data['set_name'],
                card_data.get('card_number', ''),
                card_data.get('parallel_name', ''),
                card_data.get('is_auto', False),
                card_data.get('is_relic', False)
            ))
            result = cur.fetchone()
            if result:
                return True, result[0]
            return False, None
    except Exception as e:
        raise Exception(f"Duplicate check failed: {e}")

def insert_card(conn, card_data, is_test=False):
    """
    Insert a new card variant into the cards table.
    Returns: card_id
    """
    query = """
    INSERT INTO cards (
        sport, year, manufacturer, set_name, card_number, player_name, team,
        is_base, insert_name, parallel_name, is_auto, is_relic, is_patch,
        is_rookie, is_numbered, print_run, notes, is_test
    )
    VALUES (
        %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s
    )
    RETURNING card_id
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(query, (
                card_data['sport'],
                card_data['year'],
                card_data['manufacturer'],
                card_data['set_name'],
                card_data.get('card_number'),
                card_data['player_name'],
                card_data.get('team'),
                card_data.get('is_base', True),
                card_data.get('insert_name'),
                card_data.get('parallel_name'),
                card_data.get('is_auto', False),
                card_data.get('is_relic', False),
                card_data.get('is_patch', False),
                card_data.get('is_rookie', False),
                card_data.get('is_numbered', False),
                card_data.get('print_run'),
                card_data.get('notes'),
                is_test
            ))
            card_id = cur.fetchone()[0]
            conn.commit()
            return card_id
    except Exception as e:
        conn.rollback()
        raise Exception(f"Card insert failed: {e}")

def log_import(conn, import_method, file_name=None, record_count=0, 
               success_count=0, error_count=0, status='SUCCESS', 
               error_message=None, execution_time=None):
    """
    Log import operation to import_logs table.
    Returns: import_id
    """
    query = """
    INSERT INTO import_logs (
        import_method, file_name, record_count, success_count, error_count,
        status, error_message, execution_time_seconds
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING import_id
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(query, (
                import_method,
                file_name,
                record_count,
                success_count,
                error_count,
                status,
                error_message,
                execution_time
            ))
            import_id = cur.fetchone()[0]
            conn.commit()
            return import_id
    except Exception as e:
        conn.rollback()
        raise Exception(f"Import logging failed: {e}")

def close_connection(conn):
    """Close database connection safely."""
    try:
        if conn:
            conn.close()
    except Exception as e:
        print(f"Warning: Failed to close connection: {e}")
