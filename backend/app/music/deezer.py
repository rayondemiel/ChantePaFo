import logging
import random
import time
from typing import Any

import httpx

from app.config import settings
from app.metrics import DEEZER_API_CALL_DURATION_SECONDS, DEEZER_API_CALLS_TOTAL

logger = logging.getLogger(__name__)

_API_TIMEOUT = 10.0  # seconds

# Each genre lists multiple playlist queries — sampled at random per game so
# the same room never sees the same starting catalog twice in a row.
# `search` is the keyword fallback when playlists return too few tracks.
GENRE_CONFIG: dict[str, dict[str, Any]] = {
    # Mainstream
    "pop": {
        "playlists": [
            "pop hits",
            "pop classics",
            "pop français",
            "pop 2010s",
            "pop 2020s",
            "best of pop",
        ],
        "search": "pop",
    },
    "rock": {
        "playlists": [
            "rock classics",
            "rock hits",
            "rock essentials",
            "rock français",
            "rock 80s",
            "rock 90s",
            "rock 2000s",
        ],
        "search": "rock",
    },
    "rap": {
        "playlists": [
            "rap français",
            "rap us",
            "rap classics",
            "rap 2010",
            "rap 2020",
            "rap fr classics",
        ],
        "search": "rap",
    },
    "hiphop": {
        "playlists": [
            "hip hop essentials",
            "hip hop classics",
            "old school hip hop",
            "hip hop 90s",
            "hip hop 2000s",
            "best of hip hop",
        ],
        "search": "hip hop",
    },
    "rnb": {
        "playlists": [
            "r&b essentials",
            "r&b classics",
            "r&b 2000s",
            "r&b 2010",
            "neo soul",
            "best of r&b",
        ],
        "search": "r&b",
    },
    "electro": {
        "playlists": [
            "electro mix",
            "electro essentials",
            "electro français",
            "electronic hits",
            "edm hits",
            "electro 2020",
        ],
        "search": "electronic",
    },
    "dance": {
        "playlists": ["dance hits", "dance classics", "dance 2010", "dance 90s", "dance party"],
        "search": "dance",
    },
    "house": {
        "playlists": [
            "house music essentials",
            "deep house",
            "tech house",
            "house classics",
            "french house",
        ],
        "search": "house music",
    },
    "techno": {
        "playlists": [
            "techno essentials",
            "techno classics",
            "minimal techno",
            "berlin techno",
            "techno hits",
        ],
        "search": "techno",
    },
    "trance": {
        "playlists": ["trance essentials", "trance classics", "vocal trance", "uplifting trance"],
        "search": "trance",
    },
    "drum_n_bass": {
        "playlists": ["drum and bass", "dnb essentials", "liquid dnb", "drum and bass classics"],
        "search": "drum and bass",
    },
    # Origines
    "jazz": {
        "playlists": [
            "jazz essentials",
            "jazz classics",
            "smooth jazz",
            "bebop",
            "modern jazz",
            "jazz french",
        ],
        "search": "jazz",
    },
    "blues": {
        "playlists": ["blues essentials", "blues classics", "delta blues", "modern blues"],
        "search": "blues",
    },
    "soul": {
        "playlists": [
            "soul classics",
            "neo soul",
            "soul essentials",
            "northern soul",
            "motown classics",
        ],
        "search": "soul",
    },
    "funk": {
        "playlists": ["funk classics", "funk essentials", "p-funk", "modern funk", "french funk"],
        "search": "funk",
    },
    "gospel": {
        "playlists": ["gospel essentials", "gospel classics", "modern gospel"],
        "search": "gospel",
    },
    "disco": {
        "playlists": ["disco essentials", "disco classics", "disco 70s", "italo disco"],
        "search": "disco",
    },
    # Rock sub-genres
    "metal": {
        "playlists": [
            "metal essentials",
            "metal classics",
            "heavy metal",
            "thrash metal",
            "death metal",
            "metal français",
        ],
        "search": "metal",
    },
    "punk": {
        "playlists": [
            "punk rock essentials",
            "punk classics",
            "pop punk",
            "punk 90s",
            "punk français",
        ],
        "search": "punk rock",
    },
    "grunge": {
        "playlists": ["grunge essentials", "grunge classics", "seattle grunge"],
        "search": "grunge",
    },
    "indie": {
        "playlists": [
            "indie rock essentials",
            "indie classics",
            "indie 2010",
            "indie folk",
            "indie pop",
        ],
        "search": "indie rock",
    },
    "alternative": {
        "playlists": [
            "alternative essentials",
            "alternative rock",
            "alt 90s",
            "alt 2000s",
            "alternative français",
        ],
        "search": "alternative",
    },
    # World / tropical
    "reggae": {
        "playlists": ["reggae essentials", "reggae classics", "roots reggae", "dancehall"],
        "search": "reggae",
    },
    "reggaeton": {
        "playlists": ["reggaeton hits", "reggaeton classics", "perreo", "latin urban"],
        "search": "reggaeton",
    },
    "latino": {
        "playlists": ["latin hits", "latin classics", "salsa", "bachata", "latin pop"],
        "search": "latin music",
    },
    "bossa_nova": {
        "playlists": ["bossa nova", "bossa nova classics", "brazilian jazz"],
        "search": "bossa nova",
    },
    "afrobeats": {
        "playlists": ["afrobeats hits", "afrobeats classics", "afro pop", "naija hits"],
        "search": "afrobeats",
    },
    "kpop": {
        "playlists": [
            "k-pop hits",
            "k-pop classics",
            "k-pop 2020",
            "k-pop girl groups",
            "k-pop boy groups",
        ],
        "search": "k-pop",
    },
    "jpop": {
        "playlists": ["j-pop hits", "j-pop classics", "japanese rock", "city pop"],
        "search": "j-pop",
    },
    "bollywood": {
        "playlists": ["bollywood hits", "bollywood classics", "modern bollywood"],
        "search": "bollywood",
    },
    "rai": {
        "playlists": ["rai algérien", "rai classics", "khaled rai", "rai français"],
        "search": "rai",
    },
    "zouk": {
        "playlists": ["zouk hits", "zouk classics", "zouk love"],
        "search": "zouk",
    },
    "afro_trap": {
        "playlists": ["afro trap", "afro trap français", "afro trap classics"],
        "search": "afro trap",
    },
    # France
    "chanson_francaise": {
        "playlists": [
            "chanson française",
            "chanson française classique",
            "nouvelle chanson française",
            "chanson française 80s",
            "chanson française 70s",
        ],
        "search": "chanson française",
    },
    "variete_francaise": {
        "playlists": [
            "variété française",
            "variété 80s",
            "variété 90s",
            "variété 2000",
            "variété française classics",
        ],
        "search": "variété française",
    },
    "rap_fr": {
        "playlists": [
            "rap français",
            "rap fr classics",
            "rap fr 2010",
            "rap fr 2020",
            "rap fr underground",
        ],
        "search": "rap français",
    },
    "pop_fr": {
        "playlists": [
            "pop française",
            "pop fr 2020",
            "nouvelle pop française",
            "pop fr classics",
        ],
        "search": "pop française",
    },
    # Décennies
    "annees60": {
        "playlists": ["60s essentials", "60s rock", "60s pop", "60s classics", "60s soul"],
        "search": "60s",
    },
    "annees70": {
        "playlists": ["70s essentials", "70s rock", "70s disco", "70s pop", "70s funk"],
        "search": "70s",
    },
    "annees80": {
        "playlists": ["80s essentials", "80s rock", "80s pop", "80s synth", "80s new wave"],
        "search": "80s",
    },
    "annees90": {
        "playlists": ["90s essentials", "90s rock", "90s pop", "90s rap", "90s dance"],
        "search": "90s",
    },
    "annees2000": {
        "playlists": ["2000s essentials", "2000s rock", "2000s pop", "2000s rap", "2000s rnb"],
        "search": "2000s",
    },
    "annees2010": {
        "playlists": ["2010s essentials", "2010s pop", "2010s indie", "2010s rap", "2010s edm"],
        "search": "2010s",
    },
    # Vibes / moods
    "classique": {
        "playlists": [
            "classical essentials",
            "classical masterpieces",
            "baroque",
            "romantic classical",
            "modern classical",
        ],
        "search": "classical",
    },
    "opera": {
        "playlists": ["opera essentials", "opera classics", "italian opera"],
        "search": "opera",
    },
    "country": {
        "playlists": ["country essentials", "country classics", "modern country", "outlaw country"],
        "search": "country",
    },
    "folk": {
        "playlists": ["folk essentials", "folk classics", "modern folk", "indie folk"],
        "search": "folk",
    },
    "acoustic": {
        "playlists": ["acoustic vibes", "acoustic covers", "acoustic essentials"],
        "search": "acoustic",
    },
    "lo_fi": {
        "playlists": ["lo-fi beats", "lo-fi hip hop", "chill lo-fi", "study lo-fi"],
        "search": "lo-fi",
    },
    "ambient": {
        "playlists": ["ambient relaxation", "ambient classics", "dark ambient", "drone ambient"],
        "search": "ambient",
    },
    "new_wave": {
        "playlists": ["new wave essentials", "new wave classics", "post punk new wave"],
        "search": "new wave",
    },
    "synthwave": {
        "playlists": ["synthwave", "synthwave classics", "darksynth", "retrowave"],
        "search": "synthwave",
    },
    "ska": {
        "playlists": ["ska essentials", "ska classics", "two tone ska"],
        "search": "ska",
    },
    "swing": {
        "playlists": ["swing jazz", "swing classics", "electro swing"],
        "search": "swing",
    },
    # Cinéma / cultures
    "bo_films": {
        "playlists": [
            "movie soundtracks",
            "epic film scores",
            "oscar winning soundtracks",
            "french movie soundtracks",
        ],
        "search": "soundtrack",
    },
    "bo_series": {
        "playlists": ["tv series soundtrack", "netflix soundtracks", "hbo soundtracks"],
        "search": "tv series soundtrack",
    },
    "bo_jeux_video": {
        "playlists": [
            "video game music",
            "video game soundtracks",
            "rpg soundtracks",
            "indie game music",
        ],
        "search": "video game soundtrack",
    },
    "anime": {
        "playlists": ["anime hits", "anime openings", "anime classics", "anime 2020"],
        "search": "anime",
    },
    "disney": {
        "playlists": ["disney hits", "disney classics", "pixar songs", "disney french"],
        "search": "disney",
    },
    "comedie_musicale": {
        "playlists": ["musical theatre", "broadway hits", "comédie musicale française"],
        "search": "musical",
    },
    # Catch-all
    "all": {
        "playlists": [
            "top hits",
            "global top hits",
            "today's top hits",
            "viral hits",
            "throwback hits",
        ],
        "search": "top hits",
    },
}

