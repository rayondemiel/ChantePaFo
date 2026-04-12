from pydantic import BaseModel


class Track(BaseModel):
    id: int
    title: str
    artist: str
    album: str
    cover_url: str
    preview_url: str
    duration: int
    genre: str = ""
