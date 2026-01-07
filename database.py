'''
This module handles all interactions with the SQLite database.
'''
import sqlite3
from typing import List, Dict, Any

DB_FILE = 'leboncoin_ads.db'

def initialize_db():
    """
    Initializes the database and creates/updates the 'ads' table.
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Create table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ads (
                id TEXT PRIMARY KEY,
                search_name TEXT NOT NULL,
                title TEXT NOT NULL,
                price REAL,
                location TEXT,
                date TEXT,
                url TEXT UNIQUE,
                description TEXT
            )
        ''')
        # Add the new ai_summary column if it doesn't exist (for migration)
        try:
            cursor.execute("ALTER TABLE ads ADD COLUMN ai_summary TEXT")
        except sqlite3.OperationalError:
            # Column already exists, which is fine.
            pass
        conn.commit()

def add_ad(ad_data: Dict[str, Any]):
    """
    Inserts a new ad into the database. Returns True if insertion is successful.
    The dictionary must contain the 'ai_summary' key.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ads (id, search_name, title, price, location, date, url, description, ai_summary)
                VALUES (:id, :search_name, :title, :price, :location, :date, :url, :description, :ai_summary)
            ''', ad_data)
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        # This happens if the ad ID or URL already exists, which is expected.
        return False
    except Exception as e:
        print(f"[Database Error] Failed to add ad: {e}")
        return False

def get_all_ad_ids() -> List[str]:
    """
    Retrieves a list of all ad IDs currently in the database.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM ads')
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"[Database Error] Failed to get ad IDs: {e}")
        return []

def get_all_ads() -> List[Dict[str, Any]]:
    """
    Retrieves all ads from the database for analysis.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM ads')
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[Database Error] Failed to get all ads: {e}")
        return []

# Initialize or update the database as soon as this module is loaded
initialize_db()