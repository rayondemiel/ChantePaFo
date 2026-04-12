from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.music.deezer import DeezerClient


@pytest.fixture
def deezer():
    return DeezerClient()


async def test_search_tracks(deezer):
    mock_response = {
        "data": [
            {
                "id": 3135556,
                "title": "Harder, Better, Faster, Stronger",
                "artist": {"name": "Daft Punk"},
                "album": {"title": "Discovery", "cover_medium": "https://example.com/cover.jpg"},
                "preview": "https://cdns-preview.deezer.com/stream/abc123",
                "duration": 224,
                "release_date": "2001-03-12",
            }
        ]
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        tracks = await deezer.search("daft punk harder better")
        assert len(tracks) == 1
        assert tracks[0]["title"] == "Harder, Better, Faster, Stronger"
        assert tracks[0]["artist"] == "Daft Punk"
        assert tracks[0]["preview_url"].startswith("https://")


async def test_search_by_genre(deezer):
    mock_response = {
        "data": [
            {
                "id": 1,
                "title": "Test",
                "artist": {"name": "A"},
                "album": {"title": "B", "cover_medium": ""},
                "preview": "https://preview.test",
                "duration": 180,
                "release_date": "2020-01-01",
            }
        ]
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        tracks = await deezer.search_by_genre("rock")
        assert len(tracks) >= 1


async def test_get_track(deezer):
    mock_response = {
        "id": 3135556,
        "title": "Harder, Better, Faster, Stronger",
        "artist": {"name": "Daft Punk"},
        "album": {"title": "Discovery", "cover_medium": ""},
        "preview": "https://cdns-preview.deezer.com/stream/abc123",
        "duration": 224,
        "release_date": "2001-03-12",
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        track = await deezer.get_track(3135556)
        assert track["title"] == "Harder, Better, Faster, Stronger"
