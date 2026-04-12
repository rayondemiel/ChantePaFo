from pydantic import BaseModel


class AmbianceConfig(BaseModel):
    palette: list[str]
    behavior: str
    intensity: float
    vibe: str
    bpm: int = 120
