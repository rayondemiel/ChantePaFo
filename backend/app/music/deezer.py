import logging
import random
import time
from typing import Any

import httpx

from app.config import settings
from app.metrics import DEEZER_API_CALL_DURATION_SECONDS, DEEZER_API_CALLS_TOTAL

logger = logging.getLogger(__name__)

_API_TIMEOUT = 10.0  # seconds

# Each genre maps to a playlist search query (primary) and a keyword fallback.
# Playlists are human-curated → genre accuracy is much better than keyword search.
GENRE_CONFIG: dict[str, dict[str, str]] = {
    # Mainstream
    "pop": {"playlist": "pop hits", "search": "pop"},
    "rock": {"playlist": "rock classics", "search": "rock"},
    "rap": {"playlist": "rap français", "search": "rap français"},
    "hiphop": {"playlist": "hip hop essentials", "search": "hip hop"},
    "rnb": {"playlist": "r&b essentials", "search": "r&b"},
    "electro": {"playlist": "electro mix", "search": "electronic"},
    "dance": {"playlist": "dance hits", "search": "dance"},
    "house": {"playlist": "house music essentials", "search": "house music"},
    "techno": {"playlist": "techno essentials", "search": "techno"},
    "trance": {"playlist": "trance essentials", "search": "trance"},
    "drum_n_bass": {"playlist": "drum and bass", "search": "drum and bass"},
    # Origines
    "jazz": {"playlist": "jazz essentials", "search": "jazz"},
    "blues": {"playlist": "blues essentials", "search": "blues"},
    "soul": {"playlist": "soul classics", "search": "soul"},
    "funk": {"playlist": "funk classics", "search": "funk"},
    "gospel": {"playlist": "gospel essentials", "search": "gospel"},
    "disco": {"playlist": "disco essentials", "search": "disco"},
    # Rock sub-genres
    "metal": {"playlist": "metal essentials", "search": "metal"},
    "punk": {"playlist": "punk rock essentials", "search": "punk rock"},
    "grunge": {"playlist": "grunge essentials", "search": "grunge"},
    "indie": {"playlist": "indie rock essentials", "search": "indie rock"},
    "alternative": {"playlist": "alternative essentials", "search": "alternative"},
    # World / tropical
    "reggae": {"playlist": "reggae essentials", "search": "reggae"},
    "reggaeton": {"playlist": "reggaeton hits", "search": "reggaeton"},
    "latino": {"playlist": "latin hits", "search": "latin music"},
    "bossa_nova": {"playlist": "bossa nova", "search": "bossa nova"},
    "afrobeats": {"playlist": "afrobeats hits", "search": "afrobeats"},
    "kpop": {"playlist": "k-pop hits", "search": "k-pop"},
    "jpop": {"playlist": "j-pop hits", "search": "j-pop"},
    "bollywood": {"playlist": "bollywood hits", "search": "bollywood"},
    "rai": {"playlist": "rai algérien", "search": "khaled rai"},
    "zouk": {"playlist": "zouk hits", "search": "zouk"},
    "afro_trap": {"playlist": "afro trap", "search": "afro trap"},
    # France
    "chanson_francaise": {"playlist": "chanson française", "search": "chanson française"},
    "variete_francaise": {"playlist": "variété française", "search": "variété française"},
    "rap_fr": {"playlist": "rap français", "search": "rap français"},
    "pop_fr": {"playlist": "pop française", "search": "pop française"},
    # Décennies
    "annees60": {"playlist": "60s essentials", "search": "60s"},
    "annees70": {"playlist": "70s essentials", "search": "70s"},
    "annees80": {"playlist": "80s essentials", "search": "80s"},
    "annees90": {"playlist": "90s essentials", "search": "90s"},
    "annees2000": {"playlist": "2000s essentials", "search": "2000s"},
    "annees2010": {"playlist": "2010s essentials", "search": "2010s"},
    # Vibes / moods
    "classique": {"playlist": "classical essentials", "search": "classical"},
    "opera": {"playlist": "opera essentials", "search": "opera"},
    "country": {"playlist": "country essentials", "search": "country"},
    "folk": {"playlist": "folk essentials", "search": "folk"},
    "acoustic": {"playlist": "acoustic vibes", "search": "acoustic"},
    "lo_fi": {"playlist": "lo-fi beats", "search": "lo-fi"},
    "ambient": {"playlist": "ambient relaxation", "search": "ambient"},
    "new_wave": {"playlist": "new wave essentials", "search": "new wave"},
    "synthwave": {"playlist": "synthwave", "search": "synthwave"},
    "ska": {"playlist": "ska essentials", "search": "ska"},
    "swing": {"playlist": "swing jazz", "search": "swing"},
    # Cinéma / cultures
    "bo_films": {"playlist": "movie soundtracks", "search": "soundtrack"},
    "bo_series": {"playlist": "tv series soundtrack", "search": "tv series soundtrack"},
    "bo_jeux_video": {"playlist": "video game music", "search": "video game soundtrack"},
    "anime": {"playlist": "anime hits", "search": "anime"},
    "disney": {"playlist": "disney hits", "search": "disney"},
    "comedie_musicale": {"playlist": "musical theatre", "search": "musical"},
    # Catch-all
    "all": {"playlist": "top hits", "search": "top hits"},
}

