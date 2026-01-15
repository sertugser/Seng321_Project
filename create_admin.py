"""
Admin User Creation Script
Usage: python create_admin.py
"""
from app import create_app
from models.database import db
from models.entities import User
from werkzeug.security import generate_password_hash

def create_admin_user():
    app = create_app()
    
    with app.app_context():
        # Check if admin already exists
        existing_admin = User.query.filter_by(role='Admin').first()
        if existing_admin:
            print(f"⚠️  Admin user already exists: {existing_admin.username} ({existing_admin.email})")
            response = input("Do you want to create another admin? (y/n): ")
            if response.lower() != 'y':
                print("❌ Operation cancelled.")
                return
        
        print("=" * 50)
        print("Admin User Creation")
        print("=" * 50)
        
        username = input("Enter username: ").strip()
        if not username:
            print("❌ Username cannot be empty!")
            return
        
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"❌ Username '{username}' already exists!")
            return
        
        email = input("Enter email: ").strip()
        if not email or '@' not in email:
            print("❌ Invalid email address!")
            return
        
        # Check if email already exists
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            print(f"❌ Email '{email}' is already registered!")
            return
        
        password = input("Enter password (min 6 characters): ").strip()
        if len(password) < 6:
            print("❌ Password must be at least 6 characters!")
            return
        
        confirm_password = input("Confirm password: ").strip()
        if password != confirm_password:
            print("❌ Passwords do not match!")
            return
        
        # Create admin user
        try:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            admin_user = User(
                username=username,
                email=email,
                password=hashed_password,
                role='Admin'
            )
            db.session.add(admin_user)
            db.session.commit()
            
            print("\n" + "=" * 50)
            print("✅ Admin user created successfully!")
            print("=" * 50)
            print(f"Username: {username}")
            print(f"Email: {email}")
            print(f"Role: Admin")
            print("\nYou can now login at: http://127.0.0.1:5000/login")
            print("=" * 50)
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating admin user: {str(e)}")

if __name__ == '__main__':
    create_admin_user()
