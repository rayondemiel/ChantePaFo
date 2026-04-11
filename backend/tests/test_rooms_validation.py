import pytest


@pytest.mark.asyncio
async def test_create_room_rejects_empty_name(authed_client):
    resp = await authed_client.post("/rooms", json={"host_name": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_room_rejects_oversize_name(authed_client):
    resp = await authed_client.post("/rooms", json={"host_name": "x" * 33})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_room_rejects_control_chars(authed_client):
    resp = await authed_client.post("/rooms", json={"host_name": "bad\x00name"})
    assert resp.status_code == 422
