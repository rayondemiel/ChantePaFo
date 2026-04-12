from typing import Any

from app.game.awards import compute_awards
from app.game.engine import GameMode, registry
from app.game.fuzzy import fuzzy_match

PROGRESSIVE_TABLE: list[dict[str, Any]] = [
    {"listen_duration": 30, "constraint": "free", "delay": 0},
    {"listen_duration": 20, "constraint": "hum", "delay": 0},
    {"listen_duration": 20, "constraint": "onomatopoeia", "delay": 15},
    {"listen_duration": 10, "constraint": "voice_imposed", "delay": 15},
    {"listen_duration": 10, "constraint": "whisper", "delay": 30},
]


class KaraokeMystereMode(GameMode):
    name = "karaoke_mystere"

    def __init__(self) -> None:
        self.state: dict[str, Any] = {}
        self.players: list[dict[str, Any]] = []
        self.tracks: list[dict[str, Any]] = []
        # round_idx -> list of {player_id, audio_url}
        self.recordings: dict[int, list[dict[str, Any]]] = {}
        # round_idx -> {singer_player_id -> list of guess dicts}
        self.guesses: dict[int, dict[str, list[dict[str, Any]]]] = {}
        self.history: dict[str, Any] = {
            "rounds": [],
            "total_scores": {},
            "players": {},
        }

    async def start(
        self,
        players: list[dict[str, Any]],
        settings: dict[str, Any],
        track_provider: Any,
    ) -> None:
        self.players = players
        variant: str = settings.get("karaoke_variant", "classic")
        num_rounds: int = settings.get("num_rounds", 3)
        genres: dict[str, int] = settings.get("genres", {"all": 1})

        self.tracks = await track_provider.get_random_tracks(genres, num_rounds)

        for p in self.players:
            self.history["players"][p["id"]] = {"name": p["name"]}
            self.history["total_scores"][p["id"]] = 0

        round_config = self._get_round_config(0, variant)
        self.state = {
            "phase": "listening",
            "current_round": 0,
            "total_rounds": len(self.tracks),
            "variant": variant,
            "current_recording_idx": 0,
            **round_config,
            "track": {
                "preview_url": self.tracks[0]["preview_url"],
                "genre": self.tracks[0].get("genre", ""),
            },
        }
        self.recordings = {}
        self.guesses = {}

    def _get_round_config(self, round_idx: int, variant: str) -> dict[str, Any]:
        if variant == "progressive" and round_idx < len(PROGRESSIVE_TABLE):
            cfg = PROGRESSIVE_TABLE[round_idx]
            return {
                "listen_duration": cfg["listen_duration"],
                "constraint": cfg["constraint"],
                "delay_before_recording": cfg["delay"],
            }
        return {"listen_duration": 30, "constraint": "free", "delay_before_recording": 0}

    async def handle_event(
        self,
        event_type: str,
        player_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        if event_type == "listening_done":
            return self._on_listening_done()
        if event_type == "recording_submitted" and self.state["phase"] == "recording":
            return self._on_recording_submitted(player_id, data)
        if event_type == "guess" and self.state["phase"] == "guessing":
            return self._on_guess(player_id, data)
        if event_type == "next_recording":
            return self._on_next_recording()
        if event_type == "next_round":
            return self._on_next_round()
        return None

    def _on_listening_done(self) -> dict[str, Any]:
        self.state["phase"] = "recording"
        self.recordings.setdefault(self.state["current_round"], [])
        return {"phase": "recording"}

    def _on_recording_submitted(self, player_id: str, data: dict[str, Any]) -> dict[str, Any]:
        round_idx = self.state["current_round"]
        self.recordings.setdefault(round_idx, [])
        self.recordings[round_idx].append({"player_id": player_id, "audio_url": data["audio_url"]})
        all_recorded = len(self.recordings[round_idx]) >= len(self.players)
        if all_recorded:
            self.state["phase"] = "guessing"
            self.state["current_recording_idx"] = 0
            self.guesses[round_idx] = {}
        return {"status": "recorded", "all_done": all_recorded}

    def _on_guess(self, player_id: str, data: dict[str, Any]) -> dict[str, Any]:
        round_idx = self.state["current_round"]
        rec_idx = self.state["current_recording_idx"]
        recordings = self.recordings.get(round_idx, [])

        if rec_idx < len(recordings) and recordings[rec_idx]["player_id"] == player_id:
            return {"error": "cannot_guess_own_recording"}

        track = self.tracks[round_idx]
        result: dict[str, Any] = fuzzy_match(data["text"], track["title"], track["artist"])
        result.update(
            {"time_ms": data.get("time_ms", 0), "text": data["text"], "player_id": player_id}
        )

        if rec_idx < len(recordings):
            singer_id = recordings[rec_idx]["player_id"]
            self.guesses.setdefault(round_idx, {}).setdefault(singer_id, []).append(result)

        return result

    def _on_next_recording(self) -> dict[str, Any]:
        round_idx = self.state["current_round"]
        self.state["current_recording_idx"] += 1
        if self.state["current_recording_idx"] >= len(self.recordings.get(round_idx, [])):
            self._score_round(round_idx)
            self.state["phase"] = "reveal"
        return {"phase": self.state["phase"], "recording_idx": self.state["current_recording_idx"]}

    def _on_next_round(self) -> dict[str, Any]:
        next_round = self.state["current_round"] + 1
        if next_round >= len(self.tracks):
            self.state["phase"] = "finished"
            return {"phase": "finished"}
        round_config = self._get_round_config(next_round, self.state["variant"])
        self.state.update(
            {
                "current_round": next_round,
                "phase": "listening",
                "current_recording_idx": 0,
                **round_config,
                "track": {
                    "preview_url": self.tracks[next_round]["preview_url"],
                    "genre": self.tracks[next_round].get("genre", ""),
                },
            }
        )
        return {"phase": "listening"}

    def _score_round(self, round_idx: int) -> None:
        round_data: dict[str, Any] = {"answers": {}, "scores": {}}
        for singer_id, guesses in self.guesses.get(round_idx, {}).items():
            correct_guesses = [g for g in guesses if g["title_match"]]
            singer_bonus = len(correct_guesses) * 200
            self.history["total_scores"][singer_id] = (
                self.history["total_scores"].get(singer_id, 0) + singer_bonus
            )

            for g in guesses:
                guesser_id: str = g["player_id"]
                pts = 500 if g["title_match"] else 0
                self.history["total_scores"][guesser_id] = (
                    self.history["total_scores"].get(guesser_id, 0) + pts
                )
                # Keep first answer text; accumulate scores across multiple singers
                if guesser_id not in round_data["answers"]:
                    round_data["answers"][guesser_id] = {
                        "text": g["text"],
                        "title_match": g["title_match"],
                        "artist_match": g.get("artist_match", False),
                        "time_ms": g["time_ms"],
                        "attempts": 1,
                        "distance": g.get("distance", 0),
                    }
                round_data["scores"][guesser_id] = round_data["scores"].get(guesser_id, 0) + pts

        self.history["rounds"].append(round_data)

    def get_state(self) -> dict[str, Any]:
        return {**self.state, "total_scores": self.history["total_scores"]}

    async def end(self) -> dict[str, Any]:
        awards = compute_awards(self.history, mode="karaoke")
        return {
            "total_scores": self.history["total_scores"],
            "awards": awards,
            "rounds": self.history["rounds"],
            "players": self.history["players"],
            "recordings": self.recordings,
        }


registry.register(KaraokeMystereMode)