# Difficulty is cumulative and genre-relative.
# We use PERCENTILES within each genre's track pool. A "hit" in jazz
# (rank ~200k) differs from a "hit" in pop (rank ~900k) — percentiles
# adapt automatically.
#
# keep_top_pct: fraction of tracks to keep (sorted by rank desc).
# max_playlists: how many playlists to pull tracks from (more = deeper catalog).
# use_charts: also include Deezer global top charts.
DIFFICULTY_CONFIG: dict[int, dict[str, Any]] = {
    1: {"keep_top_pct": 0.25, "max_playlists": 1, "use_charts": True, "label": "Facile"},
    2: {"keep_top_pct": 0.50, "max_playlists": 2, "use_charts": True, "label": "Normal"},
    3: {"keep_top_pct": 0.75, "max_playlists": 3, "use_charts": False, "label": "Difficile"},
    4: {"keep_top_pct": 1.00, "max_playlists": 3, "use_charts": False, "label": "Expert"},
}


def _parse_track(data: dict[str, Any]) -> dict[str, Any]:
    artist_info = data.get("artist", {})
    album_info = data.get("album", {})
    return {
        "id": data["id"],
        "title": data["title"],
        "artist": artist_info["name"] if isinstance(artist_info, dict) else "",
        "album": album_info.get("title", "") if isinstance(album_info, dict) else "",
        "cover_url": album_info.get("cover_medium", "") if isinstance(album_info, dict) else "",
        "preview_url": data.get("preview", ""),
        "duration": data.get("duration", 0),
        "release_date": data.get("release_date", ""),
        "rank": data.get("rank", 0),
    }


