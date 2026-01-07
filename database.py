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
        # Table des annonces
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
                ai_summary TEXT,
                ai_score REAL,
                ai_tips TEXT,
                image_url TEXT,
                is_pro INTEGER DEFAULT 0,
                lat REAL,
                lng REAL,
                category TEXT
            )
        ''')
        # Table des veilles (Searches)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS searches (
                name TEXT PRIMARY KEY,
                query_text TEXT NOT NULL,
                city TEXT,
                radius INTEGER DEFAULT 10,
                lat REAL,
                lng REAL,
                zip_code TEXT,
                price_min REAL,
                price_max REAL,
                category TEXT,
                last_run TEXT,
                is_active INTEGER DEFAULT 1,
                ai_context TEXT
            )
        ''')
        conn.commit()

        try:
            cursor.execute("SELECT ai_context FROM searches LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE searches ADD COLUMN ai_context TEXT")
            conn.commit()

        # Migrations (ensure columns exist if table was already there)
        try:
            cursor.execute("SELECT ai_score FROM ads LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE ads ADD COLUMN ai_score REAL")
            cursor.execute("ALTER TABLE ads ADD COLUMN ai_tips TEXT")
            cursor.execute("ALTER TABLE ads ADD COLUMN lat REAL")
            cursor.execute("ALTER TABLE ads ADD COLUMN lng REAL")
            cursor.execute("ALTER TABLE ads ADD COLUMN category TEXT")
            conn.commit()

        try:
            cursor.execute("SELECT lat FROM searches LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE searches ADD COLUMN lat REAL")
            cursor.execute("ALTER TABLE searches ADD COLUMN lng REAL")
            cursor.execute("ALTER TABLE searches ADD COLUMN zip_code TEXT")
            conn.commit()

def add_ad(ad_data: Dict[str, Any]):
    """
    Inserts a new ad into the database. Robust with defaults.
    """
    # Force defaults for missing keys to avoid SQL errors
    defaults = {
        'search_name': 'Unknown',
        'title': 'No Title',
        'price': 0,
        'location': 'Unknown',
        'date': '',
        'url': '',
        'description': '',
        'ai_summary': None,
        'ai_score': None,
        'ai_tips': None,
        'image_url': None,
        'is_pro': 0,
        'lat': None,
        'lng': None,
        'category': None
    }
    data = {**defaults, **ad_data}
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ads (id, search_name, title, price, location, date, url, description, ai_summary, ai_score, ai_tips, image_url, is_pro, lat, lng, category)
                VALUES (:id, :search_name, :title, :price, :location, :date, :url, :description, :ai_summary, :ai_score, :ai_tips, :image_url, :is_pro, :lat, :lng, :category)
            ''', data)
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
                SET ai_summary = :summary, ai_score = :score, ai_tips = :tips
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

# --- Gestion des veilles (Searches) ---

def save_search(search_data: Dict[str, Any]):
    """Saves or updates a search configuration."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO searches (name, query_text, city, radius, lat, lng, zip_code, price_min, price_max, category, last_run, is_active, ai_context)
                VALUES (:name, :query_text, :city, :radius, :lat, :lng, :zip_code, :price_min, :price_max, :category, :last_run, :is_active, :ai_context)
            ''', search_data)
            conn.commit()
        return True
    except Exception as e:
        print(f"[Database Error] Failed to save search: {e}")
        return False

def get_active_searches() -> List[Dict[str, Any]]:
    """Retrieves all active search configurations."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM searches WHERE is_active = 1')
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[Database Error] Failed to get searches: {e}")
        return []

def delete_search(name: str):
    """Deletes a search configuration."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM searches WHERE name = ?', (name,))
            conn.commit()
        return True
    except Exception as e:
        print(f"[Database Error] Failed to delete search: {e}")
        return False

# Initialize or update the database
initialize_db()
