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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ads (
                id TEXT PRIMARY KEY,
                search_name TEXT NOT NULL,
                title TEXT NOT NULL,
                price REAL,
                location TEXT,
                date TEXT,
                url TEXT UNIQUE,
                description TEXT,
                ai_summary TEXT
            )
        ''')
        try:
            cursor.execute("SELECT ai_summary FROM ads LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE ads ADD COLUMN ai_summary TEXT")
        conn.commit()

def add_ad(ad_data: Dict[str, Any]):
    """
    Inserts a new ad into the database. The summary can be None.
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
        return False
    except Exception as e:
        print(f"[Database Error] Failed to add ad: {e}")
        return False

def get_ads_without_summary() -> List[Dict[str, Any]]:
    """
    Retrieves all ads that do not have an AI summary yet.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT id, title, description FROM ads WHERE ai_summary IS NULL OR ai_summary = ""')
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[Database Error] Failed to get ads for summary: {e}")
        return []

def update_summaries_in_batch(summaries: List[Dict[str, str]]):
    """
    Updates the ai_summary for multiple ads in a single transaction.
    Expects a list of dictionaries, each with 'id' and 'summary'.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.executemany('''
                UPDATE ads
                SET ai_summary = :summary
                WHERE id = :id
            ''', summaries)
            conn.commit()
            print(f"Successfully updated {len(summaries)} summaries in the database.")
    except Exception as e:
        print(f"[Database Error] Failed to update summaries in batch: {e}")

def get_all_ad_ids() -> List[str]:
    # ... (rest of the file is similar)
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM ads')
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"[Database Error] Failed to get ad IDs: {e}")
        return []

def get_all_ads() -> List[Dict[str, Any]]:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM ads')
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[Database Error] Failed to get all ads: {e}")
        return []

# Initialize or update the database
initialize_db()