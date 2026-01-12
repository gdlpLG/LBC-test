
import sqlite3
import os

DB_FILE = 'leboncoin_ads.db'

def check_ads():
    if not os.path.exists(DB_FILE):
        print("DB Not found")
        return

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check total ads
    cursor.execute("SELECT COUNT(*) FROM ads")
    total = cursor.fetchone()[0]
    print(f"Total Ads: {total}")
    
    # Check ads without summary
    cursor.execute('SELECT COUNT(*) FROM ads WHERE ai_summary IS NULL OR ai_summary = ""')
    no_summary = cursor.fetchone()[0]
    print(f"Ads without summary (Raw): {no_summary}")
    
    # Check ads without summary AND joined with searches (like in the app)
    # Note: user_id is hardcoded to 1 often but let's check
    cursor.execute('''
        SELECT COUNT(*) 
        FROM ads 
        INNER JOIN searches ON ads.search_name = searches.name AND ads.user_id = searches.user_id
        WHERE ads.user_id = 1 AND (ads.ai_summary IS NULL OR ads.ai_summary = "")
    ''')
    joined_count = cursor.fetchone()[0]
    print(f"Ads ready for analysis (Joined with Active Searches, User 1): {joined_count}")
    
    # Check if there are ads with search_name that don't match any search in searches table
    cursor.execute('''
        SELECT ads.search_name, COUNT(*)
        FROM ads 
        LEFT JOIN searches ON ads.search_name = searches.name AND ads.user_id = searches.user_id
        WHERE searches.name IS NULL
        GROUP BY ads.search_name
    ''')
    orphans = cursor.fetchall()
    if orphans:
        print("\nOrphan Ads (Search name not found in searches table):")
        for o in orphans:
            print(f" - {o[0]}: {o[1]} ads")
            
    conn.close()

if __name__ == "__main__":
    check_ads()
