"""
Authentication service for session management and user operations.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session as DbSession

from app.models import User, Session, WordSkillMastery, UserWordStatus, UserStats, DailyPracticeLog
from app.config import settings


def generate_session_token() -> str:
    """Generate a cryptographically secure session token."""
    return secrets.token_hex(32)


def create_session(
    db: DbSession,
    user_id: int,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None
) -> str:
    """
    Create a new session for a user.
    Returns the session token to be stored in a cookie.
    """
    token = generate_session_token()
    expires_at = datetime.utcnow() + timedelta(days=settings.session_duration_days)

    session = Session(
        id=token,
        user_id=user_id,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address
    )
    db.add(session)
    db.commit()

    return token


def get_session(db: DbSession, token: str) -> Optional[Session]:
    """
    Retrieve and validate a session by token.
    Returns None if session doesn't exist or is expired.
    """
    session = db.query(Session).filter(Session.id == token).first()

    if not session:
        return None

    # Check if session has expired
    if session.expires_at < datetime.utcnow():
        # Delete expired session
        db.delete(session)
        db.commit()
        return None

    return session


def delete_session(db: DbSession, token: str) -> bool:
    """Delete a session (logout)."""
    session = db.query(Session).filter(Session.id == token).first()
    if session:
        db.delete(session)
        db.commit()
        return True
    return False


def cleanup_expired_sessions(db: DbSession) -> int:
    """Remove all expired sessions. Returns count of deleted sessions."""
    now = datetime.utcnow()
    result = db.query(Session).filter(Session.expires_at < now).delete()
    db.commit()
    return result


def get_user_by_google_id(db: DbSession, google_id: str) -> Optional[User]:
    """Find a user by their Google ID."""
    return db.query(User).filter(
        User.auth_provider == "google",
        User.auth_provider_id == google_id
    ).first()


def get_or_create_user_from_google(
    db: DbSession,
    google_user_info: Dict[str, Any]
) -> tuple[User, bool]:
    """
    Find existing user by Google ID or create new one.
    Returns tuple of (user, is_new_user).
    """
    google_id = google_user_info.get("sub")
    email = google_user_info.get("email")
    name = google_user_info.get("name")

    # Try to find existing user
    user = get_user_by_google_id(db, google_id)

    if user:
        # Update last login
        user.last_login = datetime.utcnow()
        # Update name/email in case they changed on Google's side
        if email:
            user.email = email
        if name:
            user.name = name
        db.commit()
        return user, False

    # Create new user
    user = User(
        email=email,
        name=name,
        auth_provider="google",
        auth_provider_id=google_id,
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user, True


def migrate_guest_data(
    db: DbSession,
    from_user_id: int,
    to_user_id: int
) -> Dict[str, int]:
    """
    Transfer all learning progress from guest user to authenticated user.
    Called once during first OAuth login.

    Returns dict with counts of migrated records.
    """
    migrated = {
        "word_skills": 0,
        "word_status": 0,
        "daily_logs": 0,
        "stats_merged": False
    }

    # 1. Migrate WordSkillMastery records
    skills = db.query(WordSkillMastery).filter(
        WordSkillMastery.user_id == from_user_id
    ).all()
    for skill in skills:
        skill.user_id = to_user_id
        migrated["word_skills"] += 1

    # 2. Migrate UserWordStatus records
    statuses = db.query(UserWordStatus).filter(
        UserWordStatus.user_id == from_user_id
    ).all()
    for status in statuses:
        status.user_id = to_user_id
        migrated["word_status"] += 1

    # 3. Migrate DailyPracticeLog records
    logs = db.query(DailyPracticeLog).filter(
        DailyPracticeLog.user_id == from_user_id
    ).all()
    for log in logs:
        log.user_id = to_user_id
        migrated["daily_logs"] += 1

    # 4. Merge UserStats
    guest_stats = db.query(UserStats).filter(
        UserStats.user_id == from_user_id
    ).first()

    if guest_stats:
        # Get or create stats for new user
        new_stats = db.query(UserStats).filter(
            UserStats.user_id == to_user_id
        ).first()

        if not new_stats:
            new_stats = UserStats(user_id=to_user_id)
            db.add(new_stats)

        # Transfer stats
        new_stats.current_streak = guest_stats.current_streak
        new_stats.longest_streak = max(
            new_stats.longest_streak or 0,
            guest_stats.longest_streak or 0
        )
        new_stats.total_practice_time_seconds = guest_stats.total_practice_time_seconds or 0
        new_stats.total_words_mastered = guest_stats.total_words_mastered or 0
        new_stats.last_practice_date = guest_stats.last_practice_date

        # Delete guest stats after merge
        db.delete(guest_stats)
        migrated["stats_merged"] = True

    db.commit()
    return migrated
