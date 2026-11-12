"""Ship the default WBooks achievement set with fresh databases."""
from django.db import migrations

DEFAULT_BADGES = [
    {
        "slug": "first-book",
        "name": "First Book",
        "description": "Finish your very first WBooks story.",
        "icon": "📖",
        "criteria": "first_book",
        "threshold": 1,
        "theme_key": "",
        "order": 1,
    },
    {
        "slug": "forest-explorer",
        "name": "Forest Explorer",
        "description": "Finish a story set in the enchanted forest.",
        "icon": "🌿",
        "criteria": "theme_explorer",
        "threshold": 1,
        "theme_key": "forest",
        "order": 2,
    },
    {
        "slug": "ice-voyager",
        "name": "Ice Voyager",
        "description": "Finish a story from the frozen peaks or deep ocean.",
        "icon": "❄️",
        "criteria": "theme_explorer",
        "threshold": 1,
        "theme_key": "ice",
        "order": 3,
    },
    {
        "slug": "holo-navigator",
        "name": "Holo Navigator",
        "description": "Finish a story from space or the neon city.",
        "icon": "🚀",
        "criteria": "theme_explorer",
        "threshold": 1,
        "theme_key": "holo",
        "order": 4,
    },
    {
        "slug": "classic-storyteller",
        "name": "Classic Storyteller",
        "description": "Finish a story from the storybook castle.",
        "icon": "🏰",
        "criteria": "theme_explorer",
        "threshold": 1,
        "theme_key": "classic",
        "order": 5,
    },
    {
        "slug": "first-quiz",
        "name": "First Quiz",
        "description": "Complete your first WBooks quiz.",
        "icon": "🎯",
        "criteria": "first_quiz",
        "threshold": 1,
        "theme_key": "",
        "order": 6,
    },
    {
        "slug": "quiz-master",
        "name": "Quiz Master",
        "description": "Score a perfect 100% on any quiz.",
        "icon": "🏆",
        "criteria": "quiz_master",
        "threshold": 1,
        "theme_key": "",
        "order": 7,
    },
    {
        "slug": "bookworm",
        "name": "Bookworm",
        "description": "Finish three stories from the library.",
        "icon": "🐛",
        "criteria": "bookworm",
        "threshold": 3,
        "theme_key": "",
        "order": 8,
    },
]


def create_default_badges(apps, schema_editor):
    Badge = apps.get_model("books", "Badge")
    for badge in DEFAULT_BADGES:
        Badge.objects.update_or_create(
            slug=badge["slug"],
            defaults={key: value for key, value in badge.items() if key != "slug"},
        )


def remove_default_badges(apps, schema_editor):
    Badge = apps.get_model("books", "Badge")
    Badge.objects.filter(
        slug__in=[badge["slug"] for badge in DEFAULT_BADGES]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("books", "0004_book_key_lessons_book_recap_video_url_and_more"),
    ]

    operations = [
        migrations.RunPython(create_default_badges, remove_default_badges),
    ]
