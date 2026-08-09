from typing import Any

import pytest

from app.game.blindtest import BlindtestMode


class FakeTrackProvider:
    def __init__(self, custom_tracks: list[dict[str, Any]] | None = None) -> None:
        self._custom_tracks = custom_tracks

    async def get_random_tracks(
        self, genre_config: dict[str, int], count: int = 10
    ) -> list[dict[str, Any]]:
        if self._custom_tracks is not None:
            return self._custom_tracks[:count]
        return [
            {
                "id": i,
                "title": f"Song{i}" if i != 0 else "Thriller",
                "artist": f"Artist{i}" if i != 0 else "Michael Jackson",
                "preview_url": f"https://preview/{i}",
                "cover_url": f"https://cover/{i}",
                "album": "",
                "duration": 30,
                "rank": 500000,
            }
            for i in range(count)
        ]


def _players(n: int) -> list[dict[str, str]]:
    return [{"id": f"p{i}", "name": f"Player{i}"} for i in range(n)]


async def _started_mode(
    num_rounds: int = 2,
    num_players: int = 2,
    custom_tracks: list[dict[str, Any]] | None = None,
) -> BlindtestMode:
    mode = BlindtestMode()
    await mode.start(
        players=_players(num_players),
        settings={"num_rounds": num_rounds, "genres": {"pop": 1}},
        track_provider=FakeTrackProvider(custom_tracks),
    )
    return mode


@pytest.mark.asyncio
async def test_blindtest_start_initial_phase_is_countdown() -> None:
    mode = await _started_mode()
    state = mode.get_state()
    assert state["phase"] == "countdown"
    assert state["current_round"] == 0
    assert state["total_rounds"] == 2


@pytest.mark.asyncio
async def test_countdown_done_transitions_to_playing() -> None:
    mode = await _started_mode()
    result = await mode.handle_event("countdown_done", "p0", {})
    assert result == {"phase": "playing"}
    assert mode.state["phase"] == "playing"


@pytest.mark.asyncio
async def test_playing_track_has_no_cover_or_title_or_artist() -> None:
    mode = await _started_mode()
    await mode.handle_event("countdown_done", "p0", {})
    track = mode.state["track"]
    assert "cover_url" not in track
    assert "title" not in track
    assert "artist" not in track
    assert "preview_url" in track
    assert "genre" in track


@pytest.mark.asyncio
async def test_blindtest_correct_answer() -> None:
    mode = await _started_mode()
    await mode.handle_event("countdown_done", "p0", {})
    # Round 0: title="Thriller" / artist="Michael Jackson"
    result = await mode.handle_event("answer", "p0", {"text": "thriller", "time_ms": 5000})
    assert result is not None
    assert result["title_match"] is True


@pytest.mark.asyncio
async def test_blindtest_wrong_answer() -> None:
    mode = await _started_mode()
    await mode.handle_event("countdown_done", "p0", {})
    result = await mode.handle_event("answer", "p0", {"text": "bananas", "time_ms": 5000})
    assert result is not None
    assert result["title_match"] is False


@pytest.mark.asyncio
async def test_answer_ignored_outside_playing_phase() -> None:
    mode = await _started_mode()
    # Still in countdown — answer must be silently ignored.
    result = await mode.handle_event("answer", "p0", {"text": "thriller", "time_ms": 5000})
    assert result is None

    await mode.handle_event("countdown_done", "p0", {})
    mode.advance_to_reveal()
    # In playing_reveal, answers are no longer accepted.
    result2 = await mode.handle_event("answer", "p0", {"text": "thriller", "time_ms": 5000})
    assert result2 is None


@pytest.mark.asyncio
async def test_advance_to_reveal_exposes_cover_and_round_results() -> None:
    mode = await _started_mode()
    await mode.handle_event("countdown_done", "p0", {})
    mode.advance_to_reveal()

    assert mode.state["phase"] == "playing_reveal"
    assert mode.state["track"]["cover_url"] == "https://cover/0"
    results = mode.state["round_results"]
    assert results["correct_title"] == "Thriller"
    assert results["correct_artist"] == "Michael Jackson"
    assert results["cover_url"] == "https://cover/0"


