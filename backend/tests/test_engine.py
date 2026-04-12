import pytest

from app.game.engine import GameMode, GameRegistry, GameSession


class FakeMode(GameMode):
    name = "fake"

    async def start(self, players: list[str], settings: dict, track_provider: object) -> None:
        self.state = {"phase": "playing", "round": 1}

    async def handle_event(self, event_type: str, player_id: str, data: dict) -> dict | None:
        if event_type == "answer":
            return {"type": "answer_result", "correct": True}
        return None

    def get_state(self) -> dict:
        return self.state  # type: ignore[return-value]

    async def end(self) -> dict:
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

    await session.start(players=["p1", "p2"], settings={}, track_provider=None)
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
    await session.start(players=["p1"], settings={}, track_provider=None)
    assert session.active is True


@pytest.mark.asyncio
async def test_session_inactive_after_end() -> None:
    mode = FakeMode()
    session = GameSession(mode)
    await session.start(players=["p1"], settings={}, track_provider=None)
    await session.end()
    assert session.active is False


def test_registry_overwrite_mode() -> None:
    """Registering the same name twice replaces the previous entry."""
    registry = GameRegistry()
    registry.register(FakeMode)

    class AnotherFake(GameMode):
        name = "fake"

        async def start(self, players: list[str], settings: dict, track_provider: object) -> None:
            pass

        async def handle_event(self, event_type: str, player_id: str, data: dict) -> dict | None:
            return None

        def get_state(self) -> dict:
            return {}

        async def end(self) -> dict:
            return {}

    registry.register(AnotherFake)
    mode = registry.create("fake")
    assert isinstance(mode, AnotherFake)
