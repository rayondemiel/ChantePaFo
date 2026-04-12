"""Ambiance Engine — maps music genres and game moments to light/visual configs.

Each config dict has the keys accepted by ``AmbianceConfig`` (palette, behavior,
intensity, vibe, bpm) so callers can validate with it when needed.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Genre → ambiance map
# Covers all 63 genres defined in app/music/deezer.py's GENRE_CONFIG.
# Keys are normalized (lowercase, no dashes/spaces/accents).
# ---------------------------------------------------------------------------

_G = dict[str, Any]

GENRE_AMBIANCE_MAP: dict[str, _G] = {
    # --- Disco / Funk ---
    "disco": {
        "palette": ["#FFD700", "#8B00FF", "#FF69B4"],
        "behavior": "pulse_fast",
        "intensity": 0.9,
        "vibe": "party",
        "bpm": 120,
    },
    "funk": {
        "palette": ["#FFD700", "#8B00FF", "#FF69B4"],
        "behavior": "pulse_fast",
        "intensity": 0.85,
        "vibe": "groove",
        "bpm": 115,
    },
    # --- Rock / Metal / Punk / Grunge / Alternative / Indie ---
    "rock": {
        "palette": ["#FF2200", "#111111", "#FF6622"],
        "behavior": "flash_aggressive",
        "intensity": 0.95,
        "vibe": "raw",
        "bpm": 130,
    },
    "metal": {
        "palette": ["#FF2200", "#111111", "#FF6622"],
        "behavior": "flash_aggressive",
        "intensity": 1.0,
        "vibe": "heavy",
        "bpm": 160,
    },
    "punk": {
        "palette": ["#FF2200", "#111111", "#FF6622"],
        "behavior": "flash_aggressive",
        "intensity": 0.95,
        "vibe": "raw",
        "bpm": 180,
    },
    "grunge": {
        "palette": ["#FF2200", "#111111", "#FF6622"],
        "behavior": "flash_aggressive",
        "intensity": 0.85,
        "vibe": "dirty",
        "bpm": 100,
    },
    "indie": {
        "palette": ["#FF6688", "#AADDFF", "#FFEEAA"],
        "behavior": "wave_smooth",
        "intensity": 0.6,
        "vibe": "chill",
        "bpm": 110,
    },
    "alternative": {
        "palette": ["#FF6688", "#AADDFF", "#FFEEAA"],
        "behavior": "wave_smooth",
        "intensity": 0.65,
        "vibe": "moody",
        "bpm": 115,
    },
    # --- Pop ---
    "pop": {
        "palette": ["#FF99CC", "#99CCFF", "#FFFFAA"],
        "behavior": "wave_smooth",
        "intensity": 0.7,
        "vibe": "bright",
        "bpm": 120,
    },
    "dance": {
        "palette": ["#FF99CC", "#99CCFF", "#FFFFAA"],
        "behavior": "pulse_fast",
        "intensity": 0.85,
        "vibe": "energetic",
        "bpm": 128,
    },
    "rnb": {
        "palette": ["#FF99CC", "#99CCFF", "#FFFFAA"],
        "behavior": "wave_smooth",
        "intensity": 0.65,
        "vibe": "smooth",
        "bpm": 90,
    },
    # --- Rap / Hip-Hop / Afro Trap ---
    "rap": {
        "palette": ["#8800FF", "#00FF88", "#111111"],
        "behavior": "pulse_heavy",
        "intensity": 0.9,
        "vibe": "street",
        "bpm": 90,
    },
    "hiphop": {
        "palette": ["#8800FF", "#00FF88", "#111111"],
        "behavior": "pulse_heavy",
        "intensity": 0.9,
        "vibe": "street",
        "bpm": 90,
    },
    "afrotrap": {
        "palette": ["#8800FF", "#00FF88", "#111111"],
        "behavior": "pulse_heavy",
        "intensity": 0.88,
        "vibe": "urban",
        "bpm": 140,
    },
    "afro_trap": {
        "palette": ["#8800FF", "#00FF88", "#111111"],
        "behavior": "pulse_heavy",
        "intensity": 0.88,
        "vibe": "urban",
        "bpm": 140,
    },
    # --- Electro / House / Techno / Trance / Drum n Bass ---
    "electro": {
        "palette": ["#00FFFF", "#FF00FF", "#FFFFFF"],
        "behavior": "strobe_fast",
        "intensity": 0.95,
        "vibe": "electric",
        "bpm": 128,
    },
    "house": {
        "palette": ["#00FFFF", "#FF00FF", "#FFFFFF"],
        "behavior": "strobe_fast",
        "intensity": 0.9,
        "vibe": "club",
        "bpm": 128,
    },
    "techno": {
        "palette": ["#00FFFF", "#FF00FF", "#FFFFFF"],
        "behavior": "strobe_fast",
        "intensity": 1.0,
        "vibe": "dark_club",
        "bpm": 140,
    },
    "trance": {
        "palette": ["#00FFFF", "#FF00FF", "#FFFFFF"],
        "behavior": "strobe_fast",
        "intensity": 0.95,
        "vibe": "hypnotic",
        "bpm": 138,
    },
    "drumnbass": {
        "palette": ["#00FFFF", "#FF00FF", "#FFFFFF"],
        "behavior": "strobe_fast",
        "intensity": 0.95,
        "vibe": "frenetic",
        "bpm": 174,
    },
    "drum_n_bass": {
        "palette": ["#00FFFF", "#FF00FF", "#FFFFFF"],
        "behavior": "strobe_fast",
        "intensity": 0.95,
        "vibe": "frenetic",
        "bpm": 174,
    },
    # --- Jazz / Blues / Soul / Swing ---
    "jazz": {
        "palette": ["#FFBB44", "#223366", "#CC8833"],
        "behavior": "breathe_slow",
        "intensity": 0.5,
        "vibe": "lounge",
        "bpm": 80,
    },
    "blues": {
        "palette": ["#FFBB44", "#223366", "#CC8833"],
        "behavior": "breathe_slow",
        "intensity": 0.5,
        "vibe": "melancholy",
        "bpm": 75,
    },
    "soul": {
        "palette": ["#FFBB44", "#223366", "#CC8833"],
        "behavior": "breathe_slow",
        "intensity": 0.55,
        "vibe": "warm",
        "bpm": 85,
    },
    "swing": {
        "palette": ["#FFBB44", "#223366", "#CC8833"],
        "behavior": "breathe_slow",
        "intensity": 0.6,
        "vibe": "swing",
        "bpm": 120,
    },
    # --- 80s / New Wave / Synthwave ---
    "annees80": {
        "palette": ["#FF00CC", "#00FFFF", "#CC00FF"],
        "behavior": "grid_neon",
        "intensity": 0.85,
        "vibe": "retro",
        "bpm": 120,
    },
    "newwave": {
        "palette": ["#FF00CC", "#00FFFF", "#CC00FF"],
        "behavior": "grid_neon",
        "intensity": 0.8,
        "vibe": "cold_wave",
        "bpm": 115,
    },
    "new_wave": {
        "palette": ["#FF00CC", "#00FFFF", "#CC00FF"],
        "behavior": "grid_neon",
        "intensity": 0.8,
        "vibe": "cold_wave",
        "bpm": 115,
    },
    "synthwave": {
        "palette": ["#FF00CC", "#00FFFF", "#CC00FF"],
        "behavior": "grid_neon",
        "intensity": 0.9,
        "vibe": "synthwave",
        "bpm": 118,
    },
    # --- Other decades (share 80s palette, adjust intensity) ---
    "annees60": {
        "palette": ["#FF99CC", "#99CCFF", "#FFFFAA"],
        "behavior": "wave_smooth",
        "intensity": 0.6,
        "vibe": "vintage",
        "bpm": 100,
    },
    "annees70": {
        "palette": ["#FFD700", "#8B00FF", "#FF69B4"],
        "behavior": "pulse_fast",
        "intensity": 0.7,
        "vibe": "groovy",
        "bpm": 110,
    },
    "annees90": {
        "palette": ["#FF2200", "#111111", "#FF6622"],
        "behavior": "flash_aggressive",
        "intensity": 0.8,
        "vibe": "grunge",
        "bpm": 120,
    },
    "annees2000": {
        "palette": ["#FF99CC", "#99CCFF", "#FFFFAA"],
        "behavior": "wave_smooth",
        "intensity": 0.75,
        "vibe": "bubblegum",
        "bpm": 125,
    },
    "annees2010": {
        "palette": ["#8800FF", "#00FF88", "#111111"],
        "behavior": "pulse_heavy",
        "intensity": 0.8,
        "vibe": "trap_era",
        "bpm": 130,
    },
    # --- Classique / Opéra ---
    "classique": {
        "palette": ["#FFFFFF", "#FFD700", "#F5F0E8"],
        "behavior": "shimmer",
        "intensity": 0.35,
        "vibe": "elegant",
        "bpm": 60,
    },
    "opera": {
        "palette": ["#FFFFFF", "#FFD700", "#F5F0E8"],
        "behavior": "shimmer",
        "intensity": 0.4,
        "vibe": "dramatic",
        "bpm": 65,
    },
    # --- Reggae / Ska ---
    "reggae": {
        "palette": ["#00CC44", "#FFDD00", "#CC2200"],
        "behavior": "wave_slow",
        "intensity": 0.6,
        "vibe": "chill",
        "bpm": 75,
    },
    "ska": {
        "palette": ["#00CC44", "#FFDD00", "#CC2200"],
        "behavior": "wave_slow",
        "intensity": 0.7,
        "vibe": "upbeat",
        "bpm": 160,
    },
    # --- Latino / Reggaeton / Bossa Nova / Zouk ---
    "latino": {
        "palette": ["#FF6600", "#CC0000", "#FFCC00"],
        "behavior": "pulse_warm",
        "intensity": 0.85,
        "vibe": "sensual",
        "bpm": 100,
    },
    "reggaeton": {
        "palette": ["#FF6600", "#CC0000", "#FFCC00"],
        "behavior": "pulse_warm",
        "intensity": 0.9,
        "vibe": "hot",
        "bpm": 92,
    },
    "bossanova": {
        "palette": ["#FF6600", "#CC0000", "#FFCC00"],
        "behavior": "pulse_warm",
        "intensity": 0.5,
        "vibe": "sophisticated",
        "bpm": 100,
    },
    "bossa_nova": {
        "palette": ["#FF6600", "#CC0000", "#FFCC00"],
        "behavior": "pulse_warm",
        "intensity": 0.5,
        "vibe": "sophisticated",
        "bpm": 100,
    },
    "zouk": {
        "palette": ["#FF6600", "#CC0000", "#FFCC00"],
        "behavior": "pulse_warm",
        "intensity": 0.75,
        "vibe": "romantic",
        "bpm": 75,
    },
    # --- Country / Folk / Acoustic ---
    "country": {
        "palette": ["#8B5E3C", "#4CAF50", "#F5DEB3"],
        "behavior": "sway_gentle",
        "intensity": 0.45,
        "vibe": "earthy",
        "bpm": 100,
    },
    "folk": {
        "palette": ["#8B5E3C", "#4CAF50", "#F5DEB3"],
        "behavior": "sway_gentle",
        "intensity": 0.4,
        "vibe": "natural",
        "bpm": 90,
    },
    "acoustic": {
        "palette": ["#8B5E3C", "#4CAF50", "#F5DEB3"],
        "behavior": "sway_gentle",
        "intensity": 0.35,
        "vibe": "intimate",
        "bpm": 85,
    },
    # --- K-Pop / J-Pop ---
    "kpop": {
        "palette": ["#FF00AA", "#00AAFF", "#FFFFFF"],
        "behavior": "flash_pop",
        "intensity": 0.95,
        "vibe": "idol",
        "bpm": 130,
    },
    "jpop": {
        "palette": ["#FF00AA", "#00AAFF", "#FFFFFF"],
        "behavior": "flash_pop",
        "intensity": 0.9,
        "vibe": "kawaii",
        "bpm": 125,
    },
    # --- Raï ---
    "rai": {
        "palette": ["#FFD700", "#00AA44", "#8B00FF"],
        "behavior": "pulse_oriental",
        "intensity": 0.8,
        "vibe": "maghreb",
        "bpm": 110,
    },
    # --- Afrobeats ---
    "afrobeats": {
        "palette": ["#FF6600", "#228B22", "#FFD700"],
        "behavior": "pulse_afro",
        "intensity": 0.85,
        "vibe": "afro",
        "bpm": 100,
    },
    # --- Ambient / Lo-Fi ---
    "ambient": {
        "palette": ["#001133", "#220044", "#000000"],
        "behavior": "breathe_deep",
        "intensity": 0.2,
        "vibe": "meditative",
        "bpm": 60,
    },
    "lofi": {
        "palette": ["#001133", "#220044", "#000000"],
        "behavior": "breathe_deep",
        "intensity": 0.25,
        "vibe": "cozy",
        "bpm": 70,
    },
    "lo_fi": {
        "palette": ["#001133", "#220044", "#000000"],
        "behavior": "breathe_deep",
        "intensity": 0.25,
        "vibe": "cozy",
        "bpm": 70,
    },
    # --- Bande originale (films, séries, jeux vidéo) ---
    "bofilms": {
        "palette": ["#001566", "#C0C0C0", "#003399"],
        "behavior": "cinematic_sweep",
        "intensity": 0.6,
        "vibe": "epic",
        "bpm": 90,
    },
    "bo_films": {
        "palette": ["#001566", "#C0C0C0", "#003399"],
        "behavior": "cinematic_sweep",
        "intensity": 0.6,
        "vibe": "epic",
        "bpm": 90,
    },
    "boseries": {
        "palette": ["#001566", "#C0C0C0", "#003399"],
        "behavior": "cinematic_sweep",
        "intensity": 0.55,
        "vibe": "dramatic",
        "bpm": 85,
    },
    "bo_series": {
        "palette": ["#001566", "#C0C0C0", "#003399"],
        "behavior": "cinematic_sweep",
        "intensity": 0.55,
        "vibe": "dramatic",
        "bpm": 85,
    },
    "bojeuxvideo": {
        "palette": ["#001566", "#C0C0C0", "#003399"],
        "behavior": "cinematic_sweep",
        "intensity": 0.7,
        "vibe": "action",
        "bpm": 130,
    },
    "bo_jeux_video": {
        "palette": ["#001566", "#C0C0C0", "#003399"],
        "behavior": "cinematic_sweep",
        "intensity": 0.7,
        "vibe": "action",
        "bpm": 130,
    },
    # --- Disney / Comédie musicale ---
    "disney": {
        "palette": ["#FF2244", "#FFEE00", "#0044FF"],
        "behavior": "sparkle",
        "intensity": 0.85,
        "vibe": "magic",
        "bpm": 120,
    },
    "comediemusicale": {
        "palette": ["#FF2244", "#FFEE00", "#0044FF"],
        "behavior": "sparkle",
        "intensity": 0.8,
        "vibe": "showtime",
        "bpm": 120,
    },
    "comedie_musicale": {
        "palette": ["#FF2244", "#FFEE00", "#0044FF"],
        "behavior": "sparkle",
        "intensity": 0.8,
        "vibe": "showtime",
        "bpm": 120,
    },
    # --- Gospel ---
    "gospel": {
        "palette": ["#FFD700", "#FFFFFF", "#FF9900"],
        "behavior": "shimmer_warm",
        "intensity": 0.7,
        "vibe": "uplifting",
        "bpm": 90,
    },
    # --- Bollywood ---
    "bollywood": {
        "palette": ["#CC0000", "#FFD700", "#FF6600"],
        "behavior": "pulse_bollywood",
        "intensity": 0.9,
        "vibe": "vibrant",
        "bpm": 110,
    },
    # --- Anime ---
    "anime": {
        "palette": ["#FF00AA", "#00FF66", "#AA00FF"],
        "behavior": "flash_pop",
        "intensity": 0.9,
        "vibe": "otaku",
        "bpm": 150,
    },
    # --- French genres ---
    "chansonfrancaise": {
        "palette": ["#0033AA", "#FFFFFF", "#CC1111"],
        "behavior": "wave_smooth",
        "intensity": 0.5,
        "vibe": "poetic",
        "bpm": 90,
    },
    "chanson_francaise": {
        "palette": ["#0033AA", "#FFFFFF", "#CC1111"],
        "behavior": "wave_smooth",
        "intensity": 0.5,
        "vibe": "poetic",
        "bpm": 90,
    },
    "varietefraaise": {
        "palette": ["#FF99CC", "#99CCFF", "#FFFFAA"],
        "behavior": "wave_smooth",
        "intensity": 0.55,
        "vibe": "nostalgic",
        "bpm": 100,
    },
    "varietefrancaise": {
        "palette": ["#FF99CC", "#99CCFF", "#FFFFAA"],
        "behavior": "wave_smooth",
        "intensity": 0.55,
        "vibe": "nostalgic",
        "bpm": 100,
    },
    "variete_francaise": {
        "palette": ["#FF99CC", "#99CCFF", "#FFFFAA"],
        "behavior": "wave_smooth",
        "intensity": 0.55,
        "vibe": "nostalgic",
        "bpm": 100,
    },
    "rapfr": {
        "palette": ["#8800FF", "#00FF88", "#111111"],
        "behavior": "pulse_heavy",
        "intensity": 0.88,
        "vibe": "street",
        "bpm": 90,
    },
    "rap_fr": {
        "palette": ["#8800FF", "#00FF88", "#111111"],
        "behavior": "pulse_heavy",
        "intensity": 0.88,
        "vibe": "street",
        "bpm": 90,
    },
    "popfr": {
        "palette": ["#FF99CC", "#99CCFF", "#FFFFAA"],
        "behavior": "wave_smooth",
        "intensity": 0.65,
        "vibe": "bright",
        "bpm": 118,
    },
    "pop_fr": {
        "palette": ["#FF99CC", "#99CCFF", "#FFFFAA"],
        "behavior": "wave_smooth",
        "intensity": 0.65,
        "vibe": "bright",
        "bpm": 118,
    },
    # --- Catch-all key from GENRE_CONFIG ---
    "all": {
        "palette": ["#FF99CC", "#99CCFF", "#FFFFAA"],
        "behavior": "wave_smooth",
        "intensity": 0.7,
        "vibe": "generic",
        "bpm": 120,
    },
}

DEFAULT_AMBIANCE: _G = {
    "palette": ["#AAAAAA", "#DDDDDD", "#FFFFFF"],
    "behavior": "wave_smooth",
    "intensity": 0.5,
    "vibe": "neutral",
    "bpm": 100,
}

# ---------------------------------------------------------------------------
# Moment → ambiance map
# ---------------------------------------------------------------------------

MOMENT_MAP: dict[str, _G] = {
    "lobby": {
        "palette": ["#334466", "#223355", "#445577"],
        "behavior": "breathe_slow",
        "intensity": 0.3,
        "vibe": "waiting",
        "bpm": 80,
    },
    "countdown": {
        "palette": ["#FF6600", "#FFCC00", "#FF3300"],
        "behavior": "buildup",
        "intensity": 0.75,
        "vibe": "tension",
        "bpm": 130,
    },
    "correct_answer": {
        "palette": ["#00FF88", "#00FFFF", "#FFFFFF"],
        "behavior": "flash_pop",
        "intensity": 1.0,
        "vibe": "victory",
        "bpm": 140,
    },
    "recording": {
        "palette": ["#FF0000", "#FF6600", "#FFCC00"],
        "behavior": "pulse_slow",
        "intensity": 0.6,
        "vibe": "recording",
        "bpm": 90,
    },
    "suspense": {
        "palette": ["#110022", "#220044", "#330066"],
        "behavior": "strobe_slow",
        "intensity": 0.55,
        "vibe": "mystery",
        "bpm": 60,
    },
    "reveal": {
        "palette": ["#FFD700", "#FF4400", "#FFFFFF"],
        "behavior": "cinematic_sweep",
        "intensity": 0.9,
        "vibe": "dramatic",
        "bpm": 110,
    },
    "applause": {
        "palette": ["#FFD700", "#00FF88", "#FF69B4"],
        "behavior": "sparkle",
        "intensity": 0.95,
        "vibe": "celebration",
        "bpm": 130,
    },
    "shame": {
        "palette": ["#333333", "#660000", "#440000"],
        "behavior": "strobe_slow",
        "intensity": 0.4,
        "vibe": "shame",
        "bpm": 60,
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _normalize_genre(genre: str) -> str:
    """Normalize genre key to match GENRE_AMBIANCE_MAP keys."""
    key = genre.lower()
    # Remove accents (simple ASCII replacement for common French chars)
    replacements = {
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "à": "a",
        "â": "a",
        "ù": "u",
        "û": "u",
        "ô": "o",
        "î": "i",
        "ï": "i",
        "ç": "c",
    }
    for src, dst in replacements.items():
        key = key.replace(src, dst)
    key = key.replace("-", "").replace(" ", "")
    return key


def get_ambiance_for_genre(genre: str) -> dict[str, Any]:
    """Return the ambiance config for a given genre name.

    Falls back to DEFAULT_AMBIANCE for unknown genres.
    Always returns a copy — callers may mutate freely.
    """
    key = _normalize_genre(genre)
    return GENRE_AMBIANCE_MAP.get(key, DEFAULT_AMBIANCE).copy()


def get_ambiance_for_moment(moment: str) -> dict[str, Any]:
    """Return the ambiance config for a game moment.

    Falls back to DEFAULT_AMBIANCE for unknown moments.
    Always returns a copy — callers may mutate freely.
    """
    return MOMENT_MAP.get(moment, DEFAULT_AMBIANCE).copy()
