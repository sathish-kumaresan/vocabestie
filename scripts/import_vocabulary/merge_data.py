"""
Merge all processed batches into vocabulary.json.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
IMPORT_DIR = DATA_DIR / "import"
BATCHES_DIR = IMPORT_DIR / "batches"
VOCABULARY_FILE = DATA_DIR / "vocabulary.json"
SCENARIOS_FILE = IMPORT_DIR / "scenarios_master.json"


def load_scenarios_master() -> dict:
    """Load scenario definitions from master file."""
    with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Index by name for easy lookup
    return {s["name"]: s for s in data["scenarios"]}


def load_existing_vocabulary() -> dict:
    """Load existing vocabulary.json."""
    if not VOCABULARY_FILE.exists():
        return {"scenarios": []}
    with open(VOCABULARY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_all_batches() -> list[dict]:
    """Load all processed batch files."""
    all_words = []
    batch_files = sorted(BATCHES_DIR.glob("batch_*.json"))

    print(f"Found {len(batch_files)} batch files")

    for batch_file in batch_files:
        with open(batch_file, "r", encoding="utf-8") as f:
            words = json.load(f)
            all_words.extend(words)

    print(f"Loaded {len(all_words)} words from batches")
    return all_words


def group_words_by_scenario(words: list[dict]) -> dict[str, list[dict]]:
    """Group words by their assigned scenario."""
    grouped = defaultdict(list)

    for word in words:
        scenario = word.get("scenario", "Common Verbs")  # Default fallback
        grouped[scenario].append({
            "swedish": word.get("swedish", ""),
            "english": word.get("english", ""),
            "grammar_hint": word.get("grammar_hint", "noun"),
            "example_sv": word.get("example_sv", ""),
            "example_en": word.get("example_en", ""),
            "difficulty": word.get("difficulty", "B1")
        })

    return grouped


def merge_vocabulary(existing: dict, new_words_by_scenario: dict[str, list[dict]], scenarios_master: dict) -> dict:
    """Merge new words into existing vocabulary."""
    # Build index of existing scenarios
    existing_scenarios = {s["name"]: s for s in existing.get("scenarios", [])}

    # Track all Swedish words to avoid duplicates
    all_swedish_words = set()
    for scenario in existing.get("scenarios", []):
        for word in scenario.get("words", []):
            all_swedish_words.add(word.get("swedish", "").lower())

    # Process each scenario
    merged_scenarios = []

    # First, process existing scenarios and add new words
    for scenario in existing.get("scenarios", []):
        scenario_name = scenario["name"]
        new_words = new_words_by_scenario.pop(scenario_name, [])

        # Filter out duplicates
        unique_new_words = []
        for word in new_words:
            swedish = word.get("swedish", "").lower()
            if swedish not in all_swedish_words:
                unique_new_words.append(word)
                all_swedish_words.add(swedish)

        # Merge words
        merged_words = scenario.get("words", []) + unique_new_words

        # Sort by difficulty then alphabetically
        difficulty_order = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
        merged_words.sort(key=lambda w: (
            difficulty_order.get(w.get("difficulty", "B1"), 3),
            w.get("swedish", "").lower()
        ))

        # Update scenario
        scenario["words"] = merged_words
        scenario["word_count"] = len(merged_words)
        merged_scenarios.append(scenario)

    # Then, create new scenarios for remaining word groups
    for scenario_name, words in new_words_by_scenario.items():
        if scenario_name not in scenarios_master:
            print(f"Warning: Unknown scenario '{scenario_name}', assigning to Common Verbs")
            # Add to existing Common Verbs scenario
            for s in merged_scenarios:
                if s["name"] == "Common Verbs":
                    for word in words:
                        swedish = word.get("swedish", "").lower()
                        if swedish not in all_swedish_words:
                            s["words"].append(word)
                            all_swedish_words.add(swedish)
                    s["word_count"] = len(s["words"])
                    break
            continue

        # Filter duplicates
        unique_words = []
        for word in words:
            swedish = word.get("swedish", "").lower()
            if swedish not in all_swedish_words:
                unique_words.append(word)
                all_swedish_words.add(swedish)

        if not unique_words:
            continue

        # Sort words
        difficulty_order = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
        unique_words.sort(key=lambda w: (
            difficulty_order.get(w.get("difficulty", "B1"), 3),
            w.get("swedish", "").lower()
        ))

        # Create new scenario
        master = scenarios_master[scenario_name]
        new_scenario = {
            "name": master["name"],
            "slug": master["slug"],
            "icon": master["icon"],
            "description": master["description"],
            "category": master["category"],
            "difficulty_level": master["difficulty_level"],
            "display_order": master["display_order"],
            "words": unique_words,
            "word_count": len(unique_words)
        }
        merged_scenarios.append(new_scenario)

    # Sort scenarios by display_order
    merged_scenarios.sort(key=lambda s: s.get("display_order", 999))

    return {"scenarios": merged_scenarios}


def validate_vocabulary(vocab: dict) -> list[str]:
    """Validate the merged vocabulary."""
    errors = []
    all_words = set()

    for scenario in vocab.get("scenarios", []):
        for word in scenario.get("words", []):
            swedish = word.get("swedish", "").lower()

            # Check for duplicates
            if swedish in all_words:
                errors.append(f"Duplicate word: {swedish}")
            all_words.add(swedish)

            # Check required fields
            if not word.get("swedish"):
                errors.append(f"Missing swedish in {scenario['name']}")
            if not word.get("english"):
                errors.append(f"Missing english for {swedish}")

    return errors


def main():
    """Main entry point."""
    print("=" * 50)
    print("Merging Vocabulary Data")
    print("=" * 50)

    # Backup existing vocabulary
    if VOCABULARY_FILE.exists():
        backup_file = DATA_DIR / f"vocabulary_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        shutil.copy(VOCABULARY_FILE, backup_file)
        print(f"Backed up existing vocabulary to {backup_file}")

    # Load data
    scenarios_master = load_scenarios_master()
    existing = load_existing_vocabulary()
    new_words = load_all_batches()

    print(f"Existing scenarios: {len(existing.get('scenarios', []))}")
    print(f"New words to merge: {len(new_words)}")

    # Group and merge
    new_words_by_scenario = group_words_by_scenario(new_words)
    print(f"Words distributed across {len(new_words_by_scenario)} scenarios")

    merged = merge_vocabulary(existing, new_words_by_scenario, scenarios_master)

    # Validate
    errors = validate_vocabulary(merged)
    if errors:
        print(f"\nValidation errors ({len(errors)}):")
        for error in errors[:10]:
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")

    # Save
    with open(VOCABULARY_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    # Summary
    total_words = sum(len(s.get("words", [])) for s in merged.get("scenarios", []))
    print("\n" + "=" * 50)
    print("Merge Complete!")
    print(f"Total scenarios: {len(merged.get('scenarios', []))}")
    print(f"Total words: {total_words}")
    print(f"Saved to {VOCABULARY_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    main()
