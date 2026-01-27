#!/bin/bash
set -e

echo "Applying semantic grouping to vocabulary..."
python3 scripts/categorize_vocabulary.py

echo "Re-seeding database..."
python3 scripts/seed_data.py --clear

echo "Done! Vocabulary regrouped and database updated."
