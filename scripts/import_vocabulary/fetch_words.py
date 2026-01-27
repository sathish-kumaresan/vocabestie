"""
Fetch Swedish words from Kelly dataset (HuggingFace) and filter out existing words.
Source: https://huggingface.co/datasets/codesue/kelly
"""

import json
from pathlib import Path
import pandas as pd

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
IMPORT_DIR = DATA_DIR / "import"
VOCABULARY_FILE = DATA_DIR / "vocabulary.json"
FILTERED_WORDS_FILE = IMPORT_DIR / "filtered_words.json"

KELLY_PARQUET_URL = "https://huggingface.co/api/datasets/codesue/kelly/parquet/default/train/0.parquet"

# POS → grammar_hint mapping
# Kelly POS values: noun-en, noun-ett, noun-en/-ett, noun, verb, adjective,
#   adverb, pronoun, prep, conj, numeral, interj, proper name, det, subj,
#   aux verb, particle, particip
POS_MAP = {
    "noun-en": "en-word",
    "noun-ett": "ett-word",
    "noun-en/-ett": "noun",
    "noun": "noun",
    "verb": "verb",
    "aux verb": "verb",
    "adjective": "adjective",
    "particip": "adjective",
    "adverb": "adverb",
    "pronoun": "pronoun",
    "det": "pronoun",
    "prep": "preposition",
    "conj": "conjunction",
    "subj": "conjunction",
    "numeral": "number",
    "interj": "interjection",
    "proper name": "noun",
    "particle": "adverb",
}


def map_grammar_hint(pos: str, marker: str) -> str:
    """Map Kelly POS + marker to grammar_hint."""
    pos_lower = (pos or "").lower().strip()
    marker_lower = (marker or "").lower().strip()

    # Check POS field first (Kelly encodes gender in POS like noun-en, noun-ett)
    if pos_lower in POS_MAP:
        return POS_MAP[pos_lower]

    # Fallback: use marker for plain "noun"
    if "noun" in pos_lower:
        if marker_lower == "en":
            return "en-word"
        elif marker_lower == "ett":
            return "ett-word"
        return "noun"

    return "noun"


def fetch_kelly_words() -> list[dict]:
    """Download Kelly dataset from HuggingFace parquet file."""
    print("Fetching Kelly dataset from HuggingFace...")
    df = pd.read_parquet(KELLY_PARQUET_URL)
    print(f"Downloaded {len(df)} rows")

    words = []
    for i, row in df.iterrows():
        lemma = str(row.get("lemma") or "").strip()
        if not lemma or len(lemma) < 2:
            continue

        pos = str(row.get("pos") or "")
        marker = str(row.get("marker") or "")

        words.append({
            "word": lemma.lower(),
            "word_original": lemma,
            "cefr_level": str(row.get("cefr_level") or "B1"),
            "pos": pos,
            "marker": marker,
            "grammar_hint": map_grammar_hint(pos, marker),
            "kelly_examples": str(row.get("examples") or ""),
            "rank": i + 1,
        })

    print(f"Fetched {len(words)} words from Kelly dataset")
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


def filter_and_save(source_words: list[dict], existing_words: set[str]) -> list[dict]:
    """Filter out existing words and save with Kelly metadata."""
    filtered = []
    seen = set()

    for word_data in source_words:
        word_lower = word_data["word"]

        if word_lower in existing_words:
            continue

        if word_lower in seen:
            continue
        seen.add(word_lower)

        filtered.append(word_data)

    print(f"Filtered to {len(filtered)} new words")

    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(FILTERED_WORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    print(f"Saved to {FILTERED_WORDS_FILE}")
    return filtered


def main():
    """Main entry point."""
    print("=" * 50)
    print("Fetching and Filtering Swedish Words (Kelly Dataset)")
    print("=" * 50)

    source_words = fetch_kelly_words()
    existing_words = load_existing_words()
    filtered = filter_and_save(source_words, existing_words)

    # CEFR distribution
    cefr_counts = {}
    for w in filtered:
        level = w.get("cefr_level", "?")
        cefr_counts[level] = cefr_counts.get(level, 0) + 1

    # Grammar hint distribution
    hint_counts = {}
    for w in filtered:
        hint = w.get("grammar_hint", "?")
        hint_counts[hint] = hint_counts.get(hint, 0) + 1

    print("\n" + "=" * 50)
    print("Summary:")
    print(f"  Kelly dataset words: {len(source_words)}")
    print(f"  Existing words: {len(existing_words)}")
    print(f"  New words to process: {len(filtered)}")
    print(f"  CEFR distribution: {json.dumps(cefr_counts, indent=4)}")
    print(f"  Grammar hints: {json.dumps(hint_counts, indent=4)}")
    print("=" * 50)

    return filtered


if __name__ == "__main__":
    main()
