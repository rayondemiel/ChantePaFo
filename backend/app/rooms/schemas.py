from pydantic import BaseModel, ConfigDict, Field

_NAME_PATTERN = r"^[^\x00-\x1f\x7f]+$"


class PlayerInfo(BaseModel):
    id: str
    name: str
    is_host: bool = False


class RoomSettings(BaseModel):
    game_mode: str = "blindtest"
    genres: list[str] = ["all"]
    num_rounds: int = 10
    extract_duration: int = 20
    karaoke_variant: str = "classic"


class PartialRoomSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    game_mode: str | None = None
    genres: list[str] | None = None
    num_rounds: int | None = Field(default=None, ge=1, le=50)
    extract_duration: int | None = Field(default=None, ge=5, le=60)
    karaoke_variant: str | None = None


class RoomCreate(BaseModel):
    host_name: str = Field(..., min_length=1, max_length=32, pattern=_NAME_PATTERN)


class RoomJoin(BaseModel):
    player_name: str = Field(..., min_length=1, max_length=32, pattern=_NAME_PATTERN)


class RoomState(BaseModel):
    code: str
    host_id: str
    players: list[PlayerInfo]
    settings: RoomSettings
    status: str = "lobby"
