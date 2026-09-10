import pytest

# ---------------------------------------------------------------------------
# Auth-guarded access tests (new — finding #1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_room_requires_auth(client):
    resp = await client.post("/rooms", json={"host_name": "Alice"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_room_requires_auth(client):
    # Auth is verified before the room lookup, so a fake code is fine here
    resp = await client.get("/rooms/FAKE99")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_join_room_requires_auth(client):
    resp = await client.post("/rooms/FAKE99/join", json={"player_name": "Bob"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Happy-path tests (authed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_room_endpoint(authed_client):
    resp = await authed_client.post("/rooms", json={"host_name": "Alice"})
    assert resp.status_code == 201
    data = resp.json()
    assert "room" in data
    # host_id must NOT leak to the client
    assert "host_id" not in data
    assert "host_id" not in data["room"]
    assert len(data["room"]["code"]) > 0


@pytest.mark.asyncio
async def test_create_room_uses_authed_user_id(authed_client):
    """The host player's id in the room must equal the authed user's id from the JWT."""
    # Retrieve the authed user id by logging in
    login_resp = await authed_client.post(
        "/auth/login", json={"username": "alice", "password": "password1"}
    )
    assert login_resp.status_code == 200
    user_id = login_resp.json()["user_id"]

    create_resp = await authed_client.post("/rooms", json={"host_name": "Alice"})
    assert create_resp.status_code == 201
    players = create_resp.json()["room"]["players"]
    host_player = next(p for p in players if p["is_host"])
    assert host_player["id"] == user_id


@pytest.mark.asyncio
async def test_get_room_endpoint(authed_client):
    create_resp = await authed_client.post("/rooms", json={"host_name": "Alice"})
    code = create_resp.json()["room"]["code"]

    resp = await authed_client.get(f"/rooms/{code}")
    assert resp.status_code == 200
    body = resp.json()
    assert "room" in body
    room = body["room"]
    assert room["code"] == code
    # host_id must not leak
    assert "host_id" not in room


@pytest.mark.asyncio
async def test_get_room_not_found(authed_client):
    resp = await authed_client.get("/rooms/FAKE99")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_join_room_endpoint(authed_client, client, fake_redis):
    """A second user joins a room created by alice."""
    create_resp = await authed_client.post("/rooms", json={"host_name": "Alice"})
    code = create_resp.json()["room"]["code"]

    # Register and authenticate a second user
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from app.database import get_db, get_redis
    from app.main import app

    TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
    engine2 = create_async_engine(
        TEST_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.database import Base

    async with engine2.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory2 = async_sessionmaker(engine2, expire_on_commit=False)

    async with session_factory2() as db2:

        async def override_db2():
            yield db2

        async def override_redis2():
            return fake_redis

        app.dependency_overrides[get_db] = override_db2
        app.dependency_overrides[get_redis] = override_redis2
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as bob_client:
                reg = await bob_client.post(
                    "/auth/register",
                    json={"username": "bob", "email": "bob@example.com", "password": "password1"},
                )
                assert reg.status_code == 201
                bob_token = reg.json()["token"]
                bob_client.headers["Authorization"] = f"Bearer {bob_token}"

                resp = await bob_client.post(f"/rooms/{code}/join", json={"player_name": "Bob"})
                assert resp.status_code == 200
                data = resp.json()
                assert "room" in data
                # host_id must not leak
                assert "host_id" not in data
                assert "host_id" not in data["room"]
                names = [p["name"] for p in data["room"]["players"]]
                assert "Bob" in names
        finally:
            app.dependency_overrides.clear()

    await engine2.dispose()


async def _authed_user_id(authed_client) -> str:
    login_resp = await authed_client.post(
        "/auth/login", json={"username": "alice", "password": "password1"}
    )
    return login_resp.json()["user_id"]


async def _room_hosted_by_someone_else(fake_redis) -> str:
    from app.rooms.service import RoomService

    room = await RoomService(fake_redis).create_room(host_id="other-host", host_name="Host")
    return room["code"]


@pytest.mark.asyncio
async def test_join_room_rejects_kicked_player(authed_client, fake_redis):
    """The kick ban must hold on the REST path too, otherwise Home lets the
    kicked player back into the roster while the socket refuses them."""
    code = await _room_hosted_by_someone_else(fake_redis)
    user_id = await _authed_user_id(authed_client)
    await fake_redis.set(f"kicked:{code}:{user_id}", "1")

    resp = await authed_client.post(f"/rooms/{code}/join", json={"player_name": "Alice"})
    assert resp.status_code == 403
    assert "exclu" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_join_room_rejects_newcomer_while_game_is_running(authed_client, fake_redis):
    from app.rooms.service import RoomService

    code = await _room_hosted_by_someone_else(fake_redis)
    await RoomService(fake_redis).set_status(code, "playing")

    resp = await authed_client.post(f"/rooms/{code}/join", json={"player_name": "Alice"})
    assert resp.status_code == 409
    assert "partie en cours" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_join_room_lets_a_member_back_in_while_playing(authed_client, fake_redis):
    from app.rooms.service import RoomService

    code = await _room_hosted_by_someone_else(fake_redis)
    first = await authed_client.post(f"/rooms/{code}/join", json={"player_name": "Alice"})
    assert first.status_code == 200
    await RoomService(fake_redis).set_status(code, "playing")

    again = await authed_client.post(f"/rooms/{code}/join", json={"player_name": "Alice"})
    assert again.status_code == 200


@pytest.mark.asyncio
async def test_join_room_not_found_message_is_french(authed_client):
    resp = await authed_client.post("/rooms/FAKE99/join", json={"player_name": "Bob"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Room introuvable ou pleine"


@pytest.mark.asyncio
async def test_join_room_not_found(authed_client):
    resp = await authed_client.post("/rooms/FAKE99/join", json={"player_name": "Bob"})
    assert resp.status_code == 404
