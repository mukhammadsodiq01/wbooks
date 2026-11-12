from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

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
    User,
)


@admin.register(User)
class WBooksUserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "display_name",
        "email",
        "role",
        "is_staff",
        "date_joined",
    )
    list_filter = BaseUserAdmin.list_filter + ("role",)
    search_fields = ("username", "display_name", "email")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("WBooks account", {"fields": ("role", "display_name")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "WBooks account",
            {
                "classes": ("wide",),
                "fields": ("role", "display_name", "email"),
            },
        ),
    )


class ChildLinkInline(admin.TabularInline):
    model = ParentChildLink
    fk_name = "parent_profile"
    extra = 0
    autocomplete_fields = ("child",)
    verbose_name = "linked young reader"
    verbose_name_plural = "linked young readers"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "favorite_theme", "reading_goal_minutes", "updated_at")
    list_filter = ("favorite_theme",)
    search_fields = ("user__username", "user__display_name", "user__email")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ChildLinkInline]
    fields = (
        "user",
        "avatar",
        "bio",
        "birth_date",
        "favorite_theme",
        "reading_goal_minutes",
        "created_at",
        "updated_at",
    )


@admin.register(ParentChildLink)
class ParentChildLinkAdmin(admin.ModelAdmin):
    list_display = ("parent_profile", "child", "created_at")
    search_fields = (
        "parent_profile__user__email",
        "parent_profile__user__display_name",
        "child__email",
        "child__display_name",
    )
    autocomplete_fields = ("parent_profile", "child")


class BookPageInline(admin.StackedInline):
    model = BookPage
    extra = 0
    max_num = BookPage.MAX_PAGE
    fields = (
        "page_number",
        "content_text",
        "illustration_url",
        "animation_type",
    )


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "age_group",
        "theme_default",
        "is_published",
        "order",
        "page_total",
        "created_at",
    )
    list_filter = ("age_group", "theme_default", "is_published")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [BookPageInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("pages")

    @admin.display(description="Pages")
    def page_total(self, obj: Book) -> int:
        return len(obj.pages.all())


@admin.register(BookPage)
class BookPageAdmin(admin.ModelAdmin):
    list_display = ("book", "page_number", "animation_type")
    list_filter = ("animation_type",)
    search_fields = ("book__title", "content_text")
    autocomplete_fields = ("book",)


@admin.register(ReadingProgress)
class ReadingProgressAdmin(admin.ModelAdmin):
    list_display = (
        "child",
        "book",
        "current_page",
        "is_completed",
        "reading_time_label",
        "updated_at",
    )
    list_filter = ("is_completed", "book")
    search_fields = (
        "child__display_name",
        "child__email",
        "book__title",
    )
    autocomplete_fields = ("child", "book")
    readonly_fields = ("started_at", "updated_at", "reading_time_label")

    @admin.display(description="Reading time")
    def reading_time_label(self, obj):
        return obj.reading_time_label


@admin.register(ReadingSession)
class ReadingSessionAdmin(admin.ModelAdmin):
    list_display = (
        "child",
        "book",
        "seconds",
        "current_page",
        "started_at",
    )
    list_filter = ("book",)
    search_fields = (
        "child__display_name",
        "child__email",
        "book__title",
    )
    autocomplete_fields = ("child", "book")
    readonly_fields = ("started_at",)


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "question_text",
        "book",
        "is_general_quiz",
        "correct_option",
        "order",
    )
    list_filter = ("is_general_quiz", "book")
    search_fields = ("question_text", "book__title")
    autocomplete_fields = ("book",)
    fields = (
        "book",
        "is_general_quiz",
        "question_text",
        "options",
        "correct_option",
        "explanation",
        "order",
    )


@admin.register(QuizResult)
class QuizResultAdmin(admin.ModelAdmin):
    list_display = (
        "child",
        "book",
        "score_percentage",
        "correct_answers",
        "total_questions",
        "is_general_quiz",
        "created_at",
    )
    list_filter = ("is_general_quiz", "book", "score_percentage")
    search_fields = ("child__display_name", "child__email", "book__title")
    autocomplete_fields = ("child", "book")
    filter_horizontal = ("awarded_badges",)
    readonly_fields = ("created_at",)


class ChildBadgeInline(admin.TabularInline):
    model = ChildBadge
    extra = 0
    autocomplete_fields = ("child",)
    readonly_fields = ("awarded_at",)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "criteria",
        "theme_key",
        "threshold",
        "order",
        "is_active",
    )
    list_filter = ("criteria", "theme_key", "is_active")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ChildBadgeInline]
    fields = (
        "slug",
        "name",
        "description",
        "icon",
        "criteria",
        "threshold",
        "theme_key",
        "order",
        "is_active",
    )


@admin.register(ChildBadge)
class ChildBadgeAdmin(admin.ModelAdmin):
    list_display = ("child", "badge", "note", "awarded_at")
    list_filter = ("badge",)
    search_fields = (
        "child__display_name",
        "child__email",
        "badge__name",
        "note",
    )
    autocomplete_fields = ("child", "badge")
    readonly_fields = ("awarded_at",)

