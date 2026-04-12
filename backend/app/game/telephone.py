from typing import Any

from app.game.awards import compute_awards
from app.game.engine import GameMode, registry
from app.game.fuzzy import fuzzy_match


class TelephoneArabeMode(GameMode):
    name = "telephone_arabe"

    def __init__(self) -> None:
        self.state: dict[str, Any] = {}
        self.players: list[dict[str, Any]] = []
        self.chains: list[dict[str, Any]] = []
        # step_idx -> set of player_ids who submitted
        self.step_submissions: dict[int, set[str]] = {}
        self.rotation: list[dict[str, int]] = []
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
        n = len(self.players)
        genres: dict[str, int] = settings.get("genres", {"all": 1})

        tracks: list[dict[str, Any]] = await track_provider.get_random_tracks(genres, n)

        for p in self.players:
            self.history["players"][p["id"]] = {"name": p["name"]}
            self.history["total_scores"][p["id"]] = 0

        # Guard against empty tracks list — game cannot function without tracks
        if not tracks:
            self.state = {
                "phase": "finished",
                "current_step": 0,
                "total_steps": 0,
                "chains": [],
                "error": "no_tracks_available",
            }
            return

        # Each player starts a chain with a different track
        self.chains = []
        for i, p in enumerate(self.players):
            self.chains.append(
                {
                    "chain_id": i,
                    "starter_id": p["id"],
                    "original_track": tracks[i % len(tracks)],
                    "steps": [],
                }
            )

        # Rotation matrix: at step s, player[pi] works on chain (pi + s) % n
        self.rotation = []
        for step in range(n):
            assignments: dict[str, int] = {}
            for pi in range(n):
                chain_idx = (pi + step) % n
                assignments[self.players[pi]["id"]] = chain_idx
            self.rotation.append(assignments)

        self.state = {
            "phase": "singing",  # alternates: singing -> writing -> singing -> ...
            "current_step": 0,
            "total_steps": n,
            "chains": [
                {"chain_id": c["chain_id"], "starter": c["starter_id"]} for c in self.chains
            ],
        }
        self.step_submissions = {}

    def _get_player_assignment(self, player_id: str) -> int:
        step: int = int(self.state["current_step"])
        return self.rotation[step].get(player_id, 0)

    def _get_player_input(self, player_id: str) -> dict[str, Any] | None:
        chain_idx = self._get_player_assignment(player_id)
        chain = self.chains[chain_idx]
        step = self.state["current_step"]

        if step == 0:
            return {
                "type": "original",
                "preview_url": chain["original_track"]["preview_url"],
            }

        prev_step = chain["steps"][-1] if chain["steps"] else None
        if prev_step:
            return dict(prev_step)
        return None

    async def handle_event(
        self,
        event_type: str,
        player_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        if event_type == "get_input":
            return self._get_player_input(player_id)

        if event_type == "submit_step":
            step_idx: int = self.state["current_step"]
            chain_idx = self._get_player_assignment(player_id)
            chain = self.chains[chain_idx]
            is_singing = self.state["phase"] == "singing"

            step_data: dict[str, Any] = {
                "player_id": player_id,
                "player_name": self.history["players"].get(player_id, {}).get("name", player_id),
                "step_idx": step_idx,
                "type": "sing" if is_singing else "write",
            }
            if is_singing:
                step_data["audio_url"] = data.get("audio_url", "")
            else:
                step_data["text"] = data.get("text", "")

            chain["steps"].append(step_data)

            self.step_submissions.setdefault(step_idx, set())
            self.step_submissions[step_idx].add(player_id)

            all_done = len(self.step_submissions[step_idx]) >= len(self.players)
            if all_done:
                self._advance_step()

            return {"status": "submitted", "all_done": all_done}

        if event_type == "vote_chain":
            chain_id: int = data.get("chain_id", -1)
            vote_type: str = data.get("vote_type", "funniest")
            if 0 <= chain_id < len(self.chains):
                self.chains[chain_id].setdefault("votes", {})
                self.chains[chain_id]["votes"].setdefault(vote_type, 0)
                self.chains[chain_id]["votes"][vote_type] += 1
            return {"status": "voted"}

        return None

    def _advance_step(self) -> None:
        next_step = self.state["current_step"] + 1
        if next_step >= self.state["total_steps"]:
            self._compute_scores()
            self.state["phase"] = "reveal"
            return

        self.state["current_step"] = next_step
        is_even_step = next_step % 2 == 0
        self.state["phase"] = "singing" if is_even_step else "writing"

    def _compute_scores(self) -> None:
        for chain in self.chains:
            round_data = self._score_chain(chain)
            self.history["rounds"].append(round_data)

    def _score_chain(self, chain: dict[str, Any]) -> dict[str, Any]:
        title = chain["original_track"]["title"]
        artist = chain["original_track"]["artist"]
        round_data: dict[str, Any] = {"answers": {}, "scores": {}}

        for i, step in enumerate(chain["steps"]):
            pid = step["player_id"]
            if step["type"] == "write":
                self._score_writer(pid, step, title, artist, round_data)
            elif step["type"] == "sing":
                self._score_singer(pid, i, chain["steps"], title, artist, round_data)

        return round_data

    def _score_writer(
        self, pid: str, step: dict[str, Any], title: str, artist: str, round_data: dict[str, Any]
    ) -> None:
        result = fuzzy_match(step.get("text", ""), title, artist)
        pts = 500 if result["title_match"] else 0
        self.history["total_scores"][pid] = self.history["total_scores"].get(pid, 0) + pts
        round_data["answers"][pid] = {
            "text": step.get("text", ""),
            "title_match": result["title_match"],
            "artist_match": result.get("artist_match", False),
            "time_ms": 0,
            "attempts": 1,
            "distance": result.get("distance", 0),
        }
        round_data["scores"][pid] = round_data["scores"].get(pid, 0) + pts

    def _score_singer(
        self,
        pid: str,
        step_idx: int,
        steps: list[dict[str, Any]],
        title: str,
        artist: str,
        round_data: dict[str, Any],
    ) -> None:
        if step_idx + 1 >= len(steps):
            return
        next_step = steps[step_idx + 1]
        if next_step["type"] != "write":
            return
        result = fuzzy_match(next_step.get("text", ""), title, artist)
        if result["title_match"]:
            self.history["total_scores"][pid] = self.history["total_scores"].get(pid, 0) + 300
            round_data["scores"][pid] = round_data["scores"].get(pid, 0) + 300

    def get_state(self) -> dict[str, Any]:
        return {
            **self.state,
            "total_scores": self.history["total_scores"],
        }

    async def end(self) -> dict[str, Any]:
        awards = compute_awards(self.history, mode="telephone")
        return {
            "total_scores": self.history["total_scores"],
            "awards": awards,
            "chains": [
                {
                    "chain_id": c["chain_id"],
                    "original_track": c["original_track"],
                    "steps": c["steps"],
                    "votes": c.get("votes", {}),
                }
                for c in self.chains
            ],
            "players": self.history["players"],
        }


registry.register(TelephoneArabeMode)
