"""Unit tests for Pydantic schemas — focused on the genres allowlist."""

import pytest
from pydantic import ValidationError

from app.rooms.schemas import PartialRoomSettings, RoomSettings


def test_genres_accepts_known_keys():
    s = PartialRoomSettings(genres={"pop": 2, "rock": 4})
    assert s.genres == {"pop": 2, "rock": 4}


def test_genres_rejects_unknown_key():
    with pytest.raises(ValidationError, match="Unknown genre key"):
        PartialRoomSettings(genres={"fakegenre": 2})


def test_genres_rejects_difficulty_out_of_range():
    with pytest.raises(ValidationError, match="between 1 and 4"):
        PartialRoomSettings(genres={"pop": 99})
    with pytest.raises(ValidationError, match="between 1 and 4"):
        PartialRoomSettings(genres={"pop": 0})


def test_genres_rejects_non_int_difficulty():
    with pytest.raises(ValidationError):
        PartialRoomSettings(genres={"pop": "hard"})  # type: ignore[dict-item]


def test_genres_rejects_oversize_dict():
    # Build a payload with 21 entries — even with all valid keys the cap blocks it
    oversized = {f"pop{i}": 2 for i in range(21)}
    with pytest.raises(ValidationError):
        PartialRoomSettings(genres=oversized)


def test_genres_none_is_valid():
    s = PartialRoomSettings(genres=None)
    assert s.genres is None


def test_room_settings_default_genres_valid():
    # Default {"all": 2} must pass the validator
    s = RoomSettings()
    assert s.genres == {"all": 2}
