import secrets

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
    # The code is what gates access to a room, so it comes from the CSPRNG.
    # The keyspace stays small (32 words x 9000) — brute force is held off by
    # rate limiting on join, not by entropy.
    word = secrets.choice(THEME_WORDS)
    digits = secrets.randbelow(9000) + 1000
    return f"{word}{digits}"
