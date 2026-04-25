import time
from typing import Any

from app.game.awards import compute_awards
from app.game.engine import GameMode, registry
from app.game.fuzzy import fuzzy_match
from app.game.scoring import calculate_round_scores


def _now_ms() -> int:
    """Monotonic clock in ms. Module-level so tests can patch it."""
    return int(time.monotonic() * 1000)

_EMPTY_ANSWER: dict[str, Any] = {
    "text": "",
    "title_match": False,
    "artist_match": False,
    "bonus": False,
    "time_ms": 0,
    "title_time_ms": 0,
    "artist_time_ms": 0,
    "bonus_time_ms": 0,
    "attempts": 0,
    "distance": 999,
}

# Phase constants for the auto-advancing blindtest timeline:
#   countdown      → only at game start, exited via "countdown_done" event
#   playing        → music plays, players answer (no cover/title/artist exposed)
#   playing_reveal → music continues, cover/title/artist revealed, scores locked
#   round_pause    → silent transition between rounds
#   finished       → game over
PHASE_COUNTDOWN = "countdown"
PHASE_PLAYING = "playing"
PHASE_PLAYING_REVEAL = "playing_reveal"
PHASE_ROUND_PAUSE = "round_pause"
PHASE_FINISHED = "finished"


class BlindtestMode(GameMode):
    name = "blindtest"

    def __init__(self) -> None:
        self.state: dict[str, Any] = {}
        self.players: list[dict[str, Any]] = []
        self.tracks: list[dict[str, Any]] = []
        self.round_answers: dict[str, dict[str, Any]] = {}
        self.history: dict[str, Any] = {"rounds": [], "total_scores": {}, "players": {}}

    async def start(
        self,
        players: list[dict[str, Any]],
        settings: dict[str, Any],
        track_provider: Any,
    ) -> None:
        self.players = players
        num_rounds = settings.get("num_rounds", 10)

        self.tracks = await track_provider.get_random_tracks(
            genre_config=settings.get("genres", {"all": 2}),
            count=num_rounds,
        )

        for p in players:
            self.history["players"][p["id"]] = {"name": p["name"]}
            self.history["total_scores"][p["id"]] = 0

        self.state = {
            "phase": PHASE_COUNTDOWN,
            "current_round": 0,
            "total_rounds": len(self.tracks),
            "extract_duration": settings.get("extract_duration", 30),
            "track": None,
            "round_scores": {},
            "round_results": {},
        }
        self._load_round(0)
        # _load_round leaves phase untouched on success; the game starts in
        # countdown explicitly (only once, at the very beginning of the game).
        self.state["phase"] = PHASE_COUNTDOWN

    def _load_round(self, round_idx: int) -> None:
        if round_idx >= len(self.tracks):
            self.state["phase"] = PHASE_FINISHED
            return
        track = self.tracks[round_idx]
        self.state["current_round"] = round_idx
        # Only expose preview_url and genre during play. cover_url / title /
        # artist are added at the reveal transition, otherwise visual leaks
        # would let players see the answer.
        self.state["track"] = {
            "preview_url": track["preview_url"],
            "genre": track.get("genre", ""),
        }
        self.state["round_scores"] = {}
        self.state["round_results"] = {}
        self.round_answers = {}

    async def handle_event(
        self,
        event_type: str,
        player_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        if event_type == "countdown_done":
            self.state["phase"] = PHASE_PLAYING
            self.state["round_started_at_ms"] = _now_ms()
            return {"phase": PHASE_PLAYING}

        if event_type == "answer" and self.state.get("phase") == PHASE_PLAYING:
            return self._handle_answer(player_id, data)

        return None

    def _compute_answer_time_ms(self, data: dict[str, Any]) -> int:
        """Server-authoritative timestamp for an answer, clamped to the round window.

        The client supplies a `time_ms` hint but it is NEVER trusted: a tampered
        client could send 0 to score max points each round. When the round has
        a server-side start (production path), we always recompute from the
        monotonic clock. The client hint is only used in test environments
        that don't simulate the timeline.
        """
        round_started_ms = self.state.get("round_started_at_ms")
        if round_started_ms is None:
            return int(data.get("time_ms", 0))
        elapsed_ms = max(0, _now_ms() - int(round_started_ms))
        extract_duration_ms = int(self.state.get("extract_duration", 30)) * 1000
        return min(elapsed_ms, extract_duration_ms)

    def _handle_answer(self, player_id: str, data: dict[str, Any]) -> dict[str, Any]:
        track = self.tracks[self.state["current_round"]]
        result: dict[str, Any] = fuzzy_match(data["text"], track["title"], track["artist"])
        answer_time_ms = self._compute_answer_time_ms(data)
        result["time_ms"] = answer_time_ms
        result["text"] = data["text"]
        result["player_id"] = player_id

        prev = self.round_answers.get(player_id)
        result["attempts"] = (prev["attempts"] + 1) if prev else 1

        # Title timestamp = first answer that matched the title.
        prev_title_match = bool(prev and prev.get("title_match"))
        if prev_title_match:
            result["title_match"] = True
            result["title_time_ms"] = prev.get("title_time_ms", prev.get("time_ms", 0))
        elif result.get("title_match"):
            result["title_time_ms"] = answer_time_ms
        else:
            result["title_time_ms"] = 0

        # Artist: accumulate matched components across guesses so that composite
        # artists (e.g. "David Guetta feat. Florida") can be typed in pieces.
        prev_indices = set(prev.get("matched_artist_indices", [])) if prev else set()
        new_indices = set(result.get("matched_artist_indices", []))
        all_indices = prev_indices | new_indices
        total = result.get("total_artist_components", 1)
        result["matched_artist_indices"] = sorted(all_indices)
        result["artist_match"] = len(all_indices) >= total

        # Artist timestamp = the answer that completed the artist (all components).
        prev_artist_match = bool(prev and prev.get("artist_match"))
        if prev_artist_match:
            result["artist_time_ms"] = prev.get("artist_time_ms", prev.get("time_ms", 0))
        elif result["artist_match"]:
            result["artist_time_ms"] = answer_time_ms
        else:
            result["artist_time_ms"] = 0

        result["bonus"] = result["title_match"] and result["artist_match"]
        # Bonus timestamp = the moment the second half (title or artist) landed.
        if result["bonus"]:
            result["bonus_time_ms"] = max(result["title_time_ms"], result["artist_time_ms"])
        else:
            result["bonus_time_ms"] = 0

        self.round_answers[player_id] = result
        return result

    def advance_to_reveal(self) -> dict[str, Any]:
        """Transition playing → playing_reveal. Locks scores and exposes cover/title/artist."""
        self._end_round_scoring()
        track = self.tracks[self.state["current_round"]]
        # Expose cover_url on the track dict now that the round is over.
        current_track = self.state.get("track") or {}
        current_track["cover_url"] = track.get("cover_url", "")
        self.state["track"] = current_track

        winners = self._compute_top_winners()

        self.state["round_results"] = {
            "correct_title": track["title"],
            "correct_artist": track["artist"],
            "cover_url": track.get("cover_url", ""),
            "winners": winners,
            "all_matches": self._compute_all_matches(),
        }
        self.state["phase"] = PHASE_PLAYING_REVEAL
        return {
            "phase": PHASE_PLAYING_REVEAL,
            "scores": self.state["round_scores"],
            "results": self.state["round_results"],
        }

    def _compute_top_winners(self, limit: int = 3) -> list[dict[str, Any]]:
        player_names: dict[str, str] = {p["id"]: p["name"] for p in self.players}
        bonus_answers = [a for a in self.round_answers.values() if a.get("bonus") is True]
        bonus_answers.sort(key=lambda a: a.get("bonus_time_ms", a.get("time_ms", 0)))
        return [
            {
                "player_id": a["player_id"],
                "name": player_names.get(a["player_id"], a["player_id"]),
                "time_ms": a.get("bonus_time_ms", a.get("time_ms", 0)),
            }
            for a in bonus_answers[:limit]
        ]

    def _compute_all_matches(self) -> list[dict[str, Any]]:
        player_names: dict[str, str] = {p["id"]: p["name"] for p in self.players}
        matches: list[dict[str, Any]] = []
        for a in self.round_answers.values():
            if a.get("title_match") or a.get("artist_match"):
                if a.get("bonus"):
                    match_type = "bonus"
                    time_ms = a.get("bonus_time_ms", a.get("time_ms", 0))
                elif a.get("title_match"):
                    match_type = "title"
                    time_ms = a.get("title_time_ms", a.get("time_ms", 0))
                else:
                    match_type = "artist"
                    time_ms = a.get("artist_time_ms", a.get("time_ms", 0))
                matches.append(
                    {
                        "player_id": a["player_id"],
                        "name": player_names.get(a["player_id"], a["player_id"]),
                        "time_ms": time_ms,
                        "match_type": match_type,
                    }
                )
        matches.sort(key=lambda m: m["time_ms"])
        return matches

    def advance_to_pause(self) -> dict[str, Any]:
        """Transition playing_reveal → round_pause. Frontend stops audio here."""
        self.state["phase"] = PHASE_ROUND_PAUSE
        self.state["is_last_round"] = (self.state["current_round"] + 1) >= len(self.tracks)
        return {"phase": PHASE_ROUND_PAUSE, "is_last_round": self.state["is_last_round"]}

    def advance_to_next_round(self) -> dict[str, Any]:
        """Transition round_pause → playing (next round) or finished if last."""
        next_round = self.state["current_round"] + 1
        if next_round >= len(self.tracks):
            self.state["phase"] = PHASE_FINISHED
            return {"phase": PHASE_FINISHED}
        self._load_round(next_round)
        self.state["phase"] = PHASE_PLAYING
        self.state["round_started_at_ms"] = _now_ms()
        return {"phase": PHASE_PLAYING}

    def _end_round_scoring(self) -> None:
        self._fill_missing_answers()
        extract_duration_ms = int(self.state.get("extract_duration", 30)) * 1000
        scores = calculate_round_scores(
            list(self.round_answers.values()),
            extract_duration_ms=extract_duration_ms,
        )
        self.state["round_scores"] = scores

        self.history["rounds"].append({"answers": dict(self.round_answers), "scores": scores})
        for pid, pts in scores.items():
            self.history["total_scores"][pid] = self.history["total_scores"].get(pid, 0) + pts

    def _fill_missing_answers(self) -> None:
        for p in self.players:
            if p["id"] not in self.round_answers:
                self.round_answers[p["id"]] = {**_EMPTY_ANSWER, "player_id": p["id"]}

    def get_state(self) -> dict[str, Any]:
        return {**self.state, "total_scores": self.history["total_scores"]}

    async def end(self) -> dict[str, Any]:
        awards = compute_awards(self.history, mode="blindtest")
        return {
            "total_scores": self.history["total_scores"],
            "awards": awards,
            "rounds": self.history["rounds"],
            "players": self.history["players"],
        }


registry.register(BlindtestMode)
