"""
Migration script to add attachment fields to LearningActivity table
Run this script to update the database schema
"""
import sys
import os

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from app import create_app
from models.database import db
from sqlalchemy import text

def migrate_add_attachment_fields():
    app = create_app()
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('learning_activity')]
            
            if 'attachment_path' not in columns:
                # Add attachment_path column
                db.session.execute(text("ALTER TABLE learning_activity ADD COLUMN attachment_path VARCHAR(500)"))
                print("[OK] Added attachment_path column")
            else:
                print("[OK] attachment_path column already exists")
            
            if 'attachment_filename' not in columns:
                # Add attachment_filename column
                db.session.execute(text("ALTER TABLE learning_activity ADD COLUMN attachment_filename VARCHAR(200)"))
                print("[OK] Added attachment_filename column")
            else:
                print("[OK] attachment_filename column already exists")
            
            db.session.commit()
            print("\n[SUCCESS] Migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Migration failed: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    migrate_add_attachment_fields()
