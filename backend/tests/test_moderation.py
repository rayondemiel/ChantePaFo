"""Tests for the custom profanity filter in app/moderation/filter.py."""

from app.moderation.filter import is_prohibited


def test_blocks_french_slur():
    assert is_prohibited("connard") is True


def test_blocks_english_slur():
    assert is_prohibited("nigger") is True


def test_blocks_leet_speak():
    assert is_prohibited("c0nn4rd") is True


def test_blocks_separated():
    assert is_prohibited("p.u.t.e") is True


def test_blocks_accented():
    assert is_prohibited("enculé") is True


def test_allows_normal_name():
    assert is_prohibited("rayondebazar") is False


def test_allows_french_name():
    assert is_prohibited("Jean-Pierre") is False


def test_allows_numbers():
    assert is_prohibited("player42") is False
