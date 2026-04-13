import time

from service.api import fetch_session

TOKEN_TTL_SECONDS = 300


def should_refresh(expires_at: float, now: float | None = None) -> bool:
    current_time = now or time.time()
    return current_time >= expires_at - 60


def refresh_token(client: object, refresh_token_value: str) -> str:
    session = fetch_session(client, refresh_token_value)
    return session["access_token"]


class AuthService:
    def ensure_token(self, client: object, refresh_token_value: str, expires_at: float) -> str | None:
        if not should_refresh(expires_at):
            return None
        return refresh_token(client, refresh_token_value)