# Difficulty maps to:
#   - rank_window (lo, hi): percentile band of popularity to draw from after
#     sorting tracks by Deezer rank descending. (1.0 = most popular,
#     0.0 = least popular). Higher difficulties move the window DOWN so
#     players face genuinely lesser-known tracks rather than just "more variety".
#   - num_queries: how many distinct playlist queries to draw per genre.
#   - playlists_per_query: how many playlists to fetch per query (sampled at
#     random from Deezer's results).
#
# Net effect: harder difficulty ⇒ broader catalog AND lower-popularity slice.
DIFFICULTY_CONFIG: dict[int, dict[str, Any]] = {
    1: {
        "rank_window": (0.75, 1.00),
        "num_queries": 1,
        "playlists_per_query": 1,
        "use_charts": True,
        "label": "Facile",
    },
    2: {
        "rank_window": (0.40, 1.00),
        "num_queries": 2,
        "playlists_per_query": 1,
        "use_charts": True,
        "label": "Normal",
    },
    3: {
        "rank_window": (0.15, 0.70),
        "num_queries": 3,
        "playlists_per_query": 2,
        "use_charts": False,
        "label": "Difficile",
    },
    4: {
        "rank_window": (0.15, 0.55),
        "num_queries": 4,
        "playlists_per_query": 2,
        "use_charts": False,
        "label": "Expert",
    },
}

