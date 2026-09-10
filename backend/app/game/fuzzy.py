import re
import time
import unicodedata
from typing import Any

from app.metrics import FUZZY_MATCH_DURATION_SECONDS

# ---------------------------------------------------------------------------
# Title noise: parenthetical/bracketed metadata junk from Deezer titles
# ---------------------------------------------------------------------------
_NOISE_PATTERNS = re.compile(
    r"\s*[\(\[]"
    r"(?:feat\.?|ft\.?|with|remaster(?:ed)?|deluxe(?:\s*edition)?|bonus|"
    r"radio\s*edit|album\s*version|live|acoustic|original\s*mix|"
    r"extended\s*mix|\d{4}\s*remaster(?:ed)?)"
    r"[^\)\]]*[\)\]]"
    r"|\s*-\s*(?:bonus\s*track|remaster(?:ed)?|deluxe).*$",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Artist separators for composite artist names
# ---------------------------------------------------------------------------
# No leading \s*: re.split retries the pattern at every offset, and a greedy
# leading \s* re-consumes the whole whitespace run each time (quadratic —
# 16k spaces took 4s). The caller strips each part anyway.
_ARTIST_SEPARATORS = re.compile(
    r"(?:\bfeat\.?|\bft\.?|[&+,]|\bx\b|\band\b|\bavec\b)\s*",
    re.IGNORECASE,
)


def _strip_title_noise(title: str) -> str:
    return _NOISE_PATTERNS.sub("", title).strip()


def _split_artist(artist: str) -> list[str]:
    parts = _ARTIST_SEPARATORS.split(artist)
    return [p.strip() for p in parts if p.strip()]


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


def _is_match(
    answer: str, target: str, threshold: float = 0.3, substring_ratio: float = 0.9
) -> tuple[bool, int]:
    if not answer or not target:
        return False, 999

    norm_answer = normalize_text(answer)
    norm_target = normalize_text(target)

    if not norm_answer or not norm_target:
        return False, 999

    shorter = min(len(norm_answer), len(norm_target))
    longer = max(len(norm_answer), len(norm_target))
    if shorter >= longer * substring_ratio and (
        norm_target in norm_answer or norm_answer in norm_target
    ):
        return True, 0

    distance = _levenshtein(norm_answer, norm_target)
    max_len = max(len(norm_answer), len(norm_target))
    if max_len == 0:
        return False, 999

    ratio = distance / max_len
    return ratio <= threshold, distance


def _match_artist_components(
    answer: str, correct_artist: str, threshold: float = 0.3
) -> tuple[list[int], int, int]:
    """Match a guess against artist components. Returns (matched_indices, total, best_dist).

    Each component must be typed nearly in full (80% substring ratio). For composite
    artists (feat/&/+), the caller accumulates matched indices across guesses.
    """
    cleaned = _strip_title_noise(correct_artist)
    components = _split_artist(cleaned)
    if not components:
        components = [cleaned]

    # Try the full combined artist string first — handles "David Guetta feat Florida"
    full_match, full_dist = _is_match(answer, cleaned, threshold)
    if full_match:
        return list(range(len(components))), len(components), full_dist

    matched: list[int] = []
    best_dist = 999
    for i, comp in enumerate(components):
        is_matched, dist = _is_match(answer, comp, threshold)
        if dist < best_dist:
            best_dist = dist
        if is_matched:
            matched.append(i)

    return matched, len(components), best_dist


def fuzzy_match(answer: str, correct_title: str, correct_artist: str) -> dict[str, Any]:
    start = time.perf_counter()

    clean_title = _strip_title_noise(correct_title)
    title_match, title_dist = _is_match(answer, clean_title)

    matched_indices, total_components, artist_dist = _match_artist_components(
        answer, correct_artist
    )
    # artist_match = True only when ALL components matched by this single guess
    artist_match = len(matched_indices) >= total_components

    # Fallback: full "title artist" combined string for one-shot guesses
    if not (title_match and artist_match):
        combined = f"{clean_title} {_strip_title_noise(correct_artist)}"
        norm_answer = normalize_text(answer)
        norm_combined = normalize_text(combined)
        use_combined = True
        if title_match or artist_match:
            if norm_combined and len(norm_answer) < len(norm_combined) * 0.7:
                use_combined = False
        if use_combined:
            combined_match, _ = _is_match(answer, combined)
            if combined_match:
                title_match = True
                artist_match = True
                matched_indices = list(range(total_components))

    bonus = title_match and artist_match
    distance = min(title_dist, artist_dist)

    result: dict[str, Any] = {
        "title_match": title_match,
        "artist_match": artist_match,
        "bonus": bonus,
        "distance": distance,
        "score": (1 if title_match else 0) + (1 if artist_match else 0),
        "matched_artist_indices": matched_indices,
        "total_artist_components": total_components,
    }

    FUZZY_MATCH_DURATION_SECONDS.observe(time.perf_counter() - start)
    return result