@pytest.mark.asyncio
async def test_advance_to_reveal_calculates_scores_and_locks_history() -> None:
    mode = await _started_mode()
    await mode.handle_event("countdown_done", "p0", {})
    await mode.handle_event("answer", "p0", {"text": "thriller michael jackson", "time_ms": 3000})
    mode.advance_to_reveal()

    assert "p0" in mode.state["round_scores"]
    assert mode.state["round_scores"]["p0"] > 0
    # History should have been appended.
    assert len(mode.history["rounds"]) == 1
    assert mode.history["total_scores"]["p0"] == mode.state["round_scores"]["p0"]


@pytest.mark.asyncio
async def test_advance_to_pause_only_changes_phase() -> None:
    mode = await _started_mode()
    await mode.handle_event("countdown_done", "p0", {})
    mode.advance_to_reveal()

    cover_before = mode.state["track"]["cover_url"]
    results_before = dict(mode.state["round_results"])

    mode.advance_to_pause()
    assert mode.state["phase"] == "round_pause"
    # Track and results untouched.
    assert mode.state["track"]["cover_url"] == cover_before
    assert mode.state["round_results"] == results_before


@pytest.mark.asyncio
async def test_advance_to_next_round_loads_next_track_in_playing() -> None:
    mode = await _started_mode(num_rounds=3)
    await mode.handle_event("countdown_done", "p0", {})
    mode.advance_to_reveal()
    mode.advance_to_pause()
    mode.advance_to_next_round()

    assert mode.state["phase"] == "playing"
    assert mode.state["current_round"] == 1
    track = mode.state["track"]
    # Cover/title/artist must NOT leak after loading the next round.
    assert "cover_url" not in track
    assert "title" not in track
    assert track["preview_url"] == "https://preview/1"
    # Round results cleared for the new round.
    assert mode.state["round_results"] == {}


@pytest.mark.asyncio
async def test_advance_to_next_round_finishes_on_last_round() -> None:
    mode = await _started_mode(num_rounds=2)
    await mode.handle_event("countdown_done", "p0", {})
    # Round 0 → reveal → pause → round 1
    mode.advance_to_reveal()
    mode.advance_to_pause()
    mode.advance_to_next_round()
    assert mode.state["phase"] == "playing"
    assert mode.state["current_round"] == 1
    # Round 1 → reveal → pause → finished
    mode.advance_to_reveal()
    mode.advance_to_pause()
    result = mode.advance_to_next_round()
    assert result["phase"] == "finished"
    assert mode.state["phase"] == "finished"


@pytest.mark.asyncio
async def test_blindtest_artist_then_title_gives_bonus() -> None:
    """Bug 3: finding artist first then title must yield bonus=True."""
    mode = await _started_mode(num_rounds=1)
    await mode.handle_event("countdown_done", "p0", {})

    # Round 0: title="Thriller" / artist="Michael Jackson"
    r1 = await mode.handle_event("answer", "p0", {"text": "michael jackson", "time_ms": 3000})
    assert r1 is not None
    assert r1["artist_match"] is True

    r2 = await mode.handle_event("answer", "p0", {"text": "thriller", "time_ms": 5000})
    assert r2 is not None
    assert r2["title_match"] is True
    assert r2["artist_match"] is True
    assert r2["bonus"] is True


@pytest.mark.asyncio
async def test_unknown_event_returns_none() -> None:
    mode = await _started_mode()
    assert await mode.handle_event("next_round", "p0", {}) is None
    assert await mode.handle_event("advance_round", "p0", {}) is None
    assert await mode.handle_event("round_timeout", "p0", {}) is None


