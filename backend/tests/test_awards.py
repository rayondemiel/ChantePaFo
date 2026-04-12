from typing import Any

from app.game.awards import compute_awards


def _make_history() -> dict[str, Any]:
    return {
        "players": {
            "p1": {"name": "Alice"},
            "p2": {"name": "Bob"},
            "p3": {"name": "Charlie"},
        },
        "rounds": [
            {
                "answers": {
                    "p1": {
                        "text": "thriller",
                        "title_match": True,
                        "artist_match": True,
                        "time_ms": 2000,
                        "attempts": 1,
                        "distance": 0,
                    },
                    "p2": {
                        "text": "Michel Jacqueson",
                        "title_match": False,
                        "artist_match": False,
                        "time_ms": 5000,
                        "attempts": 3,
                        "distance": 12,
                    },
                    "p3": {
                        "text": "",
                        "title_match": False,
                        "artist_match": False,
                        "time_ms": 0,
                        "attempts": 0,
                        "distance": 999,
                    },
                },
                "scores": {"p1": 1000, "p2": 0, "p3": 0},
            },
            {
                "answers": {
                    "p1": {
                        "text": "billie jean",
                        "title_match": True,
                        "artist_match": False,
                        "time_ms": 3000,
                        "attempts": 1,
                        "distance": 0,
                    },
                    "p2": {
                        "text": "billy jeans",
                        "title_match": True,
                        "artist_match": False,
                        "time_ms": 4000,
                        "attempts": 2,
                        "distance": 2,
                    },
                    "p3": {
                        "text": "",
                        "title_match": False,
                        "artist_match": False,
                        "time_ms": 0,
                        "attempts": 0,
                        "distance": 999,
                    },
                },
                "scores": {"p1": 1000, "p2": 700, "p3": 0},
            },
        ],
        "total_scores": {"p1": 2000, "p2": 700, "p3": 0},
    }


def test_maestro_is_highest_scorer() -> None:
    awards = compute_awards(_make_history(), mode="blindtest")
    maestro = next((a for a in awards if a["id"] == "maestro"), None)
    assert maestro is not None
    assert maestro["player_id"] == "p1"


def test_oreille_en_carton_is_lowest() -> None:
    awards = compute_awards(_make_history(), mode="blindtest")
    award = next((a for a in awards if a["id"] == "oreille_carton"), None)
    assert award is not None
    assert award["player_id"] == "p3"


def test_shazam_is_fastest() -> None:
    awards = compute_awards(_make_history(), mode="blindtest")
    award = next((a for a in awards if a["id"] == "shazam"), None)
    assert award is not None
    assert award["player_id"] == "p1"


def test_fantome_never_answered() -> None:
    awards = compute_awards(_make_history(), mode="blindtest")
    award = next((a for a in awards if a["id"] == "fantome"), None)
    assert award is not None
    assert award["player_id"] == "p3"


def test_poete_worst_answer() -> None:
    awards = compute_awards(_make_history(), mode="blindtest")
    award = next((a for a in awards if a["id"] == "poete"), None)
    assert award is not None
    assert award["player_id"] == "p2"
    assert "Michel Jacqueson" in award["detail"]


def test_no_duplicate_award_ids() -> None:
    awards = compute_awards(_make_history(), mode="blindtest")
    ids = [a["id"] for a in awards]
    assert len(ids) == len(set(ids)), f"Duplicate award IDs: {ids}"
    for a in awards:
        assert "id" in a
        assert "player_id" in a
        assert "title" in a


def test_awards_list_is_non_empty() -> None:
    awards = compute_awards(_make_history(), mode="blindtest")
    assert len(awards) > 0


def test_rageux_most_attempts() -> None:
    """p2 has 3 attempts in round 1 — qualifies for Le Rageux."""
    awards = compute_awards(_make_history(), mode="blindtest")
    award = next((a for a in awards if a["id"] == "rageux"), None)
    # rageux requires >= 3 attempts; p2 has 3 in round 1
    assert award is not None
    assert award["player_id"] == "p2"


def test_one_player_no_oreille_carton_same_as_maestro() -> None:
    """When only 1 player exists, oreille_carton should not be awarded to same as maestro."""
    history: dict[str, Any] = {
        "players": {"p1": {"name": "Solo"}},
        "rounds": [
            {
                "answers": {
                    "p1": {
                        "text": "hit",
                        "title_match": True,
                        "artist_match": False,
                        "time_ms": 1000,
                        "attempts": 1,
                        "distance": 0,
                    }
                },
                "scores": {"p1": 1000},
            }
        ],
        "total_scores": {"p1": 1000},
    }
    awards = compute_awards(history, mode="blindtest")
    maestro_id = next(a["player_id"] for a in awards if a["id"] == "maestro")
    oreille = next((a for a in awards if a["id"] == "oreille_carton"), None)
    if oreille is not None:
        assert oreille["player_id"] != maestro_id


def test_all_award_fields_present() -> None:
    awards = compute_awards(_make_history(), mode="blindtest")
    for award in awards:
        assert "id" in award, f"Missing 'id' in {award}"
        assert "player_id" in award, f"Missing 'player_id' in {award}"
        assert "title" in award, f"Missing 'title' in {award}"
        assert "emoji" in award, f"Missing 'emoji' in {award}"
        assert "detail" in award, f"Missing 'detail' in {award}"
