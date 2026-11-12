"""HTML views for accounts, dashboards and the story library."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from .achievements import badge_shelf, evaluate_badges
from .decorators import child_required, parent_required
from .forms import LinkChildForm, SignUpForm, WBooksAuthenticationForm
from .models import (
    Book,
    BookPage,
    ParentChildLink,
    QuizQuestion,
    QuizResult,
    ReadingProgress,
    User,
)
from .quizzes import grade_quiz
from .recap import build_recap
from .reports import (
    badge_catalogue,
    family_report,
    minutes_read_today,
    reading_minutes_by_book,
    weekly_reading_minutes,
)
from .themes import READER_THEME_MAP, READER_THEMES

# The reader ships four visual atmospheres. Each story's default theme is
# translated from the eight library themes into one of them.


def home(request: HttpRequest) -> HttpResponse:
    books = (
        Book.objects.filter(is_published=True)
        .prefetch_related("pages")
        .annotate(page_total=Count("pages"))[:9]
    )
    progress_by_book = {}
    if request.user.is_authenticated and request.user.is_child:
        progress_by_book = {
            item.book_id: item
            for item in ReadingProgress.objects.filter(child=request.user)
        }
    for book in books:
        book.user_progress = progress_by_book.get(book.pk)
    featured = books[0] if books else None
    return render(
        request,
        "books/home.html",
        {
            "books": books,
            "featured": featured,
            "progress_by_book": progress_by_book,
            "total_books": Book.objects.filter(is_published=True).count(),
        },
    )


def register(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("books:dashboard")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend",
            )
            if form.parent_user is not None:
                messages.success(
                    request,
                    f"Welcome to WBooks! Your account is now linked to "
                    f"{form.parent_user.display_name}.",
                )
            else:
                messages.success(
                    request, f"Welcome to WBooks, {user.first_name_only}!"
                )
            return redirect("books:dashboard")
        messages.error(request, "Please check the highlighted fields and try again.")
    else:
        form = SignUpForm()

    return render(request, "auth/register.html", {"form": form})


class WBooksLoginView(LoginView):
    template_name = "auth/login.html"
    authentication_form = WBooksAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Welcome back, {self.request.user.first_name_only}!",
        )
        return response

    def get_success_url(self) -> str:
        return str(reverse_lazy("books:dashboard"))


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    if request.user.is_parent:
        return redirect("books:parent_dashboard")
    if request.user.is_child:
        return redirect("books:child_dashboard")
    return redirect("books:home")


@parent_required
def parent_dashboard(request: HttpRequest) -> HttpResponse:
    profile = request.user.profile
    form = LinkChildForm(parent=request.user)

    if request.method == "POST":
        form = LinkChildForm(request.POST, parent=request.user)
        if form.is_valid():
            ParentChildLink.objects.create(
                parent_profile=profile, child=form.child
            )
            messages.success(
                request,
                f"{form.child.first_name_only} is now on your family shelf.",
            )
            return redirect("books:parent_dashboard")
        messages.error(request, "We couldn't link that reader yet.")

    children = list(
        User.objects.filter(parent_link__parent_profile=profile)
        .select_related("profile")
        .prefetch_related(
            "reading_progress__book",
            "quiz_results__book",
            "badge_awards__badge",
        )
        .order_by("display_name")
    )

    family = family_report(children)
    reports = family["reports"]

    family_progress = ReadingProgress.objects.filter(
        child__parent_link__parent_profile=profile
    ).select_related("child", "book")
    family_in_progress = family_progress.filter(is_completed=False).count()

    recent_quizzes = (
        QuizResult.objects.filter(child__parent_link__parent_profile=profile)
        .select_related("child", "book")
        .order_by("-created_at")[:8]
    )

    goal_minutes = profile.reading_goal_minutes
    minutes_today = minutes_read_today(children)
    goal_percentage = min(
        100, round((minutes_today / goal_minutes) * 100) if goal_minutes else 0
    )
    minutes_remaining = max(0, goal_minutes - minutes_today)

    return render(
        request,
        "dashboard/parent.html",
        {
            "children": children,
            "link_form": form,
            "family_progress": family_progress[:8],
            "family_in_progress": family_in_progress,
            "children_count": family["children_count"],
            "family": family,
            "reports": reports,
            "recent_quizzes": recent_quizzes,
            "weekly_chart": weekly_reading_minutes(children),
            "book_times": reading_minutes_by_book(children),
            "badge_catalogue": badge_catalogue(children),
            "minutes_today": minutes_today,
            "goal_minutes": goal_minutes,
            "goal_percentage": goal_percentage,
            "minutes_remaining": minutes_remaining,
            "pages_per_book": BookPage.MAX_PAGE,
        },
    )


@child_required
def child_dashboard(request: HttpRequest) -> HttpResponse:
    progress_entries = (
        ReadingProgress.objects.filter(child=request.user)
        .select_related("book")
        .prefetch_related("book__pages")
    )
    active_progress = [entry for entry in progress_entries if not entry.is_completed]
    completed_count = sum(1 for entry in progress_entries if entry.is_completed)
    pages_turned = sum(entry.current_page for entry in progress_entries)
    shelf_book_ids = {entry.book_id for entry in progress_entries}

    new_badges = evaluate_badges(request.user)
    badge_cards = badge_shelf(request.user)
    general_quiz_count = QuizQuestion.objects.filter(is_general_quiz=True).count()

    recommendations = (
        Book.objects.filter(is_published=True)
        .exclude(pk__in=shelf_book_ids)
        .prefetch_related("pages")
        .annotate(page_total=Count("pages"))[:6]
    )

    return render(
        request,
        "dashboard/child.html",
        {
            "progress_entries": progress_entries,
            "active_progress": active_progress,
            "completed_count": completed_count,
            "pages_turned": pages_turned,
            "recommendations": recommendations,
            "pages_per_book": BookPage.MAX_PAGE,
            "badge_cards": badge_cards,
            "new_badges": new_badges,
            "general_quiz_count": general_quiz_count,
            "earned_badge_count": sum(1 for card in badge_cards if card["earned"]),
        },
    )


@child_required
def reader(request: HttpRequest, slug: str) -> HttpResponse:
    """Immersive, auto-saving reader with live atmosphere switching."""
    book = get_object_or_404(
        Book.objects.prefetch_related("pages"), slug=slug, is_published=True
    )
    pages = list(book.pages.all())
    if not pages:
        messages.info(
            request,
            "This story is still being illustrated. Please check back soon.",
        )
        return redirect("books:book_detail", slug=book.slug)

    progress, _ = ReadingProgress.objects.get_or_create(
        child=request.user, book=book, defaults={"current_page": 1}
    )

    available_pages = {page.page_number for page in pages}
    initial_page = progress.current_page
    restart = request.GET.get("restart") == "1"

    if restart or initial_page not in available_pages:
        initial_page = pages[0].page_number
        progress.current_page = initial_page
        progress.is_completed = False
        progress.save(
            update_fields=["current_page", "is_completed", "updated_at"]
        )

    initial_index = next(
        index
        for index, page in enumerate(pages)
        if page.page_number == initial_page
    )
    initial_percentage = min(
        100, round((initial_index + 1) / len(pages) * 100)
    )

    return render(
        request,
        "books/reader.html",
        {
            "book": book,
            "pages": pages,
            "progress": progress,
            "initial_page": initial_page,
            "initial_percentage": initial_percentage,
            "default_theme": READER_THEME_MAP.get(
                book.theme_default, "classic"
            ),
            "reader_themes": READER_THEMES,
            "pages_per_book": BookPage.MAX_PAGE,
            "quiz_question_count": book.quiz_questions.filter(
                is_general_quiz=False
            ).count(),
        },
    )


def _story_quiz_questions(book: Book) -> list[QuizQuestion]:
    return list(
        book.quiz_questions.filter(is_general_quiz=False).order_by(
            "order", "pk"
        )[:8]
    )


def _general_quiz_questions() -> list[QuizQuestion]:
    return list(
        QuizQuestion.objects.filter(is_general_quiz=True).order_by(
            "order", "pk"
        )[:10]
    )


def _quiz_answers(request: HttpRequest, questions: list[QuizQuestion]) -> dict:
    answers = {}
    for question in questions:
        raw = request.POST.get(f"question_{question.pk}")
        if raw not in (None, ""):
            answers[question.pk] = raw
    return answers


def _record_quiz(
    request: HttpRequest,
    questions: list[QuizQuestion],
    *,
    book: Book | None,
    is_general_quiz: bool,
) -> QuizResult:
    graded = grade_quiz(questions, _quiz_answers(request, questions))
    result = QuizResult.objects.create(
        child=request.user,
        book=book,
        is_general_quiz=is_general_quiz,
        total_questions=graded["total_questions"],
        correct_answers=graded["correct_answers"],
        score_percentage=graded["score_percentage"],
        review=graded["review"],
    )
    new_awards = evaluate_badges(
        request.user,
        book=book,
        quiz_result=result,
    )
    if new_awards:
        result.awarded_badges.set([award.badge for award in new_awards])
    return result


@child_required
def recap(request: HttpRequest, slug: str) -> HttpResponse:
    """Animated post-reading storyboard that leads into the quiz."""
    book = get_object_or_404(
        Book.objects.prefetch_related("pages"), slug=slug, is_published=True
    )
    progress = ReadingProgress.objects.filter(
        child=request.user, book=book
    ).first()

    if progress is None or not progress.is_completed:
        messages.info(
            request,
            f"Turn the last page of {book.title} to unlock its recap.",
        )
        return redirect("books:reader", slug=book.slug)

    storyboard = build_recap(book)
    new_badges = evaluate_badges(request.user, book=book)
    quiz_count = book.quiz_questions.filter(is_general_quiz=False).count()
    general_count = QuizQuestion.objects.filter(is_general_quiz=True).count()

    return render(
        request,
        "books/recap.html",
        {
            "book": book,
            "progress": progress,
            "storyboard": storyboard,
            "new_badges": new_badges,
            "quiz_count": quiz_count,
            "general_quiz_count": general_count,
            "pages_per_book": BookPage.MAX_PAGE,
        },
    )


@child_required
def quiz(request: HttpRequest, slug: str) -> HttpResponse:
    """Play a story's quiz, with instant client feedback and server grading."""
    book = get_object_or_404(
        Book.objects.prefetch_related("pages"), slug=slug, is_published=True
    )
    progress = ReadingProgress.objects.filter(
        child=request.user, book=book
    ).first()

    if progress is None or not progress.is_completed:
        messages.info(
            request,
            f"Finish {book.title} first, then its quiz will be waiting.",
        )
        return redirect("books:reader", slug=book.slug)

    questions = _story_quiz_questions(book)
    if not questions:
        messages.info(
            request,
            f"The quiz for {book.title} is still being written. Try the recap "
            "and check back soon.",
        )
        return redirect("books:recap", slug=book.slug)

    if request.method == "POST":
        result = _record_quiz(
            request, questions, book=book, is_general_quiz=False
        )
        return redirect("books:quiz_result", pk=result.pk)

    return render(
        request,
        "books/quiz.html",
        {
            "book": book,
            "questions": questions,
            "quiz_mode": "story",
            "quiz_title": f"{book.title} quiz",
            "quiz_kicker": "Book quiz",
            "back_url": reverse_lazy("books:recap", kwargs={"slug": book.slug}),
            "back_label": "Back to recap",
            "general_quiz_count": QuizQuestion.objects.filter(
                is_general_quiz=True
            ).count(),
        },
    )


