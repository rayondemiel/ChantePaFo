import re
import time
import unicodedata
from typing import Any

from app.metrics import FUZZY_MATCH_DURATION_SECONDS


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^the\s+", "", text)
    return text


def _levenshtein(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]


def _is_match(answer: str, target: str, threshold: float = 0.3) -> tuple[bool, int]:
    if not answer or not target:
        return False, 999

    norm_answer = normalize_text(answer)
    norm_target = normalize_text(target)

    if norm_target in norm_answer or norm_answer in norm_target:
        return True, 0

    distance = _levenshtein(norm_answer, norm_target)
    max_len = max(len(norm_answer), len(norm_target))
    if max_len == 0:
        return False, 999

    ratio = distance / max_len
    return ratio <= threshold, distance


def fuzzy_match(answer: str, correct_title: str, correct_artist: str) -> dict[str, Any]:
    start = time.perf_counter()

    title_match, title_dist = _is_match(answer, correct_title)
    artist_match, artist_dist = _is_match(answer, correct_artist)

    if not title_match:
        combined = f"{correct_title} {correct_artist}"
        combined_match, _ = _is_match(answer, combined)
        if combined_match:
            title_match = True
            artist_match = True

    bonus = title_match and artist_match
    distance = min(title_dist, artist_dist)

    result: dict[str, Any] = {
        "title_match": title_match,
        "artist_match": artist_match,
        "bonus": bonus,
        "distance": distance,
        "score": (1 if title_match else 0) + (1 if artist_match else 0),
    }

    FUZZY_MATCH_DURATION_SECONDS.observe(time.perf_counter() - start)
    return result
