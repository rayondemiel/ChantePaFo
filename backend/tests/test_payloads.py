import pytest
from pydantic import ValidationError

from app.sockets.payloads import (
    JoinRoomPayload,
    ReactionPayload,
    SoundboardPayload,
    StartGamePayload,
    UpdateSettingsPayload,
)


def test_join_room_upper_cases_code():
    p = JoinRoomPayload(code="funk4242")
    assert p.code == "FUNK4242"


def test_join_room_rejects_short_code():
    with pytest.raises(ValidationError):
        JoinRoomPayload(code="FUNK42")


def test_reaction_rejects_long_emoji():
    with pytest.raises(ValidationError):
        ReactionPayload(code="FUNK4242", emoji="x" * 9)


def test_reaction_rejects_extra_fields():
    with pytest.raises(ValidationError):
        ReactionPayload(code="FUNK4242", emoji="🎉", extra="nope")


def test_soundboard_rejects_unknown_sound():
    with pytest.raises(ValidationError):
        SoundboardPayload(code="FUNK4242", sound="shotgun")


def test_soundboard_accepts_allowed_sound():
    p = SoundboardPayload(code="FUNK4242", sound="applause")
    assert p.sound == "applause"


@pytest.mark.parametrize(
    "sound",
    [
        "applause",
        "boo",
        "drumroll",
        "buzzer",
        "airhorn",
        "laugh",
        "sadtrombone",
        "crickets",
        "tada",
    ],
)
def test_soundboard_accepts_every_shipped_sound(sound):
    # Mirrors frontend/src/components/Soundboard.vue and public/sounds/*.mp3.
    assert SoundboardPayload(code="FUNK4242", sound=sound).sound == sound


def test_start_game_forbids_host_id_in_payload():
    # host_id comes from the server session, never from client payload.
    with pytest.raises(ValidationError):
        StartGamePayload(code="FUNK4242", host_id="h1")


def test_update_settings_forbids_extra():
    with pytest.raises(ValidationError):
        UpdateSettingsPayload(code="FUNK4242", settings={}, host_id="h1")
