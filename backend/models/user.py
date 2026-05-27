from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class UserPublic(BaseModel):
    id: str
    full_name: str
    email: EmailStr


class UserRecord(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    password_hash: str
    created_at: str


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class AuthMessageResponse(BaseModel):
    message: str