@child_required
def general_quiz(request: HttpRequest) -> HttpResponse:
    """A platform-wide quiz available to every young reader."""
    questions = _general_quiz_questions()
    if not questions:
        messages.info(
            request,
            "The general quiz is being prepared. Explore a story in the meantime.",
        )
        return redirect("books:child_dashboard")

    if request.method == "POST":
        result = _record_quiz(
            request, questions, book=None, is_general_quiz=True
        )
        return redirect("books:quiz_result", pk=result.pk)

    return render(
        request,
        "books/quiz.html",
        {
            "book": None,
            "questions": questions,
            "quiz_mode": "general",
            "quiz_title": "The WBooks Wonder Quiz",
            "quiz_kicker": "Platform quiz",
            "back_url": reverse_lazy("books:child_dashboard"),
            "back_label": "Back to my shelf",
            "general_quiz_count": len(questions),
        },
    )


@child_required
def quiz_result(request: HttpRequest, pk: int) -> HttpResponse:
    result = get_object_or_404(
        QuizResult.objects.select_related("book").prefetch_related(
            "awarded_badges"
        ),
        pk=pk,
        child=request.user,
    )
    missed = [entry for entry in result.review if not entry["is_correct"]]
    for entry in result.review:
        options = entry.get("options", [])
        selected = entry.get("selected_option")
        correct = entry.get("correct_option")
        entry["selected_text"] = (
            options[selected]
            if isinstance(selected, int) and 0 <= selected < len(options)
            else None
        )
        entry["correct_text"] = (
            options[correct]
            if isinstance(correct, int) and 0 <= correct < len(options)
            else ""
        )
    return render(
        request,
        "books/quiz_result.html",
        {
            "result": result,
            "missed": missed,
            "awarded_badges": list(result.awarded_badges.all()),
            "general_quiz_count": QuizQuestion.objects.filter(
                is_general_quiz=True
            ).count(),
        },
    )



