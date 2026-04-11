from pydantic import BaseModel


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


class RoomCreate(BaseModel):
    host_name: str


class RoomJoin(BaseModel):
    player_name: str


class RoomState(BaseModel):
    code: str
    host_id: str
    players: list[PlayerInfo]
    settings: RoomSettings
    status: str = "lobby"
