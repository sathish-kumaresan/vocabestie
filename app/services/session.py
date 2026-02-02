"""
Learning session service for adaptive word selection and exercise flow.

A session picks words based on:
- Words due for review (time decay)
- Words with lowest mastery scores
- A few new words (not started)
"""

import random
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Word, WordSkillMastery, UserWordStatus, Scenario
from app.services.mastery import (
    get_word_mastery,
    get_word_status,
    get_weakest_skill,
    PASS_THRESHOLD,
    SKILL_TYPES,
)


# Guest user ID for unauthenticated users
GUEST_USER_ID = 1

# Session configuration
MAX_WORDS_PER_SESSION = 10
NEW_WORDS_RATIO = 0.3  # 30% new words


def select_session_words(
    db: Session,
    scenario_id: int,
    user_id: int = GUEST_USER_ID,
    limit: int = MAX_WORDS_PER_SESSION,
) -> List[Word]:
    """
    Select words for a learning session using adaptive algorithm.

    Priority:
    1. Words with low mastery (in_progress, need review)
    2. New words (not_started)
    3. Random sampling for variety
    """
    # Get all words in the scenario
    all_words = db.query(Word).filter(Word.scenario_id == scenario_id).all()

    if not all_words:
        return []

    # Categorize words by status
    not_started = []
    in_progress = []
    mastered = []

    for word in all_words:
        status = get_word_status(db, user_id, word.id)
        if status == 'not_started':
            not_started.append(word)
        elif status == 'in_progress':
            in_progress.append(word)
        elif status == 'mastered':
            mastered.append(word)
        # Skip 'already_known' words

    selected = []

    # Priority 1: In-progress words (need practice)
    # Sort by lowest average mastery
    if in_progress:
        in_progress_scored = []
        for word in in_progress:
            skills = get_word_mastery(db, user_id, word.id)
            avg_mastery = sum(skills.values()) / len(skills)
            in_progress_scored.append((word, avg_mastery))

        # Sort by lowest mastery first
        in_progress_scored.sort(key=lambda x: x[1])
        for word, _ in in_progress_scored[:limit]:
            selected.append(word)

    # Priority 2: Add new words
    new_word_slots = int(limit * NEW_WORDS_RATIO)
    if not_started and len(selected) < limit:
        slots_available = min(new_word_slots, limit - len(selected))
        new_words = random.sample(not_started, min(slots_available, len(not_started)))
        selected.extend(new_words)

    # Priority 3: Fill remaining with mastered words for review
    if mastered and len(selected) < limit:
        slots_available = limit - len(selected)
        review_words = random.sample(mastered, min(slots_available, len(mastered)))
        selected.extend(review_words)

    # Shuffle the final selection
    random.shuffle(selected)

    return selected[:limit]


def get_exercise_for_word(
    db: Session,
    word: Word,
    user_id: int = GUEST_USER_ID,
    forced_skill_type: Optional[str] = None,
) -> Tuple[str, dict]:
    """
    Get the appropriate exercise type and data for a word.

    Returns: (skill_type, exercise_data)
    """
    # Get the weakest skill if not forced
    if forced_skill_type:
        skill_type = forced_skill_type
    else:
        skill_type = get_weakest_skill(db, user_id, word.id)

    # Prepare exercise data based on skill type
    exercise_data = {
        'word_id': word.id,
        'swedish': word.swedish,
        'english': word.english,
        'skill_type': skill_type,
    }

    if skill_type == 'read':
        # Show Swedish, pick English from 4 options
        exercise_data['question'] = word.swedish
        exercise_data['correct_answer'] = word.english
        exercise_data['options'] = generate_options(db, word, 'english')

    elif skill_type == 'listen':
        # Play Swedish audio, pick English from 4 options
        exercise_data['question'] = word.swedish  # For TTS
        exercise_data['correct_answer'] = word.english
        exercise_data['options'] = generate_options(db, word, 'english')

    elif skill_type == 'speak':
        # Show Swedish word, user speaks it
        exercise_data['question'] = word.swedish
        exercise_data['expected'] = word.swedish

    elif skill_type == 'write':
        # Show English, user arranges jumbled Swedish letters
        exercise_data['question'] = word.english
        exercise_data['correct_answer'] = word.swedish
        exercise_data['jumbled'] = jumble_letters(word.swedish)

    return skill_type, exercise_data


def generate_options(
    db: Session,
    correct_word: Word,
    field: str,
    num_options: int = 4,
) -> List[str]:
    """
    Generate multiple choice options including the correct answer.
    IMPORTANT: Only uses words from the SAME scenario/level to avoid confusion.
    """
    correct_value = getattr(correct_word, field)

    # Get other words ONLY from the same scenario for distractors
    other_words = db.query(Word).filter(
        Word.scenario_id == correct_word.scenario_id,
        Word.id != correct_word.id,
    ).all()

    # Get values for distractors
    distractors = [getattr(w, field) for w in other_words if getattr(w, field) != correct_value]

    # Remove duplicates
    distractors = list(set(distractors))

    # Sample distractors - use what's available from the same level only
    num_distractors = min(num_options - 1, len(distractors))

    if num_distractors > 0:
        selected_distractors = random.sample(distractors, num_distractors)
    else:
        selected_distractors = []

    # Combine and shuffle
    options = [correct_value] + selected_distractors
    random.shuffle(options)

    return options


def jumble_letters(word: str) -> List[str]:
    """
    Jumble the letters of a word for the write exercise.
    """
    letters = list(word.lower())
    random.shuffle(letters)
    return letters


def check_answer(
    skill_type: str,
    user_answer: str,
    correct_answer: str,
) -> Tuple[bool, float]:
    """
    Check if user's answer is correct.

    Returns: (is_correct, accuracy_score)
    """
    if skill_type in ['read', 'listen']:
        # Multiple choice - exact match
        is_correct = user_answer.lower().strip() == correct_answer.lower().strip()
        return is_correct, 1.0 if is_correct else 0.0

    elif skill_type == 'write':
        # Letter arrangement - exact match
        is_correct = user_answer.lower().strip() == correct_answer.lower().strip()
        return is_correct, 1.0 if is_correct else 0.0

    elif skill_type == 'speak':
        # Speech recognition - fuzzy match
        user_clean = user_answer.lower().strip()
        correct_clean = correct_answer.lower().strip()

        if user_clean == correct_clean:
            return True, 1.0

        # Calculate similarity (simple character overlap)
        user_set = set(user_clean)
        correct_set = set(correct_clean)
        overlap = len(user_set & correct_set) / len(correct_set) if correct_set else 0

        # Consider correct if > 70% overlap
        is_correct = overlap >= 0.7
        return is_correct, overlap

    return False, 0.0
