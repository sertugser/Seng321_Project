from models.entities import User, UserRole
from models.database import db

class UserRepository:
    @staticmethod
    def create_user(username, email, password, role=UserRole.STUDENT):
        new_user = User(username=username, email=email, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        return new_user

    @staticmethod
    def find_by_username(username):
        return User.query.filter_by(username=username).first()

    @staticmethod
    def find_by_id(user_id):
        return User.query.get(user_id)