from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from core.config import Settings, get_settings
from core.security import normalize_email
from models.user import UserPublic
from services import user_store

_bearer = HTTPBearer(auto_error=False)


def create_access_token(settings: Settings, user_id: str, email: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {"sub": user_id, "email": normalize_email(email), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(settings: Settings, token: str) -> dict[str, str]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = str(payload.get("sub") or "")
        email = str(payload.get("email") or "")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return {"user_id": user_id, "email": email}
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc


async def get_current_user(
    settings: Settings = Depends(get_settings),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserPublic:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    claims = decode_access_token(settings, credentials.credentials)
    user = user_store.get_user_by_id(settings, claims["user_id"])
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return UserPublic(id=user.id, full_name=user.full_name, email=user.email)


CurrentUser = Annotated[UserPublic, Depends(get_current_user)]