@pytest.mark.asyncio
async def test_advance_to_reveal_populates_top_3_winners_sorted_by_time(monkeypatch) -> None:
    fake = {"now_ms": 0}
    monkeypatch.setattr("app.game.blindtest._now_ms", lambda: fake["now_ms"])

    mode = await _started_mode(num_rounds=1, num_players=4)
    fake["now_ms"] = 0
    await mode.handle_event("countdown_done", "p0", {})

    fake["now_ms"] = 4000
    await mode.handle_event("answer", "p0", {"text": "thriller michael jackson"})
    fake["now_ms"] = 2000
    await mode.handle_event("answer", "p1", {"text": "thriller michael jackson"})
    fake["now_ms"] = 6000
    await mode.handle_event("answer", "p2", {"text": "thriller michael jackson"})
    fake["now_ms"] = 3000
    await mode.handle_event("answer", "p3", {"text": "thriller michael jackson"})
    mode.advance_to_reveal()

    winners = mode.state["round_results"]["winners"]
    assert len(winners) == 3
    assert [w["player_id"] for w in winners] == ["p1", "p3", "p0"]
    assert [w["time_ms"] for w in winners] == [2000, 3000, 4000]
    assert winners[0]["name"] == "Player1"


@pytest.mark.asyncio
async def test_advance_to_reveal_winners_empty_when_no_bonus_matches() -> None:
    mode = await _started_mode(num_rounds=1, num_players=2)
    await mode.handle_event("countdown_done", "p0", {})
    await mode.handle_event("answer", "p0", {"text": "bananas", "time_ms": 1000})
    mode.advance_to_reveal()

    assert mode.state["round_results"]["winners"] == []


@pytest.mark.asyncio
async def test_advance_to_reveal_winners_fewer_than_three_when_not_enough_matches(
    monkeypatch,
) -> None:
    fake = {"now_ms": 0}
    monkeypatch.setattr("app.game.blindtest._now_ms", lambda: fake["now_ms"])

    mode = await _started_mode(num_rounds=1, num_players=4)
    await mode.handle_event("countdown_done", "p0", {})
    fake["now_ms"] = 3000
    await mode.handle_event("answer", "p0", {"text": "thriller michael jackson"})
    fake["now_ms"] = 2000
    await mode.handle_event("answer", "p1", {"text": "thriller michael jackson"})
    mode.advance_to_reveal()

    winners = mode.state["round_results"]["winners"]
    assert len(winners) == 2
    assert [w["player_id"] for w in winners] == ["p1", "p0"]


@pytest.mark.asyncio
async def test_all_matches_includes_partial_and_bonus_sorted_by_time(monkeypatch) -> None:
    fake = {"now_ms": 0}
    monkeypatch.setattr("app.game.blindtest._now_ms", lambda: fake["now_ms"])

    mode = await _started_mode(num_rounds=1, num_players=3)
    await mode.handle_event("countdown_done", "p0", {})

    # p0: bonus (title+artist), p1: title-only, p2: artist-only
    fake["now_ms"] = 4000
    await mode.handle_event("answer", "p0", {"text": "thriller michael jackson"})
    fake["now_ms"] = 2000
    await mode.handle_event("answer", "p1", {"text": "thriller"})
    fake["now_ms"] = 6000
    await mode.handle_event("answer", "p2", {"text": "michael jackson"})
    mode.advance_to_reveal()

    all_matches = mode.state["round_results"]["all_matches"]
    assert len(all_matches) == 3
    assert [m["time_ms"] for m in all_matches] == [2000, 4000, 6000]
    assert all_matches[0]["match_type"] == "title"
    assert all_matches[1]["match_type"] == "bonus"
    assert all_matches[2]["match_type"] == "artist"


@pytest.mark.asyncio
async def test_all_matches_empty_when_no_matches() -> None:
    mode = await _started_mode(num_rounds=1, num_players=2)
    await mode.handle_event("countdown_done", "p0", {})
    await mode.handle_event("answer", "p0", {"text": "bananas", "time_ms": 1000})
    mode.advance_to_reveal()

    assert mode.state["round_results"]["all_matches"] == []


