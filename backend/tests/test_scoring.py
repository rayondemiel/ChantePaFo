from app.game.scoring import (
    ARTIST_MAX_POINTS,
    BONUS_MAX_POINTS,
    TITLE_MAX_POINTS,
    calculate_round_scores,
    calculate_time_score,
)


def test_zero_time_yields_max_points():
    assert calculate_time_score(0, 30_000, 1000) == 1000


def test_full_duration_yields_zero():
    assert calculate_time_score(30_000, 30_000, 1000) == 0


def test_half_duration_yields_half_points():
    assert calculate_time_score(15_000, 30_000, 1000) == 500


def test_overtime_clamped_to_zero():
    assert calculate_time_score(45_000, 30_000, 1000) == 0


def test_invalid_duration_returns_zero():
    assert calculate_time_score(1000, 0, 1000) == 0


def test_title_only_score_uses_title_time():
    scores = calculate_round_scores(
        answers=[
            {
                "player_id": "p1",
                "title_match": True,
                "artist_match": False,
                "bonus": False,
                "title_time_ms": 6000,
                "artist_time_ms": 0,
                "bonus_time_ms": 0,
                "time_ms": 6000,
            },
        ],
        extract_duration_ms=30_000,
    )
    # 6s sur 30s → 80% of 1000 = 800
    assert scores["p1"] == 800


def test_artist_only_score_uses_artist_time():
    scores = calculate_round_scores(
        answers=[
            {
                "player_id": "p1",
                "title_match": False,
                "artist_match": True,
                "bonus": False,
                "title_time_ms": 0,
                "artist_time_ms": 15_000,
                "bonus_time_ms": 0,
                "time_ms": 15_000,
            },
        ],
        extract_duration_ms=30_000,
    )
    # 15s sur 30s → 500
    assert scores["p1"] == 500


def test_bonus_sums_three_independent_scores():
    scores = calculate_round_scores(
        answers=[
            {
                "player_id": "p1",
                "title_match": True,
                "artist_match": True,
                "bonus": True,
                "title_time_ms": 3000,
                "artist_time_ms": 9000,
                "bonus_time_ms": 9000,
                "time_ms": 9000,
            },
        ],
        extract_duration_ms=30_000,
    )
    # title: 1000 * (1 - 3/30) = 900
    # artist: 1000 * (1 - 9/30) = 700
    # bonus: 500 * (1 - 9/30) = 350
    assert scores["p1"] == 900 + 700 + 350


def test_partial_finder_can_beat_slow_bonus():
    """Modèle A : un joueur qui trouve juste le titre très vite peut battre
    un joueur qui trouve tout mais lentement."""
    scores = calculate_round_scores(
        answers=[
            {
                "player_id": "fast_title",
                "title_match": True,
                "artist_match": False,
                "bonus": False,
                "title_time_ms": 1000,
                "artist_time_ms": 0,
                "bonus_time_ms": 0,
                "time_ms": 1000,
            },
            {
                "player_id": "slow_bonus",
                "title_match": True,
                "artist_match": True,
                "bonus": True,
                "title_time_ms": 28_000,
                "artist_time_ms": 28_000,
                "bonus_time_ms": 28_000,
                "time_ms": 28_000,
            },
        ],
        extract_duration_ms=30_000,
    )
    # fast: 1000 * (1 - 1/30) ≈ 966
    # slow: 1000*(2/30) + 1000*(2/30) + 500*(2/30) ≈ 66 + 66 + 33 = 165
    assert scores["fast_title"] > scores["slow_bonus"]


def test_no_match_no_points():
    scores = calculate_round_scores(
        answers=[
            {
                "player_id": "p1",
                "title_match": False,
                "artist_match": False,
                "bonus": False,
                "title_time_ms": 0,
                "artist_time_ms": 0,
                "bonus_time_ms": 0,
                "time_ms": 5000,
            },
        ],
        extract_duration_ms=30_000,
    )
    assert scores["p1"] == 0


def test_max_points_constants_are_positive():
    assert TITLE_MAX_POINTS > 0
    assert ARTIST_MAX_POINTS > 0
    assert BONUS_MAX_POINTS > 0