def book_detail(request: HttpRequest, slug: str) -> HttpResponse:
    book = get_object_or_404(
        Book.objects.prefetch_related("pages"), slug=slug, is_published=True
    )
    progress = None
    if request.user.is_authenticated and request.user.is_child:
        progress = ReadingProgress.objects.filter(
            child=request.user, book=book
        ).first()

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect(f"{reverse_lazy('books:login')}?next={request.path}")
        if not request.user.is_child:
            messages.warning(
                request, "Only young reader accounts can save stories to a shelf."
            )
            return redirect("books:book_detail", slug=book.slug)
        progress, created = ReadingProgress.objects.get_or_create(
            child=request.user, book=book
        )
        if created:
            messages.success(
                request, f"{book.title} was added to your reading shelf."
            )
        else:
            messages.info(request, "This story is already on your shelf.")
        return redirect("books:book_detail", slug=book.slug)

    return render(
        request,
        "books/book_detail.html",
        {
            "book": book,
            "progress": progress,
            "pages": book.pages.all(),
            "pages_per_book": BookPage.MAX_PAGE,
            "quiz_question_count": book.quiz_questions.filter(
                is_general_quiz=False
            ).count(),
        },
    )


@login_required
@require_POST
def update_progress(request: HttpRequest, slug: str) -> HttpResponse:
    """Persist a reader's current page (used by the Phase 2 reading engine)."""
    if not request.user.is_child:
        messages.warning(request, "Only young reader accounts track progress.")
        return redirect("books:home")

    book = get_object_or_404(Book, slug=slug, is_published=True)
    progress, _ = ReadingProgress.objects.get_or_create(
        child=request.user, book=book
    )
    try:
        page_number = int(request.POST.get("current_page", progress.current_page))
    except (TypeError, ValueError):
        messages.error(request, "That page number was not valid.")
        return redirect("books:book_detail", slug=book.slug)

    if not 1 <= page_number <= BookPage.MAX_PAGE:
        messages.error(
            request, f"Choose a page between 1 and {BookPage.MAX_PAGE}."
        )
        return redirect("books:book_detail", slug=book.slug)

    progress.current_page = page_number
    progress.is_completed = (
        page_number >= BookPage.MAX_PAGE
        or request.POST.get("is_completed") == "true"
    )
    progress.save()
    messages.success(request, "Your reading progress was saved.")
    return redirect("books:book_detail", slug=book.slug)
