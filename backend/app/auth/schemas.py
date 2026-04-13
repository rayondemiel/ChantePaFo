from pydantic import BaseModel, EmailStr, Field, field_validator

from app.moderation.filter import is_prohibited

# bcrypt silently truncates inputs > 72 bytes, so we reject them at the schema layer
# rather than letting a user choose a password whose suffix is ignored on verify.
BCRYPT_MAX_PASSWORD_BYTES = 72


class RegisterRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=32,
        pattern=r"^[A-Za-z0-9_.-]+$",
    )
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=BCRYPT_MAX_PASSWORD_BYTES)

    @field_validator("username")
    @classmethod
    def _check_profanity(cls, v: str) -> str:
        if is_prohibited(v):
            raise ValueError("Ce pseudo n'est pas autorisé")
        return v


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=BCRYPT_MAX_PASSWORD_BYTES)


class TokenResponse(BaseModel):
    token: str
    username: str
    user_id: str
