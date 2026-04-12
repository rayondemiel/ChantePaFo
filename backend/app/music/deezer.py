import random
import time
from typing import Any

import httpx

from app.config import settings
from app.metrics import DEEZER_API_CALL_DURATION_SECONDS, DEEZER_API_CALLS_TOTAL

GENRE_SEARCH_TERMS: dict[str, str] = {
    # Mainstream
    "pop": "pop",
    "rock": "rock",
    "rap": "rap français",
    "hiphop": "hip hop",
    "rnb": "r&b",
    "electro": "electronic",
    "dance": "dance",
    "house": "house music",
    "techno": "techno",
    "trance": "trance",
    "drum_n_bass": "drum and bass",
    # Origines
    "jazz": "jazz",
    "blues": "blues",
    "soul": "soul",
    "funk": "funk",
    "gospel": "gospel",
    "disco": "disco",
    # Rock sub-genres
    "metal": "metal",
    "punk": "punk rock",
    "grunge": "grunge",
    "indie": "indie rock",
    "alternative": "alternative",
    # World / tropical
    "reggae": "reggae",
    "reggaeton": "reggaeton",
    "latino": "latin music",
    "bossa_nova": "bossa nova",
    "afrobeats": "afrobeats",
    "kpop": "k-pop",
    "jpop": "j-pop",
    "bollywood": "bollywood",
    "raï": "raï",
    "zouk": "zouk",
    "afro_trap": "afro trap",
    # France
    "chanson_francaise": "chanson française",
    "variete_francaise": "variété française",
    "rap_fr": "rap français",
    "pop_fr": "pop française",
    # Décennies
    "annees60": "60s",
    "annees70": "70s",
    "annees80": "80s",
    "annees90": "90s",
    "annees2000": "2000s",
    "annees2010": "2010s",
    # Vibes / moods
    "classique": "classical",
    "opera": "opera",
    "country": "country",
    "folk": "folk",
    "acoustic": "acoustic",
    "lo_fi": "lo-fi",
    "ambient": "ambient",
    "new_wave": "new wave",
    "synthwave": "synthwave",
    "ska": "ska",
    "swing": "swing",
    # Cinéma / cultures
    "bo_films": "soundtrack",
    "bo_series": "tv series soundtrack",
    "bo_jeux_video": "video game soundtrack",
    "anime": "anime",
    "disney": "disney",
    "comedie_musicale": "musical",
    # Catch-all
    "all": "",
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
    }


class DeezerClient:
    def __init__(self) -> None:
        self.base_url = settings.deezer_api_base

    async def search(self, query: str, limit: int = 25) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            start = time.perf_counter()
            resp = await client.get(
                f"{self.base_url}/search",
                params={"q": query, "limit": limit},
            )
            duration = time.perf_counter() - start
            DEEZER_API_CALL_DURATION_SECONDS.labels(endpoint="search").observe(duration)
            DEEZER_API_CALLS_TOTAL.labels(
                endpoint="search",
                status="success" if resp.status_code == 200 else "error",
            ).inc()
            data: list[dict[str, Any]] = resp.json().get("data", [])
            return [_parse_track(t) for t in data if t.get("preview")]

    async def search_by_genre(self, genre: str, limit: int = 50) -> list[dict[str, Any]]:
        search_term = GENRE_SEARCH_TERMS.get(genre, genre)
        if not search_term:
            search_term = "top hits"
        return await self.search(search_term, limit=limit)

    async def get_track(self, track_id: int) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            start = time.perf_counter()
            resp = await client.get(f"{self.base_url}/track/{track_id}")
            duration = time.perf_counter() - start
            DEEZER_API_CALL_DURATION_SECONDS.labels(endpoint="get_track").observe(duration)
            DEEZER_API_CALLS_TOTAL.labels(
                endpoint="get_track",
                status="success" if resp.status_code == 200 else "error",
            ).inc()
            return _parse_track(resp.json())

    async def get_random_tracks(self, genres: list[str], count: int = 10) -> list[dict[str, Any]]:
        all_tracks: list[dict[str, Any]] = []
        for genre in genres:
            tracks = await self.search_by_genre(genre, limit=50)
            all_tracks.extend(tracks)

        seen_ids: set[int] = set()
        unique: list[dict[str, Any]] = []
        for t in all_tracks:
            track_id = int(t["id"])
            if track_id not in seen_ids:
                seen_ids.add(track_id)
                unique.append(t)

        random.shuffle(unique)
        return unique[:count]
