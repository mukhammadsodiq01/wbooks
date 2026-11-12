"""Guardian-facing reading reports.

The parent dashboard needs a single place that turns stored progress into
readable numbers: pages read, minutes spent, quiz scores and badges. Every
figure is derived from stored records, never from client input.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from django.db.models import Sum
from django.utils import timezone

from .models import (
    Badge,
    ChildBadge,
    QuizResult,
    ReadingProgress,
    ReadingSession,
    User,
)

MINUTES_PER_DAY = 7


def _average(values: list[int]) -> int | None:
    if not values:
        return None
    return round(sum(values) / len(values))


def child_report(child: User) -> dict:
    """Build a complete reading report for one young reader."""
    progress_entries = list(
        ReadingProgress.objects.filter(child=child)
        .select_related("book")
        .order_by("-updated_at")
    )
    quiz_results = list(
        QuizResult.objects.filter(child=child)
        .select_related("book")
        .order_by("-created_at")
    )
    awards = list(
        ChildBadge.objects.filter(child=child).select_related("badge")
    )

    books_started = len(progress_entries)
    books_completed = sum(1 for entry in progress_entries if entry.is_completed)
    pages_read = sum(entry.current_page for entry in progress_entries)
    reading_seconds = sum(entry.reading_seconds for entry in progress_entries)
    scores = [result.score_percentage for result in quiz_results]

    in_progress = [entry for entry in progress_entries if not entry.is_completed]
    current_book = in_progress[0] if in_progress else None

    return {
        "child": child,
        "progress_entries": progress_entries,
        "quiz_results": quiz_results,
        "awards": awards,
        "badges": [award.badge for award in awards],
        "badge_count": len(awards),
        "books_started": books_started,
        "books_completed": books_completed,
        "pages_read": pages_read,
        "reading_seconds": reading_seconds,
        "reading_minutes": round(reading_seconds / 60),
        "reading_time_label": _duration_label(reading_seconds),
        "quizzes_taken": len(quiz_results),
        "average_score": _average(scores),
        "best_score": max(scores) if scores else None,
        "passed_quizzes": sum(
            1 for result in quiz_results if result.score_percentage >= 70
        ),
        "current_book": current_book,
        "last_read": progress_entries[0].updated_at if progress_entries else None,
    }


def _duration_label(seconds: int) -> str:
    """Render seconds as ``45m`` or ``2h 15m``."""
    minutes = round(seconds / 60)
    if minutes < 60:
        return f"{minutes}m"
    hours, remainder = divmod(minutes, 60)
    if remainder:
        return f"{hours}h {remainder}m"
    return f"{hours}h"


def family_report(children: list[User]) -> dict:
    """Combine several reader reports into family-wide totals."""
    reports = [child_report(child) for child in children]

    total_seconds = sum(report["reading_seconds"] for report in reports)
    total_pages = sum(report["pages_read"] for report in reports)
    books_completed = sum(report["books_completed"] for report in reports)
    books_started = sum(report["books_started"] for report in reports)
    quizzes = sum(report["quizzes_taken"] for report in reports)
    scores = [
        result.score_percentage
        for report in reports
        for result in report["quiz_results"]
    ]
    badge_count = sum(report["badge_count"] for report in reports)

    return {
        "reports": reports,
        "children_count": len(reports),
        "books_started": books_started,
        "books_completed": books_completed,
        "pages_read": total_pages,
        "reading_seconds": total_seconds,
        "reading_minutes": round(total_seconds / 60),
        "reading_time_label": _duration_label(total_seconds),
        "quizzes_taken": quizzes,
        "average_score": _average(scores),
        "best_score": max(scores) if scores else None,
        "badge_count": badge_count,
    }


def reading_minutes_by_book(children: list[User]) -> list[dict]:
    """Minutes spent per story, biggest first, for the guardian breakdown."""
    totals = (
        ReadingProgress.objects.filter(child__in=children)
        .values("book_id", "book__title", "book__slug")
        .annotate(seconds=Sum("reading_seconds"))
        .order_by("-seconds")
    )
    books = []
    for row in totals:
        if not row["seconds"]:
            continue
        books.append(
            {
                "title": row["book__title"],
                "slug": row["book__slug"],
                "seconds": row["seconds"],
                "minutes": round(row["seconds"] / 60),
                "label": _duration_label(row["seconds"]),
            }
        )

    peak = max((book["seconds"] for book in books), default=0)
    for book in books:
        book["percent"] = round((book["seconds"] / peak) * 100) if peak else 0
    return books


def weekly_reading_minutes(children: list[User]) -> list[dict]:
    """Minutes read per day for the last seven days, oldest first."""
    today = timezone.localdate()
    days = [
        today - timedelta(days=offset)
        for offset in range(MINUTES_PER_DAY - 1, -1, -1)
    ]
    start = timezone.make_aware(datetime.combine(days[0], datetime.min.time()))

    totals = (
        ReadingSession.objects.filter(
            child__in=children,
            started_at__gte=start,
        )
        .extra(
            select={
                "day": "DATE(started_at)",
            }
        )
        .values("day")
        .annotate(seconds=Sum("seconds"))
    )
    by_day = {str(row["day"]): row["seconds"] for row in totals}

    chart = []
    for day in days:
        seconds = by_day.get(str(day), 0)
        chart.append(
            {
                "day": day,
                "label": day.strftime("%a")[0],
                "date_label": f"{day.strftime('%b')} {day.day}",
                "minutes": round(seconds / 60),
                "seconds": seconds,
            }
        )

    peak = max((point["minutes"] for point in chart), default=0)
    for point in chart:
        point["height"] = round((point["minutes"] / peak) * 100) if peak else 0
    return chart


def minutes_read_today(children: list[User]) -> int:
    """Minutes read by the family since midnight."""
    start = timezone.localtime().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    seconds = (
        ReadingSession.objects.filter(
            child__in=children,
            started_at__gte=start,
        ).aggregate(total=Sum("seconds"))["total"]
        or 0
    )
    return round(seconds / 60)


def badge_catalogue(children: list[User]) -> list[dict]:
    """Every active badge with the family's progress towards it."""
    earned_ids = set(
        ChildBadge.objects.filter(child__in=children).values_list(
            "badge_id", flat=True
        )
    )
    total_completed = ReadingProgress.objects.filter(
        child__in=children, is_completed=True
    ).count()
    total_quizzes = QuizResult.objects.filter(child__in=children).count()

    catalogue = []
    for badge in Badge.objects.filter(is_active=True):
        if badge.criteria == Badge.Criteria.FIRST_BOOK:
            progress = f"{min(total_completed, 1)} of 1 story finished"
        elif badge.criteria == Badge.Criteria.BOOKWORM:
            progress = f"{min(total_completed, badge.threshold)} of {badge.threshold} stories finished"
        elif badge.criteria == Badge.Criteria.FIRST_QUIZ:
            progress = f"{min(total_quizzes, 1)} of 1 quiz taken"
        elif badge.criteria == Badge.Criteria.QUIZ_MASTER:
            progress = "Score 100% on any quiz"
        else:
            progress = badge.get_theme_key_display() or "Reading atmosphere"
        catalogue.append(
            {
                "badge": badge,
                "earned": badge.pk in earned_ids,
                "progress": progress,
            }
        )
    return catalogue
