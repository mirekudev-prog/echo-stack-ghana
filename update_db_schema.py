import sqlite3
import os

def migrate():
    db_path = 'echostack.db'
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current columns
    cursor.execute("PRAGMA table_info(posts)")
    columns = [row[1] for row in cursor.fetchall()]
    
    # Columns to add
    new_cols = [
        ("media_path", "TEXT DEFAULT ''"),
        ("media_type", "TEXT DEFAULT 'image'"),
        ("likes_count", "INTEGER DEFAULT 0")
    ]
    
    for col_name, col_type in new_cols:
        if col_name not in columns:
            print(f"Adding column {col_name} to posts table...")
            try:
                cursor.execute(f"ALTER TABLE posts ADD COLUMN {col_name} {col_type}")
                conn.commit()
                print(f"Column {col_name} added successfully.")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
        else:
            print(f"Column {col_name} already exists.")
            
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
