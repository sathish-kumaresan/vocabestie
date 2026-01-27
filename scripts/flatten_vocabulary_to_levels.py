#!/usr/bin/env python3
"""
Flatten vocabulary structure: Level -> Words.
Removes "Scenario" differentiation by merging all scenarios in a level into one massive scenario.

Usage:
    python scripts/flatten_vocabulary_to_levels.py
"""

import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
VOCAB_FILE = DATA_DIR / "vocabulary.json"

LEVEL_META = {
    "A1": {"name": "Beginner", "icon": "🟢", "description": "Essential everyday words and phrases"},
    "A2": {"name": "Elementary", "icon": "🔵", "description": "Common words for familiar situations"},
    "B1": {"name": "Intermediate", "icon": "🟡", "description": "Words for work, school, and travel"},
    "B2": {"name": "Upper Intermediate", "icon": "🟠", "description": "Complex topics and abstract ideas"},
    "C1": {"name": "Advanced", "icon": "🔴", "description": "Nuanced and specialized vocabulary"},
    "C2": {"name": "Mastery", "icon": "🟣", "description": "Rare and sophisticated expressions"},
}

def load_vocabulary() -> dict:
    with open(VOCAB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def backup_vocabulary():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DATA_DIR / f"vocabulary_backup_flatten_{timestamp}.json"
    import shutil
    shutil.copy2(VOCAB_FILE, backup_path)
    print(f"Backed up to {backup_path}")

def main():
    print("Loading vocabulary...")
    data = load_vocabulary()
    backup_vocabulary()

    # Pool words by level
    words_by_level = defaultdict(list)
    
    # Iterate through existing scenarios and gather words
    count = 0
    for scenario in data["scenarios"]:
        lvl = scenario.get("difficulty_level", "A1")
        # Safety fallback
        if lvl not in LEVEL_META:
            lvl = "A1"
        
        words_by_level[lvl].extend(scenario["words"])
        count += len(scenario["words"])

    print(f"Pooled {count} words.")

    new_scenarios = []
    display_order = 1
    
    for level in ["A1", "A2", "B1", "B2", "C1", "C2"]:
        words = words_by_level[level]
        meta = LEVEL_META[level]
        
        # Sort words alphabetically
        words.sort(key=lambda w: w["swedish"].lower())
        
        # Create SINGLE scenario for this level
        scenario = {
            "name": f"Level {level}",
            "slug": f"level-{level.lower()}", # simple slug
            "icon": meta["icon"],
            "description": meta["description"],
            "category": "All Words",
            "difficulty_level": level,
            "display_order": display_order,
            "word_count": len(words),
            "words": words
        }
        
        new_scenarios.append(scenario)
        display_order += 1
        print(f"Created '{scenario['name']}' with {len(words)} words.")

    # Save
    output = {"scenarios": new_scenarios}
    with open(VOCAB_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved {len(new_scenarios)} flattened scenarios to {VOCAB_FILE}")

if __name__ == "__main__":
    main()