# Hard popularity floor: tracks with a Deezer rank below this threshold are
# dropped at every difficulty. Even Expert mode should stay within
# "recognizable but not chart-topping" territory — bands known by ten people
# are useless for a party game.
MIN_RANK_THRESHOLD = 100_000


def _parse_track(data: dict[str, Any]) -> dict[str, Any] | None:
    if "id" not in data or "title" not in data:
        return None
    artist_info = data.get("artist", {})
    album_info = data.get("album", {})
    return {
        "id": data["id"],
        "title": data["title"],
        "artist": artist_info.get("name", "") if isinstance(artist_info, dict) else "",
        "album": album_info.get("title", "") if isinstance(album_info, dict) else "",
        "cover_url": album_info.get("cover_medium", "") if isinstance(album_info, dict) else "",
        "preview_url": data.get("preview", ""),
        "duration": data.get("duration", 0),
        "release_date": data.get("release_date", ""),
        "rank": data.get("rank", 0),
    }


def _apply_rank_window(
    tracks: list[dict[str, Any]], window: tuple[float, float]
) -> list[dict[str, Any]]:
    """Slice a track list by popularity-percentile window.

    `tracks` is sorted by rank descending: index 0 = most popular. The window
    (lo, hi) specifies which popularity percentiles to keep, where 1.0 is the
    top of the chart and 0.0 the bottom. We translate this to indices.
    """
    if not tracks:
        return []
    lo_pct, hi_pct = window
    n = len(tracks)
    start = max(0, int(round((1 - hi_pct) * n)))
    end = max(start + 1, int(round((1 - lo_pct) * n)))
    return tracks[start:end]


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
        return [
            p
            for t in data.get("data", [])
            if t.get("preview") and (p := _parse_track(t)) is not None
        ]

    async def get_track(self, track_id: int) -> dict[str, Any] | None:
        data = await self._api_get(f"/track/{track_id}", endpoint_label="get_track")
        return _parse_track(data)

    async def get_chart_tracks(self, limit: int = 100) -> list[dict[str, Any]]:
        data = await self._api_get(
            "/chart/0/tracks",
            params={"limit": limit},
            endpoint_label="chart",
        )
        return [
            p
            for t in data.get("data", [])
            if t.get("preview") and (p := _parse_track(t)) is not None
        ]

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
        return [
            p
            for t in data.get("data", [])
            if t.get("preview") and (p := _parse_track(t)) is not None
        ]

    async def _fetch_one_query(
        self, query: str, playlists_per_query: int, fallback_search: str | None = None
    ) -> list[dict[str, Any]]:
        """Fetch tracks for a single playlist query.

        Searches Deezer for matching playlists, picks `playlists_per_query`
        at random (instead of always the top-ranked ones — this is what made
        repeated games feel identical), then pulls their tracks.
        """
        candidates = await self.search_playlists(query, limit=max(8, playlists_per_query * 3))
        if not candidates:
            search_q = fallback_search or query
            return await self.search(search_q, limit=50)

        sample_size = min(playlists_per_query, len(candidates))
        chosen = random.sample(candidates, sample_size)  # nosec B311

        tracks: list[dict[str, Any]] = []
        for pl in chosen:
            pl_tracks = await self.get_playlist_tracks(pl["id"], limit=100)
            tracks.extend(pl_tracks)

        if len(tracks) < 10:
            search_q = fallback_search or query
            tracks.extend(await self.search(search_q, limit=50))
        return tracks

    async def get_tracks_for_genre(
        self, genre: str, num_queries: int = 1, playlists_per_query: int = 1
    ) -> list[dict[str, Any]]:
        """Fetch tracks for a genre or custom theme using random query sampling."""
        if genre.startswith("custom:"):
            query = genre[len("custom:") :].strip()
            return await self._fetch_one_query(query, playlists_per_query)

        config = GENRE_CONFIG.get(genre)
        if config is None:
            # Unknown genre key — degrade to using the key itself as a query.
            return await self._fetch_one_query(genre, playlists_per_query, fallback_search=genre)

        playlists_pool: list[str] = list(config["playlists"])
        sample_n = min(num_queries, len(playlists_pool))
        chosen_queries = random.sample(playlists_pool, sample_n)  # nosec B311

        all_tracks: list[dict[str, Any]] = []
        for query in chosen_queries:
            tracks = await self._fetch_one_query(
                query, playlists_per_query, fallback_search=config.get("search")
            )
            all_tracks.extend(tracks)
        return all_tracks

    async def get_random_tracks(
        self,
        genre_config: dict[str, int],
        count: int = 10,
        excluded_track_ids: set[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch tracks for multiple genres, each with its own difficulty level.

        Difficulty inverts popularity: low difficulty = top hits, high difficulty
        = lesser-known tracks. The popularity window is genre-relative.

        Args:
            genre_config: mapping of genre key → difficulty (1-4).
            count: total number of tracks to return.
            excluded_track_ids: track ids to filter out (recently played).
        """
        excluded = excluded_track_ids or set()
        all_tracks: list[dict[str, Any]] = []
        chart_diff: dict[str, Any] | None = None

        for genre, difficulty in genre_config.items():
            diff = DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG[2])
            num_queries: int = diff["num_queries"]
            playlists_per_query: int = diff["playlists_per_query"]
            rank_window: tuple[float, float] = diff["rank_window"]

            if diff["use_charts"] and genre == "all":
                chart_diff = diff

            tracks = await self.get_tracks_for_genre(
                genre,
                num_queries=num_queries,
                playlists_per_query=playlists_per_query,
            )

            # Sort by rank desc → most popular first, then take the configured
            # popularity window for this difficulty.
            tracks.sort(key=lambda t: t.get("rank", 0), reverse=True)
            filtered = _apply_rank_window(tracks, rank_window)
            all_tracks.extend(filtered)

        # Charts only make sense as a popularity booster on the global "all"
        # mode — and only when the difficulty actually wants top hits.
        if chart_diff is not None:
            chart_tracks = await self.get_chart_tracks(limit=100)
            chart_tracks.sort(key=lambda t: t.get("rank", 0), reverse=True)
            all_tracks.extend(_apply_rank_window(chart_tracks, chart_diff["rank_window"]))

        # Deduplicate, drop excluded ids, and apply the absolute popularity
        # floor (kills off truly obscure outliers that slipped through the
        # genre playlists).
        seen_ids: set[int] = set()
        unique: list[dict[str, Any]] = []
        for t in all_tracks:
            track_id = int(t["id"])
            if track_id in seen_ids or track_id in excluded:
                continue
            if int(t.get("rank", 0)) < MIN_RANK_THRESHOLD:
                continue
            seen_ids.add(track_id)
            unique.append(t)

        # If exclusion left us short, we still ship what we have (caller
        # handles short rounds). The shuffle ensures variety across games.
        random.shuffle(unique)  # nosec B311
        return unique[:count]


class RoomScopedDeezerClient:
    """Wraps DeezerClient with a per-room played-tracks history in Redis.

    Recently played track ids are stored in a Redis sorted set scored by
    insertion time. Before each game we read the set and exclude those ids
    from the new draw; after the draw we insert the new ids. The set is
    capped at HISTORY_MAX_SIZE entries (oldest evicted) and expires after
    HISTORY_TTL_S of inactivity.

    Failures against Redis degrade silently — the game still starts, with
    the only consequence being a possibility of repeats.
    """

    HISTORY_KEY_TEMPLATE = "played_tracks:{code}"
    # 30-minute window: tracks played in the last half hour are excluded so
    # players don't hear the same song twice in the same session. After
    # 30 min idle, the slate clears and occasional repeats are fine.
    HISTORY_TTL_S = 30 * 60
    HISTORY_MAX_SIZE = 300

    def __init__(self, redis: Any, room_code: str) -> None:
        self._client = DeezerClient()
        self._redis = redis
        self._room_code = room_code

    def _key(self) -> str:
        return self.HISTORY_KEY_TEMPLATE.format(code=self._room_code)

    async def _read_history(self) -> set[int]:
        try:
            members = await self._redis.zrange(self._key(), 0, -1)
        except Exception:
            logger.warning("read history failed room=%s", self._room_code)
            return set()
        result: set[int] = set()
        for m in members:
            try:
                result.add(int(m))
            except (TypeError, ValueError):
                continue
        return result

    async def _write_history(self, track_ids: list[int]) -> None:
        if not track_ids:
            return
        try:
            now = time.time()
            mapping: dict[str, float] = {
                str(tid): now + i / 1000.0 for i, tid in enumerate(track_ids)
            }
            await self._redis.zadd(self._key(), mapping)
            await self._redis.expire(self._key(), self.HISTORY_TTL_S)
            await self._redis.zremrangebyrank(self._key(), 0, -self.HISTORY_MAX_SIZE - 1)
        except Exception:
            logger.warning("write history failed room=%s", self._room_code)

    async def get_random_tracks(
        self, genre_config: dict[str, int], count: int = 10
    ) -> list[dict[str, Any]]:
        excluded = await self._read_history()
        tracks = await self._client.get_random_tracks(
            genre_config, count=count, excluded_track_ids=excluded
        )
        await self._write_history([int(t["id"]) for t in tracks])
        return tracks
