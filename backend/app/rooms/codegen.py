import random

THEME_WORDS = [
    "FUNK",
    "ROCK",
    "JAZZ",
    "PUNK",
    "SOUL",
    "BASS",
    "DRUM",
    "BEAT",
    "RIFF",
    "LOOP",
    "TUNE",
    "SING",
    "VIBE",
    "WAVE",
    "TONE",
    "LOUD",
    "DEEP",
    "FAST",
    "SLOW",
    "HIGH",
    "DROP",
    "FLOW",
    "HITS",
    "CLAP",
    "BUMP",
    "BOOM",
    "WAIL",
    "YELL",
    "RAVE",
    "SLAM",
    "JUMP",
    "ROAR",
]


def generate_room_code() -> str:
    word = random.choice(THEME_WORDS)
    digits = random.randint(10, 99)
    return f"{word}{digits}"
