from typing import Any

BONUS_MULTIPLIER = 1.5


def calculate_speed_score(position: int, total_players: int, max_points: int = 1000) -> int:
    if total_players <= 1:
        return max_points
    min_points = max(100, max_points // 10)
    decay = (max_points - min_points) / (total_players - 1)
    return int(max_points - (position * decay))


def calculate_round_scores(answers: list[dict[str, Any]], max_points: int = 1000) -> dict[str, int]:
    correct = [a for a in answers if a["title_match"] or a["artist_match"]]
    correct.sort(key=lambda a: a["time_ms"])

    scores: dict[str, int] = {}
    for i, answer in enumerate(correct):
        base = calculate_speed_score(i, len(correct), max_points)
        if answer["bonus"]:
            base = int(base * BONUS_MULTIPLIER)
        scores[str(answer["player_id"])] = base

    for answer in answers:
        player_id = str(answer["player_id"])
        if player_id not in scores:
            scores[player_id] = 0

    return scores
