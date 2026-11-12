"""Domain models for WBooks: readers, stories, pages and reading progress."""
from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils.text import slugify


class Theme(models.TextChoices):
    FOREST = "forest", "Enchanted Forest"
    OCEAN = "ocean", "Deep Ocean"
    SPACE = "space", "Outer Space"
    CASTLE = "castle", "Storybook Castle"
    SAFARI = "safari", "Wild Safari"
    CANDY = "candy", "Candy Kingdom"
    SNOW = "snow", "Frozen Peaks"
    NEON = "neon", "Neon City"


class User(AbstractUser):
    """Single account model for both young readers and their guardians."""

    class Role(models.TextChoices):
        PARENT = "parent", "Parent / Guardian"
        CHILD = "child", "Young Reader"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.CHILD,
        db_index=True,
    )
    display_name = models.CharField(max_length=50, blank=True)
    email = models.EmailField(unique=True)

    REQUIRED_FIELDS = ["email"]

    class Meta:
        ordering = ["-date_joined"]
        verbose_name = "user"
        verbose_name_plural = "users"
        constraints = [
            models.UniqueConstraint(Lower("email"), name="unique_user_email_ci")
        ]

    def __str__(self) -> str:
        return self.display_name or self.get_full_name() or self.username

    @property
    def is_parent(self) -> bool:
        return self.role == self.Role.PARENT

    @property
    def is_child(self) -> bool:
        return self.role == self.Role.CHILD

    @property
    def first_name_only(self) -> str:
        return (self.display_name or self.first_name or self.username).split()[0]

    def save(self, *args, **kwargs):
        if not self.display_name:
            self.display_name = self.first_name or self.username
        super().save(*args, **kwargs)


