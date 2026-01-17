"""
Migration script to add assignment_courses many-to-many relationship table
This creates the association table between LearningActivity and Course

Usage:
    python migrate_add_assignment_courses.py
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
            print("✓ Migration completed - new database includes assignment_courses table.")
            return
        
        # Connect to SQLite database directly
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Check if assignment_courses table already exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='assignment_courses'
            """)
            table_exists = cursor.fetchone()
            
            if table_exists:
                print("✓ Table 'assignment_courses' already exists.")
                print("✓ No migration needed.")
                conn.close()
                return
            
            # Create assignment_courses association table
            print("Creating assignment_courses table...")
            cursor.execute("""
                CREATE TABLE assignment_courses (
                    activity_id INTEGER NOT NULL,
                    course_id INTEGER NOT NULL,
                    PRIMARY KEY (activity_id, course_id),
                    FOREIGN KEY (activity_id) REFERENCES learning_activity(id) ON DELETE CASCADE,
                    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
                )
            """)
            
            conn.commit()
            print("✓ Successfully created assignment_courses table.")
            
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
