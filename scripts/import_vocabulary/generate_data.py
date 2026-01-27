"""
Generate vocabulary data using Claude AI in batches.
"""

import json
import time
import os
import anthropic
from pathlib import Path
from datetime import datetime

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
IMPORT_DIR = DATA_DIR / "import"
BATCHES_DIR = IMPORT_DIR / "batches"
FILTERED_WORDS_FILE = IMPORT_DIR / "filtered_words.json"
STATE_FILE = IMPORT_DIR / "processing_state.json"
SCENARIOS_FILE = IMPORT_DIR / "scenarios_master.json"

# Config
BATCH_SIZE = 50
DELAY_BETWEEN_BATCHES = 2  # seconds


def load_scenarios() -> list[str]:
    """Load scenario names from master file."""
    with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [s["name"] for s in data["scenarios"]]


def load_filtered_words() -> list[dict]:
    """Load filtered words to process."""
    with open(FILTERED_WORDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state() -> dict:
    """Load processing state or create new."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "total_words": 0,
        "batch_size": BATCH_SIZE,
        "total_batches": 0,
        "completed_batches": [],
        "failed_batches": [],
        "last_updated": None
    }


def save_state(state: dict):
    """Save processing state."""
    state["last_updated"] = datetime.utcnow().isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def get_difficulty(rank: int) -> str:
    """Assign difficulty based on frequency rank."""
    if rank <= 200:
        return "A1"
    elif rank <= 500:
        return "A2"
    elif rank <= 1000:
        return "B1"
    elif rank <= 1500:
        return "B2"
    elif rank <= 2000:
        return "C1"
    else:
        return "C2"


def process_batch(client: anthropic.Anthropic, batch_num: int, words: list[dict], scenarios: list[str]) -> list[dict]:
    """Process a batch of words using Claude."""
    # Build word list for prompt
    word_list = "\n".join([f"{i+1}. {w['word']} (rank: {w['rank']})" for i, w in enumerate(words)])
    scenario_list = ", ".join(scenarios)

    prompt = f"""You are a Swedish language expert. For each Swedish word below, provide:
1. english: The most common English translation
2. grammar_hint: One of: en-word, ett-word, verb, adjective, adverb, pronoun, preposition, conjunction, interjection, noun, plural, number, ordinal, phrase
3. example_sv: A natural Swedish sentence using the word (8-12 words)
4. example_en: English translation of that sentence
5. scenario: The BEST matching scenario from the list (choose only ONE)

Words to process:
{word_list}

Available scenarios (choose exactly ONE per word):
{scenario_list}

Return ONLY a valid JSON array with this exact format (no markdown, no explanation):
[
  {{
    "swedish": "word",
    "english": "translation",
    "grammar_hint": "category",
    "example_sv": "Swedish sentence",
    "example_en": "English translation",
    "scenario": "Scenario Name"
  }}
]

Important:
- Ensure grammar_hint accurately reflects the word type
- Example sentences should be practical and natural
- Each word must have exactly one scenario
- Return valid JSON only"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse response
    response_text = response.content[0].text.strip()

    # Remove markdown code blocks if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    try:
        results = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Response: {response_text[:500]}...")
        raise

    # Add difficulty based on rank
    word_ranks = {w["word"]: w["rank"] for w in words}
    for result in results:
        swedish = result.get("swedish", "").lower()
        rank = word_ranks.get(swedish, 1000)
        result["difficulty"] = get_difficulty(rank)
        result["rank"] = rank

    return results


def main(resume: bool = True, start_batch: int = None):
    """Main entry point."""
    print("=" * 50)
    print("Generating Vocabulary Data with AI")
    print("=" * 50)

    # Setup
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var

    # Load data
    words = load_filtered_words()
    scenarios = load_scenarios()
    state = load_state()

    # Calculate batches
    total_batches = (len(words) + BATCH_SIZE - 1) // BATCH_SIZE
    state["total_words"] = len(words)
    state["total_batches"] = total_batches

    print(f"Total words: {len(words)}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Total batches: {total_batches}")
    print(f"Already completed: {len(state['completed_batches'])}")

    # Determine starting point
    if start_batch is not None:
        batches_to_process = [start_batch]
    elif resume:
        batches_to_process = [
            i for i in range(1, total_batches + 1)
            if i not in state["completed_batches"]
        ]
    else:
        batches_to_process = list(range(1, total_batches + 1))

    print(f"Batches to process: {len(batches_to_process)}")

    # Process batches
    for batch_num in batches_to_process:
        print(f"\n--- Processing batch {batch_num}/{total_batches} ---")

        # Get words for this batch
        start_idx = (batch_num - 1) * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, len(words))
        batch_words = words[start_idx:end_idx]

        if not batch_words:
            continue

        try:
            # Process with AI
            results = process_batch(client, batch_num, batch_words, scenarios)

            # Save batch results
            batch_file = BATCHES_DIR / f"batch_{batch_num:03d}.json"
            with open(batch_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            print(f"Saved {len(results)} words to {batch_file}")

            # Update state
            if batch_num not in state["completed_batches"]:
                state["completed_batches"].append(batch_num)
            if batch_num in state["failed_batches"]:
                state["failed_batches"].remove(batch_num)
            save_state(state)

            # Delay between batches
            if batch_num < total_batches:
                print(f"Waiting {DELAY_BETWEEN_BATCHES}s before next batch...")
                time.sleep(DELAY_BETWEEN_BATCHES)

        except Exception as e:
            print(f"Error processing batch {batch_num}: {e}")
            if batch_num not in state["failed_batches"]:
                state["failed_batches"].append(batch_num)
            save_state(state)
            continue

    # Final summary
    print("\n" + "=" * 50)
    print("Processing Complete!")
    print(f"Completed batches: {len(state['completed_batches'])}/{total_batches}")
    print(f"Failed batches: {state['failed_batches']}")
    print("=" * 50)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-resume", action="store_true", help="Start fresh")
    parser.add_argument("--batch", type=int, help="Process specific batch")
    parser.add_argument("--status", action="store_true", help="Show status only")
    args = parser.parse_args()

    if args.status:
        state = load_state()
        print(f"Total batches: {state['total_batches']}")
        print(f"Completed: {len(state['completed_batches'])}")
        print(f"Failed: {state['failed_batches']}")
        print(f"Last updated: {state['last_updated']}")
    else:
        main(resume=not args.no_resume, start_batch=args.batch)
