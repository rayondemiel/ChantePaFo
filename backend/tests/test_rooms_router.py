import pytest


@pytest.mark.asyncio
async def test_create_room_endpoint(client):
    resp = await client.post("/rooms", json={"host_name": "Alice"})
    assert resp.status_code == 201
    data = resp.json()
    assert "room" in data
    assert "player_id" in data
    assert data["room"]["host_id"] == data["player_id"]
    assert len(data["room"]["code"]) > 0


@pytest.mark.asyncio
async def test_get_room_endpoint(client):
    create_resp = await client.post("/rooms", json={"host_name": "Alice"})
    code = create_resp.json()["room"]["code"]

    resp = await client.get(f"/rooms/{code}")
    assert resp.status_code == 200
    assert resp.json()["code"] == code


@pytest.mark.asyncio
async def test_get_room_not_found(client):
    resp = await client.get("/rooms/FAKE99")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_join_room_endpoint(client):
    create_resp = await client.post("/rooms", json={"host_name": "Alice"})
    code = create_resp.json()["room"]["code"]

    resp = await client.post(f"/rooms/{code}/join", json={"player_name": "Bob"})
    assert resp.status_code == 200
    data = resp.json()
    assert "room" in data
    assert "player_id" in data
    names = [p["name"] for p in data["room"]["players"]]
    assert "Bob" in names


@pytest.mark.asyncio
async def test_join_room_not_found(client):
    resp = await client.post("/rooms/FAKE99/join", json={"player_name": "Bob"})
    assert resp.status_code == 404
