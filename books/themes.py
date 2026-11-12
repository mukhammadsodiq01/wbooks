"""Reader atmospheres and the mapping from library themes to them.

Keeping this in one module lets the reader, recap and achievement code agree
on how a story's library theme becomes a reading atmosphere.
"""
from __future__ import annotations

READER_THEMES = (
    {
        "key": "forest",
        "name": "ForestBook",
        "tagline": "Bark, leaves and warm earth tones.",
    },
    {
        "key": "ice",
        "name": "IceBook",
        "tagline": "Frosted glass and sparkling crystals.",
    },
    {
        "key": "holo",
        "name": "HoloBook",
        "tagline": "Neon cyan holograms and scanlines.",
    },
    {
        "key": "classic",
        "name": "ClassicBook",
        "tagline": "Warm paper, serif type, easy on the eyes.",
    },
)

READER_THEME_KEYS = tuple(theme["key"] for theme in READER_THEMES)

READER_THEME_MAP = {
    "forest": "forest",
    "safari": "forest",
    "candy": "forest",
    "ocean": "ice",
    "snow": "ice",
    "space": "holo",
    "neon": "holo",
    "castle": "classic",
}


def reader_theme_for(theme_default: str) -> str:
    """Return the reader atmosphere used by a library theme."""
    return READER_THEME_MAP.get(theme_default, "classic")
