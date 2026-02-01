"""
Learning Session Manager Service.

Handles the daily learning flow:
1. Word introduction (10 words)
2. Exercise queue (40 new + optionally 10 review = 40 or 50 total)
3. Session resume and completion
4. "Learn More" flow

Key concepts:
- Gate for reviews: mastered_count >= 10 AND due_review_count >= 10
- Progress is DERIVED from queue state (not stored counters)
- Queue ordering: queue_order ASC only (not by queue_type)
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import (
    Word,
    LearningSession,
    ExerciseQueue,
    UserWordStatus,
)
from app.services.mastery import get_word_status, SKILL_TYPES, update_mastery
from app.services.sm2 import (
    get_due_review_words,
    count_mastered_words,
    handle_correct_answer,
    handle_incorrect_answer,
    initialize_word_for_review,
)


# Skills cycle for review exercises: R, W, S, L, R, W, S, L, R, W
REVIEW_SKILL_CYCLE = ['read', 'write', 'speak', 'listen'] * 3  # 12 items (only need 10)


def get_active_session(
    db: Session,
    user_id: int,
) -> Optional[LearningSession]:
    """Get the user's currently active learning session, if any."""
    return db.query(LearningSession).filter(
        LearningSession.user_id == user_id,
        LearningSession.status == 'active',
    ).first()


def get_new_words_for_session(
    db: Session,
    user_id: int,
    scenario_id: int,
    exclude_word_ids: Optional[List[int]] = None,
    limit: int = 10,
) -> List[Word]:
    """
    Get new words for a learning session.

    Selection pool:
    - status: not_started, in_progress (0%, 25%, 50%, 75%)

    Exclude:
    - mastered/known (100%)
    - words already in pending queue
    """
    exclude_word_ids = exclude_word_ids or []

    # Get all words in scenario ordered by display_order/id
    all_words = db.query(Word).filter(
        Word.scenario_id == scenario_id,
    ).order_by(Word.display_order.asc().nullslast(), Word.id.asc()).all()

    words = []
    for word in all_words:
        if len(words) >= limit:
            break

        if word.id in exclude_word_ids:
            continue

        status = get_word_status(db, user_id, word.id)
        if status in ('not_started', 'in_progress'):
            words.append(word)

    return words


def create_learning_session(
    db: Session,
    user_id: int,
    scenario_id: int,
    intro_word_ids: List[int],
) -> LearningSession:
    """
    Create a new learning session with exercise queue.

    Gate for 50 exercises:
    - mastered_word_count >= 10 AND
    - due_review_word_count >= 10

    If gate passes: 40 new + 10 review = 50
    If gate fails: 40 new only

    Args:
        db: Database session
        user_id: User ID
        scenario_id: Scenario ID
        intro_word_ids: The 10 word IDs from intro (after any mark-as-known replacements)
    """
    # Get the actual word objects
    new_words = db.query(Word).filter(Word.id.in_(intro_word_ids)).all()
    # Maintain order from intro_word_ids
    word_map = {w.id: w for w in new_words}
    new_words = [word_map[wid] for wid in intro_word_ids if wid in word_map]

    if len(new_words) < 10:
        # Not enough new words - use what we have
        pass

    # Check gate conditions
    mastered_count = count_mastered_words(db, user_id, scenario_id)
    due_words = get_due_review_words(
        db, user_id, scenario_id,
        exclude_word_ids=intro_word_ids,
        limit=10
    )

    include_review = (mastered_count >= 10 and len(due_words) >= 10)
    total_exercises = 50 if include_review else 40

    # Create session
    session = LearningSession(
        user_id=user_id,
        scenario_id=scenario_id,
        total_exercises=total_exercises,
        status='active',
    )
    db.add(session)
    db.flush()  # Get session.id

    # Create exercise entries list
    exercises_to_create = []

    # 1. New word exercises: 10 words × 4 skills
    for word in new_words:
        for skill in SKILL_TYPES:  # read, listen, speak, write
            exercises_to_create.append({
                'word_id': word.id,
                'skill_type': skill,
                'queue_type': 'new'
            })

    # 2. Review exercises: 10 words (if gate passed)
    if include_review:
        review_words = due_words[:10]
        for i, word in enumerate(review_words):
            skill = REVIEW_SKILL_CYCLE[i]
            exercises_to_create.append({
                'word_id': word.id,
                'skill_type': skill,
                'queue_type': 'review'
            })
            
    # 3. Randomize the order
    import random
    random.shuffle(exercises_to_create)

    # 4. Create DB entries with sequential queue_order
    for i, data in enumerate(exercises_to_create):
        entry = ExerciseQueue(
            session_id=session.id,
            user_id=user_id,
            word_id=data['word_id'],
            skill_type=data['skill_type'],
            queue_type=data['queue_type'],
            queue_order=i,
            status='pending',
        )
        db.add(entry)

    db.commit()
    return session


