from typing import Any

import pytest

from app.game.telephone import TelephoneArabeMode


class FakeTrackProvider:
    async def get_random_tracks(
        self, genre_config: dict[str, int], count: int = 10
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": i,
                "title": f"Song{i}",
                "artist": f"Artist{i}",
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
async def test_telephone_start() -> None:
    mode = TelephoneArabeMode()
    await mode.start(
        players=_players(4),
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )
    state = mode.get_state()
    assert state["phase"] == "singing"
    assert state["current_step"] == 0
    assert state["total_steps"] == 4
    assert len(state["chains"]) == 4


@pytest.mark.asyncio
async def test_telephone_chain_assignment() -> None:
    mode = TelephoneArabeMode()
    await mode.start(
        players=_players(4),
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )
    for chain in mode.chains:
        assert chain["original_track"]["id"] is not None
        assert len(chain["steps"]) == 0


@pytest.mark.asyncio
async def test_telephone_submit_singing() -> None:
    mode = TelephoneArabeMode()
    await mode.start(
        players=_players(3),
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )
    mode.state["phase"] = "singing"

    await mode.handle_event("submit_step", "p0", {"audio_url": "/uploads/p0_s0.webm"})
    await mode.handle_event("submit_step", "p1", {"audio_url": "/uploads/p1_s0.webm"})
    result = await mode.handle_event("submit_step", "p2", {"audio_url": "/uploads/p2_s0.webm"})

    assert result is not None
    assert result["all_done"] is True
    assert mode.state["phase"] == "writing"


@pytest.mark.asyncio
async def test_telephone_submit_writing() -> None:
    mode = TelephoneArabeMode()
    await mode.start(
        players=_players(3),
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )
    mode.state["phase"] = "singing"
    mode.state["current_step"] = 0

    for i in range(3):
        await mode.handle_event("submit_step", f"p{i}", {"audio_url": f"/uploads/p{i}.webm"})

    # Now in writing phase
    assert mode.state["phase"] == "writing"
    await mode.handle_event("submit_step", "p0", {"text": "Song guess 0"})
    await mode.handle_event("submit_step", "p1", {"text": "Song guess 1"})
    result = await mode.handle_event("submit_step", "p2", {"text": "Song guess 2"})

    assert result is not None
    assert result["all_done"] is True


@pytest.mark.asyncio
async def test_telephone_full_game() -> None:
    mode = TelephoneArabeMode()
    players = _players(3)
    await mode.start(
        players=players,
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )

    # 3 players = 3 steps (sing, write, sing)
    for step in range(3):
        for p in players:
            if mode.state["phase"] == "singing":
                await mode.handle_event(
                    "submit_step", p["id"], {"audio_url": f"/u/{p['id']}_s{step}.webm"}
                )
            else:
                await mode.handle_event(
                    "submit_step", p["id"], {"text": f"guess_{p['id']}_s{step}"}
                )

    assert mode.state["phase"] == "reveal"


@pytest.mark.asyncio
async def test_telephone_end() -> None:
    mode = TelephoneArabeMode()
    await mode.start(
        players=_players(3),
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )
    final = await mode.end()
    assert "chains" in final
    assert "total_scores" in final
