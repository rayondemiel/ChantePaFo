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


def _load_wordlist() -> frozenset[str]:
    if not _WORDLIST_PATH.exists():
        return frozenset()
    words: set[str] = set()
    for line in _WORDLIST_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            words.add(stripped)
    return frozenset(words)


_BLOCKED_WORDS: frozenset[str] = _load_wordlist()


def _normalize(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = "".join(_LEET_MAP.get(c, c) for c in text)
    text = re.sub(r"[.\-_\s]+", "", text)
    return text


def is_prohibited(text: str) -> bool:
    normalized = _normalize(text)
    return any(word in normalized for word in _BLOCKED_WORDS)
