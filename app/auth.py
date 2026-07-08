import hmac

from fastapi import HTTPException


def verify_app_key(x_app_key: str | None, expected_key: str) -> None:
    if x_app_key is None or not hmac.compare_digest(x_app_key, expected_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
