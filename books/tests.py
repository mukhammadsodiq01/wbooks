import json
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .forms import SignUpForm
from .models import (
    Badge,
    Book,
    BookPage,
    ChildBadge,
    ParentChildLink,
    Profile,
    QuizQuestion,
    QuizResult,
    ReadingProgress,
    ReadingSession,
    Theme,
    User,
)
from .themes import reader_theme_for

PASSWORD = "WonderBooks!234"


def make_user(username, email, role, **extra):
    user = User.objects.create_user(
        username=username,
        email=email,
        password=PASSWORD,
        role=role,
        display_name=extra.pop("display_name", username.title()),
        **extra,
    )
    return user


def make_book(title="The Moon Garden"):
    book = Book.objects.create(
        title=title,
        description="A gentle moonlit adventure.",
        age_group=Book.AgeGroup.EARLY,
        theme_default=Theme.CASTLE,
    )
    for number in range(1, BookPage.MAX_PAGE + 1):
        BookPage.objects.create(
            book=book,
            page_number=number,
            content_text=f"Page {number} of the story.",
            animation_type=BookPage.Animation.FADE,
        )
    return book


def make_question(book=None, *, order=1, correct=1, general=False):
    return QuizQuestion.objects.create(
        book=None if general else book,
        question_text=f"Question {order} about the story?",
        options=["Wrong answer", "Right answer", "Another answer", "Last answer"],
        correct_option=correct,
        explanation="Because this is the right detail.",
        is_general_quiz=general,
        order=order,
    )


class UserModelTests(TestCase):
    def test_profile_is_created_for_every_user(self):
        user = make_user("amara", "amara@example.com", User.Role.CHILD)
        self.assertTrue(hasattr(user, "profile"))
        self.assertIsInstance(user.profile, Profile)
        self.assertTrue(user.is_child)

    def test_default_display_name_falls_back_to_username(self):
        user = User.objects.create_user(
            username="kofi", email="kofi@example.com", password=PASSWORD
        )
        self.assertEqual(user.display_name, "kofi")

    def test_parent_child_link_rejects_wrong_roles(self):
        parent = make_user("parent", "parent@example.com", User.Role.PARENT)
        other_parent = make_user("other", "other@example.com", User.Role.PARENT)
        link = ParentChildLink(parent_profile=parent.profile, child=other_parent)
        with self.assertRaises(ValidationError):
            link.full_clean()


