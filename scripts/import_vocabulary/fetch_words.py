"""
Fetch Swedish words from GitHub source and filter out existing words.
"""

import json
import httpx
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
IMPORT_DIR = DATA_DIR / "import"
VOCABULARY_FILE = DATA_DIR / "vocabulary.json"
FILTERED_WORDS_FILE = IMPORT_DIR / "filtered_words.json"

# Source URL
SOURCE_URL = "https://raw.githubusercontent.com/oprogramador/most-common-words-by-language/master/src/resources/swedish.txt"


def fetch_source_words() -> list[str]:
    """Download words from GitHub source."""
    print(f"Fetching words from {SOURCE_URL}...")
    response = httpx.get(SOURCE_URL, timeout=30)
    response.raise_for_status()

    # Parse words - one per line
    words = []
    for line in response.text.strip().split("\n"):
        word = line.strip().lower()
        if word and len(word) > 0:
            words.append(word)

    print(f"Fetched {len(words)} words from source")
    return words


def load_existing_words() -> set[str]:
    """Load existing words from vocabulary.json."""
    if not VOCABULARY_FILE.exists():
        return set()

    with open(VOCABULARY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    existing = set()
    for scenario in data.get("scenarios", []):
        for word in scenario.get("words", []):
            swedish = word.get("swedish", "").lower().strip()
            if swedish:
                existing.add(swedish)

    print(f"Found {len(existing)} existing words in vocabulary.json")
    return existing


def filter_and_save(source_words: list[str], existing_words: set[str]) -> list[dict]:
    """Filter out existing words and save with frequency rank."""
    filtered = []
    rank = 0

    for word in source_words:
        rank += 1
        word_lower = word.lower().strip()

        # Skip if already exists
        if word_lower in existing_words:
            continue

        # Skip very short words (single characters) unless meaningful
        if len(word_lower) < 2:
            continue

        filtered.append({
            "word": word_lower,
            "rank": rank  # Original frequency rank
        })

    print(f"Filtered to {len(filtered)} new words")

    # Save to file
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(FILTERED_WORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    print(f"Saved to {FILTERED_WORDS_FILE}")
    return filtered


def main():
    """Main entry point."""
    print("=" * 50)
    print("Fetching and Filtering Swedish Words")
    print("=" * 50)

    # Fetch from source
    source_words = fetch_source_words()

    # Load existing
    existing_words = load_existing_words()

    # Filter and save
    filtered = filter_and_save(source_words, existing_words)

    # Summary
    print("\n" + "=" * 50)
    print("Summary:")
    print(f"  Source words: {len(source_words)}")
    print(f"  Existing words: {len(existing_words)}")
    print(f"  New words to process: {len(filtered)}")
    print("=" * 50)

    return filtered


if __name__ == "__main__":
    main()
