from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.moderation.filter import is_prohibited

_NAME_PATTERN = r"^[^\x00-\x1f\x7f]+$"

GameModeType = Literal["blindtest", "karaoke", "telephone"]
KaraokeVariantType = Literal["classic", "progressive", "mystery"]


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


class PartialRoomSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    game_mode: GameModeType | None = None
    genres: dict[str, int] | None = None
    num_rounds: int | None = Field(default=None, ge=1, le=50)
    extract_duration: int | None = Field(default=None, ge=5, le=60)
    karaoke_variant: KaraokeVariantType | None = None


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
