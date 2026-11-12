"""Automatic achievement unlocking for young readers."""
from __future__ import annotations

from .models import Badge, ChildBadge, QuizResult, ReadingProgress, User
from .themes import reader_theme_for


def _award(child: User, badge: Badge, note: str) -> ChildBadge | None:
    award, created = ChildBadge.objects.get_or_create(
        child=child,
        badge=badge,
        defaults={"note": note},
    )
    return award if created else None


def evaluate_badges(
    child: User,
    *,
    book=None,
    quiz_result: QuizResult | None = None,
) -> list[ChildBadge]:
    """Award every badge the reader now qualifies for.

    The function is idempotent: calling it repeatedly only returns badges that
    were created on this pass. ``book`` and ``quiz_result`` add friendly notes
    to the award, but qualification is always derived from stored progress so
    no badge can be unlocked by a forged request.
    """
    if child is None or not getattr(child, "is_child", False):
        return []

    badges = list(Badge.objects.filter(is_active=True))
    if not badges:
        return []

    completed = list(
        ReadingProgress.objects.filter(child=child, is_completed=True)
        .select_related("book")
        .order_by("-updated_at")
    )
    completed_count = len(completed)
    completed_themes = {
        reader_theme_for(progress.book.theme_default) for progress in completed
    }

    quiz_results = QuizResult.objects.filter(child=child)
    quiz_count = quiz_results.count()
    best_score = (
        quiz_results.order_by("-score_percentage")
        .values_list("score_percentage", flat=True)
        .first()
        or 0
    )

    earned_ids = set(
        ChildBadge.objects.filter(child=child).values_list("badge_id", flat=True)
    )

    context_parts = []
    if book is not None:
        context_parts.append(book.title)
    if quiz_result is not None:
        context_parts.append(f"Quiz {quiz_result.score_percentage}%")
    context = " · ".join(context_parts) or "WBooks achievement"

    new_awards: list[ChildBadge] = []
    for badge in badges:
        if badge.pk in earned_ids:
            continue

        qualifies = False
        if badge.criteria == Badge.Criteria.FIRST_BOOK:
            qualifies = completed_count >= 1
        elif badge.criteria == Badge.Criteria.BOOKWORM:
            qualifies = completed_count >= badge.threshold
        elif badge.criteria == Badge.Criteria.THEME_EXPLORER:
            qualifies = badge.theme_key in completed_themes
        elif badge.criteria == Badge.Criteria.FIRST_QUIZ:
            qualifies = quiz_count >= 1
        elif badge.criteria == Badge.Criteria.QUIZ_MASTER:
            qualifies = best_score >= 100

        if not qualifies:
            continue

        note = context
        if badge.criteria == Badge.Criteria.THEME_EXPLORER:
            note = f"{badge.get_theme_key_display()} · {context}"
        award = _award(child, badge, note)
        if award is not None:
            new_awards.append(award)

    return new_awards


def badge_shelf(child: User) -> list[dict]:
    """Return every active badge paired with this child's award state."""
    awards = {
        award.badge_id: award
        for award in ChildBadge.objects.filter(child=child).select_related("badge")
    }
    return [
        {
            "badge": badge,
            "earned": badge.pk in awards,
            "award": awards.get(badge.pk),
        }
        for badge in Badge.objects.filter(is_active=True)
    ]
