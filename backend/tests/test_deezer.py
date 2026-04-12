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


async def test_get_tracks_for_genre(deezer):
    mock_playlists = [{"id": 42, "title": "Rock Essentials", "nb_tracks": 50}]
    mock_tracks = [
        {
            "id": 1,
            "title": "Test Rock",
            "artist": "A",
            "album": "B",
            "cover_url": "",
            "preview_url": "https://preview.test",
            "duration": 180,
            "release_date": "2020-01-01",
            "rank": 500000,
        }
    ]
    with (
        patch.object(
            deezer, "search_playlists", new_callable=AsyncMock, return_value=mock_playlists
        ),
        patch.object(
            deezer, "get_playlist_tracks", new_callable=AsyncMock, return_value=mock_tracks
        ),
    ):
        tracks = await deezer.get_tracks_for_genre("rock")
        assert len(tracks) >= 1
        assert tracks[0]["title"] == "Test Rock"


async def test_get_tracks_custom_theme(deezer):
    mock_playlists = [{"id": 99, "title": "Films 90s Soundtrack", "nb_tracks": 30}]
    mock_tracks = [
        {
            "id": 7,
            "title": "My Heart Will Go On",
            "artist": "Céline Dion",
            "album": "Titanic OST",
            "cover_url": "",
            "preview_url": "https://preview.test",
            "duration": 280,
            "release_date": "1997-01-01",
            "rank": 900000,
        }
    ]
    with (
        patch.object(
            deezer, "search_playlists", new_callable=AsyncMock, return_value=mock_playlists
        ) as mock_sp,
        patch.object(
            deezer, "get_playlist_tracks", new_callable=AsyncMock, return_value=mock_tracks
        ),
    ):
        tracks = await deezer.get_tracks_for_genre("custom:films années 90")
        assert len(tracks) >= 1
        assert tracks[0]["title"] == "My Heart Will Go On"
        # Verify the raw query was passed, not a genre config lookup
        mock_sp.assert_called_once_with("films années 90", limit=4)


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
