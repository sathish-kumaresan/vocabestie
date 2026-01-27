#!/usr/bin/env python3
"""
Categorize vocabulary into meaningful scenarios using semantic similarity.

This script:
1. Loads the current flat vocabulary.
2. Defines a master list of scenarios/topics (from VOCABESTIE_PLAN.md).
3. Uses 'sentence-transformers' to embed both words (English) and topics.
4. Assigns each word to the most similar topic within its CEFR level.
5. Groups words into new Scenarios.
6. Writes the new structure to data/vocabulary.json.

Requires: pip install sentence-transformers scipy
"""

import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

try:
    from sentence_transformers import SentenceTransformer, util
    import torch
except ImportError:
    print("Error: sentence-transformers not installed.")
    print("Please run: pip install sentence-transformers scipy")
    sys.exit(1)

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
VOCAB_FILE = DATA_DIR / "vocabulary.json"

# --- Helper Functions ---

def make_slug(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug

def load_vocabulary() -> dict:
    with open(VOCAB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def backup_vocabulary():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DATA_DIR / f"vocabulary_backup_{timestamp}.json"
    import shutil
    shutil.copy2(VOCAB_FILE, backup_path)
    print(f"Backed up to {backup_path}")

# --- Configuration ---

# Categories and Topics from VOCABESTIE_PLAN.md
# Structure: Category -> [ (Topic Name, Description, Icon) ]
CATEGORIES = {
    "Daily Life": [
        ("At Home", "furniture, rooms, household items, daily chores", "🏠"),
        ("Family & Relationships", "relatives, friends, dating, social roles", "👨‍👩‍👧"),
        ("Food & Cooking", "ingredients, meals, verbs for cooking, kitchen", "🍳"),
        ("Clothing", "apparel, fashion, accessories, fabrics", "👕"),
        ("Shopping", "buying, paying, shops, prices, groceries", "🛒"),
        ("Daily Routines", "waking up, hygiene, sleep, habits", "⏰"),
    ],
    "Work & Education": [
        ("At the Office", "meetings, colleagues, supplies, business verbs", "🏢"),
        ("Job Interview", "resume, skills, questions, career", "💼"),
        ("Emails & Communication", "writing, internet, calls, messages", "📧"),
        ("At School/University", "studying, exams, subjects, classroom", "🎓"),
        ("Technology", "computers, software, devices, digital life", "💻"),
    ],
    "Health & Wellbeing": [
        ("At the Doctor", "illness, symptoms, appointments, body parts", "🏥"),
        ("Pharmacy", "medicine, prescriptions, remedies", "💊"),
        ("Fitness & Sports", "exercise, gym, games, team sports", "🏋️"),
        ("Emotions & Feelings", "happy, sad, angry, mood, psychology", "😊"),
    ],
    "Travel & Transport": [
        ("At the Airport", "flights, luggage, customs, planes", "✈️"),
        ("Public Transport", "bus, train, ticket, station, commuting", "🚂"),
        ("Hotel", "reservation, room, check-in, amenities", "🏨"),
        ("Directions", "left, right, map, location, lost", "🗺️"),
        ("Driving", "car, road, traffic, signs, parking", "🚗"),
    ],
    "Social & Leisure": [
        ("Restaurant & Café", "ordering, menu, dining out, drinks", "🍽️"),
        ("Celebrations", "birthday, party, wedding, holidays, gifts", "🎉"),
        ("Entertainment", "music, movies, theater, art, books", "🎬"),
        ("Hobbies", "crafts, collecting, gardening, photography", "⚽"),
        ("Small Talk", "weather, intro, casual chat, greetings", "💬"),
    ],
    "Services & Admin": [
        ("Banking", "money, account, atm, credit card, loans", "🏦"),
        ("Post Office", "mail, stamps, shipping, packages", "📮"),
        ("Government & ID", "passport, forms, bureaucracy, laws", "🏛️"),
        ("Phone & Internet", "wifi, data, mobile, connection", "📱"),
    ],
    "Nature & Weather": [
        ("Weather", "rain, sun, snow, temperature, climate", "🌤️"),
        ("Nature & Outdoors", "forest, sea, mountains, hiking, camping", "🌳"),
        ("Animals", "pets, wild animals, birds, insects", "🐕"),
        ("Seasons", "spring, summer, autumn, winter, time", "🌸"),
    ],
    "Grammar Essentials": [
        ("Pronouns", "I, you, he, she, they, my, your", "👤"),
        ("Numbers", "one, two, first, second, quantity", "🔢"),
        ("Days & Months", "Monday, January, week, year, calendar", "📅"),
        ("Colors", "red, blue, light, dark, shades", "🎨"),
        ("Question Words", "who, what, where, when, why, how", "❓"),
        ("Common Verbs", "be, have, do, say, go, get, make, can, will", "🔗"),
        ("Common Adjectives", "good, bad, big, small, effective, happy, sad", "✨"),
        ("Common Adverbs", "now, then, here, there, always, never, very", "⚡"),
    ],
    "Swedish Culture": [
        ("Traditions", "customs, history, typical swedish things", "🇸🇪"),
        ("Holidays", "midsummer, lucia, christmas, easter", "🎄"),
        ("Fika Culture", "coffee, bun, break, socializing", "☕"),
    ],
}

# Add a "General" catch-all topic for each category to handle misc words
# We will distinctively mark these so we can use them as fallbacks
GENERAL_TOPICS = {}
for cat in CATEGORIES:
    slug_cat = make_slug(cat)
    # Create a generic topic for this category
    gen_topic = (f"General {cat}", f"general, miscellaneous, other words related to {cat.lower()}", "📌")
    CATEGORIES[cat].append(gen_topic)
    GENERAL_TOPICS[cat] = gen_topic[0] # Map category name to its general topic name

# Flatten topics for embedding
# List of objects: { "category": cat, "name": name, "desc": desc, "icon": icon, "text": "name: desc" }
TOPIC_LIST = []
for cat, topics in CATEGORIES.items():
    for t_name, t_desc, t_icon in topics:
        TOPIC_LIST.append({
            "category": cat,
            "name": t_name,
            "description": t_desc,
            "icon": t_icon,
            "embed_text": f"{t_name}: {t_desc}"
        })





def main():
    print("Loading model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print("Loading vocabulary...")
    data = load_vocabulary()
    backup_vocabulary()

    # 1. Pool all words
    all_words = []
    for scenario in data["scenarios"]:
        all_words.extend(scenario["words"])
    
    print(f"Processing {len(all_words)} words...")

    # 2. Embed Topics
    print("Embedding topics...")
    topic_texts = [t["embed_text"] for t in TOPIC_LIST]
    topic_embeddings = model.encode(topic_texts, convert_to_tensor=True)

    # 3. Group words by CEFR Level
    # We want to keep A1 words in A1 scenarios, etc.
    words_by_level = defaultdict(list)
    for word in all_words:
        lvl = word.get("difficulty", "A1")
        if lvl not in ["A1", "A2", "B1", "B2", "C1", "C2"]:
            lvl = "A1"
        words_by_level[lvl].append(word)

    new_scenarios = []
    display_order_global = 1

    # 4. Process each level
    for level, words in sorted(words_by_level.items()):
        print(f"\nProcessing Level {level} ({len(words)} words)...")
        
        # Embed words in this level
        # use "english" field + "grammar_hint" for context
        word_texts = [f"{w['english']} ({w.get('grammar_hint','')})" for w in words]
        word_embeddings = model.encode(word_texts, convert_to_tensor=True)

        # Compute cosine similarity
        hits = util.semantic_search(word_embeddings, topic_embeddings, top_k=1)

        # Assign words to topics
        topic_assignments = defaultdict(list)
        
        # Threshold for semantic similarity
        # If score is lower than this, we put it in the "General" topic of its matched category
        SIMILARITY_THRESHOLD = 0.28 

        for idx, hit in enumerate(hits):
            best_topic_idx = hit[0]['corpus_id']
            score = hit[0]['score']
            original_topic = TOPIC_LIST[best_topic_idx]
            
            english_word = words[idx]['english'].lower()
            if "efficient" in english_word:  # Debug log for 'effektiv'
                print(f"DEBUG: '{english_word}' matched to '{original_topic['name']}' with score {score:.4f}")

            final_topic_idx = best_topic_idx
            
            # If score is low, fallback to General topic of that category
            if score < SIMILARITY_THRESHOLD:
                # Find the 'General X' topic for this category
                cat_name = original_topic['category']
                general_topic_name = GENERAL_TOPICS.get(cat_name)
                
                # Find index of this general topic
                # (Inefficient search but fine for script size)
                for t_idx, t in enumerate(TOPIC_LIST):
                    if t['name'] == general_topic_name:
                        final_topic_idx = t_idx
                        break
                
                if "efficient" in english_word:
                    print(f"DEBUG: '{english_word}' fell back to General topic '{TOPIC_LIST[final_topic_idx]['name']}'")

            topic_assignments[final_topic_idx].append(words[idx])

        # Create scenarios from assignments
        level_scenarios = []
        
        for topic_idx, assigned_words in topic_assignments.items():
            topic = TOPIC_LIST[topic_idx]
            
            if not assigned_words:
                continue

            # Sort alphabetically
            assigned_words.sort(key=lambda w: w["swedish"].lower())

            # Split large groups logic
            MAX_WORDS_PER_SCENARIO = 30
            
            # If group is too big, split it
            chunks = [assigned_words[i:i + MAX_WORDS_PER_SCENARIO] for i in range(0, len(assigned_words), MAX_WORDS_PER_SCENARIO)]
            
            for chunk_idx, chunk in enumerate(chunks):
                suffix = f" {chunk_idx + 1}" if len(chunks) > 1 else ""
                
                # Name: "A1: Food & Cooking" or "A1: Food & Cooking 2"
                scenario_name = f"{level}: {topic['name']}{suffix}"
                
                # Slug must be unique
                slug_base = make_slug(f"{level}-{topic['name']}{suffix}")
                
                scenario = {
                    "name": scenario_name,
                    "slug": slug_base,
                    "icon": topic["icon"],
                    "description": topic["description"],
                    "category": f"{level} - {topic['category']}", 
                    "difficulty_level": level,
                    "display_order": 0, # set later
                    "word_count": len(chunk),
                    "words": chunk
                }
                level_scenarios.append(scenario)

        # Sort scenarios within level
        # 1. By Category order
        # 2. By Topic name
        # 3. By suffix number (implicit in name)
        cat_order = list(CATEGORIES.keys())
        def sort_key(s):
            cat_name = s["category"].split(" - ")[1]
            try:
                cat_idx = cat_order.index(cat_name)
            except ValueError:
                cat_idx = 999
            return (cat_idx, s["name"])

        level_scenarios.sort(key=sort_key)
        
        # Add to main list with display order
        for s in level_scenarios:
            s["display_order"] = display_order_global
            new_scenarios.append(s)
            display_order_global += 1
            print(f"  - Created '{s['name']}' with {s['word_count']} words")

    # 5. Save
    output = {"scenarios": new_scenarios}
    with open(VOCAB_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved {len(new_scenarios)} scenarios to {VOCAB_FILE}")


if __name__ == "__main__":
    main()
