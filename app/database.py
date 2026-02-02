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


def seed_vocabulary_if_empty():
    """Seed vocabulary data if database is empty."""
    import json
    from pathlib import Path
    from app.models import Scenario, Word

    db = SessionLocal()
    try:
        # Check if data already exists
        existing_scenarios = db.query(Scenario).count()
        if existing_scenarios > 0:
            print(f"Database already has {existing_scenarios} scenarios, skipping seed.")
            return

        # Load vocabulary data
        data_file = Path(__file__).parent.parent / "data" / "vocabulary.json"
        if not data_file.exists():
            print("No vocabulary.json found, skipping seed.")
            return

        print("Seeding vocabulary data...")
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        total_words = 0
        for scenario_data in data.get("scenarios", []):
            scenario = Scenario(
                name=scenario_data["name"],
                slug=scenario_data["slug"],
                icon=scenario_data["icon"],
                description=scenario_data["description"],
                category=scenario_data["category"],
                difficulty_level=scenario_data["difficulty_level"],
                display_order=scenario_data["display_order"],
                word_count=len(scenario_data["words"]),
            )
            db.add(scenario)
            db.flush()

            for i, word_data in enumerate(scenario_data.get("words", [])):
                word = Word(
                    scenario_id=scenario.id,
                    swedish=word_data["swedish"],
                    english=word_data["english"],
                    grammar_hint=word_data.get("grammar_hint"),
                    example_sentence_sv=word_data.get("example_sv"),
                    example_sentence_en=word_data.get("example_en"),
                    difficulty_level=word_data.get("difficulty_level", "A1"),
                    display_order=i + 1,
                )
                db.add(word)
                total_words += 1

        db.commit()
        print(f"Seeded {len(data.get('scenarios', []))} scenarios with {total_words} words.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding vocabulary: {e}")
    finally:
        db.close()
