from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.reactions.service import validate_reaction

# Shared constraints
CODE_PATTERN = r"^[A-Z]{4}\d{4}$"

# Finite allowlist matching the shipped sounds — kept in sync with
# `frontend/public/sounds/*.mp3` and `frontend/src/components/Soundboard.vue`.
AllowedSound = Literal[
    "applause",
    "boo",
    "drumroll",
    "buzzer",
    "airhorn",
    "laugh",
    "sadtrombone",
    "crickets",
    "tada",
]


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

    @field_validator("emoji")
    @classmethod
    def _allowed(cls, v: str) -> str:
        # Finite allowlist mirroring the frontend ReactionBar — arbitrary
        # strings would render as floating text on every player's screen.
        if not validate_reaction(v):
            raise ValueError("emoji not in the reaction allowlist")
        return v


class SoundboardPayload(_StrictBase):
    code: str = Field(..., pattern=CODE_PATTERN)
    sound: AllowedSound

    @field_validator("code", mode="before")
    @classmethod
    def _upper(cls, v: object) -> object:
        return v.upper() if isinstance(v, str) else v


class GameEventPayload(_StrictBase):
    code: str = Field(..., pattern=CODE_PATTERN)
    event_type: str = Field(..., min_length=1, max_length=32)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("code", mode="before")
    @classmethod
    def _upper(cls, v: object) -> object:
        return v.upper() if isinstance(v, str) else v


class AnswerPayload(BaseModel):
    """Validates the inner payload of a blindtest 'answer' game event.

    Bounded `text` length kills the Levenshtein-DoS vector (a 1MB string
    against a 30-char title would block the asyncio worker for seconds).
    Client-supplied `time_ms` is accepted but IGNORED by the server, which
    computes timing from its own monotonic clock (otherwise a tampered
    client could send time_ms=0 and score max points each round).
    """

    model_config = ConfigDict(extra="ignore")

    text: str = Field(..., max_length=200)


class KickPlayerPayload(_StrictBase):
    code: str = Field(..., pattern=CODE_PATTERN)
    player_id: str = Field(..., min_length=1, max_length=64)

    @field_validator("code", mode="before")
    @classmethod
    def _upper(cls, v: object) -> object:
        return v.upper() if isinstance(v, str) else v


class RequestAmbiancePayload(_StrictBase):
    genre: str = Field(default="", max_length=64)
    moment: str = Field(default="", max_length=64)
