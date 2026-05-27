from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from core.auth import create_access_token, get_current_user
from core.config import Settings, get_settings
from core.security import (
    hash_password,
    is_valid_email,
    normalize_email,
    validate_password_strength,
    verify_password,
)
from models.user import (
    AuthMessageResponse,
    AuthTokenResponse,
    LoginRequest,
    RegisterRequest,
    UserPublic,
)
from services import user_store

router = APIRouter()


@router.post("/register", response_model=AuthTokenResponse)
async def register(body: RegisterRequest, settings: Settings = Depends(get_settings)) -> AuthTokenResponse:
    if not is_valid_email(body.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address format.")

    if body.password != body.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match.")

    pwd_error = validate_password_strength(body.password)
    if pwd_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pwd_error)

    normalized = normalize_email(body.email)
    if user_store.get_user_by_email(settings, normalized):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Please log in instead.",
        )

    try:
        record = user_store.create_user(
            settings,
            full_name=body.full_name,
            email=normalized,
            password_hash=hash_password(body.password),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    token = create_access_token(settings, record.id, record.email)
    user = UserPublic(id=record.id, full_name=record.full_name, email=record.email)
    return AuthTokenResponse(access_token=token, user=user)


@router.post("/login", response_model=AuthTokenResponse)
async def login(body: LoginRequest, settings: Settings = Depends(get_settings)) -> AuthTokenResponse:
    if not is_valid_email(body.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address format.")

    record = user_store.get_user_by_email(settings, body.email)
    if record is None or not verify_password(body.password, record.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    token = create_access_token(settings, record.id, record.email)
    user = UserPublic(id=record.id, full_name=record.full_name, email=record.email)
    return AuthTokenResponse(access_token=token, user=user)


@router.get("/me", response_model=UserPublic)
async def me(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return current_user


@router.post("/logout", response_model=AuthMessageResponse)
async def logout(_current_user: UserPublic = Depends(get_current_user)) -> AuthMessageResponse:
    return AuthMessageResponse(message="Logged out successfully. Discard the client token.")
