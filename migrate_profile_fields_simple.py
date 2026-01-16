"""
Simple migration script to add profile fields to users table
This script connects directly to the database without loading the Flask app
"""
import sqlite3
import os

# Get database path
db_path = 'site.db'

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

# Connect to SQLite database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if users table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        print("users table does not exist!")
        exit(1)
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = {column[1]: column[2] for column in cursor.fetchall()}
    
    print(f"Existing columns in users table: {list(existing_columns.keys())}")
    
    # List of columns to add
    columns_to_add = {
        'bio': 'TEXT',
        'university': 'VARCHAR(200)',
        'grade': 'VARCHAR(50)',
        'teacher': 'VARCHAR(200)',
        'phone': 'VARCHAR(50)',
        'education_status': 'VARCHAR(50)',
        'profile_image': 'VARCHAR(200)'
    }
    
    added_columns = []
    
    # Add each column if it doesn't exist
    for column_name, column_type in columns_to_add.items():
        if column_name not in existing_columns:
            print(f"Adding {column_name} column...")
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                added_columns.append(column_name)
                print(f"  Successfully added {column_name}")
            except sqlite3.Error as e:
                print(f"  Error adding {column_name}: {e}")
        else:
            print(f"  Column '{column_name}' already exists")
    
    if added_columns:
        conn.commit()
        print(f"\nSuccessfully added {len(added_columns)} columns: {', '.join(added_columns)}")
    else:
        print("\nAll columns already exist. No migration needed.")
    
    # Verify columns
    cursor.execute("PRAGMA table_info(users)")
    final_columns = [column[1] for column in cursor.fetchall()]
    print(f"\nFinal columns in users table: {final_columns}")
    
except sqlite3.Error as e:
    print(f"Error during migration: {e}")
    conn.rollback()
except Exception as e:
    print(f"Unexpected error: {e}")
    conn.rollback()
finally:
    conn.close()

print("\nMigration completed!")
