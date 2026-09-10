from typing import get_args

from app.reactions.service import (
    AVAILABLE_EMOJIS,
    AVAILABLE_SOUNDS,
    format_reaction_event,
    format_soundboard_event,
    validate_reaction,
    validate_soundboard,
)
from app.sockets.payloads import AllowedSound


def test_valid_emoji():
    assert validate_reaction("😂") is True
    assert validate_reaction("👏") is True
    assert validate_reaction("🔥") is True


def test_invalid_emoji():
    assert validate_reaction("not_an_emoji") is False
    assert validate_reaction("🎊") is False
    assert validate_reaction("") is False


def test_valid_soundboard():
    result = validate_soundboard("applause")
    assert result is not None
    assert result["id"] == "applause"
    assert result["file"].endswith(".mp3")


def test_invalid_soundboard():
    assert validate_soundboard("nonexistent_sound") is None
    assert validate_soundboard("") is None


def test_available_emojis_not_empty():
    assert len(AVAILABLE_EMOJIS) >= 6


def test_available_sounds_matches_payload_allowlist():
    # The catalog and the pydantic Literal must never drift apart.
    assert {s["id"] for s in AVAILABLE_SOUNDS} == set(get_args(AllowedSound))


def test_format_reaction_event():
    event = format_reaction_event(player_id="p1", player_name="Alice", emoji="😂")
    assert event == {"player_id": "p1", "player_name": "Alice", "emoji": "😂"}


def test_format_soundboard_event():
    # Wire shape consumed by frontend Soundboard.vue: sound stays a plain id.
    event = format_soundboard_event(player_id="p1", player_name="Alice", sound_id="applause")
    assert event == {"player_id": "p1", "player_name": "Alice", "sound": "applause"}
