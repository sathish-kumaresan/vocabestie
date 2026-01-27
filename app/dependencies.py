"""
FastAPI dependencies for authentication and user identification.
"""

from typing import Optional
from fastapi import Request, Depends
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.models import User
from app.services.auth import get_session
from app.config import settings

# Guest user ID for unauthenticated users
GUEST_USER_ID = 1


def get_current_user(
    request: Request,
    db: DbSession = Depends(get_db)
) -> Optional[User]:
    """
    Extract session cookie, validate, and return the authenticated user.
    Returns None for anonymous/guest users.
    """
    session_token = request.cookies.get(settings.session_cookie_name)

    if not session_token:
        return None

    session = get_session(db, session_token)
    if not session:
        return None

    return session.user


def get_user_id(
    request: Request,
    db: DbSession = Depends(get_db)
) -> int:
    """
    Return the authenticated user's ID, or GUEST_USER_ID for anonymous users.
    This is the main dependency to replace hardcoded GUEST_USER_ID throughout the app.
    """
    user = get_current_user(request, db)
    if user:
        return user.id
    return GUEST_USER_ID


def get_auth_context(
    request: Request,
    db: DbSession = Depends(get_db)
) -> dict:
    """
    Get authentication context for templates.
    Returns dict with user info and authentication state.
    """
    user = get_current_user(request, db)
    return {
        "user": user,
        "is_authenticated": user is not None,
        "user_name": user.name if user else "Guest",
        "user_email": user.email if user else None,
    }