def get_session_progress(db: Session, session_id: int) -> Dict[str, Any]:
    """
    Derive progress from queue state - NOT stored counters.

    Returns:
    {
        'total': 40 or 50,
        'completed': count of status='completed',
        'skipped': count of status='skipped',
        'pending': count of status='pending',
        'progress_percent': (completed + skipped) / total * 100,
        'correct_count': count of was_correct=True,
    }
    """
    session = db.query(LearningSession).get(session_id)
    if not session:
        return {'total': 0, 'completed': 0, 'skipped': 0, 'pending': 0, 'progress_percent': 0, 'correct_count': 0}

    exercises = db.query(ExerciseQueue).filter(
        ExerciseQueue.session_id == session_id,
    ).all()

    completed = sum(1 for e in exercises if e.status == 'completed')
    skipped = sum(1 for e in exercises if e.status == 'skipped')
    pending = sum(1 for e in exercises if e.status == 'pending')
    correct = sum(1 for e in exercises if e.was_correct is True)

    total = session.total_exercises
    progress_percent = int((completed + skipped) / total * 100) if total > 0 else 0

    return {
        'total': total,
        'completed': completed,
        'skipped': skipped,
        'pending': pending,
        'progress_percent': progress_percent,
        'correct_count': correct,
    }


def get_next_exercise(db: Session, session_id: int) -> Optional[ExerciseQueue]:
    """
    Get the next pending exercise in queue order.

    IMPORTANT: Order ONLY by queue_order ASC, never by queue_type.
    """
    return db.query(ExerciseQueue).filter(
        ExerciseQueue.session_id == session_id,
        ExerciseQueue.status == 'pending',
    ).order_by(
        ExerciseQueue.queue_order.asc()
    ).first()


def get_exercise_by_order(
    db: Session,
    session_id: int,
    queue_order: int,
) -> Optional[ExerciseQueue]:
    """Get a specific exercise by queue order (for Prev/Next navigation)."""
    return db.query(ExerciseQueue).filter(
        ExerciseQueue.session_id == session_id,
        ExerciseQueue.queue_order == queue_order,
    ).first()


def complete_exercise(
    db: Session,
    exercise_id: int,
    was_correct: bool,
    user_id: int,
) -> None:
    """
    Mark an exercise as completed and update mastery/SM2.
    """
    exercise = db.query(ExerciseQueue).get(exercise_id)
    if not exercise or exercise.user_id != user_id:
        return

    # Update exercise status
    exercise.status = 'completed'
    exercise.completed_at = datetime.utcnow()
    exercise.was_correct = was_correct

    # Update skill mastery
    update_mastery(
        db, user_id, exercise.word_id,
        exercise.skill_type, was_correct
    )

    # Update SM2 state
    if was_correct:
        handle_correct_answer(db, user_id, exercise.word_id)

        # Check if word just became mastered
        word_status = get_word_status(db, user_id, exercise.word_id)
        if word_status == 'mastered':
            initialize_word_for_review(db, user_id, exercise.word_id)
    else:
        handle_incorrect_answer(db, user_id, exercise.word_id)

    # Check if session is complete
    session = db.query(LearningSession).get(exercise.session_id)
    pending_count = db.query(ExerciseQueue).filter(
        ExerciseQueue.session_id == exercise.session_id,
        ExerciseQueue.status == 'pending',
    ).count()

    if pending_count == 0:
        session.status = 'completed'
        session.completed_at = datetime.utcnow()

    db.commit()


