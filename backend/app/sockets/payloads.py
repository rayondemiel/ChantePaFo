from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Shared constraints
CODE_PATTERN = r"^[A-Z]{4}\d{4}$"

# Finite allowlist matching the sounds the frontend will eventually ship.
# Kept in sync with `frontend/public/sounds/*.mp3` when they land (Task 27).
AllowedSound = Literal["applause", "boo", "drumroll", "buzzer", "airhorn"]


class _StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JoinRoomPayload(_StrictBase):
    code: str = Field(..., pattern=CODE_PATTERN)

    @field_validator("code", mode="before")
    @classmethod
    def _upper(cls, v: object) -> object:
        return v.upper() if isinstance(v, str) else v


class UpdateSettingsPayload(_StrictBase):
    code: str = Field(..., pattern=CODE_PATTERN)
    settings: dict[str, object]

    @field_validator("code", mode="before")
    @classmethod
    def _upper(cls, v: object) -> object:
        return v.upper() if isinstance(v, str) else v


class StartGamePayload(_StrictBase):
    code: str = Field(..., pattern=CODE_PATTERN)

    @field_validator("code", mode="before")
    @classmethod
    def _upper(cls, v: object) -> object:
        return v.upper() if isinstance(v, str) else v


class ReactionPayload(_StrictBase):
    code: str = Field(..., pattern=CODE_PATTERN)
    emoji: str = Field(..., min_length=1, max_length=8)

    @field_validator("code", mode="before")
    @classmethod
    def _upper(cls, v: object) -> object:
        return v.upper() if isinstance(v, str) else v


class SoundboardPayload(_StrictBase):
    code: str = Field(..., pattern=CODE_PATTERN)
    sound: AllowedSound

    @field_validator("code", mode="before")
    @classmethod
    def _upper(cls, v: object) -> object:
        return v.upper() if isinstance(v, str) else v
