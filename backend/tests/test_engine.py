from typing import Any

import pytest

from app.game.engine import GameMode, GameRegistry, GameSession


class FakeMode(GameMode):
    name = "fake"

    async def start(
        self, players: list[dict[str, Any]], settings: dict[str, Any], track_provider: Any
    ) -> None:
        self.state: dict[str, Any] = {"phase": "playing", "round": 1}

    async def handle_event(
        self, event_type: str, player_id: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        if event_type == "answer":
            return {"type": "answer_result", "correct": True}
        return None

    def get_state(self) -> dict[str, Any]:
        return self.state

    async def end(self) -> dict[str, Any]:
        return {"winner": "p1", "scores": {"p1": 100}}


def test_registry_register_and_get() -> None:
    registry = GameRegistry()
    registry.register(FakeMode)
    mode = registry.create("fake")
    assert isinstance(mode, FakeMode)


def test_registry_unknown_mode() -> None:
    registry = GameRegistry()
    with pytest.raises(KeyError):
        registry.create("nonexistent")


def test_registry_list_modes() -> None:
    registry = GameRegistry()
    registry.register(FakeMode)
    assert "fake" in registry.list_modes()


@pytest.mark.asyncio
async def test_game_session_lifecycle() -> None:
    mode = FakeMode()
    session = GameSession(mode)

    await session.start(
        players=[{"id": "p1", "name": "Player1"}, {"id": "p2", "name": "Player2"}],
        settings={},
        track_provider=None,
    )
    assert session.get_state()["phase"] == "playing"

    result = await session.handle_event("answer", "p1", {})
    assert result is not None
    assert result["correct"] is True

    final = await session.end()
    assert final["winner"] == "p1"


@pytest.mark.asyncio
async def test_handle_event_inactive_session() -> None:
    mode = FakeMode()
    session = GameSession(mode)
    result = await session.handle_event("answer", "p1", {})
    assert result is None


@pytest.mark.asyncio
async def test_session_active_after_start() -> None:
    mode = FakeMode()
    session = GameSession(mode)
    assert session.active is False
    await session.start(players=[{"id": "p1", "name": "Player1"}], settings={}, track_provider=None)
    assert session.active is True


@pytest.mark.asyncio
async def test_session_inactive_after_end() -> None:
    mode = FakeMode()
    session = GameSession(mode)
    await session.start(players=[{"id": "p1", "name": "Player1"}], settings={}, track_provider=None)
    await session.end()
    assert session.active is False


@pytest.mark.asyncio
async def test_engine_start_accepts_player_dicts() -> None:
    """Bug 4: GameSession.start must accept list[dict] players without type errors."""
    mode = FakeMode()
    session = GameSession(mode)
    players: list[dict[str, Any]] = [
        {"id": "p1", "name": "Alice"},
        {"id": "p2", "name": "Bob"},
    ]
    # Must not raise — signature now accepts list[dict[str, Any]]
    await session.start(players=players, settings={}, track_provider=None)
    assert session.active is True


def test_registry_overwrite_mode() -> None:
    """Registering the same name twice replaces the previous entry."""
    registry = GameRegistry()
    registry.register(FakeMode)

    class AnotherFake(GameMode):
        name = "fake"

        async def start(
            self,
            players: list[dict[str, Any]],
            settings: dict[str, Any],
            track_provider: Any,
        ) -> None:
            pass

        async def handle_event(
            self, event_type: str, player_id: str, data: dict[str, Any]
        ) -> dict[str, Any] | None:
            return None

        def get_state(self) -> dict[str, Any]:
            return {}

        async def end(self) -> dict[str, Any]:
            return {}

    registry.register(AnotherFake)
    mode = registry.create("fake")
    assert isinstance(mode, AnotherFake)
