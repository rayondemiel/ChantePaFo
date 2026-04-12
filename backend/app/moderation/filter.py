import re
import unicodedata
from pathlib import Path

_LEET_MAP: dict[str, str] = {
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "8": "b",
    "@": "a",
    "$": "s",
    "!": "i",
}

_WORDLIST_PATH = Path(__file__).parent / "wordlist.txt"

# Short blocked words (< 5 chars) are matched exact-only after normalization,
# to avoid the Scunthorpe problem (names like "Cassidy" containing "ass").
# Longer blocked words keep substring matching to catch leet-speak variants.
_SUBSTRING_THRESHOLD = 5


def _load_wordlist() -> tuple[frozenset[str], frozenset[str]]:
    if not _WORDLIST_PATH.exists():
        return frozenset(), frozenset()
    short: set[str] = set()
    long_: set[str] = set()
    for line in _WORDLIST_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if len(stripped) < _SUBSTRING_THRESHOLD:
            short.add(stripped)
        else:
            long_.add(stripped)
    return frozenset(short), frozenset(long_)


_BLOCKED_EXACT, _BLOCKED_SUBSTRING = _load_wordlist()


def _normalize(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = "".join(_LEET_MAP.get(c, c) for c in text)
    text = re.sub(r"[.\-_\s]+", "", text)
    return text


def is_prohibited(text: str) -> bool:
    normalized = _normalize(text)
    if normalized in _BLOCKED_EXACT:
        return True
    return any(word in normalized for word in _BLOCKED_SUBSTRING)
