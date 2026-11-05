from pydantic import BaseModel, Field, field_validator


def _email(value: str) -> str:
    normalized = value.strip().lower()
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise ValueError("Enter a valid email address.")
    return normalized


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)

    _validate_email = field_validator("email")(_email)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    _validate_email = field_validator("email")(_email)


class VerifyOtpRequest(BaseModel):
    challenge_id: str
    code: str = Field(min_length=6, max_length=6)


class AuthResponse(BaseModel):
    message: str
    challenge_id: str | None = None
