"""Direct SQLite migration for attachment fields"""
import sqlite3
import os

# Find database file (based on config.py)
db_path = os.path.join(os.path.dirname(__file__), 'site.db')
if not os.path.exists(db_path):
    # Try alternative locations
    alt_path = os.path.join(os.path.dirname(__file__), 'instance', 'database.db')
    if os.path.exists(alt_path):
        db_path = alt_path
    else:
        alt_path = os.path.join(os.path.dirname(__file__), 'database.db')
        if os.path.exists(alt_path):
            db_path = alt_path
        else:
            print(f"Database not found. Tried:")
            print(f"  - {os.path.join(os.path.dirname(__file__), 'site.db')}")
            print(f"  - {os.path.join(os.path.dirname(__file__), 'instance', 'database.db')}")
            print(f"  - {os.path.join(os.path.dirname(__file__), 'database.db')}")
            exit(1)

print(f"Connecting to database: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check existing columns
    cursor.execute("PRAGMA table_info(learning_activity)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Existing columns: {columns}")
    
    # Add attachment_path if not exists
    if 'attachment_path' not in columns:
        cursor.execute("ALTER TABLE learning_activity ADD COLUMN attachment_path VARCHAR(500)")
        print("Added attachment_path column")
    else:
        print("attachment_path column already exists")
    
    # Add attachment_filename if not exists
    if 'attachment_filename' not in columns:
        cursor.execute("ALTER TABLE learning_activity ADD COLUMN attachment_filename VARCHAR(200)")
        print("Added attachment_filename column")
    else:
        print("attachment_filename column already exists")
    
    conn.commit()
    print("\nMigration completed successfully!")
    
except Exception as e:
    conn.rollback()
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
