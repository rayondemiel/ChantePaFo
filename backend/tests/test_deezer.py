from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.music.deezer import (
    DIFFICULTY_CONFIG,
    MIN_RANK_THRESHOLD,
    DeezerClient,
    RoomScopedDeezerClient,
    _apply_rank_window,
)


@pytest.fixture
def deezer():
    return DeezerClient()


def _track(track_id: int, rank: int = 500_000) -> dict:
    return {
        "id": track_id,
        "title": f"Track {track_id}",
        "artist": "Artist",
        "album": "Album",
        "cover_url": "",
        "preview_url": "https://preview.test",
        "duration": 200,
        "release_date": "2020-01-01",
        "rank": rank,
    }


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


async def test_get_tracks_for_genre_uses_random_query_sampling(deezer):
    mock_playlists = [{"id": 42, "title": "Rock Essentials", "nb_tracks": 50}]
    mock_tracks = [_track(1)]

    with (
        patch.object(
            deezer, "search_playlists", new_callable=AsyncMock, return_value=mock_playlists
        ) as mock_sp,
        patch.object(
            deezer, "get_playlist_tracks", new_callable=AsyncMock, return_value=mock_tracks
        ),
    ):
        tracks = await deezer.get_tracks_for_genre("rock", num_queries=1, playlists_per_query=1)
        assert len(tracks) >= 1
        # The chosen query must come from the rock playlist pool.
        called_q = mock_sp.call_args.args[0]
        from app.music.deezer import GENRE_CONFIG

        assert called_q in GENRE_CONFIG["rock"]["playlists"]


async def test_get_tracks_custom_theme_uses_raw_query(deezer):
    mock_playlists = [{"id": 99, "title": "Films 90s Soundtrack"}]
    mock_tracks = [_track(7)]
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
        assert mock_sp.call_args.args[0] == "films années 90"


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


async def test_get_random_tracks_does_not_use_charts_for_specific_genres(deezer):
    genre_tracks = [_track(100 + i, rank=800_000) for i in range(5)]
    with (
        patch.object(
            deezer, "get_tracks_for_genre", new_callable=AsyncMock, return_value=genre_tracks
        ),
        patch.object(deezer, "get_chart_tracks", new_callable=AsyncMock) as mock_charts,
    ):
        tracks = await deezer.get_random_tracks({"rock": 1, "annees80": 1}, count=5)
        assert len(tracks) >= 1
        mock_charts.assert_not_called()


async def test_get_random_tracks_uses_charts_when_all_is_selected(deezer):
    genre_tracks = [_track(200, rank=900_000)]
    chart_tracks = [_track(300 + i, rank=950_000) for i in range(3)]
    with (
        patch.object(
            deezer, "get_tracks_for_genre", new_callable=AsyncMock, return_value=genre_tracks
        ),
        patch.object(
            deezer, "get_chart_tracks", new_callable=AsyncMock, return_value=chart_tracks
        ) as mock_charts,
    ):
        await deezer.get_random_tracks({"all": 1}, count=10)
        mock_charts.assert_called_once()


async def test_get_random_tracks_excludes_provided_ids(deezer):
    genre_tracks = [_track(i, rank=900_000 - i) for i in range(20)]
    with patch.object(
        deezer, "get_tracks_for_genre", new_callable=AsyncMock, return_value=genre_tracks
    ):
        excluded = {0, 1, 2, 3, 4}
        tracks = await deezer.get_random_tracks({"pop": 1}, count=20, excluded_track_ids=excluded)
        ids = {t["id"] for t in tracks}
        assert ids.isdisjoint(excluded)


async def test_difficulty_4_picks_lower_popularity_window():
    """Expert (4) should target a low-popularity slice but not the absolute floor."""
    window = DIFFICULTY_CONFIG[4]["rank_window"]
    assert window[1] <= 0.6, "Expert window must exclude top hits"
    assert window[0] > 0.0, "Expert must avoid the very bottom (truly obscure tracks)"


async def test_min_rank_threshold_filters_obscure_tracks(deezer):
    """Tracks below MIN_RANK_THRESHOLD must be dropped at every difficulty."""
    obscure = [_track(i, rank=1_000) for i in range(20)]  # below floor
    popular = [_track(100 + i, rank=600_000) for i in range(20)]
    pool = obscure + popular
    with patch.object(deezer, "get_tracks_for_genre", new_callable=AsyncMock, return_value=pool):
        tracks = await deezer.get_random_tracks({"pop": 4}, count=20)
    assert all(t["rank"] >= MIN_RANK_THRESHOLD for t in tracks)
    assert all(t["id"] >= 100 for t in tracks)


async def test_difficulty_1_picks_top_popularity_window():
    """Facile (1) should target the top 25% (the biggest hits)."""
    window = DIFFICULTY_CONFIG[1]["rank_window"]
    assert window[0] >= 0.75, "Facile window must keep only top hits"


