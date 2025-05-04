import sqlite3
import os
from pathlib import Path

DB_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "nutrition.db"

def create_database():
    """Create the SQLite database and tables if they don't exist"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create foods table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS foods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fdc_id TEXT UNIQUE,
        description TEXT NOT NULL,
        brand TEXT,
        serving_size REAL DEFAULT 100,
        serving_unit TEXT DEFAULT 'g',
        food_category TEXT,
        ingredients_text TEXT,
        image_url TEXT,
        origins TEXT
    )
    ''')
    
    # Create nutrients table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS nutrients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        food_id INTEGER,
        nutrient_type TEXT NOT NULL,
        amount REAL NOT NULL,
        FOREIGN KEY (food_id) REFERENCES foods (id),
        UNIQUE(food_id, nutrient_type)
    )
    ''')
    
    # Create allergens table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS allergens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        food_id INTEGER,
        allergen TEXT NOT NULL,
        FOREIGN KEY (food_id) REFERENCES foods (id),
        UNIQUE(food_id, allergen)
    )
    ''')
    
    # Create an index on fdc_id for faster lookups
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fdc_id ON foods (fdc_id)')
    
    # Create indexes for text search
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_description ON foods (description)')
    
    conn.commit()
    conn.close()
    
    print(f"Database created at {DB_PATH}")

if __name__ == "__main__":
    create_database() 