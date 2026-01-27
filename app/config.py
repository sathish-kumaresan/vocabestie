import json
from pathlib import Path
from pydantic_settings import BaseSettings


def load_oauth_credentials() -> tuple[str, str]:
    """Load OAuth credentials from oauth.json file."""
    oauth_file = Path(__file__).parent.parent / "oauth.json"
    if oauth_file.exists():
        with open(oauth_file) as f:
            data = json.load(f)
            return data.get("google_client_id", ""), data.get("google_client_secret", "")
    return "", ""


_google_client_id, _google_client_secret = load_oauth_credentials()


class Settings(BaseSettings):
    database_url: str = "postgresql://vocabestie:vocabestie@localhost:5433/vocabestie"

    # OAuth settings
    google_client_id: str = _google_client_id
    google_client_secret: str = _google_client_secret
    oauth_redirect_uri: str = "http://localhost:8000/auth/callback/google"

    # Session settings
    session_duration_days: int = 30
    session_cookie_name: str = "vocabestie_session"
    secret_key: str = "vocabestie-secret-key-change-in-production"

    class Config:
        env_file = ".env"


settings = Settings()
