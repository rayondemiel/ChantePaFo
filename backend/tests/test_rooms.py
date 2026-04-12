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
            "genres": {"rock": 3, "pop": 1},
            "num_rounds": 15,
        },
    )
    assert updated["settings"]["game_mode"] == "blindtest"
    assert updated["settings"]["genres"] == {"rock": 3, "pop": 1}


@pytest.mark.asyncio
async def test_update_settings_nonexistent_room(room_service):
    result = await room_service.update_settings("FAKE99", host_id="host-1", settings={})
    assert result is None


@pytest.mark.asyncio
async def test_update_settings_wrong_host(room_service):
    room = await room_service.create_room(host_id="host-1", host_name="Alice")
    result = await room_service.update_settings(
        room["code"], host_id="not-the-host", settings={"num_rounds": 5}
    )
    assert result is None


@pytest.mark.asyncio
async def test_set_status(room_service):
    room = await room_service.create_room(host_id="host-1", host_name="Alice")
    updated = await room_service.set_status(room["code"], "playing")
    assert updated["status"] == "playing"


@pytest.mark.asyncio
async def test_set_status_nonexistent_room(room_service):
    result = await room_service.set_status("FAKE99", "playing")
    assert result is None


@pytest.mark.asyncio
async def test_leave_room_when_last_player(room_service):
    """When the last player leaves, the room is deleted and status becomes 'closed'."""
    room = await room_service.create_room(host_id="host-1", host_name="Alice")
    result = await room_service.leave_room(room["code"], player_id="host-1")
    assert result["status"] == "closed"
    assert result["players"] == []
    # Room should be gone from Redis
    gone = await room_service.get_room(room["code"])
    assert gone is None


@pytest.mark.asyncio
async def test_leave_room_nonexistent(room_service):
    result = await room_service.leave_room("FAKE99", player_id="p1")
    assert result is None


@pytest.mark.asyncio
async def test_leave_room_promotes_new_host_when_host_leaves(room_service):
    room = await room_service.create_room(host_id="host-1", host_name="Alice")
    await room_service.join_room(room["code"], player_id="p2", player_name="Bob")
    await room_service.join_room(room["code"], player_id="p3", player_name="Carol")

    updated = await room_service.leave_room(room["code"], player_id="host-1")

    assert updated is not None
    assert updated["host_id"] == "p2"  # first remaining
    assert updated["players"][0]["id"] == "p2"
    assert updated["players"][0]["is_host"] is True
    assert all(p["is_host"] is False for p in updated["players"][1:])


@pytest.mark.asyncio
async def test_leave_room_non_host_keeps_host(room_service):
    room = await room_service.create_room(host_id="host-1", host_name="Alice")
    await room_service.join_room(room["code"], player_id="p2", player_name="Bob")
    updated = await room_service.leave_room(room["code"], player_id="p2")
    assert updated["host_id"] == "host-1"


@pytest.mark.asyncio
async def test_update_settings_partial_merge(room_service):
    room = await room_service.create_room(host_id="h1", host_name="Alice")
    updated = await room_service.update_settings(
        room["code"],
        host_id="h1",
        settings={"num_rounds": 15},  # only num_rounds
    )
    assert updated is not None
    assert updated["settings"]["num_rounds"] == 15
    assert updated["settings"]["game_mode"] == "blindtest"  # unchanged


@pytest.mark.asyncio
async def test_update_settings_rejects_extra_keys_at_service_level(room_service):
    # The service itself doesn't validate extra keys — the socket handler does via
    # PartialRoomSettings. The service still merges whatever dict it receives.
    room = await room_service.create_room(host_id="h1", host_name="Alice")
    updated = await room_service.update_settings(
        room["code"], host_id="h1", settings={"num_rounds": 12}
    )
    assert updated is not None
    assert updated["settings"]["num_rounds"] == 12
