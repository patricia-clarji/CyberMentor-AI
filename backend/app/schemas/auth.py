import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=2, max_length=120)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, value: str) -> str:
        classes = [
            any(character.islower() for character in value),
            any(character.isupper() for character in value),
            any(character.isdigit() for character in value),
            any(not character.isalnum() for character in value),
        ]
        if sum(classes) < 3:
            raise ValueError("Password must use at least three character classes.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(TokenRequest):
    password: str = Field(min_length=12, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class OrganizationSummary(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    kind: str
    roles: list[str]


class UserSummary(BaseModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str
    email_verified: bool
    active_organization_id: uuid.UUID
    organizations: list[OrganizationSummary]


class SessionSummary(BaseModel):
    id: uuid.UUID
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    current: bool
    user_agent: str | None