@pytest.mark.asyncio
async def test_all_matches_match_type_is_correct() -> None:
    mode = await _started_mode(num_rounds=1, num_players=3)
    await mode.handle_event("countdown_done", "p0", {})

    await mode.handle_event("answer", "p0", {"text": "thriller michael jackson", "time_ms": 1000})
    await mode.handle_event("answer", "p1", {"text": "thriller", "time_ms": 2000})
    await mode.handle_event("answer", "p2", {"text": "michael jackson", "time_ms": 3000})
    mode.advance_to_reveal()

    all_matches = mode.state["round_results"]["all_matches"]
    types_by_player = {m["player_id"]: m["match_type"] for m in all_matches}
    assert types_by_player["p0"] == "bonus"
    assert types_by_player["p1"] == "title"
    assert types_by_player["p2"] == "artist"


@pytest.mark.asyncio
async def test_blindtest_end() -> None:
    mode = await _started_mode()
    final = await mode.end()
    assert "total_scores" in final
    assert "awards" in final
    assert "rounds" in final


@pytest.mark.asyncio
async def test_end_tracklist_reports_first_finders_per_round() -> None:
    mode = await _started_mode(num_rounds=2, num_players=3)
    await mode.handle_event("countdown_done", "p0", {})
    # Round 1 (Thriller / Michael Jackson): p1 snipes the title, p2 completes
    # the artist, p0 finds nothing.
    await mode.handle_event("answer", "p1", {"text": "thriller", "time_ms": 1000})
    await mode.handle_event("answer", "p2", {"text": "michael jackson", "time_ms": 2000})
    mode.advance_to_reveal()
    mode.advance_to_pause()
    mode.advance_to_next_round()
    # Round 2 (Song1 / Artist1): nobody finds anything.
    mode.advance_to_reveal()
    mode.advance_to_pause()
    mode.advance_to_next_round()

    final = await mode.end()
    tracklist = final["tracklist"]
    assert len(tracklist) == 2

    r1 = tracklist[0]
    assert r1["round"] == 1
    assert r1["title"] == "Thriller"
    assert r1["artist"] == "Michael Jackson"
    assert r1["cover_url"] == "https://cover/0"
    assert r1["first_title"]["player_id"] == "p1"
    assert r1["first_title"]["name"] == "Player1"
    assert r1["first_artist"]["player_id"] == "p2"
    assert r1["first_artist"]["name"] == "Player2"
    assert r1["nobody_found"] is False

    r2 = tracklist[1]
    assert r2["round"] == 2
    assert r2["title"] == "Song1"
    assert r2["first_title"] is None
    assert r2["first_artist"] is None
    assert r2["nobody_found"] is True


@pytest.mark.asyncio
async def test_end_tracklist_first_title_is_the_earliest_server_time(monkeypatch) -> None:
    fake = {"now_ms": 1_000_000}
    monkeypatch.setattr("app.game.blindtest._now_ms", lambda: fake["now_ms"])

    mode = await _started_mode(num_rounds=1, num_players=3)
    await mode.handle_event("countdown_done", "p0", {})
    fake["now_ms"] = 1_002_000
    await mode.handle_event("answer", "p2", {"text": "thriller", "time_ms": 0})
    fake["now_ms"] = 1_005_000
    await mode.handle_event("answer", "p1", {"text": "thriller", "time_ms": 0})
    mode.advance_to_reveal()
    mode.advance_to_pause()
    mode.advance_to_next_round()

    final = await mode.end()
    first_title = final["tracklist"][0]["first_title"]
    assert first_title["player_id"] == "p2"
    assert first_title["time_ms"] == 2000


