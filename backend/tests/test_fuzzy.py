import time

from app.game.fuzzy import (
    _split_artist,
    _strip_title_noise,
    fuzzy_match,
    normalize_text,
)


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


def test_punctuation_only_does_not_match():
    result = fuzzy_match("!!!", "Thriller", "Michael Jackson")
    assert result["title_match"] is False
    assert result["artist_match"] is False
    assert result["score"] == 0


# --- Diacritics ---


def test_fuzzy_match_ignores_accents():
    result = fuzzy_match("etoile", "Étoile", "Artist")
    assert result["title_match"] is True


def test_fuzzy_match_ignores_case():
    result = fuzzy_match("THRILLER", "Thriller", "Michael Jackson")
    assert result["title_match"] is True


# --- Title noise stripping ---


def test_strip_title_noise_remaster():
    assert _strip_title_noise("Billie Jean (2018 Remaster)") == "Billie Jean"


def test_strip_title_noise_remastered():
    assert _strip_title_noise("Billie Jean (Remastered)") == "Billie Jean"


def test_strip_title_noise_deluxe_bracket():
    assert _strip_title_noise("Bad [Deluxe Edition]") == "Bad"


def test_strip_title_noise_feat():
    assert _strip_title_noise("Titanium (feat. Sia)") == "Titanium"


def test_strip_title_noise_ft():
    assert _strip_title_noise("Right Round (ft. Ke$ha)") == "Right Round"


def test_strip_title_noise_radio_edit():
    assert _strip_title_noise("Get Lucky (Radio Edit)") == "Get Lucky"


def test_strip_title_noise_live():
    assert _strip_title_noise("Bohemian Rhapsody (Live)") == "Bohemian Rhapsody"


def test_strip_title_noise_acoustic():
    assert _strip_title_noise("Creep (Acoustic)") == "Creep"


def test_strip_title_noise_original_mix():
    assert _strip_title_noise("Blue Monday (Original Mix)") == "Blue Monday"


def test_strip_title_noise_extended_mix():
    assert _strip_title_noise("Around The World (Extended Mix)") == "Around The World"


def test_strip_title_noise_dash_bonus_track():
    assert _strip_title_noise("Hidden Song - Bonus Track") == "Hidden Song"


def test_strip_title_noise_dash_remastered():
    assert _strip_title_noise("Song Name - Remastered") == "Song Name"


def test_strip_title_noise_with_suffix():
    assert _strip_title_noise("Song (with Sia)") == "Song"


def test_strip_title_noise_album_version():
    assert _strip_title_noise("Song (Album Version)") == "Song"


def test_strip_title_noise_preserves_clean_title():
    assert _strip_title_noise("Bohemian Rhapsody") == "Bohemian Rhapsody"


def test_strip_title_noise_multiple_patterns():
    assert _strip_title_noise("Song (feat. X) (Remastered)") == "Song"


def test_fuzzy_strips_remaster_from_title():
    result = fuzzy_match("Billie Jean", "Billie Jean (2018 Remaster)", "Michael Jackson")
    assert result["title_match"] is True


def test_fuzzy_strips_deluxe_from_title():
    result = fuzzy_match("Bad", "Bad [Deluxe Edition]", "Michael Jackson")
    assert result["title_match"] is True


def test_fuzzy_strips_feat_from_title():
    result = fuzzy_match("Titanium", "Titanium (feat. Sia)", "David Guetta")
    assert result["title_match"] is True


def test_fuzzy_strips_radio_edit():
    result = fuzzy_match("Get Lucky", "Get Lucky (Radio Edit)", "Daft Punk")
    assert result["title_match"] is True


def test_fuzzy_accepts_the_full_displayed_title_with_noise():
    # A player who types the title exactly as Deezer shows it (parenthetical
    # included) must not be told they missed.
    result = fuzzy_match("Dracula (with JENNIE)", "Dracula (with JENNIE)", "Tame Impala")
    assert result["title_match"] is True


def test_fuzzy_accepts_full_title_with_noise_plus_artist():
    result = fuzzy_match(
        "Titanium (feat. Sia) David Guetta", "Titanium (feat. Sia)", "David Guetta"
    )
    assert result["bonus"] is True


def test_fuzzy_noise_in_answer_does_not_create_false_positive():
    result = fuzzy_match("Nothing (Radio Edit)", "Get Lucky (Radio Edit)", "Daft Punk")
    assert result["title_match"] is False


def test_title_only_guess_does_not_earn_the_bonus_when_the_artist_is_short():
    # "vive la monnaie" is 15 chars, "vive la monnaie gims" 20: the loose
    # combined-string ratio used to hand out the bonus without any artist.
    result = fuzzy_match("VIVE LA MONNAIE", "VIVE LA MONNAIE", "GIMS")
    assert result["title_match"] is True
    assert result["artist_match"] is False
    assert result["bonus"] is False


def test_title_plus_short_artist_still_earns_the_bonus():
    result = fuzzy_match("vive la monnaie gims", "VIVE LA MONNAIE", "GIMS")
    assert result["bonus"] is True


def test_title_with_typo_plus_artist_earns_the_bonus():
    result = fuzzy_match("vive la monaie gims", "VIVE LA MONNAIE", "GIMS")
    assert result["bonus"] is True


def test_artist_only_guess_does_not_earn_the_bonus_when_the_title_is_short():
    result = fuzzy_match("Temper City", "Self Aware", "Temper City")
    assert result["artist_match"] is True
    assert result["title_match"] is False
    assert result["bonus"] is False


# --- Composite artist matching ---


