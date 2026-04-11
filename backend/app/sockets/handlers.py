from app.main import sio
from app.database import get_redis
from app.rooms.service import RoomService


def register_handlers():
    @sio.event
    async def connect(sid, environ):
        print(f"Client connected: {sid}")

    @sio.event
    async def disconnect(sid):
        print(f"Client disconnected: {sid}")
        redis = get_redis()
        room_code = await redis.get(f"player_room:{sid}")
        if room_code:
            svc = RoomService(redis)
            player_id = await redis.get(f"player_id:{sid}")
            if player_id:
                room = await svc.leave_room(room_code, player_id)
                if room:
                    await sio.emit("room_updated", room, room=room_code)
            await redis.delete(f"player_room:{sid}", f"player_id:{sid}")

    @sio.event
    async def join_room(sid, data):
        code = data["code"]
        player_id = data["player_id"]
        redis = get_redis()
        svc = RoomService(redis)
        room = await svc.get_room(code)
        if not room:
            await sio.emit("error", {"message": "Room not found"}, to=sid)
            return

        await sio.enter_room(sid, code)
        await redis.set(f"player_room:{sid}", code, ex=1800)
        await redis.set(f"player_id:{sid}", player_id, ex=1800)
        await sio.emit("room_updated", room, room=code)

    @sio.event
    async def update_settings(sid, data):
        code = data["code"]
        host_id = data["host_id"]
        settings = data["settings"]
        redis = get_redis()
        svc = RoomService(redis)
        room = await svc.update_settings(code, host_id, settings)
        if room:
            await sio.emit("room_updated", room, room=code)

    @sio.event
    async def start_game(sid, data):
        code = data["code"]
        redis = get_redis()
        svc = RoomService(redis)
        room = await svc.set_status(code, "playing")
        if room:
            await sio.emit("game_started", room, room=code)

    @sio.event
    async def reaction(sid, data):
        code = data["code"]
        await sio.emit(
            "reaction_received",
            {
                "player_id": data["player_id"],
                "player_name": data["player_name"],
                "emoji": data["emoji"],
            },
            room=code,
        )

    @sio.event
    async def soundboard(sid, data):
        code = data["code"]
        await sio.emit(
            "soundboard_played",
            {
                "player_name": data["player_name"],
                "sound": data["sound"],
            },
            room=code,
        )
