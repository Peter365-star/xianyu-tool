from app.database import SessionLocal
from app.models.user import User
from app.services.auth import hash_password


def seed():
    db = SessionLocal()
    try:
        from sqlalchemy import select
        result = db.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none():
            print("admin user already exists")
            return
        user = User(username="admin", password_hash=hash_password("admin123"))
        db.add(user)
        db.commit()
        print("admin user created (admin / admin123)")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
