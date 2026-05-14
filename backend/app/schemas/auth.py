from pydantic import BaseModel, Field, field_validator
from datetime import datetime


def _validate_email_loose(v: str) -> str:
    """Accept any email-shaped string, including .local TLDs (which strict
    EmailStr rejects). Good enough for app accounts."""
    if not v or "@" not in v or len(v) > 254:
        raise ValueError("invalid email format")
    local, _, domain = v.rpartition("@")
    if not local or not domain or "." not in domain:
        raise ValueError("invalid email format")
    return v.strip().lower()


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def _email_loose(cls, v: str) -> str:
        return _validate_email_loose(v)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: "UserOut"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=200)
    full_name: str = ""
    role: str = "viewer"

    @field_validator("email")
    @classmethod
    def _email_loose(cls, v: str) -> str:
        return _validate_email_loose(v)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=200)


TokenResponse.model_rebuild()
