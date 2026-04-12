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


@pytest.mark.asyncio
async def test_telephone_empty_tracks() -> None:
    """Bug 5: empty track provider must set phase=finished without crashing."""

    class EmptyTrackProvider:
        async def get_random_tracks(
            self, genre_config: dict[str, int], count: int = 10
        ) -> list[dict[str, Any]]:
            return []

    mode = TelephoneArabeMode()
    await mode.start(
        players=_players(3),
        settings={"genres": {"all": 1}},
        track_provider=EmptyTrackProvider(),
    )
    state = mode.get_state()
    assert state["phase"] == "finished"
    assert state.get("error") == "no_tracks_available"


@pytest.mark.asyncio
async def test_telephone_unknown_player_submit() -> None:
    """Bug 6: submitting a step for an unknown player must not raise KeyError."""
    mode = TelephoneArabeMode()
    await mode.start(
        players=_players(3),
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )
    # "ghost" is not in history["players"] — should use player_id as fallback name
    result = await mode.handle_event("submit_step", "ghost", {"audio_url": "/ghost.webm"})
    assert result is not None
    assert result["status"] == "submitted"


@pytest.mark.asyncio
async def test_telephone_awards_populated() -> None:
    """Bug 8: after a full game, history['rounds'] must be non-empty."""
    mode = TelephoneArabeMode()
    players = _players(3)
    await mode.start(
        players=players,
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )

    # Drive the full game to reveal phase
    for step in range(3):
        for p in players:
            if mode.state["phase"] == "singing":
                await mode.handle_event(
                    "submit_step", p["id"], {"audio_url": f"/u/{p['id']}_s{step}.webm"}
                )
            else:
                await mode.handle_event("submit_step", p["id"], {"text": f"Song{step}"})

    assert mode.state["phase"] == "reveal"
    assert len(mode.history["rounds"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# New targeted tests for missing coverage
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_telephone_get_input_step_zero() -> None:
    """_get_player_input at step 0 returns the original track preview_url."""
    mode = TelephoneArabeMode()
    await mode.start(
        players=_players(3),
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )
    # Step 0, phase = singing
    assert mode.state["current_step"] == 0
    result = await mode.handle_event("get_input", "p0", {})
    assert result is not None
    assert result["type"] == "original"
    assert result["preview_url"].startswith("https://preview/")


@pytest.mark.asyncio
async def test_telephone_get_input_later_step() -> None:
    """_get_player_input at step > 0 returns the previous step data."""
    mode = TelephoneArabeMode()
    players = _players(3)
    await mode.start(
        players=players,
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )

    # Submit all singing to advance to step 1
    for p in players:
        await mode.handle_event("submit_step", p["id"], {"audio_url": f"/u/{p['id']}.webm"})

    # Now at step 1, phase = writing
    assert mode.state["current_step"] == 1

    result = await mode.handle_event("get_input", "p0", {})
    # Should return previous step data (a sing step) — not None, not "original"
    assert result is not None
    assert result.get("type") == "sing"


@pytest.mark.asyncio
async def test_telephone_vote_chain() -> None:
    """vote_chain event registers a vote and returns {'status': 'voted'}."""
    mode = TelephoneArabeMode()
    await mode.start(
        players=_players(3),
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )

    result = await mode.handle_event("vote_chain", "p0", {"chain_id": 0, "vote_type": "funniest"})
    assert result == {"status": "voted"}
    assert mode.chains[0]["votes"]["funniest"] == 1

    # Second vote increments the counter
    await mode.handle_event("vote_chain", "p1", {"chain_id": 0, "vote_type": "funniest"})
    assert mode.chains[0]["votes"]["funniest"] == 2


@pytest.mark.asyncio
async def test_telephone_vote_chain_out_of_bounds() -> None:
    """vote_chain with an invalid chain_id returns {'status': 'voted'} but adds no votes."""
    mode = TelephoneArabeMode()
    await mode.start(
        players=_players(2),
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )

    result = await mode.handle_event("vote_chain", "p0", {"chain_id": 99, "vote_type": "funniest"})
    assert result == {"status": "voted"}
    # No chain should have votes
    for chain in mode.chains:
        assert "votes" not in chain


@pytest.mark.asyncio
async def test_telephone_end_with_votes() -> None:
    """end() includes votes dict in each chain when votes exist."""
    mode = TelephoneArabeMode()
    await mode.start(
        players=_players(2),
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )

    # Add a vote to chain 0
    await mode.handle_event("vote_chain", "p0", {"chain_id": 0, "vote_type": "funniest"})

    final = await mode.end()
    assert "chains" in final
    chains_with_votes = [c for c in final["chains"] if c.get("votes")]
    assert len(chains_with_votes) >= 1
    assert chains_with_votes[0]["votes"]["funniest"] == 1


@pytest.mark.asyncio
async def test_telephone_singer_bonus_when_next_writer_correct() -> None:
    """Singer gets 300 bonus points when the next writer correctly identifies the song."""
    mode = TelephoneArabeMode()
    players = _players(2)
    await mode.start(
        players=players,
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )

    # With 2 players there are 2 steps: step 0 (singing), step 1 (writing)
    # Step 0: both players sing
    for p in players:
        await mode.handle_event("submit_step", p["id"], {"audio_url": f"/u/{p['id']}.webm"})

    # Step 1: both players write the exact song title to trigger the singer bonus
    # The chain assigned to each player at step 1 — player[pi] works on chain (pi+1)%2
    # p0 sings chain 0, p1 sings chain 1; at step 1 p0 writes chain 1, p1 writes chain 0
    # chain 0 original_track title = "Song0", chain 1 original_track title = "Song1"
    for p in players:
        chain_idx = mode.rotation[1][p["id"]]
        title = mode.chains[chain_idx]["original_track"]["title"]
        await mode.handle_event("submit_step", p["id"], {"text": title})

    assert mode.state["phase"] == "reveal"

    # Each singer should have received 300 bonus points
    assert mode.history["total_scores"]["p0"] >= 300
    assert mode.history["total_scores"]["p1"] >= 300


@pytest.mark.asyncio
async def test_telephone_get_input_step_gt_zero_no_steps() -> None:
    """_get_player_input at step > 0 returns None when chain has no steps yet."""
    mode = TelephoneArabeMode()
    players = _players(3)
    await mode.start(
        players=players,
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )

    # Manually advance state to step 1 without submitting any steps
    mode.state["current_step"] = 1
    mode.state["phase"] = "writing"

    # Chain still has empty steps list — should return None
    result = await mode.handle_event("get_input", "p0", {})
    assert result is None


@pytest.mark.asyncio
async def test_telephone_handle_event_unknown_type_returns_none() -> None:
    """handle_event with an unknown event_type returns None."""
    mode = TelephoneArabeMode()
    await mode.start(
        players=_players(2),
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )

    result = await mode.handle_event("unknown_event", "p0", {})
    assert result is None


@pytest.mark.asyncio
async def test_telephone_singer_no_bonus_when_next_step_is_not_write() -> None:
    """_score_singer skips bonus when step after singing is also a sing step."""
    mode = TelephoneArabeMode()
    players = _players(2)
    await mode.start(
        players=players,
        settings={"genres": {"all": 1}},
        track_provider=FakeTrackProvider(),
    )

    # Manually craft a chain where two consecutive steps are both "sing" (no write between)
    chain = mode.chains[0]
    chain["steps"] = [
        {"player_id": "p0", "player_name": "Player0", "step_idx": 0, "type": "sing", "audio_url": "/a.webm"},
        {"player_id": "p1", "player_name": "Player1", "step_idx": 1, "type": "sing", "audio_url": "/b.webm"},
    ]
    mode.history["total_scores"]["p0"] = 0
    mode.history["total_scores"]["p1"] = 0

    round_data: dict[str, Any] = {"answers": {}, "scores": {}}
    # Call _score_singer on step index 0; next step is "sing" not "write" → no bonus
    mode._score_singer("p0", 0, chain["steps"], chain["original_track"]["title"], chain["original_track"]["artist"], round_data)

    assert mode.history["total_scores"]["p0"] == 0
    assert round_data["scores"] == {}
