"""Wall of Shame & Fame — end-of-game award computation.

Each award is a dict with:
  id         : str  — machine identifier
  player_id  : str
  title      : str  — display name
  emoji      : str
  detail     : str  — short human-readable reason
"""

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
from collections.abc import Iterator
from typing import Any


def _player_name(players: dict[str, Any], pid: str) -> str:
    """Safely get a player's display name, even if they disconnected."""
    p = players.get(pid)
    if p and isinstance(p, dict):
        return str(p.get("name", pid))
    return pid


def _iter_known_answers(
    players: dict[str, Any], rounds: list[dict[str, Any]]
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield (player_id, answer) pairs for known players across all rounds."""
    for rnd in rounds:
        for pid, ans in rnd["answers"].items():
            if pid in players:
                yield pid, ans


def _is_correct(ans: dict[str, Any]) -> bool:
    return bool(ans.get("title_match") or ans.get("artist_match"))


def _is_wrong_with_text(ans: dict[str, Any]) -> bool:
    """True if the answer is wrong but has real text (not a sentinel)."""
    if not ans.get("text"):
        return False
    if _is_correct(ans):
        return False
    return int(ans.get("distance", 0)) < 999


def _correct_answers(
    rounds: list[dict[str, Any]], player_id: str
) -> list[tuple[int, dict[str, Any]]]:
    """Return (round_index, answer_dict) pairs where the player got it right."""
    result = []
    for i, rnd in enumerate(rounds):
        ans = rnd["answers"].get(player_id)
        if ans and _is_correct(ans):
            result.append((i, ans))
    return result


def _blank_rounds(rounds: list[dict[str, Any]], player_id: str) -> int:
    """Count rounds where player gave no answer (empty text or zero attempts)."""
    count = 0
    for rnd in rounds:
        ans = rnd["answers"].get(player_id, {})
        if not ans.get("text") or ans.get("attempts", 0) == 0:
            count += 1
    return count


# ---------------------------------------------------------------------------
# Award definitions
# ---------------------------------------------------------------------------

AwardDef = dict[str, Any]


def _award_maestro(
    players: dict[str, Any],
    rounds: list[dict[str, Any]],
    total_scores: dict[str, int],
) -> AwardDef | None:
    """Highest total score."""
    if not total_scores:
        return None
    winner = max(total_scores, key=lambda p: total_scores[p])
    return {
        "id": "maestro",
        "player_id": winner,
        "title": "Le Maestro",
        "emoji": "🏆",
        "detail": f"{_player_name(players, winner)} avec {total_scores[winner]} pts",
    }


def _award_oreille_carton(
    players: dict[str, Any],
    rounds: list[dict[str, Any]],
    total_scores: dict[str, int],
) -> AwardDef | None:
    """Lowest score — only if different player from Maestro."""
    if not total_scores:
        return None
    loser = min(total_scores, key=lambda p: total_scores[p])
    maestro = max(total_scores, key=lambda p: total_scores[p])
    if loser == maestro:
        return None
    return {
        "id": "oreille_carton",
        "player_id": loser,
        "title": "L'Oreille en carton",
        "emoji": "👂",
        "detail": f"{_player_name(players, loser)} avec seulement {total_scores[loser]} pts",
    }


def _award_shazam(
    players: dict[str, Any],
    rounds: list[dict[str, Any]],
    total_scores: dict[str, int],
) -> AwardDef | None:
    """Fastest single correct answer across all rounds."""
    best_pid: str | None = None
    best_time: int = 999_999

    for pid, ans in _iter_known_answers(players, rounds):
        t = ans.get("time_ms", 0)
        if _is_correct(ans) and 0 < t < best_time:
            best_pid, best_time = pid, t

    if best_pid is None:
        return None

    return {
        "id": "shazam",
        "player_id": best_pid,
        "title": "Le Shazam humain",
        "emoji": "⚡",
        "detail": f"{_player_name(players, best_pid)} — {best_time / 1000:.1f}s",
    }


def _award_fantome(
    players: dict[str, Any],
    rounds: list[dict[str, Any]],
    total_scores: dict[str, int],
) -> AwardDef | None:
    """Most rounds without answering (minimum 2 blank rounds)."""
    best_pid: str | None = None
    best_count = 1  # require at least 2

    for pid in players:
        blanks = _blank_rounds(rounds, pid)
        if blanks > best_count:
            best_count = blanks
            best_pid = pid

    if best_pid is None:
        return None

    return {
        "id": "fantome",
        "player_id": best_pid,
        "title": "Le Fantôme",
        "emoji": "👻",
        "detail": f"{_player_name(players, best_pid)} sans répondre {best_count} fois",
    }


def _award_poete(
    players: dict[str, Any],
    rounds: list[dict[str, Any]],
    total_scores: dict[str, int],
) -> AwardDef | None:
    """Most absurd answer: highest distance with non-empty text, on wrong answers."""
    best_pid: str | None = None
    best_distance = -1
    best_text = ""

    for pid, ans in _iter_known_answers(players, rounds):
        if not _is_wrong_with_text(ans):
            continue
        dist = ans.get("distance", 0)
        if dist > best_distance:
            best_pid, best_distance, best_text = pid, dist, ans.get("text", "")

    if best_pid is None:
        return None

    return {
        "id": "poete",
        "player_id": best_pid,
        "title": "Le Poète",
        "emoji": "🎭",
        "detail": f"« {best_text} »",
    }


def _award_touriste(
    players: dict[str, Any],
    rounds: list[dict[str, Any]],
    total_scores: dict[str, int],
) -> AwardDef | None:
    """Highest average distance on wrong answers (non-empty text only)."""
    dists_by_player: dict[str, list[int]] = {pid: [] for pid in players}

    for pid, ans in _iter_known_answers(players, rounds):
        if _is_wrong_with_text(ans):
            dists_by_player[pid].append(ans.get("distance", 0))

    best_pid: str | None = None
    best_avg = -1.0
    for pid, dists in dists_by_player.items():
        if not dists:
            continue
        avg = sum(dists) / len(dists)
        if avg > best_avg:
            best_avg, best_pid = avg, pid

    if best_pid is None:
        return None

    return {
        "id": "touriste",
        "player_id": best_pid,
        "title": "Le Touriste",
        "emoji": "🗺️",
        "detail": f"{_player_name(players, best_pid)} — distance moy. {best_avg:.1f}",
    }


def _award_rageux(
    players: dict[str, Any],
    rounds: list[dict[str, Any]],
    total_scores: dict[str, int],
) -> AwardDef | None:
    """Most attempts on a single round (minimum 3)."""
    best_pid: str | None = None
    best_attempts = 2  # require at least 3

    for pid, ans in _iter_known_answers(players, rounds):
        att = ans.get("attempts", 0)
        if att > best_attempts:
            best_attempts, best_pid = att, pid

    if best_pid is None:
        return None

    return {
        "id": "rageux",
        "player_id": best_pid,
        "title": "Le Rageux",
        "emoji": "😤",
        "detail": f"{_player_name(players, best_pid)} — {best_attempts} essais en un round",
    }


def _award_one_hit_wonder(
    players: dict[str, Any],
    rounds: list[dict[str, Any]],
    total_scores: dict[str, int],
) -> AwardDef | None:
    """Exactly 1 correct answer and it was the fastest answer in that round."""
    for pid in players:
        correct = _correct_answers(rounds, pid)
        if len(correct) != 1:
            continue
        round_idx, ans = correct[0]
        rnd = rounds[round_idx]
        round_times = [
            a.get("time_ms", 0)
            for a in rnd["answers"].values()
            if (a.get("title_match") or a.get("artist_match")) and a.get("time_ms", 0) > 0
        ]
        if not round_times:
            continue
        if ans.get("time_ms", 0) == min(round_times):
            return {
                "id": "one_hit_wonder",
                "player_id": pid,
                "title": "Le One Hit Wonder",
                "emoji": "🎯",
                "detail": f"{_player_name(players, pid)} — 1 bonne réponse, la plus rapide du round",
            }
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_AWARD_FACTORIES = [
    _award_maestro,
    _award_oreille_carton,
    _award_shazam,
    _award_fantome,
    _award_poete,
    _award_touriste,
    _award_rageux,
    _award_one_hit_wonder,
]


def compute_awards(history: dict[str, Any], mode: str) -> list[dict[str, Any]]:
    """Compute end-of-game awards from the game history.

    Args:
        history: dict with keys ``players``, ``rounds``, ``total_scores``.
        mode: game mode identifier (e.g. ``"blindtest"``).

    Returns:
        A list of award dicts. Each award ID appears at most once.
        A single player CAN receive multiple awards.
    """
    players: dict[str, Any] = history["players"]
    rounds: list[dict[str, Any]] = history["rounds"]
    total_scores: dict[str, int] = history["total_scores"]

    results: list[dict[str, Any]] = []

    for factory in _AWARD_FACTORIES:
        award = factory(players, rounds, total_scores)
        if award is not None:
            results.append(award)

    return results
