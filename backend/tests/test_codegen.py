import re

from app.rooms.codegen import THEME_WORDS, generate_room_code


def test_code_format():
    code = generate_room_code()
    assert re.match(r"^[A-Z]{4}\d{4}$", code), f"Bad format: {code}"


def test_code_uses_theme_words():
    code = generate_room_code()
    word_part = code[:4]
    assert word_part in THEME_WORDS, f"{word_part} not in THEME_WORDS"


def test_codes_are_unique():
    codes = {generate_room_code() for _ in range(50)}
    assert len(codes) > 20  # high probability of uniqueness


def test_digits_in_range():
    code = generate_room_code()
    digits = int(code[4:])
    assert 1000 <= digits <= 9999
