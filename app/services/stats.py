"""
Statistics service for tracking streaks, time, and progress.
"""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    User, Word, Scenario, WordSkillMastery, UserWordStatus,
    UserStats, DailyPracticeLog
)
from app.services.mastery import PASS_THRESHOLD, SKILL_TYPES, get_word_mastery

# Guest user ID for unauthenticated users
GUEST_USER_ID = 1


def get_or_create_user_stats(db: Session, user_id: int = GUEST_USER_ID) -> UserStats:
    """Get or create user stats record."""
    stats = db.query(UserStats).filter(UserStats.user_id == user_id).first()
    if not stats:
        stats = UserStats(user_id=user_id)
        db.add(stats)
        db.commit()
        db.refresh(stats)
    return stats


def get_or_create_daily_log(
    db: Session,
    user_id: int = GUEST_USER_ID,
    practice_date: date = None
) -> DailyPracticeLog:
    """Get or create daily practice log for a date."""
    if practice_date is None:
        practice_date = date.today()

    log = db.query(DailyPracticeLog).filter(
        DailyPracticeLog.user_id == user_id,
        DailyPracticeLog.practice_date == practice_date
    ).first()

    if not log:
        log = DailyPracticeLog(
            user_id=user_id,
            practice_date=practice_date
        )
        db.add(log)
        db.commit()
        db.refresh(log)
    return log


def update_streak(db: Session, user_id: int = GUEST_USER_ID) -> int:
    """
    Update user's streak based on practice activity.
    Returns the current streak count.
    """
    stats = get_or_create_user_stats(db, user_id)
    today = date.today()

    if stats.last_practice_date is None:
        # First practice ever
        stats.current_streak = 1
        stats.longest_streak = 1
    elif stats.last_practice_date == today:
        # Already practiced today, streak unchanged
        pass
    elif stats.last_practice_date == today - timedelta(days=1):
        # Practiced yesterday, increment streak
        stats.current_streak += 1
        if stats.current_streak > stats.longest_streak:
            stats.longest_streak = stats.current_streak
    else:
        # Missed a day, reset streak
        stats.current_streak = 1

    stats.last_practice_date = today
    stats.updated_at = datetime.utcnow()
    db.commit()

    return stats.current_streak


def record_session_completion(
    db: Session,
    user_id: int = GUEST_USER_ID,
    words_practiced: int = 0,
    exercises_completed: int = 0,
    time_seconds: int = 0,
) -> Dict[str, Any]:
    """
    Record a completed learning session.
    Updates daily log, streak, and overall stats.
    """
    today = date.today()

    # Update daily log
    daily_log = get_or_create_daily_log(db, user_id, today)
    daily_log.words_practiced += words_practiced
    daily_log.exercises_completed += exercises_completed
    daily_log.practice_time_seconds += time_seconds

    # Update streak
    current_streak = update_streak(db, user_id)

    # Update overall stats
    stats = get_or_create_user_stats(db, user_id)
    stats.total_practice_time_seconds += time_seconds

    # Count total mastered words
    stats.total_words_mastered = count_mastered_words(db, user_id)

    db.commit()

    return {
        "current_streak": current_streak,
        "longest_streak": stats.longest_streak,
        "words_practiced_today": daily_log.words_practiced,
        "exercises_completed_today": daily_log.exercises_completed,
        "time_today_seconds": daily_log.practice_time_seconds,
    }


def count_mastered_words(db: Session, user_id: int = GUEST_USER_ID) -> int:
    """Count words where all 4 skills are at or above pass threshold."""
    # Get all words with their skill masteries
    masteries = db.query(
        WordSkillMastery.word_id,
        func.count(WordSkillMastery.skill_type).label('skill_count'),
        func.min(WordSkillMastery.mastery_score).label('min_score')
    ).filter(
        WordSkillMastery.user_id == user_id,
        WordSkillMastery.mastery_score >= PASS_THRESHOLD
    ).group_by(WordSkillMastery.word_id).all()

    # Word is mastered if all 4 skills are passed
    mastered_count = sum(1 for m in masteries if m.skill_count == 4)
    return mastered_count


def get_user_statistics(db: Session, user_id: int = GUEST_USER_ID) -> Dict[str, Any]:
    """Get comprehensive user statistics for display."""
    stats = get_or_create_user_stats(db, user_id)
    today = date.today()

    # Get today's practice log
    daily_log = db.query(DailyPracticeLog).filter(
        DailyPracticeLog.user_id == user_id,
        DailyPracticeLog.practice_date == today
    ).first()

    # Count words by status
    total_words = db.query(func.count(Word.id)).scalar() or 0

    # Count words with any practice
    words_started = db.query(func.count(func.distinct(WordSkillMastery.word_id))).filter(
        WordSkillMastery.user_id == user_id
    ).scalar() or 0

    # Count mastered words
    mastered_words = count_mastered_words(db, user_id)

    # Count "already known" words
    already_known = db.query(func.count(UserWordStatus.id)).filter(
        UserWordStatus.user_id == user_id,
        UserWordStatus.status == 'already_known'
    ).scalar() or 0

    # Total exercises completed (sum from all daily logs)
    total_exercises = db.query(func.sum(DailyPracticeLog.exercises_completed)).filter(
        DailyPracticeLog.user_id == user_id
    ).scalar() or 0

    # Format practice time
    total_minutes = stats.total_practice_time_seconds // 60
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours > 0:
        time_str = f"{hours}h {minutes}m"
    else:
        time_str = f"{minutes} min"

    return {
        "current_streak": stats.current_streak,
        "longest_streak": stats.longest_streak,
        "total_words": total_words,
        "words_started": words_started,
        "words_mastered": mastered_words,
        "words_already_known": already_known,
        "words_not_started": total_words - words_started - already_known,
        "total_practice_time": time_str,
        "total_practice_seconds": stats.total_practice_time_seconds,
        "total_exercises": total_exercises,
        "practiced_today": daily_log is not None,
        "exercises_today": daily_log.exercises_completed if daily_log else 0,
    }


