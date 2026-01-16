"""
Migration script to add student_id column to learning_activity table
Run this script once to update the database schema

Usage:
    python migrate_add_student_id.py
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
            print("✓ Database created with all tables.")
            print("✓ Migration completed - new database includes student_id column.")
            return
        
        # Connect to SQLite database directly
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Check if learning_activity table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='learning_activity'
            """)
            table_exists = cursor.fetchone()
            
            if not table_exists:
                print("learning_activity table does not exist. Creating all tables...")
                conn.close()
                db.create_all()
                print("✓ Database created with all tables.")
                return
            
            # Check if student_id column already exists
            cursor.execute("PRAGMA table_info(learning_activity)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'student_id' in columns:
                print("✓ Column 'student_id' already exists in learning_activity table.")
                print("✓ No migration needed.")
                conn.close()
                return
            
            # Add student_id column
            print("Adding student_id column to learning_activity table...")
            cursor.execute("""
                ALTER TABLE learning_activity 
                ADD COLUMN student_id INTEGER 
                REFERENCES users(id)
            """)
            
            conn.commit()
            print("✓ Successfully added student_id column to learning_activity table.")
            
        except sqlite3.Error as e:
            print(f"✗ Error during migration: {e}")
            print("   Trying to recreate tables...")
            conn.rollback()
            conn.close()
            # Fallback: recreate all tables
            try:
                db.create_all()
                print("✓ Database schema recreated successfully.")
            except Exception as e2:
                print(f"✗ Error recreating tables: {e2}")
                return
        finally:
            if conn:
                conn.close()
        
        print("✓ Migration completed successfully!")

if __name__ == "__main__":
    migrate_database()
