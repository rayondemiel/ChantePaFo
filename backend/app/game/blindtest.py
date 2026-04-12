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
            "phase": "countdown",
            "current_round": 0,
            "total_rounds": len(self.tracks),
            "extract_duration": settings.get("extract_duration", 20),
            "track": None,
            "round_scores": {},
            "round_results": {},
        }
        self._load_round(0)

    def _load_round(self, round_idx: int) -> None:
        if round_idx >= len(self.tracks):
            self.state["phase"] = "finished"
            return
        track = self.tracks[round_idx]
        self.state["current_round"] = round_idx
        self.state["track"] = {
            "preview_url": track["preview_url"],
            "cover_url": track.get("cover_url", ""),
            "genre": track.get("genre", ""),
        }
        self.state["phase"] = "countdown"
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
            self.state["phase"] = "playing"
            return {"phase": "playing"}

        if event_type == "answer" and self.state["phase"] == "playing":
            return self._handle_answer(player_id, data)

        if event_type in ("round_timeout", "next_round"):
            return self._handle_end_of_round()

        if event_type == "advance_round":
            return self._handle_advance_round()

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

    def _handle_end_of_round(self) -> dict[str, Any]:
        self._fill_missing_answers()
        scores = calculate_round_scores(list(self.round_answers.values()))
        self.state["round_scores"] = scores

        track = self.tracks[self.state["current_round"]]
        round_results = {
            "correct_title": track["title"],
            "correct_artist": track["artist"],
            "cover_url": track.get("cover_url", ""),
        }
        self.state["round_results"] = round_results

        self.history["rounds"].append({"answers": dict(self.round_answers), "scores": scores})
        for pid, pts in scores.items():
            self.history["total_scores"][pid] = self.history["total_scores"].get(pid, 0) + pts

        next_round = self.state["current_round"] + 1
        if next_round >= len(self.tracks):
            self.state["phase"] = "finished"
        else:
            self.state["phase"] = "round_result"

        return {"phase": self.state["phase"], "scores": scores, "results": round_results}

    def _handle_advance_round(self) -> dict[str, Any]:
        next_round = self.state["current_round"] + 1
        if next_round < len(self.tracks):
            self._load_round(next_round)
        return {"phase": self.state["phase"]}

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
