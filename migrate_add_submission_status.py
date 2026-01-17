import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'site.db')

def migrate_add_submission_status():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Check if column exists
        cursor.execute("PRAGMA table_info(submissions);")
        columns = [col[1] for col in cursor.fetchall()]

        if 'status' not in columns:
            cursor.execute("ALTER TABLE submissions ADD COLUMN status VARCHAR(20) DEFAULT 'PENDING' NOT NULL;")
            print("Added status column to submissions table")
            
            # Update existing submissions to PENDING if they don't have a status
            cursor.execute("UPDATE submissions SET status = 'PENDING' WHERE status IS NULL;")
            print("Updated existing submissions to PENDING status")
        else:
            print("status column already exists in submissions table.")

        conn.commit()
        print("Migration completed successfully!")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate_add_submission_status()
