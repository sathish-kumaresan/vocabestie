"""
Authentication router for Google OAuth.
"""

import secrets
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session as DbSession
from starlette.config import Config

from app.database import get_db
from app.config import settings
from app.services.auth import (
    create_session,
    delete_session,
    get_or_create_user_from_google,
    migrate_guest_data,
)
from app.dependencies import GUEST_USER_ID, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

# Configure OAuth
config = Config(environ={
    "GOOGLE_CLIENT_ID": settings.google_client_id,
    "GOOGLE_CLIENT_SECRET": settings.google_client_secret,
})

oauth = OAuth(config)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/login/google")
async def login_google(request: Request):
    """
    Initiate Google OAuth login flow.
    Redirects user to Google's consent screen.
    """
    # Generate state token to prevent CSRF
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    print(f"DEBUG: Setting oauth_state: {state}")
    print(f"DEBUG: Session keys after set: {request.session.keys()}")

    redirect_uri = settings.oauth_redirect_uri
    return await oauth.google.authorize_redirect(request, redirect_uri, state=state)


@router.get("/callback/google")
async def callback_google(request: Request, db: DbSession = Depends(get_db)):
    """
    Handle Google OAuth callback.
    Creates/finds user, creates session, merges guest data if new user.
    """
    try:
        # Exchange code for token
        print(f"DEBUG: Callback received. Query params: {request.query_params}")
        print(f"DEBUG: Session keys: {request.session.keys()}")
        print(f"DEBUG: Session oauth_state: {request.session.get('oauth_state')}")
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")

    # Get user info from ID token
    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(status_code=400, detail="Could not get user info from Google")

    # Find or create user
    user, is_new_user = get_or_create_user_from_google(db, user_info)

    # If new user, migrate guest data
    if is_new_user:
        migrate_guest_data(db, GUEST_USER_ID, user.id)

    # Create server-side session
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    session_token = create_session(db, user.id, user_agent, ip_address)

    # Redirect to settings page with session cookie
    response = RedirectResponse(url="/settings", status_code=302)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
        max_age=settings.session_duration_days * 24 * 60 * 60,
    )

    return response


@router.post("/logout")
async def logout(request: Request, db: DbSession = Depends(get_db)):
    """
    Log out the current user.
    Deletes session and clears cookie.
    """
    session_token = request.cookies.get(settings.session_cookie_name)

    if session_token:
        delete_session(db, session_token)

    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key=settings.session_cookie_name)

    return response


@router.get("/me")
async def get_me(request: Request, db: DbSession = Depends(get_db)):
    """
    Get current user info (for HTMX partial updates).
    """
    user = get_current_user(request, db)
    if not user:
        return {"authenticated": False}

    return {
        "authenticated": True,
        "name": user.name,
        "email": user.email,
    }
