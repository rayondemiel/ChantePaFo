from typing import Any

# Time-based decay scoring: faster answers earn more points, regardless of
# arrival order. Each match category (title, artist, bonus) is rewarded
# independently so partial finds are fairly compensated.
TITLE_MAX_POINTS = 1000
ARTIST_MAX_POINTS = 1000
BONUS_MAX_POINTS = 500
DEFAULT_EXTRACT_DURATION_MS = 30_000


def calculate_time_score(time_ms: int, extract_duration_ms: int, max_points: int) -> int:
    if extract_duration_ms <= 0 or time_ms < 0:
        return 0
    factor = max(0.0, 1.0 - time_ms / extract_duration_ms)
    return int(max_points * factor)


def calculate_round_scores(
    answers: list[dict[str, Any]],
    extract_duration_ms: int = DEFAULT_EXTRACT_DURATION_MS,
) -> dict[str, int]:
    scores: dict[str, int] = {}
    for answer in answers:
        player_id = str(answer["player_id"])
        total = 0
        if answer.get("title_match"):
            t = answer.get("title_time_ms", answer.get("time_ms", 0))
            total += calculate_time_score(t, extract_duration_ms, TITLE_MAX_POINTS)
        if answer.get("artist_match"):
            t = answer.get("artist_time_ms", answer.get("time_ms", 0))
            total += calculate_time_score(t, extract_duration_ms, ARTIST_MAX_POINTS)
        if answer.get("bonus"):
            t = answer.get("bonus_time_ms", answer.get("time_ms", 0))
            total += calculate_time_score(t, extract_duration_ms, BONUS_MAX_POINTS)
        scores[player_id] = total
    return scores
