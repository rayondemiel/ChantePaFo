from app.game.fuzzy import fuzzy_match, normalize_text


def test_normalize_text():
    assert normalize_text("Héllo Wörld!") == "hello world"
    assert normalize_text("  The   Weeknd  ") == "weeknd"
    assert normalize_text("L'amour") == "lamour"


def test_exact_match():
    result = fuzzy_match("Thriller", "Thriller", "Michael Jackson")
    assert result["title_match"] is True
    assert result["score"] > 0


def test_typo_match_title():
    result = fuzzy_match("trhiller", "Thriller", "Michael Jackson")
    assert result["title_match"] is True


def test_typo_match_artist():
    result = fuzzy_match("michael jakson", "Thriller", "Michael Jackson")
    assert result["artist_match"] is True


def test_both_match():
    result = fuzzy_match("thriller michael jackson", "Thriller", "Michael Jackson")
    assert result["title_match"] is True
    assert result["artist_match"] is True
    assert result["bonus"] is True


def test_no_match():
    result = fuzzy_match("bananas", "Thriller", "Michael Jackson")
    assert result["title_match"] is False
    assert result["artist_match"] is False


def test_partial_title():
    result = fuzzy_match("billie jean", "Billie Jean", "Michael Jackson")
    assert result["title_match"] is True


def test_accented_match():
    result = fuzzy_match("despacito", "Despacito", "Luis Fonsi")
    assert result["title_match"] is True


def test_distance_returned():
    result = fuzzy_match("thrilr", "Thriller", "Michael Jackson")
    assert result["title_match"] is True
    assert result["distance"] >= 0


def test_the_prefix_stripped():
    result = fuzzy_match("beatles", "The Beatles", "The Beatles")
    assert result["artist_match"] is True
