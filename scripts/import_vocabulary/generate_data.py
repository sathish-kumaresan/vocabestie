"""
Generate vocabulary data using Google Gemini AI in batches.
Kelly dataset provides CEFR levels and grammar hints.
AI only needs to generate: English translation, example sentences, scenario assignment.

Uses Gemini 2.0 Flash. Set GEMINI_API_KEY environment variable before running.
"""

import json
import time
import random
from pathlib import Path
from datetime import datetime, timezone
from google import genai
from google.genai import errors as genai_errors

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
DELAY_BETWEEN_BATCHES = 2  # seconds between successful requests
MAX_RETRIES = 5
MODEL = "gemini-2.0-flash"


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
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def call_gemini_with_retry(client: genai.Client, prompt: str) -> str:
    """Call Gemini API with exponential backoff on 429 errors."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
            )
            return response.text.strip()
        except (genai_errors.ClientError, genai_errors.ServerError, genai_errors.APIError) as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "resource" in str(e).lower():
                wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"  Rate limited (attempt {attempt+1}/{MAX_RETRIES}), waiting {wait:.1f}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Failed after {MAX_RETRIES} retries due to rate limiting")


def process_batch(client: genai.Client, batch_num: int, words: list[dict], scenarios: list[str]) -> list[dict]:
    """Process a batch of words using Gemini."""
    # Build word list with Kelly metadata for context
    word_lines = []
    for i, w in enumerate(words):
        line = f"{i+1}. {w['word']} (POS: {w['pos']}, CEFR: {w['cefr_level']}"
        if w.get('kelly_examples'):
            line += f", examples: {w['kelly_examples'][:80]}"
        line += ")"
        word_lines.append(line)
    word_list = "\n".join(word_lines)

    scenario_list = ", ".join(scenarios)

    prompt = f"""You are a Swedish language expert. For each Swedish word below, provide:
1. english: The most common English translation (1-3 words)
2. example_sv: A natural Swedish sentence using the word (8-12 words)
3. example_en: English translation of that sentence
4. scenario: The BEST matching scenario from the list (choose only ONE)

The words already have POS and CEFR level data from the Kelly dataset — you do NOT need to provide those.

Words to process:
{word_list}

Available scenarios (choose exactly ONE per word):
{scenario_list}

Return ONLY a valid JSON array with this exact format (no markdown, no explanation):
[
  {{
    "swedish": "word",
    "english": "translation",
    "example_sv": "Swedish sentence",
    "example_en": "English translation",
    "scenario": "Scenario Name"
  }}
]

Important:
- Return the swedish word exactly as given (lowercase)
- Example sentences should be practical and natural
- Each word must have exactly one scenario from the list
- Return valid JSON only, no markdown code fences"""

    response_text = call_gemini_with_retry(client, prompt)

    # Remove markdown code blocks if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        if lines[-1].strip() == "```":
            response_text = "\n".join(lines[1:-1])
        else:
            response_text = "\n".join(lines[1:])

    try:
        results = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Response: {response_text[:500]}...")
        raise

    # Enrich results with Kelly metadata (CEFR, grammar_hint)
    word_meta = {w["word"]: w for w in words}
    for result in results:
        swedish = result.get("swedish", "").lower()
        meta = word_meta.get(swedish, {})
        result["difficulty"] = meta.get("cefr_level", "B1")
        result["grammar_hint"] = meta.get("grammar_hint", "noun")
        result["rank"] = meta.get("rank", 0)

    return results


def main(resume: bool = True, start_batch: int = None):
    """Main entry point."""
    print("=" * 50)
    print("Generating Vocabulary Data with Gemini AI")
    print("=" * 50)

    # Setup
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)
    client = genai.Client()  # Uses GEMINI_API_KEY env var

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
    print(f"Model: {MODEL}")
    print(f"Delay between batches: {DELAY_BETWEEN_BATCHES}s")

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

            # Delay between batches (respect free tier rate limit)
            if batch_num < total_batches and len(batches_to_process) > 1:
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
