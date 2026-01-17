"""Simple migration script for attachment fields"""
from app import create_app
from models.database import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('learning_activity')]
        
        if 'attachment_path' not in columns:
            db.session.execute(text("ALTER TABLE learning_activity ADD COLUMN attachment_path VARCHAR(500)"))
            print("Added attachment_path column")
        
        if 'attachment_filename' not in columns:
            db.session.execute(text("ALTER TABLE learning_activity ADD COLUMN attachment_filename VARCHAR(200)"))
            print("Added attachment_filename column")
        
        db.session.commit()
        print("Migration completed successfully!")
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
