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
                "cover_url": "",
                "album": "",
                "duration": 30,
                "rank": 500000,
            }
            for i in range(count)
        ]


def _players(n: int) -> list[dict[str, str]]:
    return [{"id": f"p{i}", "name": f"Player{i}"} for i in range(n)]


@pytest.mark.asyncio
async def test_blindtest_start() -> None:
    mode = BlindtestMode()
    await mode.start(
        players=_players(2),
        settings={"num_rounds": 2, "genres": {"pop": 1, "rock": 2}},
        track_provider=FakeTrackProvider(),
    )
    state = mode.get_state()
    assert state["phase"] == "countdown"
    assert state["current_round"] == 0
    assert state["total_rounds"] == 2


@pytest.mark.asyncio
async def test_blindtest_correct_answer() -> None:
    mode = BlindtestMode()
    await mode.start(
        players=_players(2),
        settings={"num_rounds": 2, "genres": {"pop": 1}},
        track_provider=FakeTrackProvider(),
    )
    mode.state["phase"] = "playing"
    # Round 0 has track title "Thriller" / artist "Michael Jackson"
    result = await mode.handle_event("answer", "p0", {"text": "thriller", "time_ms": 5000})
    assert result is not None
    assert result["title_match"] is True


@pytest.mark.asyncio
async def test_blindtest_wrong_answer() -> None:
    mode = BlindtestMode()
    await mode.start(
        players=_players(2),
        settings={"num_rounds": 2, "genres": {"pop": 1}},
        track_provider=FakeTrackProvider(),
    )
    mode.state["phase"] = "playing"
    result = await mode.handle_event("answer", "p0", {"text": "bananas", "time_ms": 5000})
    assert result is not None
    assert result["title_match"] is False


@pytest.mark.asyncio
async def test_blindtest_advance_round() -> None:
    mode = BlindtestMode()
    await mode.start(
        players=_players(2),
        settings={"num_rounds": 2, "genres": {"pop": 1}},
        track_provider=FakeTrackProvider(),
    )
    mode.state["phase"] = "playing"
    await mode.handle_event("answer", "p0", {"text": "thriller", "time_ms": 3000})
    result = await mode.handle_event("next_round", "p0", {})
    assert result is not None
    # After advancing, phase should change (either countdown for next round or finished)
    assert result["phase"] in ("countdown", "finished", "round_result")


@pytest.mark.asyncio
async def test_blindtest_end() -> None:
    mode = BlindtestMode()
    await mode.start(
        players=_players(2),
        settings={"num_rounds": 2, "genres": {"pop": 1}},
        track_provider=FakeTrackProvider(),
    )
    final = await mode.end()
    assert "total_scores" in final
    assert "awards" in final
    assert "rounds" in final
