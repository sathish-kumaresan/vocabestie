from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(settings.sqlalchemy_database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_guest_user():
    """Create the guest user (id=1) if it doesn't exist."""
    from app.models import User

    db = SessionLocal()
    try:
        guest = db.query(User).filter(User.id == 1).first()
        if not guest:
            guest = User(id=1, name="Guest", email=None, auth_provider="guest")
            db.add(guest)
            db.commit()
            print("Created guest user (id=1)")
    except Exception as e:
        db.rollback()
        print(f"Error creating guest user: {e}")
    finally:
        db.close()
