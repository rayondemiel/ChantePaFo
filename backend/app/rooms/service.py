import json
from typing import Any

from redis.asyncio import Redis

from app.metrics import ROOMS_CREATED_TOTAL
from app.rooms.codegen import generate_room_code

ROOM_TTL = 1800  # 30 minutes
MAX_PLAYERS = 10

# Server-side fields that must never be exposed to clients.
_PRIVATE_ROOM_FIELDS = frozenset({"host_id"})


def public_room(room: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the room dict with server-only fields stripped.

    Used at every client-facing boundary (REST responses, Socket.IO broadcasts)
    so that capability fields like `host_id` never leak.
    """
    return {k: v for k, v in room.items() if k not in _PRIVATE_ROOM_FIELDS}


class RoomService:
    def __init__(self, redis: Redis):
        self.redis = redis

    def _key(self, code: str) -> str:
        return f"room:{code}"

    async def create_room(self, host_id: str, host_name: str) -> dict[str, Any]:
        room: dict[str, Any] = {
            "host_id": host_id,
            "players": [{"id": host_id, "name": host_name, "is_host": True}],
            "settings": {
                "game_mode": "blindtest",
                "genres": ["all"],
                "num_rounds": 10,
                "extract_duration": 20,
                "karaoke_variant": "classic",
            },
            "status": "lobby",
        }
        # Atomically claim a unique code via SET NX to avoid a race between
        # EXISTS and SET in concurrent create_room calls.
        for _ in range(10):
            code = generate_room_code()
            room["code"] = code
            claimed = await self.redis.set(self._key(code), json.dumps(room), ex=ROOM_TTL, nx=True)
            if claimed:
                ROOMS_CREATED_TOTAL.inc()
                return room
        raise RuntimeError("Failed to allocate a unique room code after 10 attempts")

    async def get_room(self, code: str) -> dict[str, Any] | None:
        data = await self.redis.get(self._key(code))
        return json.loads(data) if data else None

    async def join_room(self, code: str, player_id: str, player_name: str) -> dict[str, Any] | None:
        room = await self.get_room(code)
        if not room:
            return None
        if len(room["players"]) >= MAX_PLAYERS:
            return None

        existing_ids = {p["id"] for p in room["players"]}
        if player_id not in existing_ids:
            room["players"].append({"id": player_id, "name": player_name, "is_host": False})

        await self.redis.set(self._key(code), json.dumps(room), ex=ROOM_TTL)
        return room

    async def leave_room(self, code: str, player_id: str) -> dict[str, Any] | None:
        room = await self.get_room(code)
        if not room:
            return None
        was_host = room["host_id"] == player_id
        room["players"] = [p for p in room["players"] if p["id"] != player_id]
        if not room["players"]:
            await self.redis.delete(self._key(code))
            return {
                "code": code,
                "players": [],
                "settings": room["settings"],
                "status": "closed",
            }
        if was_host:
            new_host = room["players"][0]
            room["host_id"] = new_host["id"]
            for p in room["players"]:
                p["is_host"] = p["id"] == new_host["id"]
        await self.redis.set(self._key(code), json.dumps(room), ex=ROOM_TTL)
        return room

    async def update_settings(
        self, code: str, host_id: str, settings: dict[str, Any]
    ) -> dict[str, Any] | None:
        room = await self.get_room(code)
        if not room or room["host_id"] != host_id:
            return None
        room["settings"].update(settings)
        await self.redis.set(self._key(code), json.dumps(room), ex=ROOM_TTL)
        return room

    async def set_status(self, code: str, status: str) -> dict[str, Any] | None:
        room = await self.get_room(code)
        if not room:
            return None
        room["status"] = status
        await self.redis.set(self._key(code), json.dumps(room), ex=ROOM_TTL)
        return room
