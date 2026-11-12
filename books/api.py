"""JSON API endpoints for the interactive reader."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Book, BookPage, ReadingProgress, ReadingSession, User


def _book_from_request(request) -> Book:
    """Resolve the story from ``book`` (slug) in the payload or query string."""
    slug = (
        request.data.get("book")
        or request.query_params.get("book")
        or ""
    )
    slug = str(slug).strip()
    if not slug:
        raise ValidationError({"book": "A book slug is required."})
    return get_object_or_404(Book, slug=slug, is_published=True)


def _last_page_number(book: Book) -> int:
    last_page = (
        book.pages.order_by("-page_number")
        .values_list("page_number", flat=True)
        .first()
    )
    if last_page is None:
        raise ValidationError({"book": "This story does not have any pages yet."})
    return last_page


def _payload(
    book: Book,
    *,
    progress: ReadingProgress | None,
) -> dict:
    last_page = _last_page_number(book)
    current_page = progress.current_page if progress else 1
    return {
        "book": book.slug,
        "book_id": book.pk,
        "title": book.title,
        "has_progress": progress is not None,
        "current_page": current_page,
        "last_page": last_page,
        "total_pages": book.pages.count(),
        "is_completed": bool(progress and progress.is_completed),
        "percentage": progress.percentage if progress else 0,
        "reading_seconds": progress.reading_seconds if progress else 0,
        "reading_minutes": progress.reading_minutes if progress else 0,
        "updated_at": progress.updated_at.isoformat() if progress else None,
    }


class ReadingProgressAPIView(APIView):
    """Read and persist a young reader's place in a story.

    ``GET /api/progress/?book=<slug>`` restores progress.
    ``POST /api/progress/`` accepts ``{"book": "<slug>", "current_page": 3}``
    and an optional ``{"seconds": 45}`` reading-time report.
    """

    MAX_SECONDS_PER_SAVE = 1800

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def _ensure_child(self, request) -> Response | None:
        if request.user.role != User.Role.CHILD:
            return Response(
                {"detail": "Only young reader accounts can track reading progress."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    def _reading_seconds(self, request) -> int:
        raw = request.data.get("seconds", 0)
        try:
            seconds = int(raw)
        except (TypeError, ValueError):
            raise ValidationError(
                {"seconds": "Reading time must be a whole number of seconds."}
            )
        if seconds < 0:
            raise ValidationError({"seconds": "Reading time cannot be negative."})
        return min(seconds, self.MAX_SECONDS_PER_SAVE)

    def get(self, request):
        denied = self._ensure_child(request)
        if denied is not None:
            return denied

        book = _book_from_request(request)
        progress = ReadingProgress.objects.filter(
            child=request.user, book=book
        ).first()
        return Response(_payload(book, progress=progress))

    def post(self, request):
        denied = self._ensure_child(request)
        if denied is not None:
            return denied

        book = _book_from_request(request)
        last_page = _last_page_number(book)
        seconds = self._reading_seconds(request)

        existing = ReadingProgress.objects.filter(
            child=request.user, book=book
        ).first()

        raw_page = request.data.get("current_page")
        if raw_page in (None, ""):
            page_number = existing.current_page if existing else 1
        else:
            try:
                page_number = int(raw_page)
            except (TypeError, ValueError):
                raise ValidationError(
                    {"current_page": "Page number must be a whole number."}
                )

            if not 1 <= page_number <= BookPage.MAX_PAGE:
                raise ValidationError(
                    {
                        "current_page": (
                            f"Choose a page between 1 and {BookPage.MAX_PAGE}."
                        )
                    }
                )

            if not book.pages.filter(page_number=page_number).exists():
                raise ValidationError(
                    {"current_page": f"{book.title} has no page {page_number}."}
                )

        progress, _ = ReadingProgress.objects.get_or_create(
            child=request.user, book=book
        )
        progress.current_page = page_number
        progress.is_completed = page_number >= last_page
        if seconds:
            progress.reading_seconds += seconds
        progress.save(
            update_fields=[
                "current_page",
                "is_completed",
                "reading_seconds",
                "updated_at",
            ]
        )

        if seconds:
            ReadingSession.objects.create(
                child=request.user,
                book=book,
                seconds=seconds,
                current_page=page_number,
            )

        return Response(
            _payload(book, progress=progress),
            status=status.HTTP_200_OK,
        )
