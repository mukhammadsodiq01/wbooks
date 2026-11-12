"""Create a small demo family and three complete stories.

Usage:
    python manage.py seed_demo

This is a thin alias for :mod:`seed_wbooks`, which holds the real demo
library, quizzes and badges.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed WBooks with a demo guardian, two readers and three stories."

    def handle(self, *args, **options):
        call_command("seed_wbooks", stdout=self.stdout)