@pytest.mark.asyncio
async def test_round_pause_is_last_round_flag_true_on_final_round() -> None:
    mode = await _started_mode(num_rounds=1)
    await mode.handle_event("countdown_done", "p0", {})
    mode.advance_to_reveal()
    result = mode.advance_to_pause()
    assert result["is_last_round"] is True
    assert mode.state["is_last_round"] is True


@pytest.mark.asyncio
async def test_round_pause_is_last_round_flag_false_on_non_final_round() -> None:
    mode = await _started_mode(num_rounds=3)
    await mode.handle_event("countdown_done", "p0", {})
    mode.advance_to_reveal()
    result = mode.advance_to_pause()
    assert result["is_last_round"] is False
    assert mode.state["is_last_round"] is False


@pytest.mark.asyncio
async def test_server_clock_overrides_client_supplied_time_ms(monkeypatch) -> None:
    """Anti-cheat: a tampered client sending time_ms=0 must not score max points.

    The server stamps the round start with a monotonic clock and computes the
    answer time from that. Any time_ms in the client payload is ignored.
    """
    fake = {"now_ms": 1_000_000}
    monkeypatch.setattr("app.game.blindtest._now_ms", lambda: fake["now_ms"])

    mode = await _started_mode(num_rounds=1)
    await mode.handle_event("countdown_done", "p0", {})
    # 7 seconds elapse on the server clock.
    fake["now_ms"] = 1_007_000

    # Client cheats by sending time_ms=0.
    result = await mode.handle_event("answer", "p0", {"text": "thriller", "time_ms": 0})
    assert result is not None
    assert result["title_match"] is True
    # Server-computed time_ms is the real elapsed time, not the client's lie.
    assert result["time_ms"] == 7000
    assert result["title_time_ms"] == 7000


@pytest.mark.asyncio
async def test_server_clock_clamps_to_extract_duration(monkeypatch) -> None:
    """An answer way past the round window is clamped to extract_duration_ms."""
    fake = {"now_ms": 0}
    monkeypatch.setattr("app.game.blindtest._now_ms", lambda: fake["now_ms"])

    mode = await _started_mode(num_rounds=1)
    await mode.handle_event("countdown_done", "p0", {})
    # 5 minutes later — beyond the 30s extract.
    fake["now_ms"] = 5 * 60 * 1000

    result = await mode.handle_event("answer", "p0", {"text": "thriller"})
    assert result is not None
    assert result["time_ms"] == 30_000  # clamped to extract_duration


@pytest.mark.asyncio
async def test_fuzzy_composite_accumulates_across_guesses() -> None:
    """Composite artist: each component typed separately accumulates to artist_match."""
    tracks: list[dict[str, Any]] = [
        {
            "id": 0,
            "title": "Titanium",
            "artist": "David Guetta feat. Florida",
            "preview_url": "https://preview/0",
            "cover_url": "https://cover/0",
            "album": "",
            "duration": 30,
            "rank": 500000,
        },
    ]
    mode = await _started_mode(num_rounds=1, num_players=1, custom_tracks=tracks)
    await mode.handle_event("countdown_done", "p0", {})

    # First guess: main artist (1 of 2 components)
    r1 = await mode.handle_event("answer", "p0", {"text": "David Guetta", "time_ms": 3000})
    assert r1 is not None
    assert r1["artist_match"] is False  # only 1/2 components
    assert 0 in r1["matched_artist_indices"]

    # Second guess: featured artist (2 of 2 components → artist complete)
    r2 = await mode.handle_event("answer", "p0", {"text": "Florida", "time_ms": 5000})
    assert r2 is not None
    assert r2["artist_match"] is True  # both components found
    assert r2["bonus"] is False  # title not yet found

    # Third guess: the title → bonus
    r3 = await mode.handle_event("answer", "p0", {"text": "Titanium", "time_ms": 7000})
    assert r3 is not None
    assert r3["title_match"] is True
    assert r3["artist_match"] is True
    assert r3["bonus"] is True