async def test_apply_rank_window_top_slice():
    # Tracks sorted by rank desc (most popular first)
    tracks = [_track(i, rank=1_000_000 - i) for i in range(100)]
    top = _apply_rank_window(tracks, (0.75, 1.0))
    # Top 25% = first 25 tracks
    assert all(t["id"] < 25 for t in top)
    assert len(top) == 25


async def test_apply_rank_window_bottom_slice():
    tracks = [_track(i, rank=1_000_000 - i) for i in range(100)]
    bottom = _apply_rank_window(tracks, (0.0, 0.4))
    # Bottom 40% = last 40 tracks (ids 60..99)
    assert all(t["id"] >= 60 for t in bottom)
    assert len(bottom) == 40


async def test_apply_rank_window_middle_slice():
    tracks = [_track(i, rank=1_000_000 - i) for i in range(100)]
    mid = _apply_rank_window(tracks, (0.25, 0.75))
    assert all(25 <= t["id"] < 75 for t in mid)


async def test_apply_rank_window_handles_empty():
    assert _apply_rank_window([], (0.0, 1.0)) == []


async def test_higher_difficulty_yields_less_popular_tracks(deezer):
    """End-to-end: difficulty 4 must surface tracks with lower rank than difficulty 1."""
    # 100 tracks with ranks from 1_000_000 down to 1.
    pool = [_track(i, rank=1_000_000 - i * 10_000) for i in range(100)]
    with patch.object(deezer, "get_tracks_for_genre", new_callable=AsyncMock, return_value=pool):
        easy = await deezer.get_random_tracks({"pop": 1}, count=10)
        expert = await deezer.get_random_tracks({"pop": 4}, count=10)

    # Expert tracks should have systematically lower ranks than easy tracks.
    assert max(t["rank"] for t in expert) < min(t["rank"] for t in easy) + 50_000


# ---------------------------------------------------------------------------
# RoomScopedDeezerClient
# ---------------------------------------------------------------------------


async def test_room_scoped_client_excludes_history():
    redis_mock = MagicMock()
    redis_mock.zrange = AsyncMock(return_value=["1", "2", "3"])
    redis_mock.zadd = AsyncMock()
    redis_mock.expire = AsyncMock()
    redis_mock.zremrangebyrank = AsyncMock()

    fresh_track = _track(99, rank=800_000)
    with patch.object(
        DeezerClient, "get_random_tracks", new_callable=AsyncMock, return_value=[fresh_track]
    ) as mock_get:
        client = RoomScopedDeezerClient(redis_mock, "ROOM42")
        tracks = await client.get_random_tracks({"pop": 1}, count=1)

    assert tracks == [fresh_track]
    # The exclusion set must include the previously played ids.
    excluded = mock_get.call_args.kwargs["excluded_track_ids"]
    assert excluded == {1, 2, 3}


async def test_room_scoped_client_writes_history_after_draw():
    redis_mock = MagicMock()
    redis_mock.zrange = AsyncMock(return_value=[])
    redis_mock.zadd = AsyncMock()
    redis_mock.expire = AsyncMock()
    redis_mock.zremrangebyrank = AsyncMock()

    new_tracks = [_track(10), _track(20), _track(30)]
    with patch.object(
        DeezerClient, "get_random_tracks", new_callable=AsyncMock, return_value=new_tracks
    ):
        client = RoomScopedDeezerClient(redis_mock, "ROOM42")
        await client.get_random_tracks({"pop": 1}, count=3)

    redis_mock.zadd.assert_awaited_once()
    written = redis_mock.zadd.call_args.args[1]
    assert set(written.keys()) == {"10", "20", "30"}
    redis_mock.expire.assert_awaited_once()


async def test_room_scoped_client_survives_redis_failure():
    redis_mock = MagicMock()
    redis_mock.zrange = AsyncMock(side_effect=Exception("redis down"))
    redis_mock.zadd = AsyncMock(side_effect=Exception("redis down"))
    redis_mock.expire = AsyncMock(side_effect=Exception("redis down"))
    redis_mock.zremrangebyrank = AsyncMock(side_effect=Exception("redis down"))

    fresh = [_track(7)]
    with patch.object(
        DeezerClient, "get_random_tracks", new_callable=AsyncMock, return_value=fresh
    ):
        client = RoomScopedDeezerClient(redis_mock, "ROOM42")
        tracks = await client.get_random_tracks({"pop": 1}, count=1)
    # Game still works even if Redis is down.
    assert tracks == fresh


def test_track_sampling_uses_the_os_csprng():
    import random

    from app.music import deezer

    assert isinstance(deezer._rng, random.SystemRandom)