def mark_word_known_during_intro(
    db: Session,
    user_id: int,
    word_id: int,
    scenario_id: int,
    current_intro_word_ids: List[int],
) -> Dict[str, Any]:
    """
    Mark word as known during intro and get replacement.

    Returns: {
        'success': True/False,
        'replacement_word': Word or None,
        'updated_word_ids': List[int] (new list of 10 word IDs)
    }
    """
    # Mark word as known
    existing = db.query(UserWordStatus).filter(
        UserWordStatus.user_id == user_id,
        UserWordStatus.word_id == word_id,
    ).first()

    if existing:
        existing.status = 'already_known'
        existing.marked_at = datetime.utcnow()
    else:
        status = UserWordStatus(
            user_id=user_id,
            word_id=word_id,
            status='already_known',
            marked_at=datetime.utcnow(),
        )
        db.add(status)

    # Initialize for SM2 review
    initialize_word_for_review(db, user_id, word_id)

    # Remove from list and find replacement
    updated_ids = [wid for wid in current_intro_word_ids if wid != word_id]

    # Find one replacement word
    exclude_ids = set(current_intro_word_ids)
    replacement = get_new_words_for_session(
        db, user_id, scenario_id,
        exclude_word_ids=list(exclude_ids),
        limit=1,
    )

    replacement_word = None
    if replacement:
        replacement_word = replacement[0]
        updated_ids.append(replacement_word.id)

    db.commit()

    return {
        'success': True,
        'replacement_word': replacement_word,
        'updated_word_ids': updated_ids,
    }


def mark_word_known_during_practice(
    db: Session,
    session_id: int,
    word_id: int,
    user_id: int,
) -> int:
    """
    Mark word as known during exercise session.

    - Update word to known status
    - Skip ALL remaining queue items for that word in this session
    - NO undo within session

    Returns: Number of exercises skipped
    """
    # Mark word as known
    existing = db.query(UserWordStatus).filter(
        UserWordStatus.user_id == user_id,
        UserWordStatus.word_id == word_id,
    ).first()

    if existing:
        existing.status = 'already_known'
        existing.marked_at = datetime.utcnow()
    else:
        status = UserWordStatus(
            user_id=user_id,
            word_id=word_id,
            status='already_known',
            marked_at=datetime.utcnow(),
        )
        db.add(status)

    # Initialize for SM2 review
    initialize_word_for_review(db, user_id, word_id)

    # Skip remaining exercises for this word
    pending_for_word = db.query(ExerciseQueue).filter(
        ExerciseQueue.session_id == session_id,
        ExerciseQueue.word_id == word_id,
        ExerciseQueue.status == 'pending',
    ).all()

    skipped_count = 0
    for exercise in pending_for_word:
        exercise.status = 'skipped'
        exercise.completed_at = datetime.utcnow()
        skipped_count += 1

    # Check if session is now complete
    session = db.query(LearningSession).get(session_id)
    pending_count = db.query(ExerciseQueue).filter(
        ExerciseQueue.session_id == session_id,
        ExerciseQueue.status == 'pending',
    ).count()

    if pending_count == 0:
        session.status = 'completed'
        session.completed_at = datetime.utcnow()

    db.commit()
    return skipped_count


def complete_current_session(db: Session, user_id: int) -> Optional[LearningSession]:
    """Mark the current active session as completed."""
    session = get_active_session(db, user_id)
    if session:
        session.status = 'completed'
        session.completed_at = datetime.utcnow()
        db.commit()
    return session


def get_or_resume_session(
    db: Session,
    user_id: int,
    scenario_id: int,
) -> Dict[str, Any]:
    """
    Resume active session or prepare for new one.

    Returns: {
        'action': 'resume' or 'new',
        'session': LearningSession or None,
        'skip_intro': True/False,
    }
    """
    active_session = get_active_session(db, user_id)

    if active_session and active_session.scenario_id == scenario_id:
        return {
            'action': 'resume',
            'session': active_session,
            'skip_intro': True,
        }

    # If there's an active session for a different scenario, complete it first
    if active_session:
        active_session.status = 'completed'
        active_session.completed_at = datetime.utcnow()
        db.commit()

    # No active session - need to show intro
    return {
        'action': 'new',
        'session': None,
        'skip_intro': False,
    }
