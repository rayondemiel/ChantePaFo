from typing import Any

from app.game.awards import compute_awards
from app.game.engine import GameMode, registry
from app.game.fuzzy import fuzzy_match
from app.game.scoring import calculate_round_scores

_EMPTY_ANSWER: dict[str, Any] = {
    "text": "",
    "title_match": False,
    "artist_match": False,
    "bonus": False,
    "time_ms": 0,
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
            "extract_duration": settings.get("extract_duration", 20),
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
            return {"phase": PHASE_PLAYING}

        if event_type == "answer" and self.state.get("phase") == PHASE_PLAYING:
            return self._handle_answer(player_id, data)

        return None

    def _handle_answer(self, player_id: str, data: dict[str, Any]) -> dict[str, Any]:
        track = self.tracks[self.state["current_round"]]
        result: dict[str, Any] = fuzzy_match(data["text"], track["title"], track["artist"])
        result["time_ms"] = data.get("time_ms", 0)
        result["text"] = data["text"]
        result["player_id"] = player_id

        prev = self.round_answers.get(player_id)
        result["attempts"] = (prev["attempts"] + 1) if prev else 1

        if prev:
            result["title_match"] = result["title_match"] or prev.get("title_match", False)
            result["artist_match"] = result["artist_match"] or prev.get("artist_match", False)
            result["bonus"] = result["title_match"] and result["artist_match"]
            if prev.get("title_match") and not result.get("title_match"):
                result["time_ms"] = prev["time_ms"]

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
        self.state["round_results"] = {
            "correct_title": track["title"],
            "correct_artist": track["artist"],
            "cover_url": track.get("cover_url", ""),
        }
        self.state["phase"] = PHASE_PLAYING_REVEAL
        return {
            "phase": PHASE_PLAYING_REVEAL,
            "scores": self.state["round_scores"],
            "results": self.state["round_results"],
        }

    def advance_to_pause(self) -> dict[str, Any]:
        """Transition playing_reveal → round_pause. Frontend stops audio here."""
        self.state["phase"] = PHASE_ROUND_PAUSE
        return {"phase": PHASE_ROUND_PAUSE}

    def advance_to_next_round(self) -> dict[str, Any]:
        """Transition round_pause → playing (next round) or finished if last."""
        next_round = self.state["current_round"] + 1
        if next_round >= len(self.tracks):
            self.state["phase"] = PHASE_FINISHED
            return {"phase": PHASE_FINISHED}
        self._load_round(next_round)
        self.state["phase"] = PHASE_PLAYING
        return {"phase": PHASE_PLAYING}

    def _end_round_scoring(self) -> None:
        self._fill_missing_answers()
        scores = calculate_round_scores(list(self.round_answers.values()))
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
