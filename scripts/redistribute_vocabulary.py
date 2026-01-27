#!/usr/bin/env python3
"""
Redistribute vocabulary into CEFR levels with ~30 words per group.

Pools all words, groups by difficulty level (A1-C2), then splits each
level into sub-groups of ~30 words.

Usage:
    python scripts/redistribute_vocabulary.py
    python scripts/redistribute_vocabulary.py --dry-run
"""

import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
VOCAB_FILE = DATA_DIR / "vocabulary.json"

MAX_WORDS = 30
TARGET_WORDS = 25  # Aim for ~25 words per group

LEVEL_META = {
    "A1": {"name": "Beginner", "icon": "🟢", "description": "Essential everyday words and phrases"},
    "A2": {"name": "Elementary", "icon": "🔵", "description": "Common words for familiar situations"},
    "B1": {"name": "Intermediate", "icon": "🟡", "description": "Words for work, school, and travel"},
    "B2": {"name": "Upper Intermediate", "icon": "🟠", "description": "Complex topics and abstract ideas"},
    "C1": {"name": "Advanced", "icon": "🔴", "description": "Nuanced and specialized vocabulary"},
    "C2": {"name": "Mastery", "icon": "🟣", "description": "Rare and sophisticated expressions"},
}

LEVEL_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]


def load_vocabulary() -> dict:
    with open(VOCAB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def backup_vocabulary():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DATA_DIR / f"vocabulary_backup_{timestamp}.json"
    import shutil
    shutil.copy2(VOCAB_FILE, backup_path)
    print(f"Backed up to {backup_path}")


def make_slug(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("Vocabulary Redistribution (CEFR Levels)")
    print("=" * 60)

    data = load_vocabulary()
    if not dry_run:
        backup_vocabulary()

    # Pool all words from all scenarios
    all_words = []
    for scenario in data["scenarios"]:
        all_words.extend(scenario["words"])

    original_total = len(all_words)
    print(f"\nPooled {original_total} words from {len(data['scenarios'])} scenarios")

    # Group words by difficulty level
    level_words = defaultdict(list)
    for word in all_words:
        level = word.get("difficulty", "A1")
        if level not in LEVEL_ORDER:
            level = "A1"
        level_words[level].append(word)

    print("\nWords per level:")
    for level in LEVEL_ORDER:
        print(f"  {level}: {len(level_words[level])} words")

    # Build new scenarios (one per ~25-word group within each level)
    new_scenarios = []
    display_order = 1

    for level in LEVEL_ORDER:
        words = level_words[level]
        meta = LEVEL_META[level]

        # Sort alphabetically by Swedish word for consistent ordering
        words.sort(key=lambda w: w["swedish"].lower())

        # Split into chunks of TARGET_WORDS
        chunks = [words[i:i+TARGET_WORDS] for i in range(0, len(words), TARGET_WORDS)]

        print(f"\n  {meta['icon']} {level} ({meta['name']}): {len(words)} words -> {len(chunks)} groups")

        for idx, chunk in enumerate(chunks):
            group_num = idx + 1
            scenario = {
                "name": f"{level}: {meta['name']} {group_num}",
                "slug": make_slug(f"{level}-{meta['name']}-{group_num}"),
                "icon": meta["icon"],
                "description": meta["description"],
                "category": f"{level} - {meta['name']}",
                "difficulty_level": level,
                "display_order": display_order,
                "word_count": len(chunk),
                "words": chunk,
            }
            new_scenarios.append(scenario)
            display_order += 1

    # Deduplicate slugs
    seen_slugs = {}
    for s in new_scenarios:
        slug = s["slug"]
        if slug in seen_slugs:
            seen_slugs[slug] += 1
            s["slug"] = f"{slug}-{seen_slugs[slug]}"
        else:
            seen_slugs[slug] = 1

    total_words = sum(len(s["words"]) for s in new_scenarios)

    print(f"\n{'=' * 60}")
    print(f"Result: {len(new_scenarios)} levels, {total_words} total words")
    if new_scenarios:
        sizes = [len(s["words"]) for s in new_scenarios]
        print(f"Words per group: min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)/len(sizes):.0f}")
    print(f"{'=' * 60}")

    if total_words != original_total:
        print(f"\nWARNING: Word count mismatch! Original: {original_total}, New: {total_words}")
    else:
        print(f"\nAll {total_words} words accounted for.")

    if not dry_run:
        output = {"scenarios": new_scenarios}
        with open(VOCAB_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\nWritten to {VOCAB_FILE}")
    else:
        print("\n(Dry run — no files written)")


if __name__ == "__main__":
    main()
