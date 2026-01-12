'''
This module handles all interactions with the SQLite database.
'''
import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Any

DB_FILE = os.getenv('DB_PATH', 'leboncoin_ads.db')

def initialize_db():
    """
    Initializes the database and creates/updates the 'ads' table.
    """
    print(f"[Database] Initializing database at: {os.path.abspath(DB_FILE)}")
    try:
        with sqlite3.connect(DB_FILE) as conn:
            # Enable WAL mode for concurrency (Readers don't block Writers)
            conn.execute('PRAGMA journal_mode=WAL;')
            cursor = conn.cursor()
            # Table des utilisateurs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password_hash TEXT,
                    google_api_key TEXT,
                    discord_webhook TEXT,
                    created_at TEXT
                )
            ''')

            # Table des annonces (modifiée pour support multi-compte)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ads (
                    id TEXT,
                    user_id INTEGER,
                    search_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    price REAL,
                    location TEXT,
                    date TEXT,
                    url TEXT,
                    description TEXT,
                    ai_summary TEXT,
                    ai_score REAL,
                    ai_tips TEXT,
                    image_url TEXT,
                    is_pro INTEGER DEFAULT 0,
                    lat REAL,
                    lng REAL,
                    category TEXT,
                    source TEXT DEFAULT 'LBC',
                    is_hidden INTEGER DEFAULT 0,
                    PRIMARY KEY (id, user_id)
                )
            ''')

            # Table de feedback
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    type TEXT,
                    message TEXT,
                    created_at TEXT
                )
            ''')


            # Table des veilles (Searches)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS searches (
                    name TEXT,
                    user_id INTEGER,
                    query_text TEXT NOT NULL,
                    city TEXT,
                    radius INTEGER DEFAULT 10,
                    lat REAL,
                    lng REAL,
                    zip_code TEXT,
                    locations TEXT,
                    price_min REAL,
                    price_max REAL,
                    category TEXT,
                    last_run TEXT,
                    is_active INTEGER DEFAULT 1,
                    ai_context TEXT,
                    refresh_mode TEXT DEFAULT 'manual',
                    refresh_interval INTEGER DEFAULT 60,
                    platforms TEXT,
                    last_viewed TEXT,
                    discord_webhook TEXT,
                    deep_search INTEGER DEFAULT 0,
                    PRIMARY KEY (name, user_id)
                )
            ''')

            
            # Table de l'historique des prix
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    ad_id TEXT,
                    user_id INTEGER,
                    price REAL,
                    date TEXT,
                    FOREIGN KEY(ad_id, user_id) REFERENCES ads(id, user_id)
                )
            ''')
            
            # Table des paramètres verticaux (Settings)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            conn.commit()


            try:
                cursor.execute("SELECT user_id FROM searches LIMIT 1")
            except sqlite3.OperationalError:

                # Add columns for existing installations
                columns_to_add = [
                    ("searches", "user_id", "INTEGER DEFAULT 1"),
                    ("ads", "user_id", "INTEGER DEFAULT 1"),
                    ("price_history", "user_id", "INTEGER DEFAULT 1")
                ]
                for table, col, def_val in columns_to_add:
                    try:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {def_val}")
                    except: pass
                conn.commit()

            # ALWAYS ensure a default admin user exists if none
            hashed_pw = security.generate_password_hash('admin')
            cursor.execute("INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (1, 'admin', ?)", (hashed_pw,))
            conn.commit()


            try:
                cursor.execute("SELECT google_api_key FROM users LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE users ADD COLUMN google_api_key TEXT")
                cursor.execute("ALTER TABLE users ADD COLUMN discord_webhook TEXT")
                conn.commit()


            # Ensure columns exist in case recreate didn't happen
            try: cursor.execute("ALTER TABLE searches ADD COLUMN user_id INTEGER DEFAULT 1")
            except: pass
            try: cursor.execute("ALTER TABLE ads ADD COLUMN user_id INTEGER DEFAULT 1")
            except: pass
            
            try: cursor.execute("ALTER TABLE searches ADD COLUMN deep_search INTEGER DEFAULT 0")
            except: pass
            
            try: cursor.execute("ALTER TABLE ads ADD COLUMN is_hidden INTEGER DEFAULT 0")
            except: pass
            
            conn.commit()

    except Exception as e:

        print(f"[Database Error] Critical failure during initialize_db: {e}")
        import traceback
        traceback.print_exc()

import werkzeug.security as security

def create_user(username, password):
    """Creates a new user with hashed password."""
    try:
        pw_hash = security.generate_password_hash(password)
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)',
                           (username, pw_hash, datetime.now().isoformat()))
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return -1 # Username already exists
    except Exception as e:
        print(f"[Database Error] create_user failed: {e}")
        return None

def authenticate_user(username, password):
    """Authenticates a user and returns user info if success."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            if user and security.check_password_hash(user['password_hash'], password):
                return dict(user)
    except Exception as e:
        print(f"[Database Error] authenticate_user failed: {e}")
    return None

def get_user_by_id(user_id):
    """Retrieves a user by ID."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            return dict(user) if user else None
    except Exception as e:
        print(f"[Database Error] get_user_by_id failed: {e}")
        return None

def update_user_settings(user_id, settings: Dict[str, Any]):
    """Updates user-specific settings (API key, Webhook)."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            allowed = ['google_api_key', 'discord_webhook']
            for k, v in settings.items():
                if k in allowed:
                    cursor.execute(f"UPDATE users SET {k} = ? WHERE id = ?", (v, user_id))
            conn.commit()
        return True
    except Exception as e:
        print(f"[Database Error] update_user_settings failed: {e}")
        return False

def add_ad(ad_data: Dict[str, Any], user_id: int = 1):
    """
    Inserts a new ad into the database. Robust with defaults.
    """
    # Force defaults for missing keys to avoid SQL errors
    defaults = {
        'id': 'unknown_' + str(datetime.now().timestamp()),
        'user_id': user_id,
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
        'category': None,
        'source': 'LBC'
    }
    data = {**defaults, **ad_data}
    data['user_id'] = user_id
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Check for price change (specific to this user)
            ad_id = data.get('id', 'unknown')
            cursor.execute("SELECT price FROM ads WHERE id = ? AND user_id = ?", (ad_id, user_id))
            existing = cursor.fetchone()
            price_dropped = False
            
            if existing:
                old_price = existing[0]
                new_price = data.get('price', 0)
                if new_price and old_price and new_price < old_price:
                    price_dropped = True
                    # Record in history
                    cursor.execute("INSERT INTO price_history (ad_id, user_id, price, date) VALUES (?, ?, ?, ?)", 
                                 (ad_id, user_id, old_price, datetime.now().isoformat()))
                
                # Update existing ad
                # Dynamically build UPDATE to allow optional fields like is_hidden
                update_fields = [
                    "search_name = :search_name", "title = :title", "price = :price",
                    "location = :location", "date = :date", "url = :url", "description = :description",
                    "is_pro = :is_pro", "lat = :lat", "lng = :lng", "category = :category", "source = :source"
                ]
                
                # Only update is_hidden if explicitly provided (to avoid unhiding on auto-scrape)
                if 'is_hidden' in data:
                    update_fields.append("is_hidden = :is_hidden")

                sql = f"UPDATE ads SET {', '.join(update_fields)} WHERE id = :id AND user_id = :user_id"
                cursor.execute(sql, data)
                is_new = False
            else:
                # Insert new ad
                cursor.execute('''
                    INSERT INTO ads (id, user_id, search_name, title, price, location, date, url, description, ai_summary, ai_score, ai_tips, image_url, is_pro, lat, lng, category, source)
                    VALUES (:id, :user_id, :search_name, :title, :price, :location, :date, :url, :description, :ai_summary, :ai_score, :ai_tips, :image_url, :is_pro, :lat, :lng, :category, :source)
                ''', data)
                is_new = True
            
            conn.commit()
        return True, price_dropped, is_new
    except Exception as e:
        print(f"[Database Error] Failed to add/update ad: {e}")
        return False, False, False

def get_price_history(ad_id: str, user_id: int = 1) -> List[Dict[str, Any]]:
    """Retrieves the price history for a specific ad."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT price, date FROM price_history WHERE ad_id = ? AND user_id = ? ORDER BY date DESC', (ad_id, user_id))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[Database Error] Failed to get price history: {e}")
        return []

def get_ads_without_summary(user_id: int = 1) -> List[Dict[str, Any]]:
    """
    Retrieves all ads for a user that do not have an AI summary yet.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ads.* 
                FROM ads 
                LEFT JOIN searches ON ads.search_name = searches.name AND ads.user_id = searches.user_id
                WHERE ads.user_id = ? 
                  AND (ads.ai_summary IS NULL OR ads.ai_summary = "")
                  AND (searches.is_active = 1 OR ads.source = 'MANUAL')
                ORDER BY CASE WHEN ads.source = 'MANUAL' THEN 0 ELSE 1 END, ads.date DESC
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[Database Error] Failed to get ads for summary: {e}")
        return []

def update_summaries_in_batch(summaries: List[Dict[str, str]], user_id: int = 1):
    """
    Updates the ai_summary for multiple ads in a single transaction.
    """
    try:
        enriched = [dict(s, user_id=user_id) for s in summaries]
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.executemany('''
                UPDATE ads
                SET ai_summary = :ai_summary, ai_score = :ai_score, ai_tips = :ai_tips
                WHERE id = :id AND user_id = :user_id
            ''', enriched)
            conn.commit()
    except Exception as e:
        print(f"[Database Error] Failed to update summaries in batch: {e}")

def get_all_ad_ids(user_id: int = 1) -> List[str]:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM ads WHERE user_id = ?', (user_id,))
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"[Database Error] Failed to get ad IDs: {e}")
        return []

def get_all_ads(user_id: int = 1) -> List[Dict[str, Any]]:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM ads WHERE user_id = ? AND is_hidden = 0', (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:

        print(f"[Database Error] Failed to get all ads: {e}")
        return []

# --- Gestion des veilles (Searches) ---

def save_search(search_data: Dict[str, Any], user_id: int = 1):
    """Saves or updates a search configuration."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            defaults = {
                'user_id': user_id,
                'city': None, 'radius': 10, 'lat': None, 'lng': None, 'zip_code': None,
                'locations': '[]', 'price_min': None, 'price_max': None, 'category': None, 
                'last_run': None, 'is_active': 1, 'ai_context': None, 'refresh_mode': 'manual',
                'refresh_interval': 60, 'platforms': '{}', 'last_viewed': None, 'discord_webhook': None,
                'deep_search': 0
            }
            cursor.execute('''
                INSERT OR REPLACE INTO searches (user_id, name, query_text, city, radius, lat, lng, zip_code, locations, price_min, price_max, category, last_run, is_active, ai_context, refresh_mode, refresh_interval, platforms, last_viewed, discord_webhook, deep_search)
                VALUES (:user_id, :name, :query_text, :city, :radius, :lat, :lng, :zip_code, :locations, :price_min, :price_max, :category, :last_run, :is_active, :ai_context, :refresh_mode, :refresh_interval, :platforms, :last_viewed, :discord_webhook, :deep_search)
            ''', {**defaults, **search_data, 'user_id': user_id})

            conn.commit()
        return True
    except Exception as e:
        print(f"[Database Error] Failed to save search: {e}")
        return False


def update_search_last_run(name: str, user_id: int = 1):
    """Updates the last_run timestamp for a search."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE searches SET last_run = ? WHERE name = ? AND user_id = ?', (datetime.now().isoformat(), name, user_id))
            conn.commit()
        return True
    except Exception as e:
        print(f"[Database Error] Failed to update last_run: {e}")
        return False

def hide_ad(ad_id: str, user_id: int = 1):
    """Marks an ad as hidden (soft delete)."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE ads SET is_hidden = 1 WHERE id = ? AND user_id = ?', (ad_id, user_id))
            conn.commit()
        return True
    except Exception as e:
        print(f"[Database Error] Failed to hide ad: {e}")
        return False

def move_ads_to_search(ad_ids: List[str], target_search: str, user_id: int = 1):
    """Updates the search_name for a batch of ads."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # SQLite doesn't have an easy "WHERE IN" with list parameter, so we build it dynamically or use loop/executemany
            # actually executemany is for many updates. Here we want one update for many IDs.
            # Easiest is to execute one by one or formatted string
            
            placeholders = ','.join('?' for _ in ad_ids)
            sql = f'UPDATE ads SET search_name = ? WHERE user_id = ? AND id IN ({placeholders})'
            cursor.execute(sql, [target_search, user_id] + ad_ids)
            conn.commit()
        return True
    except Exception as e:
        print(f"[Database Error] Failed to move ads: {e}")
        return False


def update_search_settings(name: str, settings: Dict[str, Any], user_id: int = 1):
    """Updates specific settings for a search dynamically."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            allowed_keys = [
                'ai_context', 'refresh_mode', 'refresh_interval', 
                'platforms', 'discord_webhook', 'is_active', 'deep_search'
            ]

            
            updates = []
            params = {'name': name, 'user_id': user_id}
            
            for key in allowed_keys:
                if key in settings:
                    updates.append(f"{key} = :{key}")
                    params[key] = settings[key]
            
            if not updates:
                return True
                
            query = f"UPDATE searches SET {', '.join(updates)} WHERE name = :name AND user_id = :user_id"
            cursor.execute(query, params)
            conn.commit()
        return True
    except Exception as e:
        print(f"[Database Error] Failed to update settings: {e}")
        return False

def get_ads_by_ids(ad_ids: List[str], user_id: int = 1) -> List[Dict[str, Any]]:
    """Retrieves specific ads by their IDs."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            placeholders = ', '.join(['?'] * len(ad_ids))
            query = f'SELECT * FROM ads WHERE user_id = ? AND id IN ({placeholders})'
            cursor.execute(query, [user_id] + ad_ids)
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[Database Error] Failed to get ads by IDs: {e}")
        return []

def get_active_searches(user_id: int = None) -> List[Dict[str, Any]]:
    """Retrieves active searches. If user_id is None, returns ALL active searches (backends)."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if user_id is not None:
                cursor.execute('SELECT * FROM searches WHERE is_active = 1 AND user_id = ?', (user_id,))
            else:
                cursor.execute('SELECT * FROM searches WHERE is_active = 1')
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[Database Error] Failed to get searches: {e}")
        return []

def update_last_viewed(name: str, user_id: int = 1):
    """Updates the last_viewed timestamp for a search."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE searches SET last_viewed = ? WHERE name = ? AND user_id = ?', (datetime.now().isoformat(), name, user_id))
            conn.commit()
        return True
    except Exception as e:
        print(f"[Database Error] Failed to update last_viewed: {e}")
        return False

def get_global_watch_stats(user_id: int = 1) -> Dict[str, Any]:
    """Calculates global stats for all active searches of a user."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM searches WHERE user_id = ?', (user_id,))
            total_watches = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM ads WHERE user_id = ?', (user_id,))
            total_ads = cursor.fetchone()[0]
            
            cursor.execute('SELECT name, last_viewed FROM searches WHERE user_id = ?', (user_id,))
            searches = cursor.fetchall()
            
            new_ads_total = 0
            watch_details = []
            
            for s in searches:
                name = s['name']
                lv = s['last_viewed']
                if lv:
                    cursor.execute('SELECT COUNT(*) FROM ads WHERE search_name = ? AND user_id = ? AND date > ?', (name, user_id, lv))
                else:
                    cursor.execute('SELECT COUNT(*) FROM ads WHERE search_name = ? AND user_id = ?', (name, user_id))
                
                new_count = cursor.fetchone()[0]
                new_ads_total += new_count
                
                cursor.execute('SELECT COUNT(*) FROM ads WHERE search_name = ? AND user_id = ?', (name, user_id))
                total_for_search = cursor.fetchone()[0]
                
                watch_details.append({
                    "name": name,
                    "new_count": new_count,
                    "total_count": total_for_search
                })
                
            return {
                "total_watches": total_watches,
                "total_ads": total_ads,
                "new_ads_total": new_ads_total,
                "details": watch_details
            }
    except Exception as e:
        print(f"[Database Error] Failed to get global stats: {e}")
        return {"total_watches": 0, "total_ads": 0, "new_ads_total": 0, "details": []}

def delete_search(name: str, user_id: int = 1):
    """Deletes a search configuration and its associated ads."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Delete associated ads and price history first
            cursor.execute('DELETE FROM price_history WHERE user_id = ? AND ad_id IN (SELECT id FROM ads WHERE search_name = ? AND user_id = ?)', (user_id, name, user_id))
            cursor.execute('DELETE FROM ads WHERE search_name = ? AND user_id = ?', (name, user_id))
            # Delete the search itself
            cursor.execute('DELETE FROM searches WHERE name = ? AND user_id = ?', (name, user_id))
            conn.commit()
        return True
    except Exception as e:
        print(f"[Database Error] Failed to delete search: {e}")
        return False

def clear_ad_analyses(user_id: int = 1, search_name: str = None, ad_ids: list = None):
    """
    Clears AI summaries, scores, and tips for specified ads or all ads in a search.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            if ad_ids:
                placeholders = ', '.join(['?'] * len(ad_ids))
                cursor.execute(f'''
                    UPDATE ads 
                    SET ai_summary = NULL, ai_score = NULL, ai_tips = NULL 
                    WHERE user_id = ? AND id IN ({placeholders})
                ''', [user_id] + ad_ids)
            elif search_name:
                cursor.execute('''
                    UPDATE ads 
                    SET ai_summary = NULL, ai_score = NULL, ai_tips = NULL 
                    WHERE user_id = ? AND search_name = ?
                ''', (user_id, search_name))
            conn.commit()
        return True
    except Exception as e:
        print(f"[Database Error] Failed to clear analyses: {e}")
        return False

def get_setting(key: str, default: Any = None) -> Any:
    """Retrieves a global setting."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            return row[0] if row else default
    except Exception as e:
        print(f"[Database Error] Failed to get setting {key}: {e}")
        return default

def set_setting(key: str, value: str):
    """Saves a global setting."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
            conn.commit()
        return True
    except Exception as e:
        return False
        
def add_feedback(user_id: int, type: str, message: str):
    """Saves user feedback/bug report."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO feedback (user_id, type, message, created_at) VALUES (?, ?, ?, ?)',
                           (user_id, type, message, datetime.now().isoformat()))
            conn.commit()
        return True
    except Exception as e:
        print(f"[Database Error] Failed to add feedback: {e}")
        return False

# Initialize or update the database
initialize_db()