def test_split_artist_feat():
    assert _split_artist("David Guetta feat. Florida") == ["David Guetta", "Florida"]


def test_split_artist_ft():
    assert _split_artist("Rihanna ft. Calvin Harris") == ["Rihanna", "Calvin Harris"]


def test_split_artist_ampersand():
    assert _split_artist("Daft Punk & Pharrell Williams") == [
        "Daft Punk",
        "Pharrell Williams",
    ]


def test_split_artist_plus():
    assert _split_artist("Artist1 + Artist2") == ["Artist1", "Artist2"]


def test_split_artist_and():
    assert _split_artist("Simon and Garfunkel") == ["Simon", "Garfunkel"]


def test_split_artist_avec():
    assert _split_artist("Stromae avec Maitre Gims") == ["Stromae", "Maitre Gims"]


def test_split_artist_comma():
    assert _split_artist("Artist1, Artist2") == ["Artist1", "Artist2"]


def test_split_artist_x():
    assert _split_artist("Niska x Ninho") == ["Niska", "Ninho"]


def test_split_artist_single():
    assert _split_artist("Michael Jackson") == ["Michael Jackson"]


def test_fuzzy_matches_main_artist_component_but_not_full_artist():
    # "David Guetta" matches component 0 but artist has 2 components → artist_match=False
    result = fuzzy_match("David Guetta", "Titanium", "David Guetta feat. Florida")
    assert result["artist_match"] is False
    assert 0 in result["matched_artist_indices"]
    assert result["total_artist_components"] == 2


def test_fuzzy_matches_single_component_of_composite():
    # "Florida" matches component "Florida" → matched_artist_indices=[1]
    # But artist_match=False because only 1 of 2 components matched
    result = fuzzy_match("Florida", "Titanium", "David Guetta feat. Florida")
    assert result["artist_match"] is False
    assert 1 in result["matched_artist_indices"]
    assert result["total_artist_components"] == 2


def test_fuzzy_all_components_matched_gives_artist_match():
    # Full artist string matches all components at once
    result = fuzzy_match("David Guetta feat Florida", "Titanium", "David Guetta feat. Florida")
    assert result["artist_match"] is True


def test_fuzzy_partial_component_does_not_match():
    # "Pharrell" is only 47% of "Pharrell Williams" — too short at 80% threshold
    result = fuzzy_match("Pharrell", "Get Lucky", "Daft Punk & Pharrell Williams")
    assert result["artist_match"] is False
    assert result["matched_artist_indices"] == []


def test_fuzzy_full_component_name_matches():
    # "Pharrell Williams" matches component "Pharrell Williams" fully
    result = fuzzy_match("Pharrell Williams", "Get Lucky", "Daft Punk & Pharrell Williams")
    assert result["artist_match"] is False  # only 1 of 2 components
    assert 1 in result["matched_artist_indices"]


def test_fuzzy_matches_artist_with_typo_in_composite():
    # "David Gueta" (1 char off "David Guetta") matches via Levenshtein
    result = fuzzy_match("David Gueta", "Titanium", "David Guetta feat. Florida")
    assert 0 in result["matched_artist_indices"]


# --- Edge cases ---


def test_fuzzy_empty_guess_returns_no_match():
    result = fuzzy_match("", "Thriller", "Michael Jackson")
    assert result["title_match"] is False
    assert result["artist_match"] is False
    assert result["bonus"] is False


def test_fuzzy_matches_artist_when_guess_contains_typo():
    result = fuzzy_match("David Gueta", "Titanium", "David Guetta")
    assert result["artist_match"] is True


# --- Noise stripping on artist ---


def test_fuzzy_strips_noise_from_artist():
    result = fuzzy_match("Daft Punk", "Get Lucky", "Daft Punk (Remastered)")
    assert result["artist_match"] is True


# --- Substring length ratio guard ---


def test_short_substring_does_not_match_long_title():
    result = fuzzy_match("boys", "Boys Don't Cry", "The Cure")
    assert result["title_match"] is False


def test_title_substring_requires_80_pct():
    # "stairway" is only 44% of "stairway to heaven" — too short for title
    result = fuzzy_match("stairway", "Stairway to Heaven", "Led Zeppelin")
    assert result["title_match"] is False
    # But typing ~80% of the title works
    result2 = fuzzy_match("stairway to heav", "Stairway to Heaven", "Led Zeppelin")
    assert result2["title_match"] is True


def test_exact_substring_match_still_works():
    result = fuzzy_match("billie jean", "Billie Jean", "Michael Jackson")
    assert result["title_match"] is True


def test_short_word_does_not_match_artist():
    # "the" is stripped by normalize_text, leaving "" which should not match
    result = fuzzy_match("the", "Boys Don't Cry", "The Cure")
    assert result["artist_match"] is False


def test_split_artist_handles_separators_and_spacing():
    assert _split_artist("David Guetta feat. Flo Rida") == ["David Guetta", "Flo Rida"]
    assert _split_artist("Earth, Wind & Fire") == ["Earth", "Wind", "Fire"]
    assert _split_artist("Jay-Z x Linkin Park") == ["Jay-Z", "Linkin Park"]
    assert _split_artist("Bob Marley and The Wailers") == ["Bob Marley", "The Wailers"]
    assert _split_artist("  spaced   feat   name  ") == ["spaced", "name"]


def test_split_artist_stays_linear_on_whitespace_flood():
    # A leading \s* in the separator pattern made this quadratic: 16k spaces
    # took ~4s. Generous bound — the point is the shape, not the exact timing.
    start = time.perf_counter()
    assert _split_artist(" " * 16000) == []
    assert time.perf_counter() - start < 2.0
