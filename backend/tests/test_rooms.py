import pytest

from app.rooms.service import RoomService


@pytest.fixture
def room_service(fake_redis):
    return RoomService(fake_redis)


@pytest.mark.asyncio
async def test_create_room(room_service):
    room = await room_service.create_room(host_id="host-1", host_name="Alice")
    assert room["code"]
    assert room["host_id"] == "host-1"
    assert len(room["players"]) == 1
    assert room["players"][0]["name"] == "Alice"


@pytest.mark.asyncio
async def test_join_room(room_service):
    room = await room_service.create_room(host_id="host-1", host_name="Alice")
    updated = await room_service.join_room(room["code"], player_id="p2", player_name="Bob")
    assert len(updated["players"]) == 2
    names = [p["name"] for p in updated["players"]]
    assert "Bob" in names


@pytest.mark.asyncio
async def test_join_nonexistent_room(room_service):
    result = await room_service.join_room("FAKE99", player_id="p1", player_name="Bob")
    assert result is None


@pytest.mark.asyncio
async def test_join_full_room(room_service):
    room = await room_service.create_room(host_id="host-1", host_name="Alice")
    for i in range(9):
        await room_service.join_room(room["code"], player_id=f"p{i}", player_name=f"Player{i}")
    result = await room_service.join_room(room["code"], player_id="p99", player_name="TooMany")
    assert result is None


@pytest.mark.asyncio
async def test_leave_room(room_service):
    room = await room_service.create_room(host_id="host-1", host_name="Alice")
    await room_service.join_room(room["code"], player_id="p2", player_name="Bob")
    updated = await room_service.leave_room(room["code"], player_id="p2")
    assert len(updated["players"]) == 1


@pytest.mark.asyncio
async def test_get_room(room_service):
    room = await room_service.create_room(host_id="host-1", host_name="Alice")
    fetched = await room_service.get_room(room["code"])
    assert fetched["code"] == room["code"]


@pytest.mark.asyncio
async def test_update_room_settings(room_service):
    room = await room_service.create_room(host_id="host-1", host_name="Alice")
    updated = await room_service.update_settings(
        room["code"],
        host_id="host-1",
        settings={
            "game_mode": "blindtest",
            "genres": ["rock", "pop"],
            "num_rounds": 15,
        },
    )
    assert updated["settings"]["game_mode"] == "blindtest"
    assert updated["settings"]["genres"] == ["rock", "pop"]
