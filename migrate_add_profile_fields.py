"""
Migration script to add profile fields to users table
Run this script once to update the database schema

Usage:
    python migrate_add_profile_fields.py
"""
from app import create_app
from models.database import db
import sqlite3
import os

def migrate_database():
    app = create_app()
    
    with app.app_context():
        # Get database path
        from config import Config
        db_path = Config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
        
        # Check if database exists
        if not os.path.exists(db_path):
            print(f"Database not found at {db_path}. Creating new database...")
            db.create_all()
            print("Database created with all tables.")
            print("Migration completed - new database includes profile fields.")
            return
        
        # Connect to SQLite database directly
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Check if users table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='users'
            """)
            table_exists = cursor.fetchone()
            
            if not table_exists:
                print("users table does not exist. Creating all tables...")
                conn.close()
                db.create_all()
                print("Database created with all tables.")
                return
            
            # Check existing columns
            cursor.execute("PRAGMA table_info(users)")
            columns = {column[1]: column[2] for column in cursor.fetchall()}
            
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
                if column_name not in columns:
                    print(f"Adding {column_name} column to users table...")
                    cursor.execute(f"""
                        ALTER TABLE users 
                        ADD COLUMN {column_name} {column_type}
                    """)
                    added_columns.append(column_name)
                else:
                    print(f"Column '{column_name}' already exists in users table.")
            
            if added_columns:
                conn.commit()
                print(f"Successfully added columns: {', '.join(added_columns)}")
            else:
                print("All columns already exist. No migration needed.")
            
        except sqlite3.Error as e:
            print(f"Error during migration: {e}")
            print("   Trying to recreate tables...")
            conn.rollback()
            conn.close()
            # Fallback: recreate all tables (WARNING: This will delete data!)
            try:
                response = input("WARNING: Recreating tables will DELETE all data. Continue? (yes/no): ")
                if response.lower() == 'yes':
                    db.drop_all()
                    db.create_all()
                    print("Database schema recreated successfully.")
                else:
                    print("Migration cancelled.")
            except Exception as e2:
                print(f"Error recreating tables: {e2}")
                return
        finally:
            if conn:
                conn.close()
        
        print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_database()
