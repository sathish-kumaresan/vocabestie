"""
SM2 Spaced Repetition Algorithm Service.

This implements the SM2 algorithm PER-WORD (not per-skill).
When a word reaches mastery (>=80% on all 4 skills), it enters the SM2 review system.

Key concepts:
- easiness_factor (EF): How easy the word is (min 1.3, default 2.5)
- sm2_interval: Days until next review
- sm2_repetitions: Count of successful reviews
- next_review_date: When the word is due for review
- consecutive_failures: Track failures for mastery demotion (3+ = drop from mastered)
"""

from datetime import datetime, date, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import Word, WordReviewState
from app.services.mastery import get_word_status, PASS_THRESHOLD


def get_or_create_review_state(
    db: Session,
    user_id: int,
    word_id: int,
) -> WordReviewState:
    """Get or create a WordReviewState record for a user/word pair."""
    state = db.query(WordReviewState).filter(
        WordReviewState.user_id == user_id,
        WordReviewState.word_id == word_id,
    ).first()

    if not state:
        state = WordReviewState(
            user_id=user_id,
            word_id=word_id,
            easiness_factor=2.5,
            sm2_interval=0,
            sm2_repetitions=0,
            consecutive_failures=0,
            next_review_date=None,
        )
        db.add(state)
        db.flush()

    return state


def calculate_sm2(
    quality: int,
    easiness_factor: float,
    interval: int,
    repetitions: int,
) -> tuple[float, int, int]:
    """
    Calculate new SM2 values after a review.

    Args:
        quality: Response quality (0-5)
            0 - Complete blackout
            1 - Wrong, serious difficulty remembering
            2 - Wrong, but upon seeing correct answer, it seemed easy
            3 - Correct, but with serious difficulty
            4 - Correct, after hesitation
            5 - Correct, perfect response

    Returns:
        (new_ef, new_interval, new_repetitions)
    """
    # Calculate new easiness factor
    new_ef = easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(1.3, new_ef)  # EF minimum is 1.3

    # If quality < 3, reset repetitions (failed review)
    if quality < 3:
        new_repetitions = 0
        new_interval = 1  # Review again tomorrow
    else:
        new_repetitions = repetitions + 1
        if new_repetitions == 1:
            new_interval = 1
        elif new_repetitions == 2:
            new_interval = 6
        else:
            new_interval = int(interval * new_ef)

    return (new_ef, new_interval, new_repetitions)


def handle_correct_answer(
    db: Session,
    user_id: int,
    word_id: int,
) -> None:
    """
    Handle a correct answer - reset failure counter, update SM2 if word is mastered.

    Call this after updating skill mastery when the answer was correct.
    """
    state = get_or_create_review_state(db, user_id, word_id)

    # Reset consecutive failures on correct answer
    state.consecutive_failures = 0
    state.updated_at = datetime.utcnow()

    # Check if word is now mastered (all 4 skills >= 80%)
    word_status = get_word_status(db, user_id, word_id)

    if word_status in ('mastered', 'already_known'):
        # Update SM2 with quality 4 (correct after hesitation)
        # This is a reasonable default for exercise-based reviews
        new_ef, new_interval, new_reps = calculate_sm2(
            quality=4,
            easiness_factor=state.easiness_factor,
            interval=state.sm2_interval,
            repetitions=state.sm2_repetitions,
        )

        state.easiness_factor = new_ef
        state.sm2_interval = new_interval
        state.sm2_repetitions = new_reps
        state.next_review_date = date.today() + timedelta(days=new_interval)

    db.commit()


def handle_incorrect_answer(
    db: Session,
    user_id: int,
    word_id: int,
) -> bool:
    """
    Handle an incorrect answer - track consecutive failures.

    Returns True if word was demoted from mastered to in_progress.
    """
    state = get_or_create_review_state(db, user_id, word_id)

    state.consecutive_failures += 1
    state.updated_at = datetime.utcnow()

    demoted = False

    # If 3+ consecutive failures AND word was mastered → reset SM2
    if state.consecutive_failures >= 3:
        word_status = get_word_status(db, user_id, word_id)
        if word_status == 'mastered':
            # Reset SM2 - word will appear soon for review
            state.sm2_interval = 1
            state.sm2_repetitions = 0
            state.next_review_date = date.today()
            demoted = True
            # Note: The skill mastery scores handle the actual demotion
            # via the mastery.py update_mastery function decreasing scores

    db.commit()
    return demoted


def get_due_review_words(
    db: Session,
    user_id: int,
    scenario_id: Optional[int] = None,
    exclude_word_ids: Optional[List[int]] = None,
    limit: int = 10,
) -> List[Word]:
    """
    Get words that are due for review (next_review_date <= today).

    Only returns mastered/already_known words that have a review state.

    Args:
        db: Database session
        user_id: User ID
        scenario_id: Optional scenario to filter by
        exclude_word_ids: Word IDs to exclude (e.g., already in session)
        limit: Maximum number of words to return

    Returns:
        List of Word objects due for review
    """
    today = date.today()
    exclude_word_ids = exclude_word_ids or []

    # Query for due review states
    query = db.query(WordReviewState).filter(
        WordReviewState.user_id == user_id,
        WordReviewState.next_review_date <= today,
    )

    if exclude_word_ids:
        query = query.filter(~WordReviewState.word_id.in_(exclude_word_ids))

    # Order by most overdue first
    review_states = query.order_by(WordReviewState.next_review_date.asc()).all()

    # Get the actual words, filtering by scenario if needed
    words = []
    for state in review_states:
        if len(words) >= limit:
            break

        word = db.query(Word).filter(Word.id == state.word_id).first()
        if not word:
            continue

        # Filter by scenario if specified
        if scenario_id and word.scenario_id != scenario_id:
            continue

        # Verify word is still mastered (could have been demoted)
        word_status = get_word_status(db, user_id, word.id)
        if word_status in ('mastered', 'already_known'):
            words.append(word)

    return words


def count_due_review_words(
    db: Session,
    user_id: int,
    scenario_id: Optional[int] = None,
    exclude_word_ids: Optional[List[int]] = None,
) -> int:
    """
    Count words that are due for review.
    """
    words = get_due_review_words(db, user_id, scenario_id, exclude_word_ids, limit=1000)
    return len(words)


def count_mastered_words(
    db: Session,
    user_id: int,
    scenario_id: Optional[int] = None,
) -> int:
    """
    Count mastered words for a user, optionally filtered by scenario.
    """
    from app.models import WordSkillMastery

    # Get all words in scenario
    query = db.query(Word)
    if scenario_id:
        query = query.filter(Word.scenario_id == scenario_id)

    words = query.all()

    count = 0
    for word in words:
        status = get_word_status(db, user_id, word.id)
        if status in ('mastered', 'already_known'):
            count += 1

    return count


def initialize_word_for_review(
    db: Session,
    user_id: int,
    word_id: int,
) -> None:
    """
    Initialize a newly mastered word for the SM2 review system.

    Call this when a word first reaches mastery status.
    Sets initial review date to 1 day from now.
    """
    state = get_or_create_review_state(db, user_id, word_id)

    # Only initialize if this is a fresh entry (no review date yet)
    if state.next_review_date is None:
        state.sm2_interval = 1
        state.sm2_repetitions = 0
        state.next_review_date = date.today() + timedelta(days=1)
        state.updated_at = datetime.utcnow()
        db.commit()
