from abc import ABC, abstractmethod
from typing import Any


class GameMode(ABC):
    name: str = ""

    @abstractmethod
    async def start(
        self,
        players: list[str],
        settings: dict[str, Any],
        track_provider: Any,
    ) -> None:
        pass

    @abstractmethod
    async def handle_event(
        self,
        event_type: str,
        player_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        pass

    @abstractmethod
    def get_state(self) -> dict[str, Any]:
        pass

    @abstractmethod
    async def end(self) -> dict[str, Any]:
        pass


class GameRegistry:
    def __init__(self) -> None:
        self._modes: dict[str, type[GameMode]] = {}

    def register(self, mode_class: type[GameMode]) -> None:
        self._modes[mode_class.name] = mode_class

    def create(self, mode_name: str) -> GameMode:
        if mode_name not in self._modes:
            raise KeyError(f"Unknown game mode: {mode_name}")
        return self._modes[mode_name]()

    def list_modes(self) -> list[str]:
        return list(self._modes.keys())


class GameSession:
    def __init__(self, mode: GameMode) -> None:
        self.mode = mode
        self.active = False

    async def start(
        self,
        players: list[str],
        settings: dict[str, Any],
        track_provider: Any,
    ) -> None:
        await self.mode.start(players, settings, track_provider)
        self.active = True

    async def handle_event(
        self,
        event_type: str,
        player_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not self.active:
            return None
        return await self.mode.handle_event(event_type, player_id, data)

    def get_state(self) -> dict[str, Any]:
        return self.mode.get_state()

    async def end(self) -> dict[str, Any]:
        self.active = False
        return await self.mode.end()


# Global registry instance — game modes register themselves on import.
registry = GameRegistry()