class RegistrationTests(TestCase):
    def test_signup_form_creates_child_and_links_parent(self):
        parent = make_user("guardian", "guardian@example.com", User.Role.PARENT)
        form = SignUpForm(
            data={
                "role": User.Role.CHILD,
                "display_name": "Amara",
                "username": "amara",
                "email": "amara@example.com",
                "parent_email": "guardian@example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        child = form.save()
        self.assertTrue(child.is_child)
        self.assertTrue(
            ParentChildLink.objects.filter(
                parent_profile=parent.profile, child=child
            ).exists()
        )

    def test_signup_rejects_unknown_parent_email(self):
        form = SignUpForm(
            data={
                "role": User.Role.CHILD,
                "display_name": "Kofi",
                "username": "kofi",
                "email": "kofi@example.com",
                "parent_email": "missing@example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("parent_email", form.errors)

    def test_register_view_logs_user_in(self):
        response = self.client.post(
            reverse("books:register"),
            {
                "role": User.Role.CHILD,
                "display_name": "Nia",
                "username": "nia",
                "email": "nia@example.com",
                "parent_email": "",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertRedirects(
            response, reverse("books:dashboard"), fetch_redirect_response=False
        )
        self.assertTrue(User.objects.filter(username="nia").exists())
        self.assertEqual(int(self.client.session["_auth_user_id"]), User.objects.get(username="nia").pk)

    def test_login_redirects_to_dashboard(self):
        make_user("reader", "reader@example.com", User.Role.CHILD)
        response = self.client.post(
            reverse("books:login"),
            {"username": "reader", "password": PASSWORD},
        )
        self.assertRedirects(
            response, reverse("books:dashboard"), fetch_redirect_response=False
        )


class BookModelTests(TestCase):
    def test_page_number_is_limited_to_eight(self):
        book = make_book()
        page = BookPage(
            book=book,
            page_number=9,
            content_text="Too many pages.",
            animation_type=BookPage.Animation.FADE,
        )
        with self.assertRaises(ValidationError):
            page.full_clean()

    def test_reading_progress_percentage_and_completion(self):
        book = make_book()
        child = make_user("reader", "reader@example.com", User.Role.CHILD)
        progress = ReadingProgress.objects.create(
            child=child, book=book, current_page=4
        )
        self.assertEqual(progress.percentage, 50)
        progress.mark_completed()
        progress.refresh_from_db()
        self.assertTrue(progress.is_completed)
        self.assertEqual(progress.current_page, BookPage.MAX_PAGE)
        self.assertEqual(progress.percentage, 100)


class DashboardAccessTests(TestCase):
    def setUp(self):
        self.parent = make_user("guardian", "guardian@example.com", User.Role.PARENT)
        self.child = make_user("reader", "reader@example.com", User.Role.CHILD)

    def test_child_cannot_open_parent_dashboard(self):
        self.client.force_login(self.child)
        response = self.client.get(reverse("books:parent_dashboard"))
        self.assertRedirects(
            response, reverse("books:dashboard"), fetch_redirect_response=False
        )

    def test_parent_can_link_a_child_by_email(self):
        self.client.force_login(self.parent)
        response = self.client.post(
            reverse("books:parent_dashboard"),
            {"child_email": "reader@example.com"},
        )
        self.assertRedirects(
            response,
            reverse("books:parent_dashboard"),
            fetch_redirect_response=False,
        )
        self.assertTrue(
            ParentChildLink.objects.filter(
                parent_profile=self.parent.profile, child=self.child
            ).exists()
        )

    def test_parent_cannot_link_the_same_child_twice(self):
        ParentChildLink.objects.create(
            parent_profile=self.parent.profile, child=self.child
        )
        self.client.force_login(self.parent)
        response = self.client.post(
            reverse("books:parent_dashboard"),
            {"child_email": "reader@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already linked")


class ReadingFlowTests(TestCase):
    def setUp(self):
        self.child = make_user("reader", "reader@example.com", User.Role.CHILD)
        self.book = make_book()
        self.client.force_login(self.child)

    def test_child_can_add_book_to_shelf(self):
        response = self.client.post(self.book.get_absolute_url())
        self.assertRedirects(
            response, self.book.get_absolute_url(), fetch_redirect_response=False
        )
        self.assertTrue(
            ReadingProgress.objects.filter(
                child=self.child, book=self.book
            ).exists()
        )

    def test_child_can_update_reading_page(self):
        ReadingProgress.objects.create(child=self.child, book=self.book)
        response = self.client.post(
            reverse("books:update_progress", kwargs={"slug": self.book.slug}),
            {"current_page": "5"},
        )
        self.assertRedirects(
            response, self.book.get_absolute_url(), fetch_redirect_response=False
        )
        progress = ReadingProgress.objects.get(child=self.child, book=self.book)
        self.assertEqual(progress.current_page, 5)
        self.assertFalse(progress.is_completed)

    def test_invalid_page_number_is_rejected(self):
        ReadingProgress.objects.create(child=self.child, book=self.book)
        response = self.client.post(
            reverse("books:update_progress", kwargs={"slug": self.book.slug}),
            {"current_page": "99"},
        )
        self.assertRedirects(
            response, self.book.get_absolute_url(), fetch_redirect_response=False
        )
        progress = ReadingProgress.objects.get(child=self.child, book=self.book)
        self.assertEqual(progress.current_page, 1)

    def test_home_page_renders_library(self):
        response = self.client.get(reverse("books:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.book.title)


class AdminSmokeTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password=PASSWORD,
            display_name="Admin",
        )
        self.client.force_login(self.admin_user)

    def test_admin_changelists_render(self):
        for url_name in (
            "admin:books_user_changelist",
            "admin:books_profile_changelist",
            "admin:books_book_changelist",
            "admin:books_bookpage_changelist",
            "admin:books_readingprogress_changelist",
            "admin:books_parentchildlink_changelist",
            "admin:books_quizquestion_changelist",
            "admin:books_quizresult_changelist",
            "admin:books_badge_changelist",
            "admin:books_childbadge_changelist",
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)

    def test_admin_add_book_page_renders(self):
        for url_name in (
            "admin:books_book_add",
            "admin:books_bookpage_add",
            "admin:books_user_add",
            "admin:books_profile_add",
            "admin:books_readingprogress_add",
            "admin:books_parentchildlink_add",
            "admin:books_quizquestion_add",
            "admin:books_quizresult_add",
            "admin:books_badge_add",
            "admin:books_childbadge_add",
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)


class ReaderViewTests(TestCase):
    def setUp(self):
        self.child = make_user("reader", "reader@example.com", User.Role.CHILD)
        self.parent = make_user("guardian", "guardian@example.com", User.Role.PARENT)
        self.book = make_book()
        self.reader_url = reverse(
            "books:reader", kwargs={"slug": self.book.slug}
        )

    def test_reader_renders_pages_and_restores_progress(self):
        ReadingProgress.objects.create(
            child=self.child, book=self.book, current_page=3
        )
        self.client.force_login(self.child)
        response = self.client.get(self.reader_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.book.title)
        self.assertContains(response, 'data-initial-page="3"')
        self.assertContains(response, 'data-reader-theme="classic"')
        self.assertContains(response, "Page 3 of the story.")
        self.assertEqual(response.context["initial_page"], 3)

    def test_reader_creates_progress_for_a_new_story(self):
        self.client.force_login(self.child)
        response = self.client.get(self.reader_url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            ReadingProgress.objects.filter(
                child=self.child, book=self.book
            ).exists()
        )

    def test_restart_query_rewinds_progress(self):
        ReadingProgress.objects.create(
            child=self.child,
            book=self.book,
            current_page=8,
            is_completed=True,
        )
        self.client.force_login(self.child)
        response = self.client.get(self.reader_url + "?restart=1")

        self.assertEqual(response.status_code, 200)
        progress = ReadingProgress.objects.get(child=self.child, book=self.book)
        self.assertEqual(progress.current_page, 1)
        self.assertFalse(progress.is_completed)

    def test_parent_is_redirected_away_from_reader(self):
        self.client.force_login(self.parent)
        response = self.client.get(self.reader_url)
        self.assertRedirects(
            response, reverse("books:dashboard"), fetch_redirect_response=False
        )

    def test_anonymous_visitor_is_sent_to_login(self):
        response = self.client.get(self.reader_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("books:login"), response["Location"])


class ProgressAPITests(TestCase):
    def setUp(self):
        self.child = make_user("reader", "reader@example.com", User.Role.CHILD)
        self.parent = make_user("guardian", "guardian@example.com", User.Role.PARENT)
        self.book = make_book()
        self.api_url = reverse("books:api_progress")

    def post_progress(self, payload):
        return self.client.post(
            self.api_url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_child_can_save_current_page(self):
        self.client.force_login(self.child)
        response = self.post_progress(
            {"book": self.book.slug, "current_page": 4}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current_page"], 4)
        self.assertFalse(response.json()["is_completed"])
        progress = ReadingProgress.objects.get(child=self.child, book=self.book)
        self.assertEqual(progress.current_page, 4)

    def test_last_page_marks_the_story_complete(self):
        self.client.force_login(self.child)
        response = self.post_progress(
            {"book": self.book.slug, "current_page": BookPage.MAX_PAGE}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_completed"])
        self.assertEqual(response.json()["percentage"], 100)

    def test_get_restores_saved_position(self):
        ReadingProgress.objects.create(
            child=self.child, book=self.book, current_page=6
        )
        self.client.force_login(self.child)
        response = self.client.get(self.api_url, {"book": self.book.slug})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current_page"], 6)
        self.assertTrue(response.json()["has_progress"])

    def test_invalid_page_returns_a_validation_error(self):
        self.client.force_login(self.child)
        response = self.post_progress(
            {"book": self.book.slug, "current_page": 99}
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            ReadingProgress.objects.filter(
                child=self.child, book=self.book
            ).exists()
        )

    def test_progress_requires_a_book(self):
        self.client.force_login(self.child)
        response = self.post_progress({"current_page": 2})
        self.assertEqual(response.status_code, 400)

    def test_unknown_book_returns_not_found(self):
        self.client.force_login(self.child)
        response = self.post_progress(
            {"book": "not-a-real-story", "current_page": 2}
        )
        self.assertEqual(response.status_code, 404)

    def test_parent_cannot_write_child_progress(self):
        self.client.force_login(self.parent)
        response = self.post_progress(
            {"book": self.book.slug, "current_page": 2}
        )
        self.assertEqual(response.status_code, 403)


class QuizAndBadgeModelTests(TestCase):
    def setUp(self):
        self.child = make_user("reader", "reader@example.com", User.Role.CHILD)
        self.book = make_book()

    def test_general_question_cannot_belong_to_a_book(self):
        question = QuizQuestion(
            book=self.book,
            question_text="Which answer?",
            options=["One", "Two"],
            correct_option=0,
            is_general_quiz=True,
        )
        with self.assertRaises(ValidationError):
            question.full_clean()

    def test_story_question_requires_a_book(self):
        question = QuizQuestion(
            question_text="Which answer?",
            options=["One", "Two"],
            correct_option=0,
            is_general_quiz=False,
        )
        with self.assertRaises(ValidationError):
            question.full_clean()

    def test_options_must_be_a_short_non_empty_list(self):
        question = QuizQuestion(
            book=self.book,
            question_text="Which answer?",
            options=["Only one"],
            correct_option=0,
        )
        with self.assertRaises(ValidationError):
            question.full_clean()

        question.options = ["One", "", "Two"]
        with self.assertRaises(ValidationError):
            question.full_clean()

    def test_correct_option_must_point_at_an_answer(self):
        question = QuizQuestion(
            book=self.book,
            question_text="Which answer?",
            options=["One", "Two"],
            correct_option=4,
        )
        with self.assertRaises(ValidationError):
            question.full_clean()

    def test_quiz_result_cannot_have_more_correct_than_total(self):
        result = QuizResult(
            child=self.child,
            book=self.book,
            total_questions=3,
            correct_answers=4,
            score_percentage=100,
        )
        with self.assertRaises(ValidationError):
            result.full_clean()

    def test_badge_is_awarded_once_per_child(self):
        badge = Badge.objects.create(
            slug="test-badge",
            name="Test Badge",
            description="A test achievement.",
            criteria=Badge.Criteria.FIRST_BOOK,
        )
        ChildBadge.objects.create(child=self.child, badge=badge)
        duplicate = ChildBadge(child=self.child, badge=badge)
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_theme_badge_requires_a_theme(self):
        badge = Badge(
            slug="test-explorer",
            name="Test Explorer",
            description="Looks at a theme.",
            criteria=Badge.Criteria.THEME_EXPLORER,
        )
        with self.assertRaises(ValidationError):
            badge.full_clean()


class PostReadingFlowTests(TestCase):
    def setUp(self):
        self.child = make_user("reader", "reader@example.com", User.Role.CHILD)
        self.other_child = make_user(
            "other", "other@example.com", User.Role.CHILD
        )
        self.parent = make_user(
            "guardian", "guardian@example.com", User.Role.PARENT
        )
        self.book = make_book()
        self.book.key_lessons = [
            "A true song can plant something beautiful.",
            "Courage begins with one small step.",
            "Helping others brightens the sky.",
        ]
        self.book.story_moral = "Every kind act plants a little light somewhere."
        self.book.save()
        ReadingProgress.objects.create(
            child=self.child,
            book=self.book,
            current_page=BookPage.MAX_PAGE,
            is_completed=True,
        )
        self.question_one = make_question(self.book, order=1, correct=1)
        self.question_two = make_question(self.book, order=2, correct=2)
        self.general_question = make_question(
            general=True, order=1, correct=0
        )

        self.first_book_badge = Badge.objects.update_or_create(
            slug="first-book",
            defaults={
                "name": "First Book",
                "description": "Finish your first story.",
                "criteria": Badge.Criteria.FIRST_BOOK,
                "threshold": 1,
                "order": 1,
            },
        )[0]
        self.storyteller_badge = Badge.objects.update_or_create(
            slug="classic-storyteller",
            defaults={
                "name": "Classic Storyteller",
                "description": "Finish a castle story.",
                "criteria": Badge.Criteria.THEME_EXPLORER,
                "theme_key": "classic",
                "threshold": 1,
                "order": 2,
            },
        )[0]
        self.first_quiz_badge = Badge.objects.update_or_create(
            slug="first-quiz",
            defaults={
                "name": "First Quiz",
                "description": "Complete your first quiz.",
                "criteria": Badge.Criteria.FIRST_QUIZ,
                "threshold": 1,
                "order": 3,
            },
        )[0]
        self.quiz_master_badge = Badge.objects.update_or_create(
            slug="quiz-master",
            defaults={
                "name": "Quiz Master",
                "description": "Score 100% on a quiz.",
                "criteria": Badge.Criteria.QUIZ_MASTER,
                "threshold": 1,
                "order": 4,
            },
        )[0]

        self.recap_url = reverse("books:recap", kwargs={"slug": self.book.slug})
        self.quiz_url = reverse("books:quiz", kwargs={"slug": self.book.slug})
        self.general_url = reverse("books:general_quiz")

    def answer_all_correctly(self):
        return self.client.post(
            self.quiz_url,
            {
                f"question_{self.question_one.pk}": "1",
                f"question_{self.question_two.pk}": "2",
            },
        )

    def test_recap_is_locked_until_the_story_is_finished(self):
        ReadingProgress.objects.filter(
            child=self.child, book=self.book
        ).update(is_completed=False, current_page=4)
        self.client.force_login(self.child)
        response = self.client.get(self.recap_url)
        self.assertRedirects(
            response,
            reverse("books:reader", kwargs={"slug": self.book.slug}),
            fetch_redirect_response=False,
        )

    def test_recap_renders_storyboard_and_lessons(self):
        self.client.force_login(self.child)
        response = self.client.get(self.recap_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The story in scenes")
        self.assertContains(response, "A true song can plant something beautiful.")
        self.assertContains(response, "Every kind act plants a little light somewhere.")
        self.assertGreaterEqual(len(response.context["storyboard"]["beats"]), 2)
        self.assertContains(response, "Play the storyboard")

    def test_recap_awards_first_book_and_theme_badges(self):
        self.client.force_login(self.child)
        self.client.get(self.recap_url)

        awarded = set(
            ChildBadge.objects.filter(child=self.child).values_list(
                "badge__slug", flat=True
            )
        )
        self.assertIn(self.first_book_badge.slug, awarded)
        self.assertIn(self.storyteller_badge.slug, awarded)

    def test_reader_endnote_links_to_the_recap(self):
        self.client.force_login(self.child)
        response = self.client.get(
            reverse("books:reader", kwargs={"slug": self.book.slug})
        )
        self.assertContains(response, self.recap_url)

    def test_quiz_requires_a_finished_story(self):
        ReadingProgress.objects.filter(
            child=self.child, book=self.book
        ).update(is_completed=False, current_page=7)
        self.client.force_login(self.child)
        response = self.client.get(self.quiz_url)
        self.assertRedirects(
            response,
            reverse("books:reader", kwargs={"slug": self.book.slug}),
            fetch_redirect_response=False,
        )

    def test_quiz_renders_every_question(self):
        self.client.force_login(self.child)
        response = self.client.get(self.quiz_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.question_one.question_text)
        self.assertContains(response, self.question_two.question_text)
        self.assertContains(response, "data-quiz-form")

    def test_perfect_quiz_creates_result_and_unlocks_badges(self):
        self.client.force_login(self.child)
        response = self.answer_all_correctly()

        result = QuizResult.objects.get(child=self.child)
        self.assertRedirects(
            response,
            reverse("books:quiz_result", kwargs={"pk": result.pk}),
            fetch_redirect_response=False,
        )
        self.assertEqual(result.score_percentage, 100)
        self.assertEqual(result.correct_answers, 2)
        self.assertTrue(result.is_passed)
        self.assertFalse(result.is_general_quiz)
        self.assertEqual(result.book, self.book)
        self.assertEqual(len(result.review), 2)

        awarded = set(
            result.awarded_badges.values_list("slug", flat=True)
        )
        self.assertIn(self.quiz_master_badge.slug, awarded)
        self.assertIn(self.first_quiz_badge.slug, awarded)

        page = self.client.get(
            reverse("books:quiz_result", kwargs={"pk": result.pk})
        )
        self.assertContains(page, "Perfect score")
        self.assertContains(page, "Quiz Master")
        self.assertContains(page, "Your answer")

    def test_wrong_quiz_answers_are_graded_without_quiz_master(self):
        self.client.force_login(self.child)
        self.client.post(
            self.quiz_url,
            {
                f"question_{self.question_one.pk}": "0",
                f"question_{self.question_two.pk}": "0",
            },
        )

        result = QuizResult.objects.get(child=self.child)
        self.assertEqual(result.score_percentage, 0)
        self.assertFalse(result.is_passed)
        awarded = set(result.awarded_badges.values_list("slug", flat=True))
        self.assertIn(self.first_quiz_badge.slug, awarded)
        self.assertNotIn(self.quiz_master_badge.slug, awarded)

    def test_quiz_result_is_private_to_the_reader(self):
        self.client.force_login(self.child)
        self.answer_all_correctly()
        result = QuizResult.objects.get(child=self.child)

        self.client.force_login(self.other_child)
        response = self.client.get(
            reverse("books:quiz_result", kwargs={"pk": result.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_general_quiz_is_available_without_reading_a_story(self):
        self.client.force_login(self.other_child)
        response = self.client.post(
            self.general_url,
            {f"question_{self.general_question.pk}": "0"},
        )

        result = QuizResult.objects.get(child=self.other_child)
        self.assertRedirects(
            response,
            reverse("books:quiz_result", kwargs={"pk": result.pk}),
            fetch_redirect_response=False,
        )
        self.assertTrue(result.is_general_quiz)
        self.assertIsNone(result.book)
        self.assertEqual(result.score_percentage, 100)

        page = self.client.get(
            reverse("books:quiz_result", kwargs={"pk": result.pk})
        )
        self.assertContains(page, "Wonder Quiz")

    def test_parent_cannot_open_the_post_reading_flow(self):
        self.client.force_login(self.parent)
        for url in (self.recap_url, self.quiz_url, self.general_url):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    reverse("books:dashboard"),
                    fetch_redirect_response=False,
                )

    def test_child_dashboard_shows_the_badge_shelf(self):
        self.client.force_login(self.child)
        response = self.client.get(reverse("books:child_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My badge shelf")
        self.assertContains(response, "First Book")
        self.assertContains(response, self.recap_url)

    def test_completed_book_detail_links_to_the_post_reading_flow(self):
        self.client.force_login(self.child)
        response = self.client.get(self.book.get_absolute_url())
        self.assertContains(response, self.recap_url)
        self.assertContains(response, self.quiz_url)


class SeedDemoTests(TestCase):
    def test_seed_demo_is_complete_and_idempotent(self):
        output = StringIO()
        call_command("seed_demo", stdout=output)
        call_command("seed_demo", stdout=StringIO())

        self.assertEqual(Book.objects.count(), 3)
        self.assertEqual(BookPage.objects.count(), 24)
        self.assertEqual(QuizQuestion.objects.count(), 17)
        self.assertEqual(QuizQuestion.objects.filter(is_general_quiz=True).count(), 5)
        self.assertEqual(Badge.objects.count(), 8)
        self.assertEqual(User.objects.filter(role=User.Role.CHILD).count(), 2)
        self.assertIn("17 quiz questions", output.getvalue())


class SeedWbooksTests(TestCase):
    def setUp(self):
        call_command("seed_wbooks", stdout=StringIO())

    def test_seeds_a_guardian_and_two_readers(self):
        parent = User.objects.get(username="demo_parent")
        self.assertTrue(parent.is_parent)
        self.assertEqual(parent.email, "parent@wbooks.app")
        self.assertTrue(parent.check_password("WBooks!234"))
        self.assertEqual(parent.profile.children.count(), 2)

        children = User.objects.filter(role=User.Role.CHILD)
        self.assertEqual(children.count(), 2)
        for child in children:
            self.assertTrue(child.check_password("WBooks!234"))
            self.assertTrue(
                ParentChildLink.objects.filter(child=child).exists()
            )

    def test_seeds_three_stories_with_exactly_eight_pages(self):
        books = Book.objects.all()
        self.assertEqual(books.count(), 3)
        for book in books:
            with self.subTest(book=book.title):
                self.assertEqual(book.pages.count(), BookPage.MAX_PAGE)
                self.assertEqual(book.page_count, 8)
                self.assertEqual(
                    sorted(page.page_number for page in book.pages.all()),
                    list(range(1, 9)),
                )
                self.assertTrue(book.story_moral)
                self.assertEqual(len(book.key_lessons), 3)
                for page in book.pages.all():
                    self.assertGreater(len(page.content_text), 80)

    def test_stories_cover_the_forest_ice_and_holo_atmospheres(self):
        themes = {
            reader_theme_for(book.theme_default)
            for book in Book.objects.all()
        }
        self.assertEqual(themes, {"forest", "ice", "holo"})

    def test_seeds_quizzes_and_badges(self):
        for book in Book.objects.all():
            count = book.quiz_questions.filter(is_general_quiz=False).count()
            with self.subTest(book=book.title):
                self.assertGreaterEqual(count, 3)
                self.assertLessEqual(count, 5)
                for question in book.quiz_questions.all():
                    self.assertGreaterEqual(len(question.options), 2)
                    self.assertTrue(question.explanation)
                    self.assertLess(question.correct_option, len(question.options))

        self.assertEqual(
            QuizQuestion.objects.filter(is_general_quiz=True).count(), 5
        )
        self.assertEqual(Badge.objects.count(), 8)
        self.assertTrue(
            Badge.objects.filter(criteria=Badge.Criteria.QUIZ_MASTER).exists()
        )

    def test_seeds_reading_history_quiz_results_and_badges(self):
        child = User.objects.get(username="demo_kofi")
        self.assertTrue(
            ReadingProgress.objects.filter(
                child=child, is_completed=True
            ).exists()
        )
        self.assertTrue(QuizResult.objects.filter(child=child).exists())
        self.assertTrue(ChildBadge.objects.filter(child=child).exists())
        self.assertTrue(
            ReadingSession.objects.filter(child=child).exists()
        )

    def test_command_is_idempotent(self):
        call_command("seed_wbooks", stdout=StringIO())

        self.assertEqual(Book.objects.count(), 3)
        self.assertEqual(BookPage.objects.count(), 24)
        self.assertEqual(QuizQuestion.objects.count(), 17)
        self.assertEqual(Badge.objects.count(), 8)
        self.assertEqual(User.objects.filter(role=User.Role.CHILD).count(), 2)
        self.assertEqual(QuizResult.objects.count(), 3)
        self.assertEqual(ReadingProgress.objects.count(), 4)


class ParentDashboardTests(TestCase):
    def setUp(self):
        self.parent = make_user(
            "guardian", "guardian@example.com", User.Role.PARENT
        )
        self.child = make_user(
            "reader", "reader@example.com", User.Role.CHILD
        )
        self.other_child = make_user(
            "outsider", "outsider@example.com", User.Role.CHILD
        )
        ParentChildLink.objects.create(
            parent_profile=self.parent.profile, child=self.child
        )
        self.book = make_book("The Bramblewood Lantern")
        self.finished_book = make_book("The Glacier Light")
        self.url = reverse("books:parent_dashboard")

        ReadingProgress.objects.create(
            child=self.child,
            book=self.book,
            current_page=5,
            reading_seconds=25 * 60,
        )
        ReadingProgress.objects.create(
            child=self.child,
            book=self.finished_book,
            current_page=BookPage.MAX_PAGE,
            is_completed=True,
            reading_seconds=40 * 60,
        )
        ReadingSession.objects.create(
            child=self.child, book=self.book, seconds=15 * 60
        )

        question = make_question(self.finished_book, order=1, correct=1)
        QuizResult.objects.create(
            child=self.child,
            book=self.finished_book,
            total_questions=4,
            correct_answers=3,
            score_percentage=75,
            review=[],
        )
        QuizResult.objects.create(
            child=self.child,
            book=None,
            is_general_quiz=True,
            total_questions=5,
            correct_answers=5,
            score_percentage=100,
            review=[],
        )
        self.question = question

        badge, _ = Badge.objects.update_or_create(
            slug="first-book",
            defaults={
                "name": "First Book",
                "description": "Finish a story.",
                "criteria": Badge.Criteria.FIRST_BOOK,
                "threshold": 1,
            },
        )
        ChildBadge.objects.create(child=self.child, badge=badge)

    def test_dashboard_shows_progress_pages_and_completed_books(self):
        self.client.force_login(self.parent)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 5 of 8")
        self.assertContains(response, "Finished")
        self.assertContains(response, self.book.title)
        self.assertContains(response, self.finished_book.title)

    def test_dashboard_shows_quiz_scores(self):
        self.client.force_login(self.parent)
        response = self.client.get(self.url)

        self.assertContains(response, "75%")
        self.assertContains(response, "100%")
        self.assertContains(response, "Quiz average")

    def test_dashboard_shows_time_spent(self):
        self.client.force_login(self.parent)
        response = self.client.get(self.url)

        self.assertContains(response, "time spent")
        self.assertContains(response, "1h 5m")
        self.assertEqual(response.context["family"]["reading_minutes"], 65)
        self.assertEqual(len(response.context["weekly_chart"]), 7)

    def test_dashboard_shows_earned_badges(self):
        self.client.force_login(self.parent)
        response = self.client.get(self.url)

        self.assertContains(response, "First Book")
        self.assertContains(response, "Badges your family is chasing")
        self.assertEqual(response.context["family"]["badge_count"], 1)

    def test_dashboard_only_covers_linked_readers(self):
        self.client.force_login(self.parent)
        response = self.client.get(self.url)

        self.assertNotContains(response, "outsider@example.com")
        self.assertEqual(response.context["children_count"], 1)

    def test_family_totals_are_reported(self):
        self.client.force_login(self.parent)
        response = self.client.get(self.url)

        family = response.context["family"]
        self.assertEqual(family["books_started"], 2)
        self.assertEqual(family["books_completed"], 1)
        self.assertEqual(family["pages_read"], 13)
        self.assertEqual(family["quizzes_taken"], 2)
        self.assertEqual(family["average_score"], 88)

    def test_reading_time_is_logged_by_the_progress_api(self):
        api_url = reverse("books:api_progress")
        self.client.force_login(self.child)
        response = self.client.post(
            api_url,
            data=json.dumps(
                {"book": self.book.slug, "current_page": 6, "seconds": 90}
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        progress = ReadingProgress.objects.get(
            child=self.child, book=self.book
        )
        self.assertEqual(progress.current_page, 6)
        self.assertEqual(progress.reading_seconds, 25 * 60 + 90)
        self.assertEqual(progress.reading_minutes, 26)
        self.assertTrue(
            ReadingSession.objects.filter(child=self.child, seconds=90).exists()
        )

    def test_negative_reading_time_is_rejected(self):
        api_url = reverse("books:api_progress")
        self.client.force_login(self.child)
        response = self.client.post(
            api_url,
            data=json.dumps(
                {"book": self.book.slug, "current_page": 2, "seconds": -50}
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

