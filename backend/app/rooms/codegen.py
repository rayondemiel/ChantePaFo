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
    word = random.choice(THEME_WORDS)  # nosec B311 — room codes are not security-sensitive
    digits = random.randint(1000, 9999)  # nosec B311 — room codes are not security-sensitive
    return f"{word}{digits}"