class Profile(models.Model):
    """Extra details that every WBooks account carries."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    birth_date = models.DateField(blank=True, null=True)
    favorite_theme = models.CharField(
        max_length=20, choices=Theme.choices, default=Theme.FOREST
    )
    reading_goal_minutes = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(5), MaxValueValidator(120)],
        help_text="Daily reading goal in minutes.",
    )
    children = models.ManyToManyField(
        User,
        through="ParentChildLink",
        through_fields=("parent_profile", "child"),
        related_name="guardian_profiles",
        symmetrical=False,
        blank=True,
        limit_choices_to={"role": User.Role.CHILD},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__display_name"]

    def __str__(self) -> str:
        return f"{self.user} · {self.get_favorite_theme_display()}"


class ParentChildLink(models.Model):
    """Links a guardian profile to a young reader account.

    A child has exactly one guardian on WBooks; a guardian may have many
    children.
    """

    parent_profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="child_links",
        limit_choices_to={"user__role": User.Role.PARENT},
    )
    child = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="parent_link",
        limit_choices_to={"role": User.Role.CHILD},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["child__display_name"]

    def __str__(self) -> str:
        return f"{self.parent_profile.user} → {self.child}"

    def clean(self) -> None:
        super().clean()
        if self.parent_profile_id and self.parent_profile.user.role != User.Role.PARENT:
            raise ValidationError(
                {"parent_profile": "The selected profile does not belong to a parent."}
            )
        if self.child_id and self.child.role != User.Role.CHILD:
            raise ValidationError(
                {"child": "Only accounts with the child role can be linked."}
            )
        if (
            self.parent_profile_id
            and self.child_id
            and self.parent_profile.user_id == self.child_id
        ):
            raise ValidationError("A guardian cannot be linked to their own account.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Book(models.Model):
    class AgeGroup(models.TextChoices):
        TODDLER = "3-5", "Ages 3–5"
        EARLY = "6-8", "Ages 6–8"
        MIDDLE = "9-12", "Ages 9–12"
        TEEN = "13+", "Ages 13+"

    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(max_length=1200)
    story_moral = models.CharField(
        max_length=240,
        blank=True,
        help_text="One sentence that captures the story's heart.",
    )
    key_lessons = models.JSONField(
        default=list,
        blank=True,
        help_text="A short list of lessons shown on the recap screen.",
    )
    recap_video_url = models.URLField(
        blank=True,
        help_text="Optional MP4 or web video URL for the recap player.",
    )
    cover_image = models.ImageField(upload_to="book_covers/", blank=True)
    age_group = models.CharField(
        max_length=5, choices=AgeGroup.choices, default=AgeGroup.EARLY, db_index=True
    )
    theme_default = models.CharField(
        max_length=20, choices=Theme.choices, default=Theme.FOREST
    )
    is_published = models.BooleanField(default=True, db_index=True)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "title"]
        indexes = [models.Index(fields=["age_group", "is_published"])]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)[:120] or "story"
            slug, suffix = base_slug, 2
            while Book.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("books:book_detail", kwargs={"slug": self.slug})

    @property
    def page_count(self) -> int:
        prefetched = getattr(self, "_prefetched_objects_cache", {}).get("pages")
        if prefetched is not None:
            return len(prefetched)
        return self.pages.count()


class BookPage(models.Model):
    MAX_PAGE = 8

    class Animation(models.TextChoices):
        NONE = "none", "No animation"
        FADE = "fade", "Gentle fade"
        SLIDE_UP = "slide_up", "Slide up"
        ZOOM_IN = "zoom_in", "Zoom in"
        FLOAT = "float", "Floating"
        SPARKLE = "sparkle", "Sparkle"

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="pages")
    page_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(MAX_PAGE)]
    )
    content_text = models.TextField(max_length=2000)
    illustration_url = models.URLField(blank=True, help_text="Link to the page artwork.")
    animation_type = models.CharField(
        max_length=12, choices=Animation.choices, default=Animation.FADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["page_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["book", "page_number"], name="unique_page_per_book"
            ),
            models.CheckConstraint(
                condition=Q(page_number__gte=1, page_number__lte=8),
                name="page_number_between_1_and_8",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.book.title} · page {self.page_number}"

    def clean(self) -> None:
        super().clean()
        if self.page_number is not None and not 1 <= self.page_number <= self.MAX_PAGE:
            raise ValidationError(
                {"page_number": f"Page numbers must be between 1 and {self.MAX_PAGE}."}
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class ReadingProgress(models.Model):
    child = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reading_progress",
        limit_choices_to={"role": User.Role.CHILD},
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="progress_entries"
    )
    current_page = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(BookPage.MAX_PAGE)],
    )
    is_completed = models.BooleanField(default=False)
    reading_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Seconds spent reading this story so far.",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["child", "book"], name="unique_progress_per_child_book"
            ),
            models.CheckConstraint(
                condition=Q(current_page__gte=1, current_page__lte=BookPage.MAX_PAGE),
                name="progress_page_between_1_and_8",
            ),
        ]
        verbose_name_plural = "reading progress"

    def __str__(self) -> str:
        return f"{self.child} reading {self.book} · page {self.current_page}"

    def clean(self) -> None:
        super().clean()
        if self.child_id and self.child.role != User.Role.CHILD:
            raise ValidationError(
                {"child": "Reading progress can only belong to a child account."}
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def percentage(self) -> int:
        if self.is_completed:
            return 100
        return min(100, round((self.current_page / BookPage.MAX_PAGE) * 100))

    @property
    def reading_minutes(self) -> int:
        """Whole minutes spent with this story."""
        return round(self.reading_seconds / 60)

    @property
    def reading_time_label(self) -> str:
        """A friendly '1h 12m' style label for guardians."""
        minutes = self.reading_minutes
        if minutes < 60:
            return f"{minutes}m"
        hours, remainder = divmod(minutes, 60)
        if remainder:
            return f"{hours}h {remainder}m"
        return f"{hours}h"

    def mark_completed(self, save: bool = True) -> None:
        self.current_page = BookPage.MAX_PAGE
        self.is_completed = True
        if save:
            self.save(update_fields=["current_page", "is_completed", "updated_at"])


class ReadingSession(models.Model):
    """One sitting with a story, used to report real reading time.

    The reader posts the seconds spent since the last save; each request adds
    a session row so guardians can see when their reader is actually reading.
    """

    child = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reading_sessions",
        limit_choices_to={"role": User.Role.CHILD},
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.SET_NULL,
        related_name="reading_sessions",
        blank=True,
        null=True,
    )
    seconds = models.PositiveIntegerField(default=0)
    current_page = models.PositiveSmallIntegerField(default=1)
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["child", "-started_at"])]

    def __str__(self) -> str:
        return f"{self.child} read {self.book or 'a story'} for {self.seconds}s"

    @property
    def minutes(self) -> int:
        return round(self.seconds / 60)

    def clean(self) -> None:
        super().clean()
        if self.child_id and self.child.role != User.Role.CHILD:
            raise ValidationError(
                {"child": "Reading sessions can only belong to a child account."}
            )
        if self.seconds < 0:
            raise ValidationError({"seconds": "Reading time cannot be negative."})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class QuizQuestion(models.Model):
    """A single multiple-choice question for a story or the whole platform.

    General quiz questions have no book (``is_general_quiz=True``); story
    questions always belong to one published book.
    """

    MAX_OPTIONS = 6
    MIN_OPTIONS = 2

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="quiz_questions",
        blank=True,
        null=True,
    )
    question_text = models.CharField(max_length=400)
    options = models.JSONField(
        default=list,
        help_text="Between two and six answer choices, in display order.",
    )
    correct_option = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Zero-based index of the correct choice in options.",
    )
    explanation = models.CharField(
        max_length=400,
        blank=True,
        help_text="A friendly note shown after the reader answers.",
    )
    is_general_quiz = models.BooleanField(default=False, db_index=True)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=Q(correct_option__gte=0, correct_option__lte=5),
                name="quiz_correct_option_between_0_and_5",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_general_quiz=True, book__isnull=True)
                    | Q(is_general_quiz=False, book__isnull=False)
                ),
                name="quiz_question_scope_matches_book",
            ),
        ]
        indexes = [models.Index(fields=["book", "order"])]

    def __str__(self) -> str:
        scope = "General quiz" if self.is_general_quiz else str(self.book)
        return f"{scope} · {self.question_text[:60]}"

    def clean(self) -> None:
        super().clean()
        if self.is_general_quiz and self.book_id:
            raise ValidationError(
                {"book": "General quiz questions cannot belong to a story."}
            )
        if not self.is_general_quiz and not self.book_id:
            raise ValidationError(
                {"book": "Story questions need a book, or mark them as general."}
            )

        if not isinstance(self.options, (list, tuple)):
            raise ValidationError(
                {"options": "Provide a list of answer choices."}
            )

        cleaned_options = [
            str(option).strip() for option in self.options if str(option).strip()
        ]
        if not self.MIN_OPTIONS <= len(cleaned_options) <= self.MAX_OPTIONS:
            raise ValidationError(
                {
                    "options": (
                        f"Provide between {self.MIN_OPTIONS} and "
                        f"{self.MAX_OPTIONS} answer choices."
                    )
                }
            )
        if len(cleaned_options) != len(self.options):
            raise ValidationError(
                {"options": "Answer choices cannot be empty."}
            )

        if not 0 <= int(self.correct_option) < len(cleaned_options):
            raise ValidationError(
                {"correct_option": "Choose one of the available answer choices."}
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def option_items(self) -> list[dict]:
        """Template-friendly list of options with their zero-based index."""
        return [
            {"index": index, "text": option}
            for index, option in enumerate(self.options)
        ]


class QuizResult(models.Model):
    """A child's completed quiz attempt, with a stable review snapshot."""

    PASS_PERCENTAGE = 70

    child = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="quiz_results",
        limit_choices_to={"role": User.Role.CHILD},
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.SET_NULL,
        related_name="quiz_results",
        blank=True,
        null=True,
    )
    is_general_quiz = models.BooleanField(default=False, db_index=True)
    total_questions = models.PositiveSmallIntegerField(default=0)
    correct_answers = models.PositiveSmallIntegerField(default=0)
    score_percentage = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    review = models.JSONField(
        default=list,
        blank=True,
        help_text="Question, choices and answer snapshot for the result screen.",
    )
    awarded_badges = models.ManyToManyField(
        "Badge", blank=True, related_name="unlocked_by_results"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(correct_answers__lte=F("total_questions")),
                name="quiz_correct_not_more_than_total",
            ),
            models.CheckConstraint(
                condition=Q(score_percentage__gte=0, score_percentage__lte=100),
                name="quiz_score_between_0_and_100",
            ),
        ]
        indexes = [models.Index(fields=["child", "-created_at"])]

    def __str__(self) -> str:
        scope = "General quiz" if self.is_general_quiz else str(self.book)
        return f"{self.child} · {scope} · {self.score_percentage}%"

    def clean(self) -> None:
        super().clean()
        if self.child_id and self.child.role != User.Role.CHILD:
            raise ValidationError(
                {"child": "Quiz results can only belong to a child account."}
            )
        if self.correct_answers > self.total_questions:
            raise ValidationError(
                {"correct_answers": "Correct answers cannot exceed the total."}
            )
        if self.is_general_quiz and self.book_id:
            raise ValidationError(
                {"book": "General quiz results cannot point at a story."}
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def is_passed(self) -> bool:
        return self.score_percentage >= self.PASS_PERCENTAGE

    @property
    def incorrect_answers(self) -> int:
        return max(0, self.total_questions - self.correct_answers)


class Badge(models.Model):
    """An achievement a young reader can unlock automatically."""

    class Criteria(models.TextChoices):
        FIRST_BOOK = "first_book", "Finish your first story"
        BOOKWORM = "bookworm", "Finish several stories"
        THEME_EXPLORER = "theme_explorer", "Finish a story in an atmosphere"
        FIRST_QUIZ = "first_quiz", "Complete your first quiz"
        QUIZ_MASTER = "quiz_master", "Score 100% on a quiz"

    THEME_CHOICES = (
        ("forest", "ForestBook"),
        ("ice", "IceBook"),
        ("holo", "HoloBook"),
        ("classic", "ClassicBook"),
    )

    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=240)
    icon = models.CharField(
        max_length=8,
        default="✦",
        help_text="A single emoji or sparkle used on the badge.",
    )
    criteria = models.CharField(max_length=20, choices=Criteria.choices)
    threshold = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    theme_key = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        blank=True,
        help_text="Required for atmosphere explorer badges.",
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["order", "name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(threshold__gte=1),
                name="badge_threshold_at_least_one",
            )
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.criteria == self.Criteria.THEME_EXPLORER and not self.theme_key:
            raise ValidationError(
                {"theme_key": "Choose which reading atmosphere unlocks this badge."}
            )
        if not 1 <= int(self.threshold):
            raise ValidationError(
                {"threshold": "A badge needs a threshold of at least one."}
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class ChildBadge(models.Model):
    """A badge earned by one child, once."""

    child = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="badge_awards",
        limit_choices_to={"role": User.Role.CHILD},
    )
    badge = models.ForeignKey(
        Badge, on_delete=models.CASCADE, related_name="awards"
    )
    note = models.CharField(max_length=160, blank=True)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-awarded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["child", "badge"], name="unique_badge_per_child"
            )
        ]

    def __str__(self) -> str:
        return f"{self.child} earned {self.badge}"

    def clean(self) -> None:
        super().clean()
        if self.child_id and self.child.role != User.Role.CHILD:
            raise ValidationError(
                {"child": "Badges can only be earned by child accounts."}
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

