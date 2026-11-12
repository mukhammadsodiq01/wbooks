"""Storyboard and lesson data for the post-reading recap."""
from __future__ import annotations

import re

from .models import Book, BookPage
from .themes import reader_theme_for

BEAT_LABELS = (
    "The beginning",
    "A discovery",
    "A turning point",
    "The way home",
)

THEME_LESSONS = {
    "forest": (
        "Curiosity grows the wildest adventures.",
        "Every living thing deserves a little care.",
        "Kindness comes back in unexpected ways.",
    ),
    "ice": (
        "Courage can be quiet and steady.",
        "Looking closely reveals hidden wonders.",
        "Warmth is something we carry with us.",
    ),
    "holo": (
        "New ideas can light up the darkest places.",
        "Small helpers can solve very big problems.",
        "Thinking creatively turns mistakes into discoveries.",
    ),
    "classic": (
        "Every small promise is a kind of magic.",
        "True songs plant something somewhere.",
        "Helping others makes the whole world brighter.",
    ),
}

THEME_MORALS = {
    "forest": "The wild grows kinder when we stop to listen.",
    "ice": "Quiet courage can warm the coldest night.",
    "holo": "A curious mind is the brightest light of all.",
    "classic": "Every kind act plants a little light somewhere.",
}

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _caption(text: str, limit: int = 168) -> str:
    """Take the first one or two sentences, then trim to a panel-friendly size."""
    sentences = [part.strip() for part in _SENTENCE_END.split(text) if part.strip()]
    caption = " ".join(sentences[:2]) if sentences else text.strip()
    if len(caption) <= limit:
        return caption
    trimmed = caption[:limit].rsplit(" ", 1)[0].rstrip(",;:")
    return f"{trimmed}…"


def _selected_pages(pages: list[BookPage]) -> list[BookPage]:
    if len(pages) <= 4:
        return pages
    last = len(pages) - 1
    indices = [0, round(last / 3), round((last * 2) / 3), last]
    ordered = list(dict.fromkeys(indices))
    return [pages[index] for index in ordered]


def _labels_for(count: int) -> tuple[str, ...]:
    if count >= 4:
        return BEAT_LABELS
    if count == 3:
        return ("The beginning", "The turning point", "The way home")
    if count == 2:
        return ("The beginning", "The way home")
    return ("The story",)


def build_recap(book: Book) -> dict:
    """Create the animated storyboard, slideshow and lesson content."""
    pages = list(book.pages.all())
    chosen = _selected_pages(pages)
    labels = _labels_for(len(chosen))

    beats = []
    for index, page in enumerate(chosen):
        beats.append(
            {
                "page_number": page.page_number,
                "label": labels[index],
                "caption": _caption(page.content_text),
                "illustration_url": page.illustration_url,
                "animation": page.animation_type,
                "scene": (index % 4) + 1,
            }
        )

    reader_theme = reader_theme_for(book.theme_default)
    raw_lessons = book.key_lessons
    if not isinstance(raw_lessons, (list, tuple)):
        raw_lessons = []
    lessons = [
        str(lesson).strip()
        for lesson in raw_lessons
        if str(lesson).strip()
    ]
    if not lessons:
        lessons = list(THEME_LESSONS[reader_theme])

    moral = (book.story_moral or "").strip() or THEME_MORALS[reader_theme]

    slides = [
        {
            "image": page.illustration_url,
            "caption": _caption(page.content_text),
            "page_number": page.page_number,
        }
        for page in pages
        if page.illustration_url
    ]

    return {
        "beats": beats,
        "lessons": lessons[:3],
        "moral": moral,
        "slides": slides,
        "reader_theme": reader_theme,
    }
