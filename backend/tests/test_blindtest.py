from typing import Any

import pytest

from app.game.blindtest import BlindtestMode


class FakeTrackProvider:
    async def get_random_tracks(
        self, genre_config: dict[str, int], count: int = 10
    ) -> list[dict[str, Any]]:
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


async def _started_mode(num_rounds: int = 2, num_players: int = 2) -> BlindtestMode:
    mode = BlindtestMode()
    await mode.start(
        players=_players(num_players),
        settings={"num_rounds": num_rounds, "genres": {"pop": 1}},
        track_provider=FakeTrackProvider(),
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
async def test_blindtest_end() -> None:
    mode = await _started_mode()
    final = await mode.end()
    assert "total_scores" in final
    assert "awards" in final
    assert "rounds" in final
