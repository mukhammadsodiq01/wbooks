"""Seed WBooks with a demo family, three original stories and all rewards.

Usage:
    python manage.py seed_wbooks

The command is idempotent: running it twice leaves the same library, the same
quizzes and the same badges in place.
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from books.achievements import evaluate_badges
from books.models import (
    Badge,
    Book,
    BookPage,
    ChildBadge,
    ParentChildLink,
    QuizQuestion,
    QuizResult,
    ReadingProgress,
    ReadingSession,
    Theme,
    User,
)
from books.quizzes import grade_quiz
from books.seed_data import STORIES

DEMO_PASSWORD = "WBooks!234"

#: Books shipped by the very first demo seed, removed so the library always
#: shows the current three stories.
LEGACY_BOOK_SLUGS = (
    "the-moon-garden",
    "rocket-boots-and-the-red-planet",
    "nia-and-the-whispering-ocean",
)

BADGES = [
    {
        "slug": "first-book",
        "name": "First Book",
        "description": "Finish your very first WBooks story.",
        "icon": "📖",
        "criteria": Badge.Criteria.FIRST_BOOK,
        "threshold": 1,
        "theme_key": "",
        "order": 1,
    },
    {
        "slug": "forest-explorer",
        "name": "Forest Explorer",
        "description": "Finish a story set in the enchanted forest.",
        "icon": "🌿",
        "criteria": Badge.Criteria.THEME_EXPLORER,
        "threshold": 1,
        "theme_key": "forest",
        "order": 2,
    },
    {
        "slug": "ice-voyager",
        "name": "Ice Voyager",
        "description": "Finish a story from the frozen peaks or deep ocean.",
        "icon": "❄️",
        "criteria": Badge.Criteria.THEME_EXPLORER,
        "threshold": 1,
        "theme_key": "ice",
        "order": 3,
    },
    {
        "slug": "holo-navigator",
        "name": "Holo Navigator",
        "description": "Finish a story from space or the neon city.",
        "icon": "🚀",
        "criteria": Badge.Criteria.THEME_EXPLORER,
        "threshold": 1,
        "theme_key": "holo",
        "order": 4,
    },
    {
        "slug": "classic-storyteller",
        "name": "Classic Storyteller",
        "description": "Finish a story from the storybook castle.",
        "icon": "🏰",
        "criteria": Badge.Criteria.THEME_EXPLORER,
        "threshold": 1,
        "theme_key": "classic",
        "order": 5,
    },
    {
        "slug": "first-quiz",
        "name": "First Quiz",
        "description": "Complete your first WBooks quiz.",
        "icon": "🎯",
        "criteria": Badge.Criteria.FIRST_QUIZ,
        "threshold": 1,
        "theme_key": "",
        "order": 6,
    },
    {
        "slug": "quiz-master",
        "name": "Quiz Master",
        "description": "Score a perfect 100% on any quiz.",
        "icon": "🏆",
        "criteria": Badge.Criteria.QUIZ_MASTER,
        "threshold": 1,
        "theme_key": "",
        "order": 7,
    },
    {
        "slug": "bookworm",
        "name": "Bookworm",
        "description": "Finish three stories from the library.",
        "icon": "🐛",
        "criteria": Badge.Criteria.BOOKWORM,
        "threshold": 3,
        "theme_key": "",
        "order": 8,
    },
]

GENERAL_QUIZ = [
    {
        "question_text": "What is a good way to look after a library book?",
        "options": [
            "Fold the corners to save your place",
            "Keep it dry and turn the pages gently",
            "Draw on every page",
            "Leave it outside in the rain",
        ],
        "correct": 1,
        "explanation": "Gentle hands keep stories ready for the next reader.",
    },
    {
        "question_text": "What should you do when you find a word you don't know?",
        "options": [
            "Skip the whole page",
            "Look it up or ask for help",
            "Close the book forever",
            "Guess and never check",
        ],
        "correct": 1,
        "explanation": "Looking a word up turns a puzzle into a new word you own.",
    },
    {
        "question_text": "Which is a kind way to share a story with a friend?",
        "options": [
            "Take turns reading aloud",
            "Read over their shoulder",
            "Hide the book",
            "Tell them to hurry up",
        ],
        "correct": 0,
        "explanation": "Taking turns makes reading feel like a game for everyone.",
    },
    {
        "question_text": "What helps a story come alive in your imagination?",
        "options": [
            "Counting the page numbers",
            "Picturing the setting and the characters",
            "Reading only the last page",
            "Ignoring the pictures",
        ],
        "correct": 1,
        "explanation": "Your imagination is the best illustrator of all.",
    },
    {
        "question_text": "Why is it good to read a little every day?",
        "options": [
            "It builds a steady reading habit",
            "It makes books heavier",
            "It replaces playing outside",
            "It makes stories shorter",
        ],
        "correct": 0,
        "explanation": "Small daily reads grow into big reading superpowers.",
    },
]

#: How the demo readers are set up: minutes read, pages reached and quizzes.
DEMO_READERS = (
    {
        "username": "demo_amara",
        "email": "amara@wbooks.app",
        "display_name": "Amara",
        "favourite_theme": Theme.FOREST,
        "book": 0,
        "current_page": 5,
        "completed": False,
        "reading_minutes": 34,
        "quiz_scores": (),
    },
    {
        "username": "demo_kofi",
        "email": "kofi@wbooks.app",
        "display_name": "Kofi",
        "favourite_theme": Theme.SPACE,
        "book": 1,
        "current_page": BookPage.MAX_PAGE,
        "completed": True,
        "reading_minutes": 48,
        "quiz_scores": ((1, 75),),
    },
)


class Command(BaseCommand):
    help = "Seed WBooks with a demo guardian, two readers, three stories and rewards."

    @transaction.atomic
    def handle(self, *args, **options):
        parent = self._seed_parent()
        children = self._seed_children(parent)
        books = self._seed_stories()
        questions = self._seed_questions(books)
        self._seed_badges()
        self._seed_progress(children, books, questions)
        self._remove_legacy_books()

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded 1 guardian, 2 young readers, 3 stories, "
                f"{QuizQuestion.objects.count()} quiz questions, "
                f"{Badge.objects.count()} badges and demo reading history.\n"
                f"Parent: {parent.email} / {DEMO_PASSWORD}\n"
                "Child:  amara@wbooks.app / " + DEMO_PASSWORD + "\n"
                "Child:  kofi@wbooks.app / " + DEMO_PASSWORD + "\n"
                "Open /dashboard/parent/ as the guardian to see the family report."
            )
        )

    # ------------------------------------------------------------- accounts
    def _seed_parent(self) -> User:
        parent, created = User.objects.get_or_create(
            username="demo_parent",
            defaults={
                "email": "parent@wbooks.app",
                "display_name": "Maya Okafor",
                "role": User.Role.PARENT,
                "first_name": "Maya",
                "last_name": "Okafor",
            },
        )
        if created:
            parent.set_password(DEMO_PASSWORD)
            parent.save()

        profile = parent.profile
        if profile.reading_goal_minutes != 20:
            profile.reading_goal_minutes = 20
            profile.save(update_fields=["reading_goal_minutes", "updated_at"])
        return parent

    def _seed_children(self, parent: User) -> list[User]:
        children = []
        for reader in DEMO_READERS:
            child, created = User.objects.get_or_create(
                username=reader["username"],
                defaults={
                    "email": reader["email"],
                    "display_name": reader["display_name"],
                    "role": User.Role.CHILD,
                    "first_name": reader["display_name"],
                },
            )
            if created:
                child.set_password(DEMO_PASSWORD)
                child.save()

            profile = child.profile
            if profile.favorite_theme != reader["favourite_theme"]:
                profile.favorite_theme = reader["favourite_theme"]
                profile.save(update_fields=["favorite_theme", "updated_at"])

            ParentChildLink.objects.get_or_create(
                parent_profile=parent.profile, child=child
            )
            children.append(child)
        return children

    # --------------------------------------------------------------- stories
    def _seed_stories(self) -> list[Book]:
        books = []
        for order, story in enumerate(STORIES, start=1):
            book = Book.objects.filter(title=story["title"]).first()
            if book is None:
                book = Book(title=story["title"])
            book.description = story["description"]
            book.age_group = story["age_group"]
            book.theme_default = story["theme"]
            book.story_moral = story["story_moral"]
            book.key_lessons = story["key_lessons"]
            book.is_published = True
            book.order = order
            book.save()

            pages = story["pages"]
            if len(pages) != BookPage.MAX_PAGE:
                self.stdout.write(
                    self.style.WARNING(
                        f"{book.title} must have exactly {BookPage.MAX_PAGE} pages."
                    )
                )
                raise ValueError(
                    f"{book.title} has {len(pages)} pages, expected {BookPage.MAX_PAGE}."
                )

            for number, text in enumerate(pages, start=1):
                BookPage.objects.update_or_create(
                    book=book,
                    page_number=number,
                    defaults={
                        "content_text": text,
                        "animation_type": BookPage.Animation.FADE,
                    },
                )
            BookPage.objects.filter(book=book).exclude(
                page_number__in=range(1, BookPage.MAX_PAGE + 1)
            ).delete()

            books.append(book)
        return books

    # --------------------------------------------------------------- quizzes
    def _seed_questions(self, books: list[Book]) -> dict:
        questions: dict = {}
        for book in books:
            story = next(
                item for item in STORIES if item["title"] == book.title
            )
            book_questions = []
            for order, question in enumerate(story["quiz"], start=1):
                quiz_question, _ = QuizQuestion.objects.update_or_create(
                    book=book,
                    order=order,
                    defaults={
                        "question_text": question["question_text"],
                        "options": question["options"],
                        "correct_option": question["correct"],
                        "explanation": question["explanation"],
                        "is_general_quiz": False,
                    },
                )
                book_questions.append(quiz_question)
            book.quiz_questions.filter(is_general_quiz=False).exclude(
                pk__in=[item.pk for item in book_questions]
            ).delete()
            questions[book.title] = book_questions

        general = []
        for order, question in enumerate(GENERAL_QUIZ, start=1):
            quiz_question, _ = QuizQuestion.objects.update_or_create(
                book=None,
                is_general_quiz=True,
                order=order,
                defaults={
                    "question_text": question["question_text"],
                    "options": question["options"],
                    "correct_option": question["correct"],
                    "explanation": question["explanation"],
                },
            )
            general.append(quiz_question)
        QuizQuestion.objects.filter(is_general_quiz=True).exclude(
            pk__in=[item.pk for item in general]
        ).delete()
        questions["__general__"] = general
        return questions

    # --------------------------------------------------------------- badges
    def _seed_badges(self) -> None:
        for badge_data in BADGES:
            Badge.objects.update_or_create(
                slug=badge_data["slug"],
                defaults={
                    "name": badge_data["name"],
                    "description": badge_data["description"],
                    "icon": badge_data["icon"],
                    "criteria": badge_data["criteria"],
                    "threshold": badge_data["threshold"],
                    "theme_key": badge_data["theme_key"],
                    "order": badge_data["order"],
                    "is_active": True,
                },
            )

    # -------------------------------------------------------------- history
    def _seed_progress(
        self,
        children: list[User],
        books: list[Book],
        questions: dict,
    ) -> None:
        general_questions = questions["__general__"]

        for child, reader in zip(children, DEMO_READERS):
            # Re-seeding resets the demo readers' history so the command is
            # idempotent and the guardian report always tells the same story.
            QuizResult.objects.filter(child=child).delete()
            ChildBadge.objects.filter(child=child).delete()
            ReadingSession.objects.filter(child=child).delete()

            book = books[reader["book"]]
            progress, _ = ReadingProgress.objects.update_or_create(
                child=child,
                book=book,
                defaults={
                    "current_page": reader["current_page"],
                    "is_completed": reader["completed"],
                    "reading_seconds": reader["reading_minutes"] * 60,
                },
            )

            self._create_sessions(child, book, reader["reading_minutes"], progress)

            # A second shelf entry so guardians can see an unfinished story.
            spare_book = books[(reader["book"] + 1) % len(books)]
            spare_progress, _ = ReadingProgress.objects.update_or_create(
                child=child,
                book=spare_book,
                defaults={
                    "current_page": 3,
                    "is_completed": False,
                    "reading_seconds": 12 * 60,
                },
            )
            self._create_sessions(
                child, spare_book, 12, spare_progress, spread=False
            )

            for book_index, score in reader["quiz_scores"]:
                self._seed_quiz_result(
                    child,
                    books[book_index],
                    questions[books[book_index].title],
                    score,
                )

            self._seed_quiz_result(
                child, None, general_questions, 100, general=True
            )

            evaluate_badges(child, book=book)

    def _create_sessions(
        self,
        child: User,
        book: Book,
        minutes: int,
        progress: ReadingProgress,
        *,
        spread: bool = True,
    ) -> None:
        """Spread the reading time over the last few days for the weekly chart."""
        now = timezone.now()
        slices = max(1, minutes // 15)
        per_slice = (minutes * 60) // slices
        offsets = (0, 1, 2, 4, 6)
        for index in range(slices):
            session = ReadingSession.objects.create(
                child=child,
                book=book,
                seconds=per_slice,
                current_page=progress.current_page,
            )
            if spread:
                ReadingSession.objects.filter(pk=session.pk).update(
                    started_at=now
                    - timedelta(days=offsets[index % len(offsets)], hours=index)
                )

    def _seed_quiz_result(
        self,
        child: User,
        book: Book | None,
        quiz_questions: list[QuizQuestion],
        score: int,
        *,
        general: bool = False,
    ) -> None:
        """Store a believable past attempt with a stable review snapshot."""
        if not quiz_questions:
            return

        total = len(quiz_questions)
        correct_count = round((score / 100) * total)
        answers = {}
        for index, question in enumerate(quiz_questions):
            if index < correct_count:
                answers[question.pk] = question.correct_option
            else:
                wrong = [
                    option
                    for option in range(len(question.options))
                    if option != question.correct_option
                ]
                answers[question.pk] = wrong[0]

        graded = grade_quiz(quiz_questions, answers)
        result = QuizResult.objects.create(
            child=child,
            book=None if general else book,
            is_general_quiz=general,
            total_questions=graded["total_questions"],
            correct_answers=graded["correct_answers"],
            score_percentage=graded["score_percentage"],
            review=graded["review"],
        )
        new_awards = evaluate_badges(child, book=book, quiz_result=result)
        if new_awards:
            result.awarded_badges.set([award.badge for award in new_awards])

    # -------------------------------------------------------------- cleanup
    def _remove_legacy_books(self) -> None:
        """Remove the very first demo stories so the library stays tidy."""
        stale = Book.objects.filter(slug__in=LEGACY_BOOK_SLUGS)
        if stale.exists():
            titles = ", ".join(stale.values_list("title", flat=True))
            stale.delete()
            self.stdout.write(f"Removed old demo stories: {titles}.")
