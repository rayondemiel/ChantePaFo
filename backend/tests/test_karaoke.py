from typing import Any

import pytest

from app.game.karaoke import PROGRESSIVE_TABLE, KaraokeMystereMode


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
async def test_karaoke_start_classic() -> None:
    mode = KaraokeMystereMode()
    await mode.start(
        players=_players(2),
        settings={"num_rounds": 3, "karaoke_variant": "classic", "genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )
    state = mode.get_state()
    assert state["phase"] == "listening"
    assert state["variant"] == "classic"
    assert state["constraint"] == "free"


@pytest.mark.asyncio
async def test_karaoke_start_progressive() -> None:
    mode = KaraokeMystereMode()
    await mode.start(
        players=_players(1),
        settings={"num_rounds": 3, "karaoke_variant": "progressive", "genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )
    state = mode.get_state()
    assert state["variant"] == "progressive"
    assert state["listen_duration"] == PROGRESSIVE_TABLE[0]["listen_duration"]


@pytest.mark.asyncio
async def test_karaoke_recording_submitted() -> None:
    mode = KaraokeMystereMode()
    await mode.start(
        players=_players(2),
        settings={"num_rounds": 1, "karaoke_variant": "classic", "genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )
    mode.state["phase"] = "recording"
    result = await mode.handle_event(
        "recording_submitted", "p0", {"audio_url": "/uploads/p0_r0.webm"}
    )
    assert result is not None
    assert result["status"] == "recorded"


@pytest.mark.asyncio
async def test_karaoke_all_recorded_moves_to_guessing() -> None:
    mode = KaraokeMystereMode()
    await mode.start(
        players=_players(2),
        settings={"num_rounds": 1, "karaoke_variant": "classic", "genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )
    mode.state["phase"] = "recording"
    await mode.handle_event("recording_submitted", "p0", {"audio_url": "/uploads/p0.webm"})
    await mode.handle_event("recording_submitted", "p1", {"audio_url": "/uploads/p1.webm"})
    assert mode.state["phase"] == "guessing"


@pytest.mark.asyncio
async def test_karaoke_guess_correct() -> None:
    mode = KaraokeMystereMode()
    await mode.start(
        players=_players(2),
        settings={"num_rounds": 1, "karaoke_variant": "classic", "genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )
    mode.state["phase"] = "guessing"
    mode.state["current_recording_idx"] = 0
    mode.recordings = {
        0: [
            {"player_id": "p0", "audio_url": "/p0.webm"},
            {"player_id": "p1", "audio_url": "/p1.webm"},
        ]
    }
    result = await mode.handle_event("guess", "p1", {"text": "Song0", "time_ms": 3000})
    assert result is not None
    assert result["title_match"] is True


@pytest.mark.asyncio
async def test_karaoke_end() -> None:
    mode = KaraokeMystereMode()
    await mode.start(
        players=_players(1),
        settings={"num_rounds": 1, "karaoke_variant": "classic", "genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )
    final = await mode.end()
    assert "awards" in final
    assert "total_scores" in final


def test_progressive_table_has_5_rounds() -> None:
    assert len(PROGRESSIVE_TABLE) == 5
    assert PROGRESSIVE_TABLE[0]["constraint"] == "free"
    assert PROGRESSIVE_TABLE[4]["constraint"] == "whisper"
