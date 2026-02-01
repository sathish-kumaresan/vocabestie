#!/usr/bin/env python3
"""
Seed script to import vocabulary data into the database.

Usage:
    python scripts/seed_data.py
    python scripts/seed_data.py --clear  # Clear existing data first
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.database import engine, SessionLocal
from app.models import Scenario, Word
from app.models.mastery import WordSkillMastery, UserWordStatus


def load_vocabulary_data() -> dict:
    """Load vocabulary data from JSON file."""
    data_file = project_root / "data" / "vocabulary.json"
    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_data(db: Session) -> None:
    """Clear existing scenarios, words, and related progress data."""
    print("Clearing existing data...")
    db.query(WordSkillMastery).delete()
    db.query(UserWordStatus).delete()
    db.query(Word).delete()
    db.query(Scenario).delete()
    db.commit()
    print("Data cleared.")


def seed_scenarios(db: Session, data: dict) -> None:
    """Seed scenarios and words from vocabulary data."""
    scenarios_data = data.get("scenarios", [])

    total_words = 0

    for scenario_data in scenarios_data:
        # Create scenario
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
        db.flush()  # Get scenario ID

        # Create words for this scenario
        words_data = scenario_data.get("words", [])
        for i, word_data in enumerate(words_data):
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

        print(f"  {scenario.icon} {scenario.name}: {len(words_data)} words")

    db.commit()
    print(f"\nTotal: {len(scenarios_data)} scenarios, {total_words} words")


def main():
    """Main function to seed the database."""
    clear_existing = "--clear" in sys.argv

    print("=" * 50)
    print("Vocabestie Database Seeder")
    print("=" * 50)

    # Load data
    print("\nLoading vocabulary data...")
    data = load_vocabulary_data()
    print(f"Found {len(data.get('scenarios', []))} scenarios")

    # Create database session
    db = SessionLocal()

    try:
        if clear_existing:
            clear_data(db)

        # Check for existing data
        existing_scenarios = db.query(Scenario).count()
        if existing_scenarios > 0 and not clear_existing:
            print(f"\nDatabase already has {existing_scenarios} scenarios.")
            print("Use --clear flag to clear existing data first.")
            return

        print("\nSeeding scenarios and words...")
        seed_scenarios(db, data)

        print("\n" + "=" * 50)
        print("Seeding complete!")
        print("=" * 50)

    except Exception as e:
        print(f"\nError: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
