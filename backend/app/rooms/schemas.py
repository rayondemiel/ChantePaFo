from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.moderation.filter import is_prohibited

_NAME_PATTERN = r"^[^\x00-\x1f\x7f]+$"

GameModeType = Literal["blindtest", "karaoke", "telephone"]
KaraokeVariantType = Literal["classic", "progressive", "mystery"]

# Canonical allowlist of genre keys. Must stay in sync with
# frontend/src/lib/genres.ts. Caps payload size and rejects unknown keys.
_ALLOWED_GENRE_KEYS: frozenset[str] = frozenset(
    {
        "all",
        "pop",
        "rock",
        "rap",
        "electro",
        "disco",
        "jazz",
        "soul",
        "metal",
        "kpop",
        "annees80",
        "annees90",
        "classique",
        "rnb",
        "reggae",
        "latino",
        "bo_films",
    }
)
_MAX_GENRES = 20
_DIFFICULTY_MIN = 1
_DIFFICULTY_MAX = 4


def _validate_genres_dict(v: dict[str, int] | None) -> dict[str, int] | None:
    if v is None:
        return v
    if len(v) > _MAX_GENRES:
        raise ValueError(f"Too many genres (max {_MAX_GENRES})")
    for key, level in v.items():
        if key not in _ALLOWED_GENRE_KEYS:
            raise ValueError(f"Unknown genre key: {key!r}")
        if not isinstance(level, int) or isinstance(level, bool):
            raise ValueError(f"Difficulty for {key!r} must be an integer")
        if level < _DIFFICULTY_MIN or level > _DIFFICULTY_MAX:
            raise ValueError(
                f"Difficulty for {key!r} must be between {_DIFFICULTY_MIN} and {_DIFFICULTY_MAX}"
            )
    return v


class PlayerInfo(BaseModel):
    id: str
    name: str
    is_host: bool = False


class RoomSettings(BaseModel):
    game_mode: GameModeType = "blindtest"
    genres: dict[str, int] = {"all": 2}
    num_rounds: int = 10
    extract_duration: int = 20
    karaoke_variant: KaraokeVariantType = "classic"

    @field_validator("genres")
    @classmethod
    def _check_genres(cls, v: dict[str, int]) -> dict[str, int]:
        return _validate_genres_dict(v) or {"all": 2}


class PartialRoomSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    game_mode: GameModeType | None = None
    genres: dict[str, int] | None = None
    num_rounds: int | None = Field(default=None, ge=1, le=50)
    extract_duration: int | None = Field(default=None, ge=5, le=60)
    karaoke_variant: KaraokeVariantType | None = None

    @field_validator("genres")
    @classmethod
    def _check_genres(cls, v: dict[str, int] | None) -> dict[str, int] | None:
        return _validate_genres_dict(v)


class RoomCreate(BaseModel):
    host_name: str = Field(..., min_length=1, max_length=32, pattern=_NAME_PATTERN)

    @field_validator("host_name")
    @classmethod
    def _check_profanity(cls, v: str) -> str:
        if is_prohibited(v):
            raise ValueError("Ce pseudo n'est pas autorisé")
        return v


class RoomJoin(BaseModel):
    player_name: str = Field(..., min_length=1, max_length=32, pattern=_NAME_PATTERN)

    @field_validator("player_name")
    @classmethod
    def _check_profanity(cls, v: str) -> str:
        if is_prohibited(v):
            raise ValueError("Ce pseudo n'est pas autorisé")
        return v


class RoomState(BaseModel):
    code: str
    host_id: str
    players: list[PlayerInfo]
    settings: RoomSettings
    status: str = "lobby"
