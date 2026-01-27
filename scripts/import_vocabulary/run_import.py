"""
Main orchestrator for Swedish vocabulary import.
"""

import sys
import argparse
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.import_vocabulary import fetch_words, generate_data, merge_data


def main():
    parser = argparse.ArgumentParser(description="Import Swedish vocabulary")
    parser.add_argument("--step", choices=["fetch", "generate", "merge", "all"],
                        default="all", help="Which step to run")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from last checkpoint (for generate)")
    parser.add_argument("--batch", type=int,
                        help="Process specific batch number (for generate)")
    args = parser.parse_args()

    if args.step in ["all", "fetch"]:
        print("\n" + "=" * 60)
        print("STEP 1: Fetching and Filtering Words")
        print("=" * 60)
        fetch_words.main()

    if args.step in ["all", "generate"]:
        print("\n" + "=" * 60)
        print("STEP 2: Generating Vocabulary Data with AI")
        print("=" * 60)
        generate_data.main(resume=args.resume or args.step == "all",
                          start_batch=args.batch)

    if args.step in ["all", "merge"]:
        print("\n" + "=" * 60)
        print("STEP 3: Merging and Validating Data")
        print("=" * 60)
        merge_data.main()

    print("\n" + "=" * 60)
    print("Import process complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review vocabulary.json")
    print("2. Run: python scripts/seed_data.py --clear")
    print("3. Test the application")


if __name__ == "__main__":
    main()
