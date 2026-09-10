"""Catalog and formatting for the social layer (emoji reactions + soundboard).

Single source of truth mirrored by the frontend:
- AVAILABLE_EMOJIS ↔ frontend/src/components/ReactionBar.vue (REACTIONS)
- AVAILABLE_SOUNDS ↔ frontend/src/components/Soundboard.vue (SOUNDS)
  and frontend/public/sounds/*.mp3
The pydantic allowlist (app/sockets/payloads.py AllowedSound) must stay in
sync with AVAILABLE_SOUNDS — guarded by tests/test_reactions.py.
"""

from typing import TypedDict


class Sound(TypedDict):
    id: str
    label: str
    file: str


# "❤" (bare) kept alongside "❤️" (VS16): both encodings reach the wire
# depending on platform input.
AVAILABLE_EMOJIS: list[str] = ["😂", "👏", "💀", "🔥", "😱", "❤️", "❤"]

AVAILABLE_SOUNDS: list[Sound] = [
    {"id": "applause", "label": "Applaudir", "file": "/sounds/applause.mp3"},
    {"id": "boo", "label": "Huées", "file": "/sounds/boo.mp3"},
    {"id": "drumroll", "label": "Roulement", "file": "/sounds/drumroll.mp3"},
    {"id": "buzzer", "label": "Buzzer", "file": "/sounds/buzzer.mp3"},
    {"id": "airhorn", "label": "Airhorn", "file": "/sounds/airhorn.mp3"},
    {"id": "laugh", "label": "Rires", "file": "/sounds/laugh.mp3"},
    {"id": "sadtrombone", "label": "Womp womp", "file": "/sounds/sadtrombone.mp3"},
    {"id": "crickets", "label": "Grillons", "file": "/sounds/crickets.mp3"},
    {"id": "tada", "label": "Tada !", "file": "/sounds/tada.mp3"},
]


def validate_reaction(emoji: str) -> bool:
    return emoji in AVAILABLE_EMOJIS


def validate_soundboard(sound_id: str) -> Sound | None:
    for sound in AVAILABLE_SOUNDS:
        if sound["id"] == sound_id:
            return sound
    return None


def format_reaction_event(player_id: str, player_name: str, emoji: str) -> dict[str, str]:
    return {"player_id": player_id, "player_name": player_name, "emoji": emoji}


def format_soundboard_event(player_id: str, player_name: str, sound_id: str) -> dict[str, str]:
    # The wire carries the plain sound id — the frontend owns labels/files.
    return {"player_id": player_id, "player_name": player_name, "sound": sound_id}
