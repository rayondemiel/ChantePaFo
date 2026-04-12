from app.ambiance.engine import get_ambiance_for_genre, get_ambiance_for_moment


def test_disco_ambiance() -> None:
    a = get_ambiance_for_genre("disco")
    assert a["palette"] == ["#FFD700", "#8B00FF", "#FF69B4"]
    assert a["behavior"] == "pulse_fast"


def test_rock_ambiance() -> None:
    a = get_ambiance_for_genre("rock")
    assert a["behavior"] == "flash_aggressive"


def test_unknown_genre_falls_back() -> None:
    a = get_ambiance_for_genre("polka")
    assert a["palette"]  # should return a default


def test_lobby_moment() -> None:
    m = get_ambiance_for_moment("lobby")
    assert m["intensity"] < 0.5


def test_countdown_moment() -> None:
    m = get_ambiance_for_moment("countdown")
    assert m["behavior"] == "buildup"


def test_correct_answer_moment() -> None:
    m = get_ambiance_for_moment("correct_answer")
    assert m["intensity"] >= 0.8


def test_genre_ambiance_returns_copy() -> None:
    """Mutating the returned dict should not affect the map."""
    a1 = get_ambiance_for_genre("pop")
    a1["behavior"] = "mutated"
    a2 = get_ambiance_for_genre("pop")
    assert a2["behavior"] != "mutated"


def test_moment_ambiance_returns_copy() -> None:
    m1 = get_ambiance_for_moment("lobby")
    m1["intensity"] = 0.99
    m2 = get_ambiance_for_moment("lobby")
    assert m2["intensity"] != 0.99


def test_all_known_genres_return_palette() -> None:
    """Spot-check a broad range of known genres to confirm coverage."""
    genres = [
        "funk",
        "metal",
        "punk",
        "grunge",
        "electro",
        "house",
        "techno",
        "trance",
        "drum_n_bass",
        "jazz",
        "blues",
        "soul",
        "swing",
        "annees80",
        "new_wave",
        "synthwave",
        "classique",
        "opera",
        "reggae",
        "ska",
        "latino",
        "reggaeton",
        "bossa_nova",
        "zouk",
        "country",
        "folk",
        "acoustic",
        "kpop",
        "jpop",
        "rai",
        "afrobeats",
        "ambient",
        "lo_fi",
        "bo_films",
        "bo_series",
        "bo_jeux_video",
        "disney",
        "comedie_musicale",
        "gospel",
        "bollywood",
        "anime",
        "rap",
        "hiphop",
        "afro_trap",
    ]
    for genre in genres:
        a = get_ambiance_for_genre(genre)
        assert a["palette"], f"Empty palette for genre: {genre}"
        assert a["behavior"], f"Empty behavior for genre: {genre}"


def test_unknown_moment_returns_default() -> None:
    m = get_ambiance_for_moment("nonexistent_moment")
    assert m["palette"]


def test_suspense_moment() -> None:
    m = get_ambiance_for_moment("suspense")
    assert "behavior" in m
    assert "intensity" in m


def test_reveal_moment() -> None:
    m = get_ambiance_for_moment("reveal")
    assert m["intensity"] >= 0.7


def test_applause_moment() -> None:
    m = get_ambiance_for_moment("applause")
    assert m["intensity"] >= 0.7