class DeezerClient:
    def __init__(self) -> None:
        self.base_url = settings.deezer_api_base

    async def _api_get(
        self, path: str, params: dict[str, Any] | None = None, endpoint_label: str = "search"
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=_API_TIMEOUT) as client:
            start = time.perf_counter()
            try:
                resp = await client.get(f"{self.base_url}{path}", params=params)
            except httpx.HTTPError:
                DEEZER_API_CALLS_TOTAL.labels(endpoint=endpoint_label, status="error").inc()
                logger.warning(
                    "deezer api request failed endpoint=%s path=%s", endpoint_label, path
                )
                return {}

            duration = time.perf_counter() - start
            DEEZER_API_CALL_DURATION_SECONDS.labels(endpoint=endpoint_label).observe(duration)

            if resp.status_code != 200:
                DEEZER_API_CALLS_TOTAL.labels(endpoint=endpoint_label, status="error").inc()
                logger.warning(
                    "deezer api non-200 endpoint=%s status=%d", endpoint_label, resp.status_code
                )
                return {}

            DEEZER_API_CALLS_TOTAL.labels(endpoint=endpoint_label, status="success").inc()

            try:
                result: dict[str, Any] = resp.json()
            except ValueError:
                logger.warning("deezer api invalid json endpoint=%s", endpoint_label)
                return {}

            # Deezer error responses have an "error" key
            if "error" in result:
                logger.warning(
                    "deezer api error endpoint=%s error=%s", endpoint_label, result["error"]
                )
                return {}

            return result

    async def search(self, query: str, limit: int = 25) -> list[dict[str, Any]]:
        data = await self._api_get(
            "/search",
            params={"q": query, "limit": limit},
            endpoint_label="search",
        )
        return [_parse_track(t) for t in data.get("data", []) if t.get("preview")]

    async def get_track(self, track_id: int) -> dict[str, Any]:
        data = await self._api_get(f"/track/{track_id}", endpoint_label="get_track")
        return _parse_track(data)

    async def get_chart_tracks(self, limit: int = 100) -> list[dict[str, Any]]:
        data = await self._api_get(
            "/chart/0/tracks",
            params={"limit": limit},
            endpoint_label="chart",
        )
        return [_parse_track(t) for t in data.get("data", []) if t.get("preview")]

    async def search_playlists(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        data = await self._api_get(
            "/search/playlist",
            params={"q": query, "limit": limit},
            endpoint_label="search_playlist",
        )
        result: list[dict[str, Any]] = data.get("data", [])
        return result

    async def get_playlist_tracks(self, playlist_id: int, limit: int = 100) -> list[dict[str, Any]]:
        data = await self._api_get(
            f"/playlist/{playlist_id}/tracks",
            params={"limit": limit},
            endpoint_label="playlist_tracks",
        )
        return [_parse_track(t) for t in data.get("data", []) if t.get("preview")]

    async def get_tracks_for_genre(
        self, genre: str, max_playlists: int = 2
    ) -> list[dict[str, Any]]:
        """Fetch tracks for a genre or custom theme.

        Supports two modes:
        - Predefined genre key (e.g. "rock", "jazz") → uses GENRE_CONFIG
          playlist + keyword fallback.
        - Custom theme prefixed with "custom:" (e.g. "custom:films années 90")
          → searches playlists and tracks with the raw query. Lets the host
          define any theme they want.
        """
        if genre.startswith("custom:"):
            query = genre[len("custom:") :].strip()
            return await self._fetch_by_query(query, max_playlists)

        config = GENRE_CONFIG.get(genre, {"playlist": genre, "search": genre})
        return await self._fetch_by_query(
            config["playlist"], max_playlists, fallback_search=config["search"]
        )

    async def _fetch_by_query(
        self, query: str, max_playlists: int = 2, fallback_search: str | None = None
    ) -> list[dict[str, Any]]:
        """Search playlists for a query, pull their tracks, fallback to keyword search."""
        playlists = await self.search_playlists(query, limit=max_playlists + 2)

        tracks: list[dict[str, Any]] = []
        for pl in playlists[:max_playlists]:
            pl_tracks = await self.get_playlist_tracks(pl["id"], limit=100)
            tracks.extend(pl_tracks)

        # Fallback: if playlists returned few tracks, supplement with search
        if len(tracks) < 10:
            search_q = fallback_search or query
            search_tracks = await self.search(search_q, limit=50)
            tracks.extend(search_tracks)

        return tracks

    async def get_random_tracks(
        self, genre_config: dict[str, int], count: int = 10
    ) -> list[dict[str, Any]]:
        """Fetch tracks for multiple genres, each with its own difficulty level.

        Difficulty is cumulative and genre-relative: higher levels include
        everything from lower levels plus progressively more niche tracks.
        The pool grows, it never shrinks.

        Args:
            genre_config: mapping of genre key → difficulty (1-4).
                          Example: {"rock": 4, "pop": 1, "jazz": 2}
            count: total number of tracks to return.
        """
        all_tracks: list[dict[str, Any]] = []
        needs_charts = False

        for genre, difficulty in genre_config.items():
            diff = DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG[2])
            keep_top_pct: float = diff["keep_top_pct"]
            max_playlists: int = diff["max_playlists"]

            if diff["use_charts"]:
                needs_charts = True

            tracks = await self.get_tracks_for_genre(genre, max_playlists=max_playlists)

            # Sort by rank descending (most popular first) and keep top X%.
            # This is genre-relative: a "hit" in jazz differs from a "hit" in pop.
            tracks.sort(key=lambda t: t.get("rank", 0), reverse=True)
            keep_count = max(1, int(len(tracks) * keep_top_pct))
            filtered = tracks[:keep_count]

            all_tracks.extend(filtered)

        if needs_charts:
            chart_tracks = await self.get_chart_tracks(limit=100)
            all_tracks.extend(chart_tracks)

        # Deduplicate by track id
        seen_ids: set[int] = set()
        unique: list[dict[str, Any]] = []
        for t in all_tracks:
            track_id = int(t["id"])
            if track_id not in seen_ids:
                seen_ids.add(track_id)
                unique.append(t)

        random.shuffle(unique)  # nosec B311 — shuffling playlist, not security
        return unique[:count]
