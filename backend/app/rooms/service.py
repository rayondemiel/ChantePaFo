import json

from redis.asyncio import Redis

from app.metrics import ROOMS_CREATED_TOTAL
from app.rooms.codegen import generate_room_code

ROOM_TTL = 1800  # 30 minutes
MAX_PLAYERS = 10


class RoomService:
    def __init__(self, redis: Redis):
        self.redis = redis

    def _key(self, code: str) -> str:
        return f"room:{code}"

    async def create_room(self, host_id: str, host_name: str) -> dict:
        code = generate_room_code()
        while await self.redis.exists(self._key(code)):
            code = generate_room_code()

        room = {
            "code": code,
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
        await self.redis.set(self._key(code), json.dumps(room), ex=ROOM_TTL)
        ROOMS_CREATED_TOTAL.inc()
        return room

    async def get_room(self, code: str) -> dict | None:
        data = await self.redis.get(self._key(code))
        return json.loads(data) if data else None

    async def join_room(self, code: str, player_id: str, player_name: str) -> dict | None:
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

    async def leave_room(self, code: str, player_id: str) -> dict | None:
        room = await self.get_room(code)
        if not room:
            return None
        room["players"] = [p for p in room["players"] if p["id"] != player_id]
        if not room["players"]:
            await self.redis.delete(self._key(code))
            return {
                "code": code,
                "players": [],
                "host_id": room["host_id"],
                "settings": room["settings"],
                "status": "closed",
            }
        await self.redis.set(self._key(code), json.dumps(room), ex=ROOM_TTL)
        return room

    async def update_settings(self, code: str, host_id: str, settings: dict) -> dict | None:
        room = await self.get_room(code)
        if not room or room["host_id"] != host_id:
            return None
        room["settings"].update(settings)
        await self.redis.set(self._key(code), json.dumps(room), ex=ROOM_TTL)
        return room

    async def set_status(self, code: str, status: str) -> dict | None:
        room = await self.get_room(code)
        if not room:
            return None
        room["status"] = status
        await self.redis.set(self._key(code), json.dumps(room), ex=ROOM_TTL)
        return room