def get_scenario_progress(
    db: Session,
    scenario_id: int,
    user_id: int = GUEST_USER_ID
) -> Dict[str, Any]:
    """Get progress statistics for a specific scenario."""
    # Get all words in scenario
    words = db.query(Word).filter(Word.scenario_id == scenario_id).all()
    total_words = len(words)

    if total_words == 0:
        return {
            "total_words": 0,
            "mastered": 0,
            "in_progress": 0,
            "not_started": 0,
            "already_known": 0,
            "progress_percent": 0,
        }

    mastered = 0
    in_progress = 0
    not_started = 0
    already_known = 0
    total_mastery = 0.0  # Sum of all word masteries for progress calculation

    for word in words:
        # Check for already_known override
        override = db.query(UserWordStatus).filter(
            UserWordStatus.user_id == user_id,
            UserWordStatus.word_id == word.id,
            UserWordStatus.status == 'already_known'
        ).first()

        if override:
            already_known += 1
            total_mastery += 1.0  # Count as 100% mastered
            continue

        # Get skill masteries
        skills = get_word_mastery(db, user_id, word.id)
        avg_skill_mastery = sum(skills.values()) / len(skills) if skills else 0.0
        total_mastery += avg_skill_mastery

        if all(score == 0.0 for score in skills.values()):
            not_started += 1
        elif all(score >= PASS_THRESHOLD for score in skills.values()):
            mastered += 1
        else:
            in_progress += 1

    # Calculate progress based on average mastery across all words
    progress_percent = int((total_mastery / total_words) * 100) if total_words > 0 else 0

    return {
        "total_words": total_words,
        "mastered": mastered,
        "in_progress": in_progress,
        "not_started": not_started,
        "already_known": already_known,
        "progress_percent": progress_percent,
    }


def get_word_status_for_display(
    db: Session,
    word_id: int,
    user_id: int = GUEST_USER_ID
) -> Dict[str, Any]:
    """Get word status and skill details for UI display."""
    # Check for already_known override
    override = db.query(UserWordStatus).filter(
        UserWordStatus.user_id == user_id,
        UserWordStatus.word_id == word_id,
        UserWordStatus.status == 'already_known'
    ).first()

    if override:
        return {
            "status": "already_known",
            "status_label": "Already Known",
            "status_color": "gray",
            "skills": {},
            "overall_progress": 100,
        }

    # Get skill masteries
    skills = get_word_mastery(db, user_id, word_id)

    # Determine status
    if all(score == 0.0 for score in skills.values()):
        status = "not_started"
        status_label = "Not Started"
        status_color = "gray"
    elif all(score >= PASS_THRESHOLD for score in skills.values()):
        status = "mastered"
        status_label = "Mastered"
        status_color = "green"
    else:
        status = "in_progress"
        status_label = "In Progress"
        status_color = "yellow"

    # Calculate overall progress
    avg_mastery = sum(skills.values()) / len(skills) if skills else 0
    overall_progress = int(avg_mastery * 100)

    return {
        "status": status,
        "status_label": status_label,
        "status_color": status_color,
        "skills": {
            "read": int(skills.get("read", 0) * 100),
            "listen": int(skills.get("listen", 0) * 100),
            "speak": int(skills.get("speak", 0) * 100),
            "write": int(skills.get("write", 0) * 100),
        },
        "overall_progress": overall_progress,
    }


def mark_word_as_known(
    db: Session,
    word_id: int,
    user_id: int = GUEST_USER_ID
) -> bool:
    """Mark a word as already known."""
    # Check if override already exists
    override = db.query(UserWordStatus).filter(
        UserWordStatus.user_id == user_id,
        UserWordStatus.word_id == word_id,
    ).first()

    if override:
        override.status = 'already_known'
        override.marked_at = datetime.utcnow()
    else:
        override = UserWordStatus(
            user_id=user_id,
            word_id=word_id,
            status='already_known',
            marked_at=datetime.utcnow()
        )
        db.add(override)

    db.commit()
    return True


def unmark_word_as_known(
    db: Session,
    word_id: int,
    user_id: int = GUEST_USER_ID
) -> bool:
    """Remove the already known status from a word."""
    override = db.query(UserWordStatus).filter(
        UserWordStatus.user_id == user_id,
        UserWordStatus.word_id == word_id,
    ).first()

    if override:
        override.status = 'active'
        override.marked_at = None
        db.commit()

    return True
