"""
Mastery calculation service for the 4-skill learning system.

Each word has 4 skills: read, listen, speak, write
Each skill has a mastery_score from 0.0 to 1.0
Threshold for "passed": 0.8
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models import Word, WordSkillMastery, UserWordStatus

PASS_THRESHOLD = 0.8
SKILL_TYPES = ['read', 'listen', 'speak', 'write']


def update_mastery(
    db: Session,
    user_id: int,
    word_id: int,
    skill_type: str,
    is_correct: bool,
) -> float:
    """
    Update mastery score after an exercise attempt.

    Returns the new mastery score.
    """
    # Get or create mastery record
    mastery = db.query(WordSkillMastery).filter(
        WordSkillMastery.user_id == user_id,
        WordSkillMastery.word_id == word_id,
        WordSkillMastery.skill_type == skill_type,
    ).first()

    if not mastery:
        mastery = WordSkillMastery(
            user_id=user_id,
            word_id=word_id,
            skill_type=skill_type,
            mastery_score=0.0,
            practice_count=0,
            correct_count=0,
        )
        db.add(mastery)

    # Calculate new score
    current_score = mastery.mastery_score or 0.0

    if is_correct:
        # Increase mastery - bigger jump when score is low
        new_score = current_score + (1 - current_score) * 0.3
        mastery.correct_count = (mastery.correct_count or 0) + 1
    else:
        # Decrease mastery
        new_score = current_score * 0.7

    # Clamp to [0.0, 1.0]
    new_score = max(0.0, min(1.0, new_score))

    # Update record
    mastery.mastery_score = new_score
    mastery.practice_count = (mastery.practice_count or 0) + 1
    mastery.last_practiced = datetime.utcnow()
    mastery.updated_at = datetime.utcnow()

    db.commit()

    return new_score


def get_word_mastery(
    db: Session,
    user_id: int,
    word_id: int,
) -> dict:
    """
    Get mastery scores for all 4 skills of a word.

    Returns dict like: {'read': 0.5, 'listen': 0.3, 'speak': 0.0, 'write': 0.0}
    """
    masteries = db.query(WordSkillMastery).filter(
        WordSkillMastery.user_id == user_id,
        WordSkillMastery.word_id == word_id,
    ).all()

    result = {skill: 0.0 for skill in SKILL_TYPES}
    for m in masteries:
        result[m.skill_type] = m.mastery_score or 0.0

    return result


def get_word_status(
    db: Session,
    user_id: int,
    word_id: int,
) -> str:
    """
    Derive word status from skill mastery.

    Returns: 'not_started', 'in_progress', 'mastered', or 'already_known'
    """
    # Check for manual override
    override = db.query(UserWordStatus).filter(
        UserWordStatus.user_id == user_id,
        UserWordStatus.word_id == word_id,
    ).first()

    if override and override.status == 'already_known':
        return 'already_known'

    # Get skill mastery
    skills = get_word_mastery(db, user_id, word_id)

    # Check if not started
    if all(score == 0.0 for score in skills.values()):
        return 'not_started'

    # Check if mastered (all skills >= threshold)
    if all(score >= PASS_THRESHOLD for score in skills.values()):
        return 'mastered'

    return 'in_progress'


def get_weakest_skill(
    db: Session,
    user_id: int,
    word_id: int,
    testing_mode: bool = False,  # Set to True for testing all exercise types
) -> str:
    """
    Get the skill with lowest mastery for a word.
    Used to pick which exercise type to show.

    Returns: 'read', 'listen', 'speak', or 'write'
    """
    import random

    # TESTING MODE: Randomly pick a skill to allow testing all exercise types
    if testing_mode:
        return random.choice(SKILL_TYPES)

    # PRODUCTION MODE: Adaptive skill selection based on mastery
    skills = get_word_mastery(db, user_id, word_id)

    # Find minimum score
    min_skill = min(skills, key=skills.get)
    min_score = skills[min_skill]

    # If all skills are at the same low level, follow the learning order
    same_score_skills = [s for s, score in skills.items() if score == min_score]

    # Preferred order: read -> listen -> speak -> write
    for skill in SKILL_TYPES:
        if skill in same_score_skills:
            return skill

    return min_skill


def apply_time_decay(
    db: Session,
    user_id: int,
    word_id: int,
    skill_type: str,
) -> float:
    """
    Apply time-based decay to mastery score.
    Mastery decreases if not practiced for a while.

    Returns the decayed score.
    """
    mastery = db.query(WordSkillMastery).filter(
        WordSkillMastery.user_id == user_id,
        WordSkillMastery.word_id == word_id,
        WordSkillMastery.skill_type == skill_type,
    ).first()

    if not mastery or not mastery.last_practiced:
        return 0.0

    # Calculate days since last practice
    days_since = (datetime.utcnow() - mastery.last_practiced).days

    if days_since <= 1:
        decay_factor = 1.0
    elif days_since <= 7:
        decay_factor = 0.95  # 5% decay per week
    elif days_since <= 30:
        decay_factor = 0.85  # 15% decay per month
    else:
        decay_factor = 0.7  # 30% decay after a month

    decayed_score = mastery.mastery_score * decay_factor
    return max(0.0, decayed_score)
