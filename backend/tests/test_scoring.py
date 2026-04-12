from app.game.scoring import calculate_round_scores, calculate_speed_score


def test_fastest_gets_max_points():
    score = calculate_speed_score(position=0, total_players=6, max_points=1000)
    assert score == 1000


def test_second_gets_less():
    first = calculate_speed_score(position=0, total_players=6, max_points=1000)
    second = calculate_speed_score(position=1, total_players=6, max_points=1000)
    assert second < first
    assert second > 0


def test_last_gets_minimum():
    score = calculate_speed_score(position=5, total_players=6, max_points=1000)
    assert score >= 100


def test_title_only_score():
    scores = calculate_round_scores(
        answers=[
            {
                "player_id": "p1",
                "title_match": True,
                "artist_match": False,
                "bonus": False,
                "time_ms": 3000,
            },
        ],
        max_points=1000,
    )
    assert scores["p1"] == 1000  # only player, gets max


def test_bonus_for_both():
    scores = calculate_round_scores(
        answers=[
            {
                "player_id": "p1",
                "title_match": True,
                "artist_match": True,
                "bonus": True,
                "time_ms": 3000,
            },
            {
                "player_id": "p2",
                "title_match": True,
                "artist_match": False,
                "bonus": False,
                "time_ms": 4000,
            },
        ],
        max_points=1000,
    )
    assert scores["p1"] > scores["p2"]


def test_no_match_no_points():
    scores = calculate_round_scores(
        answers=[
            {
                "player_id": "p1",
                "title_match": False,
                "artist_match": False,
                "bonus": False,
                "time_ms": 5000,
            },
        ],
        max_points=1000,
    )
    assert scores["p1"] == 0
